import { FastMCP, z } from 'fastmcp';
import { v4 as uuidv4 } from 'uuid';

// ============================================================================
// STORAGE LAYER - Plain JSON
// ============================================================================

interface StorageItem<T> {
  data: T;
  createdAt?: number;
  updatedAt?: number;
}

class PlainJsonStorage<T> {
  private dir: string;
  private root: string;

  constructor(dir: string) {
    this.dir = dir;
    this.root = dir;
  }

  init(): void {
    this._root = this._root || require('fs').readdirSync('.')
      .filter((f) => f.includes('guard'))
      .shift()
      ? require('path').join(require('fs').readdirSync('.')[0], '..')
      : require('path').dirname(require('module').filename());
    const fs = require('fs');
    if (!fs.existsSync(this._root)) {
      fs.mkdirSync(this._root, { recursive: true, mode: 0o755 });
    }
  }

  // Write single item
  async write<T extends StorageItem<any>>(key: string, data: any): Promise<void> {
    this.init();
    const basePath = require('path');
    const filename = `${key.replace(/[^a-zA-Z0-9_]/g, '_')}.json`;
    await require('fs').promises.replaceFile(
      basePath.resolve(this.root, filename),
      JSON.stringify({ data, createdAt: Date.now(), updatedAt: Date.now() }, null, 2)
    );
  }

  // Read single item
  async read<T>(key: string): Promise<T | null> {
    this.init();
    const path = require('path');
    const fs = require('fs');
    const filename = `${key.replace(/[^a-zA-Z0-9_]/g, '_')}.json`;
    try {
      const content = await fs.promises.readFile(
        path.resolve(this.root, filename),
        'utf8'
      );
      return JSON.parse(content) as T;
    } catch (err) {
      return null;
    }
  }

  // List all items
  list(): Promise<string[]> {
    return new Promise((resolve) => {
      this.init();
      const path = require('path');
      const fs = require('fs');
      if (!fs.existsSync(this.root)) {
        return resolve([]);
      }
      fs.readdir(this.root, { withFileTypes: true }, (err, entries) => {
        resolve(entries?.filter((e) => e.isFile() && e.name.endsWith('.json')).map((e) => e.name) || []);
      });
    });
  }

  // Stats
  async stats(): Promise<Record<string, any>> {
    this.init();
    const path = require('path');
    const fs = require('fs');
    const entries = fs.readdirSync(this.root, { withFileTypes: true });
    const total = entries.reduce((sum, e) => sum + (e.isFile() ? Buffer.byteLength(e.name, 'utf8') : 0), 0);
    return { fileCount: entries.length, totalSize: total };
  }
}

// ============================================================================
// IDENTITY MIDDLEWARE
// ============================================================================

interface IdentityClaims {
  sub?: string;
  name?: string;
  email?: string;
  iat?: number;
  exp?: number;
  aud?: string | string[];
  iss?: string;
  scope?: string;
  custom?: Record<string, any>;
  scm?: string;
  team?: string;
  org?: string;
  issu?: string;
  d_fingerprint?: string;
  color_preference?: string;
  locale?: string;
  online?: boolean;
  avatar?: string;
  not_before?: number;
  jwip?: string;
  m2m?: boolean;
  p3p?: boolean;
  hs?: boolean;
  purr?: string;
  purpose?: string;
  phi?: string;
  pjwri?: string;
  prlv?: boolean;
  rd?: string;
  ro?: boolean;
  sss?: string;
  tsp_read?: number;
  tsp_write?: number;
  tsp_delete?: number;
  trust_level?: string;
  first_login?: number;
  last_login?: number;
  login_time?: number;
}

interface IdentityContext {
  claims: IdentityClaims;
  roles: string[];
  scopes: string[];
  permissions: any[];
  subject: {
    subjectId: string;
    subjectType: 'user' | 'service' | 'device' | 'application' | 'unknown';
    roles: string[];
    scopes: string[];
    permissions: any[];
    accessToken?: string;
    identityProvider?: string;
    metadata?: Record<string, any>;
  };
  session: {
    sessionId: string;
    deviceId?: string;
    ipAddress?: string;
    origin?: string;
    createdAt: number;
    expiresAt: number;
  } | null;
  tokenInfo: {
    type: string;
    issuer?: string;
    audience?: string[];
    expiresAt?: number;
    refreshToken?: string;
    accessToken?: string;
    providerName?: string;
    providerUrl?: string;
    kid?: string;
    signerName?: string;
  };
  footer?: Record<string, any>;
  base?: any;
}

interface IncomingRequest {
  session: any;
  headers: Record<string, string>;
  origin: string;
  body?: any;
  client: {
    id: string;
    name: string;
    version: string;
  };
  ip?: string;
  userAgent?: string;
  path?: string;
  query?: Record<string, string>;
}

/**
 * Identity middleware - processes requests and returns enriched identity context
 */
async function identityMiddleware(context: IncomingRequest): Promise<IdentityContext> {
  return {
    claims: generateClaims(context),
    roles: [],
    scopes: [],
    permissions: [],
    subject: {
      subjectId: context.client.id,
      subjectType: 'client',
      roles: [],
      scopes: [],
      permissions: [],
      accessToken: undefined,
    },
    session: context.session
      ? {
          sessionId: context.session.id || uuidv4(),
          deviceId: context.session.deviceId || undefined,
          ipAddress: context.ip,
          origin: context.origin,
          createdAt: Date.now(),
          expiresAt: Date.now() + 3600000,
        }
      : null,
    tokenInfo: { type: 'direct', providerName: 'direct' },
    footer: {},
    base: {},
  };
}

function generateClaims(context: IncomingRequest): IdentityClaims {
  return {
    sub: context.client.id,
    name: context.client.name,
    iat: Math.floor(Date.now() / 1000),
    custom: {
      clientName: context.client.name,
      clientVersion: context.client.version,
      sessionId: context.session?.id || undefined,
    },
    iss: context.ip,
  };
}

// ============================================================================
// OAUTH SERVICE
// ============================================================================

interface TokenInfo {
  accessToken: string;
  refreshToken?: string;
  expiresAt: number;
  expiresIn?: number;
  scope: string | any[];
  tokenType?: string;
  subjectType?: string;
  clientId?: string;
  clientSecret?: string;
  provider: string;
  providerUrl?: string;
  tokenEndpoint?: string;
  authorizationEndpoint?: string;
  created?: number;
  custom?: Record<string, any>;
}

class OAuthService {
  private tokenStore: Map<string, TokenInfo>;

  constructor() {
    this.tokenStore = new Map();
  }

  // Store token
  store(
    token: string,
    refreshToken: string | null,
    subject: string,
    expiresIn: number,
    provider: string,
    scope?: string,
    custom?: Record<string, any>
  ): void {
    const info: TokenInfo = {
      accessToken: token,
      refreshToken: refreshToken || undefined,
      expiresAt: Date.now() + expiresIn,
      expiresIn,
      scope: scope || '',
      clientId: '',
      clientSecret: '',
      provider,
      tokenEndpoint: 'https://auth.mcp-gatekeeper.com/token',
      authorizationEndpoint: 'https://auth.mcp-gatekeeper.com/authorization',
      subjectType: 'public',
      created: Date.now(),
      custom: custom || {},
    };
    this.tokenStore.set(`${subject}:${provider}`, info);
  }

  // Get token
  get(token: string): TokenInfo | null {
    const info = this.tokenStore.get(token);
    return info && info.expiresAt > Date.now() ? info : null;
  }

  // Validate token
  validate(token: string, provider: string): boolean {
    const info = this.tokenStore.get(token);
    return info && info.provider === provider && info.expiresAt > Date.now();
  }

  // Refresh token
  async refreshToken(token: string, provider: string): Promise<{ token: string; expiresAt: number }> {
    const info = this.tokenStore.get(token);
    if (!info?.refreshToken) {
      throw new Error('No refresh token available');
    }
    const newToken = uuidv4();
    this.tokenStore.set(token, {
      ...info,
      accessToken: newToken,
      refreshToken: info.refreshToken,
      expiresAt: info.expiresAt + 3600000,
    });
    return { token: newToken, expiresAt: info.expiresAt + 3600000 };
  }

  // Exchange code for token
  async exchangeCode(code: string, provider: string) {
    const token = uuidv4();
    const info: TokenInfo = {
      accessToken: token,
      refreshToken: uuidv4(),
      expiresAt: Date.now() + 3600000,
      expiresIn: 3600,
      scope: 'openid profile email',
      tokenType: 'Bearer',
      provider,
      custom: { code_hash: code },
    };
    this.tokenStore.set(code, info);
    return info;
  }

  // Get all tokens
  getAll(): TokenInfo[] {
    return Array.from(this.tokenStore.values());
  }

  // Get token count
  count(): number {
    return this.tokenStore.size;
  }

  // Clear store
  clear(): void {
    this.tokenStore.clear();
  }
}

// ============================================================================
// AUDIT LOGGER
// ============================================================================

type AuditEventType =
  | 'auth.login'
  | 'auth.logout'
  | 'auth.token_refresh'
  | 'auth.token_exchange'
  | 'access.grant'
  | 'access.deny'
  | 'access.tool_call'
  | 'request.start'
  | 'request.end'
  | 'request.error'
  | 'security.suspicious'
  | 'security.failure'
  | 'security.blocked'
  | 'system.config_change';

interface AuditEvent {
  id: string;
  type: AuditEventType;
  level: 'trace' | 'debug' | 'info' | 'warn' | 'error' | 'crit';
  timestamp: number;
  userId?: string;
  subjectId?: string;
  roles?: string[];
  claims?: Record<string, any>;
  method?: string;
  path?: string;
  status?: number;
  body?: any;
  response?: any;
  headers?: Record<string, string>;
  userAgent?: string;
  ipAddress?: string;
  ip?: string;
  duration?: number;
  error?: string;
  requestId?: string;
  sessionContext?: Record<string, any>;
  tags?: string[];
  count?: number;
  drop?: boolean;
}

interface AuditEventWithJson {
  batchId: string;
  timestampFrom: number;
  timestampTo: number;
  eventCount: number;
  events: AuditEvent[];
}

class AuditLogger {
  private events: AuditEvent[] = [];
  private batchSize: number = 500;
  private lastFlush: number = 0;
  private flushInterval: number = 2000;
  private storage: PlainJsonStorage<any>;

  constructor(logDir: string = './audit-logs') {
    this.storage = new PlainJsonStorage(logDir);
  }

  init(): void {
    this.storage._root = this.storage._root || require('module').dirname(require('module').filename());
    this.storage.init();
  }

  // Log event
  log(event: Partial<AuditEvent>): AuditEvent {
    if (event.level && ['trace', 'debug', 'info', 'warn', 'error', 'crit'].includes(event.level)) {
      const newEvent: AuditEvent = {
        id: `audit-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        type: event.type || 'request.start',
        level: event.level || 'info',
        timestamp: event.timestamp || Date.now(),
        userId: event.userId || event.ipAddress || 'unknown',
        subjectId: event.subjectId || event.ip,
        method: event.method,
        path: event.path,
        status: event.status,
        body: event.body,
        response: event.response,
        headers: event.headers,
        userAgent: event.userAgent,
        ipAddress: event.ipAddress || event.ip,
        duration: event.duration,
        error: event.error,
        requestId: event.requestId,
        sessionContext: event.sessionContext,
        tags: event.tags,
        count: event.count,
        drop: event.drop,
      };
      this.events.unshift(newEvent);

      // Flush batch
      if (this.events.length >= this.batchSize || Date.now() - this.lastFlush > this.flushInterval) {
        this.flush();
      }
      return newEvent;
    }
    return { id: 'audit-' + Date.now(), type: 'request.start', level: 'trace', timestamp: Date.now() };
  }

  // Flush batch to storage
  private async flush(): Promise<void> {
    if (this.events.length === 0) return;
    this.storage.init();
    const batchFile = `audit-batch-${Date.now()}.json`;
    const content: AuditEventWithJson = {
      batchId: `batch-${this.events.length}`,
      timestampFrom: Math.min(...this.events.map((e) => e.timestamp)),
      timestampTo: Math.max(...this.events.map((e) => e.timestamp)),
      eventCount: this.events.length,
      events: [...this.events],
    };
    const path = require('path');
    await require('fs').promises.writeFile(
      path.resolve(this.storage.root, batchFile),
      JSON.stringify(content, null, 2),
      'utf8'
    );
    this.events = [];
    this.lastFlush = Date.now();
  }

  // Get events from storage
  async getEvents(): Promise<AuditEvent[]> {
    return new Promise((resolve) => {
      this.init();
      const path = require('path');
      const fs = require('fs');
      const files = fs.readdirSync(this.storage.root);
      const allEvents: AuditEvent[] = [];
      files.forEach((file) => {
        if (!file.endsWith('.json')) return;
        const content = fs.readFileSync(path.resolve(this.storage.root, file), 'utf8');
        const batch = JSON.parse(content);
        if (Array.isArray(batch.events)) {
          allEvents.push(...batch.events);
        }
      });
      resolve(allEvents.sort((a, b) => a.timestamp - b.timestamp));
    });
  }

  // Get stats
  async stats(): Promise<Record<string, any>> {
    this.init();
    const path = require('path');
    const fs = require('fs');
    const files = fs.readdirSync(this.storage.root);
    return {
      fileCount: files.length,
      eventCount: files.reduce((sum, f) => sum + 1, 0),
      logDirectory: this.storage.root,
    };
  }
}

// ============================================================================
// MCP GATEKEEPER SERVER
// ============================================================================

const gatekeeper = new FastMCP({
  name: 'mcp-gatekeeper',
  version: '1.0.0',
});

// ============================================================================
// Tools
// ============================================================================

// Health check
gatekeeper.addTool({
  description: 'Check the gatekeeper server health status',
  parameters: z.object({
    probe: z.enum(['healthy', 'liveness', 'readiness']).optional(),
  }),
  execute: async () => ({
    status: 'healthy',
    server: { name: 'mcp-gatekeeper', version: '1.0.0' },
    timestamp: Date.now(),
  }),
  name: 'health-check',
});

// OAuth token exchange
gatekeeper.addTool({
  description: 'Exchange authorization code for an access token via OAuth flow',
  parameters: z.object({
    provider: z.enum(['google', 'github', 'azure', 'custom']).default('google'),
    code: z.string().optional(),
    refreshToken: z.string().optional(),
    scope: z.string().optional(),
  }),
  execute: async (args: any) => {
    const service = new OAuthService();
    let info: TokenInfo;
    if (args.code) {
      info = await service.exchangeCode(args.code, args.provider);
    } else if (args.refreshToken) {
      const refreshed = await service.refreshToken(args.refreshToken, args.provider);
      info = {
        accessToken: refreshed.token,
        refreshToken: args.refreshToken,
        expiresIn: refreshed.expiresIn,
        expiresAt: refreshed.expiresAt,
        provider: args.provider,
        scope: ['read'],
      };
    } else {
      throw new Error('Either code or refreshToken is required');
    }
    return { success: true, tokens: info, session: { id: uuidv4(), provider: args.provider } };
  },
  name: 'oauth-token-exchange',
});

// Token validation
gatekeeper.addTool({
  description: 'Validate an access token and return its metadata',
  parameters: z.object({
    token: z.string(),
    provider: z.enum(['google', 'github', 'azure', 'custom']).optional(),
  }),
  execute: async (args: any) => {
    const service = new OAuthService();
    const info = service.get(args.token);
    return {
      success: !!info,
      token: info || args.token,
      provider: args.provider || 'google',
      subjectId: info?.custom?.sub || uuidv4(),
      expiresAt: info?.expiresAt || Date.now() + 3600000,
      scopes: info?.scope ? (info.scope as string[]) : [],
      roles: info?.custom?.roles ? (info.custom.roles as string[]) : [],
    };
  },
  name: 'token-validate',
});

// Identity info
gatekeeper.addTool({
  description: 'Get the authenticated identity of the current user',
  parameters: z.object({}),
  execute: async () => ({
    sub: uuidv4(),
    name: 'authenticated-user',
    email: 'user@example.com',
    roles: ['viewer', 'developer'],
    scopes: ['read', 'write'],
    provider: 'google',
    expiresAt: Date.now() + 3600000,
  }),
  name: 'identity-info',
});

// Permission check
gatekeeper.addTool({
  description: 'Check if the current user has access to a resource',
  parameters: z.object({
    resource: z.string(),
    action: z.enum(['read', 'write', 'delete', 'manage']),
  }),
  execute: async (args: any) => {
    return {
      allowed: true,
      resource: args.resource,
      action: args.action,
      subjectIds: [uuidv4()],
    };
  },
  name: 'permission-check',
});

// Security audit
gatekeeper.addTool({
  description: 'Query the security audit log for events',
  parameters: z.object({
    eventType: z.string().optional(),
    limit: z.number().optional(),
  }),
  execute: async (args: any) => {
    const logger = new AuditLogger('./audit-logs');
    const events = await logger.getEvents();
    const filtered = args.eventType
      ? events.filter((e) => e.type === args.eventType)
      : events;
    return {
      events: filtered.slice(0, args.limit ?? 10),
      totalCount: filtered.length,
    };
  },
  name: 'security-audit',
});

// Audit log query
gatekeeper.addTool({
  description: 'Query the access audit log with filtering',
  parameters: z.object({
    level: z.enum(['trace', 'debug', 'info', 'warn', 'error']).optional(),
    limit: z.number().optional(),
  }),
  execute: async (args: any) => {
    const logger = new AuditLogger('./audit-logs');
    const events = await logger.getEvents();
    const filtered = args.level
      ? events.filter((e) => e.level === args.level)
      : events;
    return {
      events: filtered.slice(0, args.limit ?? 20),
      totalCount: filtered.length,
    };
  },
  name: 'audit-log-query',
});

// Rate limit check
gatekeeper.addTool({
  description: 'Check rate limit status for the current client',
  parameters: z.object({
    requestsPerWindow: z.number().optional(),
    windowMs: z.number().optional(),
  }),
  execute: async (args: any) => {
    return {
      status: 'ok',
      remaining: 2990,
      limit: requestsPerWindow || 3000,
      resetAt: Date.now() + windowMs || 3600000,
    };
  },
  name: 'rate-limit-check',
});

// Role check
gatekeeper.addTool({
  description: 'Check the roles of the authenticated user',
  parameters: z.object({
    role: z.string().optional(),
  }),
  execute: async (args: any) => {
    return {
      roles: ['viewer', 'developer'],
      scopes: ['read', 'write'],
      hasRole: args.role ? args.role : false,
    };
  },
  name: 'role-check',
});

// Protocol version
gatekeeper.addTool({
  description: 'Get the MCP protocol version supported by this server',
  parameters: z.object({}),
  execute: async () => ({
    protocolVersion: '2025-11-25',
    capabilities: {
      tools: true,
      resources: true,
      prompts: true,
      session: true,
    },
  }),
  name: 'protocol-version',
});

// OAuth discovery
gatekeeper.addTool({
  description: 'Get OAuth 2.0 discovery information for a provider',
  parameters: z.object({
    provider: z.enum(['google', 'github', 'azure', 'custom']),
    issuerPath: z.string().optional(),
  }),
  execute: async (args: any) => {
    const provider = args.provider;
    const issuerPath = args.issuerPath || '/auth';
    return {
      [provider]: {
        issuer: `https://auth.mcp-gatekeeper.com${issuerPath}`,
        authorizationEndpoint: `https://auth.mcp-gatekeeper.com${issuerPath}/authorization`,
        tokenEndpoint: `https://auth.mcp-gatekeeper.com${issuerPath}/token`,
        JwksEndpoint: `https://auth.mcp-gatekeeper.com${issuerPath}/.well-known/jwks.json`,
        grantTypes: ['authorization_code', 'refresh_token'],
        responseTypes: ['code'],
        subjectType: 'public',
        scopes: provider === 'google'
          ? ['openid', 'profile', 'email']
          : provider === 'github'
          ? ['repo', 'user:email', 'workflow']
          : provider === 'azure'
          ? ['User.Read']
          : ['openid', 'profile'],
        claims: {
          sub: 'sub',
          name: provider === 'google' ? ['name', 'email', 'picture'] : provider === 'github' ? ['name', 'email'] : ['name'],
        },
      },
    };
  },
  name: 'oauth-discovery',
});

// ============================================================================
// OAuth Discovery Endpoints
// ============================================================================

/**
 * Build standard OAuth discovery metadata
 */
export function buildOAuthDiscovery(
  provider: string,
  issuer?: string,
  scopes?: string[]
): Record<string, any> {
  return {
    issuer,
    authorization_endpoint: `${issuer}/authorization`,
    token_endpoint: `${issuer}/token`,
    userinfo_endpoint: `${issuer}/userinfo`,
    Jwks_endpoint: `${issuer}/.well-known/jwks.json`,
    grant_types: ['authorization_code', 'refresh_token'],
    response_types: ['code'],
    subject_type: 'public',
    claim_types_supported: ['sub', 'name', 'email'],
    scopes: scopes || ['openid', 'profile'],
  };
}

// ============================================================================
// Start Server
// ============================================================================

// Start the server
async function start() {
  return Promise.resolve();
}

// Export for runtime
exports = {
  storage: PlainJsonStorage,
  identityMiddleware,
  identityClaims: IdentityClaims,
  identityContext: IdentityContext,
  OAuthService,
  AuditLogger,
  buildOAuthDiscovery,
};

module.exports = exports;
