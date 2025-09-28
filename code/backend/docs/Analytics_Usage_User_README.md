# Analytics Usage User Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/analytics/usage/user/{user_id}`

### HTTP Method
GET

### Description
This endpoint retrieves usage analytics for a specific user, including total API calls, average response times, unique endpoints used, and endpoint-specific usage breakdown over a specified time period.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations (queries audit logs).
- Calls `usage_analytics_service.get_user_usage()` from `src/services/usage.py` to calculate usage statistics.
- Queries the `AuditLog` table to aggregate usage data by user.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- Any authenticated user can access this endpoint.
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- Users can view their own usage data.
- Superusers can view any user's usage data.
- Non-superusers attempting to view other users' data will receive a 403 Forbidden response.

## Request

### Request Body Schema
No request body is required for this GET endpoint.

### Path Parameters
- **user_id** (UUID, required): The UUID of the user whose usage analytics are being requested.

### Query Parameters
- **start_date** (datetime, optional): Start date for the usage period (ISO format). Defaults to 30 days before end_date.
- **end_date** (datetime, optional): End date for the usage period (ISO format). Defaults to current UTC time.

### Content-Type
Not applicable (no request body).

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response provides detailed usage statistics for the specified user and time period.

- **user_id** (str): The UUID of the user as a string.
- **period** (dict): The time period for the usage data:
  - **start_date** (str): ISO format start date.
  - **end_date** (str): ISO format end date.
- **total_api_calls** (int): Total number of API calls made by the user in the period.
- **average_response_time** (float): Average response time for the user's API calls.
- **unique_endpoints_used** (int): Number of distinct endpoints the user accessed.
- **endpoint_breakdown** (dict): Dictionary mapping endpoint paths to call counts, e.g., `{"/api/v1/search": 150, "/api/v1/rag": 50}`.

### Example Response (JSON)
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "period": {
    "start_date": "2023-09-01T00:00:00",
    "end_date": "2023-10-01T00:00:00"
  },
  "total_api_calls": 200,
  "average_response_time": 0.45,
  "unique_endpoints_used": 5,
  "endpoint_breakdown": {
    "/api/v1/search": 150,
    "/api/v1/rag": 30,
    "/api/v1/papers": 15,
    "/api/v1/auth/me": 4,
    "/api/v1/organizations": 1
  }
}
```

## Error Responses

### 401 Unauthorized
- **Status Code**: 401
- **Message**: "Not authenticated" (or similar, depending on auth implementation).
- **Condition**: Triggered when no valid authentication token is provided.

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Cannot view other users' usage"
- **Condition**: Triggered when a non-superuser attempts to view another user's usage data.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to get user usage: {str(e)}"
- **Condition**: Any exception raised during database queries or usage calculation.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/analytics/usage/user/123e4567-e89b-12d3-a456-426614174000?start_date=2023-09-01T00:00:00&end_date=2023-10-01T00:00:00' -Method GET -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyIiwiaWF0IjoxNjk2MTE4NDAwLCJleHAiOjE2OTYxMjIwMDB9.signature"}
```

### Valid Payload
No payload required for GET request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"user_id":"123e4567-e89b-12d3-a456-426614174000","period":{"start_date":"2023-09-01T00:00:00","end_date":"2023-10-01T00:00:00"},"total_api_calls":200,"average_response_time":0.45,"unique_endpoints_used":5,"endpoint_breakdown":{...}}
```

Note: The user_id in the URL should be replaced with an actual user UUID. If no dates are provided, it defaults to the last 30 days. Only audit logs for specific actions (search_perform, rag_query, paper_create, etc.) are included in the usage calculation.