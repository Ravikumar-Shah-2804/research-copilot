# Analytics Rate Limits User Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/analytics/rate-limits/{user_id}`

### HTTP Method
GET

### Description
This endpoint retrieves the current rate limit status for a specific user, showing their current usage count, remaining requests, reset time, and limit information for search operations. It helps administrators monitor and manage user rate limiting.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations (though not directly used in this endpoint).
- Calls `search_rate_limiter.get_rate_limit_info(user_id, "search")` from `src/services/rate_limiting.py` to retrieve rate limit data.
- Uses Redis cache for storing and retrieving rate limit counters.

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
No request body is required for this GET endpoint.

### Path Parameters
- **user_id** (str, required): The identifier of the user whose rate limit status is being queried.

### Content-Type
Not applicable (no request body).

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response conforms to the rate limit info structure returned by `search_rate_limiter.get_rate_limit_info()`. All fields are dynamically generated based on current Redis cache state.

- **current_count** (int): Current number of requests made by the user in the current window.
- **remaining** (int): Number of requests remaining before hitting the rate limit (calculated as max(0, limit - current_count)).
- **reset_time** (float): Unix timestamp when the current rate limit window will reset.
- **limit** (int): Maximum number of requests allowed per window (typically 60 requests per minute for search operations).
- **window_seconds** (int): Length of the rate limit window in seconds (typically 60).

### Example Response (JSON)
```json
{
  "current_count": 15,
  "remaining": 45,
  "reset_time": 1696118400.0,
  "limit": 60,
  "window_seconds": 60
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Not authorized" (or similar, depending on auth implementation).
- **Condition**: Triggered when the authenticated user is not an admin.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to get rate limit info: {str(e)}"
- **Condition**: Any exception raised during rate limit info retrieval or Redis operations.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/analytics/rate-limits/user123' -Method GET -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"}
```

### Valid Payload
No payload required for GET request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"current_count":15,"remaining":45,"reset_time":1696118400.0,"limit":60,"window_seconds":60}
```

Note: The response values are dynamically generated based on the user's current rate limit state in Redis. The user_id in the URL should be replaced with an actual user identifier.