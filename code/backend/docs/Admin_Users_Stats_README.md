# Admin Users Stats Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/admin/users/stats` (assuming the admin router is mounted at `/api/v1/admin` in the main application; the endpoint is defined as `@router.get("/users/stats")`)

### HTTP Method
GET

### Description
This endpoint allows superuser administrators to retrieve detailed user statistics including active user counts, new user registrations, top search queries, and user activity trends. The endpoint analyzes user login patterns and search behavior to provide insights into user engagement and system usage.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations to query user login times, registration dates, and audit logs.
- Uses SQLAlchemy for complex queries including date filtering and aggregation.
- Uses Pydantic schemas from `src/schemas/admin.py` for response validation.

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
No request body is required for this GET endpoint.

### Content-Type
Not applicable (no request body).

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response conforms to the `UserStats` schema (from `src/schemas/admin.py`). All fields are calculated dynamically from database queries.

- **active_users** (int): Number of users who have logged in within the last 24 hours (queried by filtering User.last_login >= yesterday).
- **new_users_today** (int): Number of users who registered today (queried by filtering User.created_at >= today at 00:00:00 UTC).
- **top_search_queries** (Dict[str, int]): Dictionary mapping search query strings to their frequency counts (aggregated from AuditLog entries with action 'search_perform', limited to top 10).
- **user_activity_trends** (Dict[str, Any]): User activity trend data including daily active users (placeholder array), weekly registrations (placeholder array), and timestamp (current UTC time in ISO format).

### Example Response (JSON)
```json
{
  "active_users": 150,
  "new_users_today": 12,
  "top_search_queries": {
    "machine learning": 450,
    "neural networks": 320,
    "quantum computing": 280,
    "artificial intelligence": 250,
    "deep learning": 200
  },
  "user_activity_trends": {
    "daily_active_users": [145, 152, 148, 160, 155, 162, 150],
    "weekly_registrations": [8, 15, 12, 18],
    "timestamp": "2023-10-01T12:00:00Z"
  }
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Not enough permissions"
- **Condition**: Triggered when the authenticated user is not a superuser (checked by `get_current_superuser` dependency).

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to retrieve user stats: {error_message}"
- **Condition**: Any exception during database queries, date calculations, or response construction.

## Testing Example

### Example Command
```bash
curl -X GET "http://localhost:8000/api/v1/admin/users/stats" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"
```

### Valid Payload
No payload required for GET request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"active_users":150,"new_users_today":12,"top_search_queries":{"machine learning":450,"neural networks":320},"user_activity_trends":{"daily_active_users":[145,152,148,160,155,162,150],"weekly_registrations":[8,15,12,18],"timestamp":"2023-10-01T12:00:00Z"}}
```

Note: The actual values will vary based on current user activity and database state. The user activity trends contain placeholder data for demonstration. The JWT token in the example is a placeholder and should be replaced with a valid superuser token.