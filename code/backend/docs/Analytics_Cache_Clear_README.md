# Analytics Cache Clear Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/analytics/cache/clear`

### HTTP Method
POST

### Description
This endpoint clears all cached search results from the Redis cache. This is an administrative action that can help resolve stale data issues or free up cache memory. The operation connects to Redis, clears the entire database, and then disconnects.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations (though not directly used in this endpoint).
- Uses `RedisCache` from `src/services/cache/client.py` to connect to and clear the Redis cache.
- Requires Redis to be available and properly configured.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `require_admin` dependency (from `src/services/auth.py`).
- The user must be an admin (superuser or have admin permissions).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `require_admin` dependency).

## Authorization

### Requirements
- Only admin users can access this endpoint.
- Non-admin users will receive a 403 Forbidden response.

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
The response is a simple confirmation message.

- **message** (str): Confirmation message indicating the cache has been cleared, formatted as "Search cache cleared".

### Example Response (JSON)
```json
{
  "message": "Search cache cleared"
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Not authorized" (or similar, depending on auth implementation).
- **Condition**: Triggered when the authenticated user is not an admin.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to clear cache: {str(e)}"
- **Condition**: Any exception raised during Redis connection, cache clearing, or disconnection operations.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/analytics/cache/clear' -Method POST -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"}
```

### Valid Payload
No payload required for POST request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"message":"Search cache cleared"}
```

Note: This endpoint clears the entire Redis database used for caching. Use with caution as it will remove all cached data, potentially impacting performance until the cache is repopulated.