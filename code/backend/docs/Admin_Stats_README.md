# Admin Stats Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/admin/stats` (assuming the admin router is mounted at `/api/v1/admin` in the main application; the endpoint is defined as `@router.get("/stats")`)

### HTTP Method
GET

### Description
This endpoint allows superuser administrators to retrieve comprehensive system statistics including user counts, paper counts, search metrics, cache performance, response times, and system uptime. The endpoint aggregates data from the database and performance monitoring services to provide a holistic view of system health and usage.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations to query user, paper, and audit log counts.
- Calls `performance_monitor.get_performance_metrics()` from `src/services/monitoring.py` to retrieve performance data including cache hit rates, response times, and uptime.
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
The response conforms to the `SystemStats` schema (from `src/schemas/admin.py`). All fields are calculated dynamically from database queries and performance metrics.

- **total_users** (int): Total number of users in the system (queried from User table).
- **total_papers** (int): Total number of research papers in the system (queried from ResearchPaper table).
- **total_searches** (int): Total number of search operations performed (counted from AuditLog entries with action 'search_perform').
- **cache_hit_rate** (float): Cache hit rate percentage (currently a placeholder value of 0.85; would be calculated from actual cache metrics in production).
- **average_response_time** (float): Average API response time in seconds (retrieved from performance metrics for 'api_request_get' operations).
- **system_uptime** (float): System uptime in seconds (retrieved from performance metrics).

### Example Response (JSON)
```json
{
  "total_users": 1250,
  "total_papers": 5000,
  "total_searches": 25000,
  "cache_hit_rate": 0.85,
  "average_response_time": 0.125,
  "system_uptime": 86400.0
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Not enough permissions"
- **Condition**: Triggered when the authenticated user is not a superuser (checked by `get_current_superuser` dependency).

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to retrieve system stats: {error_message}"
- **Condition**: Any exception during database queries, performance metric retrieval, or response construction.

## Testing Example

### Example Command
```bash
curl -X GET "http://localhost:8000/api/v1/admin/stats" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"
```

### Valid Payload
No payload required for GET request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"total_users":1250,"total_papers":5000,"total_searches":25000,"cache_hit_rate":0.85,"average_response_time":0.125,"system_uptime":86400.0}
```

Note: The actual values will vary based on the current state of the database and system performance metrics. The JWT token in the example is a placeholder and should be replaced with a valid superuser token.