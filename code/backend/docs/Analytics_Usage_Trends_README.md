# Analytics Usage Trends Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/analytics/usage/trends`

### HTTP Method
GET

### Description
This endpoint provides usage trend analysis over time, showing daily API call patterns for users or organizations. It helps identify usage patterns, growth trends, and peak usage periods.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations (queries audit logs grouped by date).
- Calls `usage_analytics_service.get_usage_trends()` from `src/services/usage.py` to calculate trend data.
- Queries the `AuditLog` and `User` tables to aggregate usage by date.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- Any authenticated user can access this endpoint.
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- Users can view trends for themselves or their organization.
- Superusers can view trends for any user or organization.
- Non-superusers attempting to view other users' or organizations' trends will receive a 403 Forbidden response.

## Request

### Request Body Schema
No request body is required for this GET endpoint.

### Query Parameters
- **user_id** (UUID, optional): Filter trends by specific user. Requires authorization to view that user's data.
- **organization_id** (UUID, optional): Filter trends by specific organization. Requires authorization to view that organization's data.
- **days** (int, optional): Number of days to analyze (1-365). Defaults to 30. Constraints: minimum 1, maximum 365.

### Content-Type
Not applicable (no request body).

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response provides time-series usage data for trend analysis.

- **period_days** (int): Number of days analyzed.
- **daily_usage** (array): Array of daily usage objects:
  - **date** (str): Date in YYYY-MM-DD format.
  - **calls** (int): Number of API calls on that date.
- **total_calls** (int): Total API calls across the entire period.
- **average_daily_calls** (float): Average calls per day.

### Example Response (JSON)
```json
{
  "period_days": 30,
  "daily_usage": [
    {
      "date": "2023-09-01",
      "calls": 150
    },
    {
      "date": "2023-09-02",
      "calls": 180
    },
    {
      "date": "2023-09-03",
      "calls": 200
    }
  ],
  "total_calls": 4500,
  "average_daily_calls": 150.0
}
```

## Error Responses

### 401 Unauthorized
- **Status Code**: 401
- **Message**: "Not authenticated" (or similar, depending on auth implementation).
- **Condition**: Triggered when no valid authentication token is provided.

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Cannot view other users' trends" or "Cannot view other organizations' trends"
- **Condition**: Triggered when a non-superuser attempts to view unauthorized user or organization trends.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to get usage trends: {str(e)}"
- **Condition**: Any exception raised during trend calculation or database queries.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/analytics/usage/trends?days=30' -Method GET -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyIiwiaWF0IjoxNjk2MTE4NDAwLCJleHAiOjE2OTYxMjIwMDB9.signature"}
```

### Valid Payload
No payload required for GET request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"period_days":30,"daily_usage":[...],"total_calls":4500,"average_daily_calls":150.0}
```

Note: If no user_id or organization_id is provided, trends are calculated across all accessible data. The days parameter controls the lookback period. Daily usage is based on audit log entries for specific tracked actions.