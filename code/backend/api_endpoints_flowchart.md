# Research Copilot API Endpoints Flowchart

```mermaid
graph TD
    A[User Interaction] --> B{Authenticated?}

    B -->|No| C[Public Endpoints]
    B -->|Yes| D{Admin/Superuser?}

    C --> E[POST /auth/register<br/>User Registration]
    C --> F[POST /auth/token<br/>Login]
    C --> G[POST /auth/refresh<br/>Refresh Token]
    C --> H[GET /health/*<br/>Health Checks]
    C --> I[GET /ping/*<br/>Ping Endpoints]

    D -->|No| J[Regular User Endpoints]
    D -->|Yes| K[Admin Endpoints]

    J --> L[Papers Management]
    J --> M[Search & RAG]
    J --> N[API Keys Management]
    J --> O[Organization View]
    J --> P[Analytics View]
    J --> Q[Audit View]
    J --> R[Roles View]

    K --> S[Full Admin Access]
    K --> T[All Categories]

    L --> L1[POST /papers<br/>Create Paper]
    L --> L2[GET /papers<br/>List Papers]
    L --> L3[GET /papers/{id}<br/>Get Paper]
    L --> L4[PUT /papers/{id}<br/>Update Paper]
    L --> L5[DELETE /papers/{id}<br/>Delete Paper]
    L --> L6[POST /papers/{id}/upload<br/>Upload PDF]

    M --> M1[POST /search/text<br/>Text Search]
    M --> M2[POST /search/hybrid<br/>Hybrid Search]
    M --> M3[POST /search/rag<br/>RAG Query]
    M --> M4[GET /search/suggestions<br/>Search Suggestions]
    M --> M5[POST /rag/generate<br/>Generate Answer]
    M --> M6[POST /rag/stream<br/>Stream Answer]
    M --> M7[POST /rag/batch<br/>Batch Generate]

    N --> N1[POST /api-keys<br/>Create API Key]
    N --> N2[GET /api-keys<br/>List API Keys]
    N --> N3[GET /api-keys/{id}<br/>Get API Key]
    N --> N4[PUT /api-keys/{id}<br/>Update API Key]
    N --> N5[DELETE /api-keys/{id}<br/>Delete API Key]
    N --> N6[POST /api-keys/{id}/revoke<br/>Revoke API Key]

    O --> O1[GET /organizations<br/>List Orgs]
    O --> O2[GET /organizations/{id}<br/>Get Org]
    O --> O3[GET /organizations/{id}/users<br/>Org Users]

    P --> P1[GET /analytics/usage/user/{id}<br/>User Usage]
    P --> P2[GET /analytics/health<br/>System Health]

    Q --> Q1[GET /audit/logs<br/>Audit Logs]
    Q --> Q2[GET /audit/user/{id}/activity<br/>User Activity]

    R --> R1[GET /roles<br/>List Roles]
    R --> R2[GET /roles/permissions<br/>List Permissions]
    R --> R3[POST /roles/check-permission<br/>Check Permission]

    S --> S1[GET /admin/stats<br/>System Stats]
    S --> S2[POST /admin/cache/clear<br/>Clear Cache]
    S --> S3[GET /admin/health/detailed<br/>Detailed Health]
    S --> S4[GET /admin/logs<br/>System Logs]

    T --> T1[POST /organizations<br/>Create Org]
    T --> T2[DELETE /organizations/{id}<br/>Delete Org]
    T --> T3[POST /ingestion/arxiv<br/>Start Ingestion]
    T --> T4[GET /analytics/performance<br/>Performance Metrics]
    T --> T5[GET /audit/export<br/>Export Audit Logs]
    T --> T6[POST /roles/permissions<br/>Create Permission]
    T --> T7[POST /roles<br/>Create Role]
    T --> T8[POST /roles/users/assign-role<br/>Assign Role]

    style A fill:#e1f5fe
    style B fill:#fff3e0
    style C fill:#e8f5e8
    style D fill:#fff3e0
    style J fill:#f3e5f5
    style K fill:#ffebee
    style L fill:#e3f2fd
    style M fill:#e3f2fd
    style N fill:#e3f2fd
    style O fill:#e3f2fd
    style P fill:#e3f2fd
    style Q fill:#e3f2fd
    style R fill:#e3f2fd
    style S fill:#ffebee
    style T fill:#ffebee
```

## Authentication Flow Summary

- **Public Endpoints**: No authentication required
  - User registration and login
  - Token refresh
  - Health checks and ping

- **Regular User Endpoints**: Require authentication
  - Basic CRUD operations on papers
  - Search and RAG queries
  - API key management (organization-scoped)
  - Limited organization and analytics views
  - Personal audit logs and role checks

- **Admin/Superuser Endpoints**: Require elevated permissions
  - System administration (stats, cache, logs)
  - Full organization management
  - Ingestion job management
  - Advanced analytics and monitoring
  - Audit log export and cleanup
  - Role and permission management

## Key Decision Points

1. **Authentication Check**: Determines if user can access protected endpoints
2. **Authorization Check**: Determines if user has admin/superuser privileges for sensitive operations
3. **Organization Scoping**: Many endpoints check if user belongs to the relevant organization
4. **Permission Checks**: Specific resource-action permissions for fine-grained access control