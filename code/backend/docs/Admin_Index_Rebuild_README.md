# Admin Index Rebuild Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/admin/index/rebuild` (assuming the admin router is mounted at `/api/v1/admin` in the main application; the endpoint is defined as `@router.post("/index/rebuild")`)

### HTTP Method
POST

### Description
This endpoint allows superuser administrators to initiate a rebuild of the search index. This operation checks the health of the OpenSearch cluster and initiates the index rebuilding process, which would typically involve creating new index mappings, re-indexing all documents from the database, and updating aliases. Currently implemented as a placeholder that validates cluster health.

### Dependencies
- Relies on `OpenSearchService` from `src/services/opensearch/client.py` for cluster health checks and index operations.
- The OpenSearch service handles connection management and provides cluster health monitoring.
- In a full implementation, this would also depend on database access for re-indexing documents.
- No database operations are performed in the current placeholder implementation.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_superuser` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is authenticated and active.
- The user must have superuser privileges (`current_user.is_superuser` must be `True`).

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_superuser` dependency, which internally uses `get_current_user` to decode and verify a JWT token).

## Authorization

### Requirements
- Only superusers can access this endpoint.
- The `get_current_superuser` dependency checks if `current_user.is_superuser` is `True`.
- Non-superusers will receive a 403 Forbidden response.

## Request

### Request Body Schema
No request body is required for this POST endpoint.

### Content-Type
Not applicable (no request body).

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response is a JSON object confirming the rebuild initiation.

- **message** (str): Confirmation message indicating the rebuild was initiated (value: "Search index rebuild initiated successfully").
- **status** (str): Current status of the rebuild operation (value: "in_progress").

### Example Response (JSON)
```json
{
  "message": "Search index rebuild initiated successfully",
  "status": "in_progress"
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Not enough permissions"
- **Condition**: Triggered when the authenticated user is not a superuser (checked by `get_current_superuser` dependency).

### 503 Service Unavailable
- **Status Code**: 503
- **Message**: "OpenSearch cluster is not healthy"
- **Condition**: Triggered when the OpenSearch cluster health status is not 'green' or 'yellow'.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to rebuild search index: {error_message}"
- **Condition**: Any exception during OpenSearch connection, health check, or other system errors.

## Testing Example

### Example Command
```bash
curl -X POST "http://localhost:8000/api/v1/admin/index/rebuild" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"
```

### Valid Payload
No payload required for POST request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"message":"Search index rebuild initiated successfully","status":"in_progress"}
```

Note: This operation initiates a search index rebuild process. In the current implementation, it only validates OpenSearch cluster health. A full implementation would perform actual re-indexing. Ensure OpenSearch is healthy before executing. The JWT token in the example is a placeholder and should be replaced with a valid superuser token.