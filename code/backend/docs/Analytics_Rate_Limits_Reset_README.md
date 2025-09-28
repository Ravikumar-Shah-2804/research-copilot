# Analytics Rate Limits Reset Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/analytics/rate-limits/{user_id}/reset`

### HTTP Method
POST

### Description
This endpoint resets the rate limit counters for a specific user, clearing their current request count and allowing them to make new requests immediately. This is an administrative action to manually reset rate limits when needed.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations (though not directly used in this endpoint).
- Calls `search_rate_limiter.reset_rate_limit(user_id, "search")` from `src/services/rate_limiting.py` to reset rate limit counters.
- Uses Redis cache for storing and resetting rate limit counters.

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

### Path Parameters
- **user_id** (str, required): The identifier of the user whose rate limits are being reset.

### Content-Type
Not applicable (no request body).

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response is a simple confirmation message.

- **message** (str): Confirmation message indicating the rate limits have been reset, formatted as "Rate limits reset for user {user_id}".

### Example Response (JSON)
```json
{
  "message": "Rate limits reset for user user123"
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Not authorized" (or similar, depending on auth implementation).
- **Condition**: Triggered when the authenticated user is not an admin.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to reset rate limits: {str(e)}"
- **Condition**: Any exception raised during rate limit reset or Redis operations.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/analytics/rate-limits/user123/reset' -Method POST -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"}
```

### Valid Payload
No payload required for POST request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"message":"Rate limits reset for user user123"}
```

Note: The user_id in the URL should be replaced with an actual user identifier. This endpoint immediately resets the user's rate limit counters, allowing them to make new requests.