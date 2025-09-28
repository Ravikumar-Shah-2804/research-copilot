# Admin Cache Clear Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/admin/cache/clear` (assuming the admin router is mounted at `/api/v1/admin` in the main application; the endpoint is defined as `@router.post("/cache/clear")`)

### HTTP Method
POST

### Description
This endpoint allows superuser administrators to clear all cached data in the Redis cache system. This operation removes all cached entries to ensure data freshness and can be useful for troubleshooting cache-related issues or forcing fresh data retrieval.

### Dependencies
- Relies on `RedisCache` from `src/services/cache/client.py` for cache operations.
- The cache service handles connection management and provides a `clear()` method to flush all cache entries.
- No database operations are performed for this endpoint.

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
The response is a simple JSON object with a success message.

- **message** (str): Confirmation message indicating the cache was cleared successfully (value: "Cache cleared successfully").

### Example Response (JSON)
```json
{
  "message": "Cache cleared successfully"
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Not enough permissions"
- **Condition**: Triggered when the authenticated user is not a superuser (checked by `get_current_superuser` dependency).

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to clear cache: {error_message}"
- **Condition**: Any exception during Redis connection, cache clearing operation, or other system errors.

## Testing Example

### Example Command
```bash
curl -X POST "http://localhost:8000/api/v1/admin/cache/clear" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"
```

### Valid Payload
No payload required for POST request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"message":"Cache cleared successfully"}
```

Note: This operation will clear all cached data in Redis. Ensure this is intended before executing in production. The JWT token in the example is a placeholder and should be replaced with a valid superuser token.