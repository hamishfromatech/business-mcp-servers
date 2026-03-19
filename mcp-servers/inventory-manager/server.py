"""
Inventory Manager MCP Server
A FastMCP server for managing inventory, stock, and product tracking.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json
from enum import Enum
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="Inventory Manager",
    instructions="An inventory management server for tracking products, stock levels, and inventory movements."
)


class MovementType(str, Enum):
    IN = "in"
    OUT = "out"
    TRANSFER = "transfer"


class Product(BaseModel):
    """A product in inventory."""
    id: int
    name: str
    sku: str
    quantity: int
    price: float
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    low_stock_threshold: int = 10
    description: Optional[str] = None
    created_at: str
    updated_at: str


class Category(BaseModel):
    """A product category."""
    id: int
    name: str
    description: Optional[str] = None
    created_at: str


class Location(BaseModel):
    """A storage location."""
    id: int
    name: str
    description: Optional[str] = None
    created_at: str


class Movement(BaseModel):
    """An inventory movement record."""
    id: int
    type: str
    product_id: int
    product_name: str
    quantity: int
    notes: Optional[str] = None
    to_location_id: Optional[int] = None
    created_at: str


class Alert(BaseModel):
    """A low stock alert."""
    id: int
    type: str
    product_id: int
    product_name: str
    current_quantity: int
    threshold: int
    created_at: str
    resolved: bool = False

# Data persistence setup
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "inventory.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "products": {}, "categories": {}, "locations": {}, "movements": {}, "alerts": {},
        "next_product_id": 1, "next_category_id": 1, "next_location_id": 1,
        "next_movement_id": 1, "next_alert_id": 1
    }


def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# Initialize data
_data = _load_data()
products: dict[int, dict] = {int(k): v for k, v in _data.get("products", {}).items()}
categories: dict[int, dict] = {int(k): v for k, v in _data.get("categories", {}).items()}
locations: dict[int, dict] = {int(k): v for k, v in _data.get("locations", {}).items()}
movements: dict[int, dict] = {int(k): v for k, v in _data.get("movements", {}).items()}
alerts: dict[int, dict] = {int(k): v for k, v in _data.get("alerts", {}).items()}

_next_product_id = _data.get("next_product_id", 1)
_next_category_id = _data.get("next_category_id", 1)
_next_location_id = _data.get("next_location_id", 1)
_next_movement_id = _data.get("next_movement_id", 1)
_next_alert_id = _data.get("next_alert_id", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "products": products, "categories": categories, "locations": locations,
        "movements": movements, "alerts": alerts,
        "next_product_id": _next_product_id, "next_category_id": _next_category_id,
        "next_location_id": _next_location_id, "next_movement_id": _next_movement_id,
        "next_alert_id": _next_alert_id
    })


def _get_next_product_id() -> int:
    global _next_product_id
    id_ = _next_product_id
    _next_product_id += 1
    return id_


def _get_next_category_id() -> int:
    global _next_category_id
    id_ = _next_category_id
    _next_category_id += 1
    return id_


def _get_next_location_id() -> int:
    global _next_location_id
    id_ = _next_location_id
    _next_location_id += 1
    return id_


def _get_next_movement_id() -> int:
    global _next_movement_id
    id_ = _next_movement_id
    _next_movement_id += 1
    return id_


def _get_next_alert_id() -> int:
    global _next_alert_id
    id_ = _next_alert_id
    _next_alert_id += 1
    return id_


def _check_low_stock(product_id: int) -> Optional[dict]:
    """Check if product is below threshold and create alert if needed."""
    if product_id not in products:
        return None

    product = products[product_id]
    threshold = product.get("low_stock_threshold", 0)

    if product["quantity"] <= threshold:
        # Check if alert already exists
        for alert in alerts.values():
            if (alert["product_id"] == product_id and
                alert["type"] == "low_stock" and
                not alert.get("resolved")):
                return None

        alert_id = _get_next_alert_id()
        alert = {
            "id": alert_id,
            "type": "low_stock",
            "product_id": product_id,
            "product_name": product["name"],
            "current_quantity": product["quantity"],
            "threshold": threshold,
            "created_at": datetime.now().isoformat(),
            "resolved": False
        }
        alerts[alert_id] = alert
        _save()
        return alert

    return None


# Category Management
@mcp.tool
def create_category(name: str, description: Optional[str] = None) -> Category:
    """Create a product category.

    Args:
        name: Category name
        description: Category description

    Returns:
        The created category
    """
    category_id = _get_next_category_id()
    category = Category(
        id=category_id,
        name=name,
        description=description,
        created_at=datetime.now().isoformat()
    )
    categories[category_id] = category.model_dump()
    _save()
    return category


@mcp.tool
def list_categories() -> list[Category]:
    """List all categories.

    Returns:
        List of categories
    """
    return [Category(**c) for c in categories.values()]


# Location Management
@mcp.tool
def create_location(name: str, description: Optional[str] = None) -> Location:
    """Create a storage location.

    Args:
        name: Location name
        description: Location description

    Returns:
        The created location
    """
    location_id = _get_next_location_id()
    location = Location(
        id=location_id,
        name=name,
        description=description,
        created_at=datetime.now().isoformat()
    )
    locations[location_id] = location.model_dump()
    _save()
    return location


@mcp.tool
def list_locations() -> list[Location]:
    """List all storage locations.

    Returns:
        List of locations
    """
    return [Location(**loc) for loc in locations.values()]


# Product Management
@mcp.tool
def create_product(
    name: str,
    sku: str,
    quantity: int = 0,
    price: float = 0.0,
    category_id: Optional[int] = None,
    location_id: Optional[int] = None,
    low_stock_threshold: int = 10,
    description: Optional[str] = None
) -> Product:
    """Create a new product.

    Args:
        name: Product name
        sku: Stock keeping unit (unique identifier)
        quantity: Initial quantity in stock
        price: Product price
        category_id: Optional category ID
        location_id: Optional storage location ID
        low_stock_threshold: Quantity below which to alert
        description: Product description

    Returns:
        The created product
    """
    # Check for duplicate SKU
    for p in products.values():
        if p["sku"] == sku:
            raise ValueError(f"Product with SKU {sku} already exists")

    product_id = _get_next_product_id()
    product = Product(
        id=product_id,
        name=name,
        sku=sku,
        quantity=quantity,
        price=price,
        category_id=category_id,
        location_id=location_id,
        low_stock_threshold=low_stock_threshold,
        description=description,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    products[product_id] = product.model_dump()

    # Check for low stock alert
    _check_low_stock(product_id)
    _save()

    return product


@mcp.tool
def get_product(product_id: int) -> Optional[Product]:
    """Get a product by ID.

    Args:
        product_id: The product ID

    Returns:
        Product details or None
    """
    if product_id in products:
        return Product(**products[product_id])
    return None


@mcp.tool
def get_product_by_sku(sku: str) -> Optional[Product]:
    """Get a product by SKU.

    Args:
        sku: The product SKU

    Returns:
        Product details or None
    """
    for product in products.values():
        if product["sku"] == sku:
            return Product(**product)
    return None


@mcp.tool
def update_product(
    product_id: int,
    name: Optional[str] = None,
    price: Optional[float] = None,
    category_id: Optional[int] = None,
    location_id: Optional[int] = None,
    low_stock_threshold: Optional[int] = None,
    description: Optional[str] = None
) -> Optional[Product]:
    """Update a product.

    Args:
        product_id: The product ID
        name: New name
        price: New price
        category_id: New category
        location_id: New location
        low_stock_threshold: New threshold
        description: New description

    Returns:
        Updated product or None
    """
    if product_id not in products:
        return None

    product = products[product_id]
    if name is not None:
        product["name"] = name
    if price is not None:
        product["price"] = price
    if category_id is not None:
        product["category_id"] = category_id
    if location_id is not None:
        product["location_id"] = location_id
    if low_stock_threshold is not None:
        product["low_stock_threshold"] = low_stock_threshold
    if description is not None:
        product["description"] = description

    product["updated_at"] = datetime.now().isoformat()
    _save()
    return Product(**product)


@mcp.tool
def delete_product(product_id: int) -> bool:
    """Delete a product.

    Args:
        product_id: The product ID

    Returns:
        True if deleted, False if not found
    """
    if product_id in products:
        del products[product_id]
        _save()
        return True
    return False


@mcp.tool
def list_products(
    category_id: Optional[int] = None,
    location_id: Optional[int] = None,
    low_stock_only: bool = False
) -> list[Product]:
    """List products with optional filters.

    Args:
        category_id: Filter by category
        location_id: Filter by location
        low_stock_only: Only show products below threshold

    Returns:
        List of products
    """
    result = list(products.values())

    if category_id is not None:
        result = [p for p in result if p.get("category_id") == category_id]
    if location_id is not None:
        result = [p for p in result if p.get("location_id") == location_id]
    if low_stock_only:
        result = [p for p in result if p["quantity"] <= p.get("low_stock_threshold", 0)]

    return [Product(**p) for p in result]


@mcp.tool
def search_products(query: str) -> list[Product]:
    """Search products by name, SKU, or description.

    Args:
        query: Search term

    Returns:
        List of matching products
    """
    query_lower = query.lower()
    return [
        Product(**p) for p in products.values()
        if (query_lower in p["name"].lower() or
            query_lower in p["sku"].lower() or
            (p.get("description") and query_lower in p["description"].lower()))
    ]


# Inventory Movement
@mcp.tool
def stock_in(product_id: int, quantity: int, notes: Optional[str] = None) -> Movement:
    """Add stock to a product.

    Args:
        product_id: The product ID
        quantity: Quantity to add
        notes: Optional notes

    Returns:
        Movement record
    """
    if product_id not in products:
        raise ValueError(f"Product {product_id} not found")

    if quantity <= 0:
        raise ValueError("Quantity must be positive")

    product = products[product_id]
    product["quantity"] += quantity
    product["updated_at"] = datetime.now().isoformat()

    movement_id = _get_next_movement_id()
    movement = Movement(
        id=movement_id,
        type=MovementType.IN.value,
        product_id=product_id,
        product_name=product["name"],
        quantity=quantity,
        notes=notes,
        to_location_id=None,
        created_at=datetime.now().isoformat()
    )
    movements[movement_id] = movement.model_dump()
    _save()

    return movement


@mcp.tool
def stock_out(product_id: int, quantity: int, notes: Optional[str] = None) -> Movement:
    """Remove stock from a product.

    Args:
        product_id: The product ID
        quantity: Quantity to remove
        notes: Optional notes

    Returns:
        Movement record
    """
    if product_id not in products:
        raise ValueError(f"Product {product_id} not found")

    if quantity <= 0:
        raise ValueError("Quantity must be positive")

    product = products[product_id]
    if product["quantity"] < quantity:
        raise ValueError(f"Insufficient stock. Available: {product['quantity']}")

    product["quantity"] -= quantity
    product["updated_at"] = datetime.now().isoformat()

    movement_id = _get_next_movement_id()
    movement = Movement(
        id=movement_id,
        type=MovementType.OUT.value,
        product_id=product_id,
        product_name=product["name"],
        quantity=quantity,
        notes=notes,
        to_location_id=None,
        created_at=datetime.now().isoformat()
    )
    movements[movement_id] = movement.model_dump()

    # Check for low stock
    _check_low_stock(product_id)
    _save()

    return movement


@mcp.tool
def transfer_stock(product_id: int, to_location_id: int, quantity: int, notes: Optional[str] = None) -> Movement:
    """Transfer stock between locations.

    Args:
        product_id: The product ID
        to_location_id: Destination location ID
        quantity: Quantity to transfer
        notes: Optional notes

    Returns:
        Movement record
    """
    if product_id not in products:
        raise ValueError(f"Product {product_id} not found")
    if to_location_id not in locations:
        raise ValueError(f"Location {to_location_id} not found")

    product = products[product_id]
    product["location_id"] = to_location_id
    product["updated_at"] = datetime.now().isoformat()

    movement_id = _get_next_movement_id()
    movement = Movement(
        id=movement_id,
        type=MovementType.TRANSFER.value,
        product_id=product_id,
        product_name=product["name"],
        quantity=quantity,
        notes=notes,
        to_location_id=to_location_id,
        created_at=datetime.now().isoformat()
    )
    movements[movement_id] = movement.model_dump()
    _save()

    return movement


@mcp.tool
def get_movement_history(product_id: Optional[int] = None, limit: int = 50) -> list[Movement]:
    """Get inventory movement history.

    Args:
        product_id: Optional filter by product
        limit: Maximum number of records

    Returns:
        List of movements
    """
    result = list(movements.values())

    if product_id is not None:
        result = [m for m in result if m.get("product_id") == product_id]

    result.sort(key=lambda x: x["created_at"], reverse=True)
    return [Movement(**m) for m in result[:limit]]


# Alerts
@mcp.tool
def get_active_alerts() -> list[Alert]:
    """Get all active (unresolved) alerts.

    Returns:
        List of active alerts
    """
    return [Alert(**a) for a in alerts.values() if not a.get("resolved")]


@mcp.tool
def resolve_alert(alert_id: int) -> Optional[Alert]:
    """Mark an alert as resolved.

    Args:
        alert_id: The alert ID

    Returns:
        Resolved alert or None
    """
    if alert_id not in alerts:
        return None

    alerts[alert_id]["resolved"] = True
    alerts[alert_id]["resolved_at"] = datetime.now().isoformat()
    _save()
    return Alert(**alerts[alert_id])


# Analytics
@mcp.tool
def get_inventory_summary() -> dict:
    """Get overall inventory summary.

    Returns:
        Summary with counts and values
    """
    total_products = len(products)
    total_quantity = sum(p["quantity"] for p in products.values())
    total_value = sum(p["quantity"] * p.get("price", 0) for p in products.values())
    low_stock_count = len([p for p in products.values() if p["quantity"] <= p.get("low_stock_threshold", 0)])

    return {
        "total_products": total_products,
        "total_quantity": total_quantity,
        "total_value": round(total_value, 2),
        "low_stock_count": low_stock_count,
        "categories": len(categories),
        "locations": len(locations)
    }


# Resources
@mcp.resource("inventory://summary")
def get_inventory_summary_resource() -> str:
    """Resource showing inventory summary."""
    summary = get_inventory_summary()

    lines = ["# Inventory Summary\n"]
    lines.append(f"- **Total Products:** {summary['total_products']}")
    lines.append(f"- **Total Items:** {summary['total_quantity']}")
    lines.append(f"- **Total Value:** ${summary['total_value']:,.2f}")
    lines.append(f"- **Low Stock Alerts:** {summary['low_stock_count']}")
    lines.append(f"- **Categories:** {summary['categories']}")
    lines.append(f"- **Locations:** {summary['locations']}")

    return "\n".join(lines)


@mcp.resource("inventory://low-stock")
def get_low_stock_resource() -> str:
    """Resource showing low stock products."""
    low_stock = list_products(low_stock_only=True)

    if not low_stock:
        return "# Low Stock Products\n\nNo products below threshold."

    lines = ["# Low Stock Products\n"]
    for p in low_stock:
        lines.append(f"- **{p['name']}** (SKU: {p['sku']})")
        lines.append(f"  - Quantity: {p['quantity']} (threshold: {p['low_stock_threshold']})")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()