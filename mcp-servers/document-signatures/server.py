"""
Document Signatures / E-Signatures MCP Server
A FastMCP server for digital contracts, signature requests, signers,
approval tracking, compliance, and signing status.
"""

from base64 import standard_b64encode as b64encode
from base64 import standard_b64decode as b64decode
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from enum import Enum
import json
import os
import shutil
import atexit
import tempfile
import threading
from pydantic import BaseModel, field_validator
from fastmcp import FastMCP

mcp = FastMCP(
    name="Document Signatures",
    instructions=(
        "A document signatures server for tracking digital contracts, "
        "signature requests, signers, approval workflows, compliance "
        "timestamps, and signing status."
    ),
)


# ============================================================
# Enums
# ============================================================

class RequestStatus(str, Enum):
    """Status of a sign request."""
    DRAFT = "draft"           # Draft stage, approval not yet needed
    PENDING_APPROVAL = "pending_approval"  # Awaiting approval
    APPROVED = "approved"         # Approved
    REJECTED = "rejected"         # Rejected
    PENDING_SIGNATURES = "pending_signatures"  # Pending all signatures
    IN_PROGRESS = "in_progress"   # Signers actively signing
    COMPLETED = "completed"       # All signatures obtained
    EXPIRED = "expired"           # Deadline passed
    CANCELLED = "cancelled"       # Request cancelled


class ApproverStatus(str, Enum):
    """Status of an approver."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SignerStatus(str, Enum):
    """Status of a signer."""
    PENDING = "pending"
    SIGNED = "signed"
    REJECTED = "rejected"


class SigningMethod(str, Enum):
    """Methods of signing a document."""
    ELECTRONIC = "electronic"       # Standard e-signature (image text)
    DIGITAL_CERTIFICATE = "digital_certificate"  # PKCS#12 / PFX certificate
    IMPRESSION = "impression"       # Biometrics, seal impression


class SigningOrder(str, Enum):
    """Order of signers."""
    SEQUENTIAL = "sequential"       # Each must sign after the previous
    PARALLEL = "parallel"          # All may sign simultaneously


# ============================================================
# Pydantic Models
# ============================================================

class SignerRequest(BaseModel):
    """A request from a person to sign a document."""
    name: str
    email: str
    signing_order: Optional[int] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("email")
    @classmethod
    def email_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Email cannot be empty")
        return v.strip()


class ApproverRequest(BaseModel):
    """A request from an approver."""
    name: str
    email: str
    required: bool = False
    department: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("email")
    @classmethod
    def email_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Email cannot be empty")
        return v.strip()


class SignatureStep(BaseModel):
    """A single signer or approver step in a workflow."""
    id: int
    name: str
    email: str
    role: str           # "signer" or "approver"
    required: bool = False
    department: Optional[str] = None
    signing_order: Optional[int] = None
    status: str = "pending"
    signed_at: Optional[str] = None
    signing_method: Optional[SigningMethod] = None
    digital_certificate_data: Optional[str] = None
    signature_image_base64: Optional[str] = None
    passthrough_declaration: Optional[str] = None
    rejected_at: Optional[str] = None
    rejection_reason: Optional[str] = None


class ComplianceRecord(BaseModel):
    """Compliance timestamps and evidence for a signature request."""
    request_id: int
    created_at: str
    capture_method: str = "automatic"
    e_sign_timestamp: Optional[str] = None
    filled_at: Optional[str] = None
    irsa_compliant: bool = True
    is_tamper_evident: bool = True
    certificate_serial: Optional[str] = None


class DocumentSignRequest(BaseModel):
    """A sign request — the main entity."""
    id: int
    title: str
    document_type: str
    document_content: str
    description: Optional[str] = None
    requested_by: str
    approvers: list = []
    signers: list = []
    signing_order: str = SigningOrder.SEQUENTIAL.value
    deadline: Optional[str] = None
    status: str = RequestStatus.DRAFT.value
    approval_status: Optional[str] = None
    signatures_status: Optional[str] = None
    compliance: ComplianceRecord
    created_at: str
    updated_at: str

    @field_validator("document_content")
    @classmethod
    def content_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Document content cannot be empty")
        return v.strip()

    @field_validator("requested_by")
    @classmethod
    def requested_by_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Requested by cannot be empty")
        return v.strip()