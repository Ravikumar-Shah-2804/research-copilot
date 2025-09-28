# Analytics Usage Organization Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/analytics/usage/organization/{org_id}`

### HTTP Method
GET

### Description
This endpoint retrieves usage analytics for a specific organization, including total users, active users, total API calls, and average response times across all organization members over a specified time period.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations (queries audit logs and user counts).
- Calls `usage_analytics_service.get_organization_usage()` from `src/services/usage.py` to calculate organization-wide usage statistics.
- Queries the `AuditLog` and `User` tables to aggregate usage data by organization.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- Any authenticated user can access this endpoint.
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- Users can view usage data for their own organization.
- Superusers can view any organization's usage data.
- Non-superusers attempting to view other organizations' data will receive a 403 Forbidden response.

## Request

### Request Body Schema
No request body is required for this GET endpoint.

### Path Parameters
- **org_id** (UUID, required): The UUID of the organization whose usage analytics are being requested.

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
The response provides aggregated usage statistics for the specified organization and time period.

- **organization_id** (str): The UUID of the organization as a string.
- **total_users** (int): Total number of users in the organization.
- **active_users** (int): Number of users who made API calls during the period.
- **total_api_calls** (int): Total number of API calls made by all organization users in the period.
- **average_response_time** (float): Average response time for all API calls in the organization.
- **period** (dict): The time period for the usage data:
  - **start_date** (str): ISO format start date.
  - **end_date** (str): ISO format end date.

### Example Response (JSON)
```json
{
  "organization_id": "456e7890-e89b-12d3-a456-426614174001",
  "total_users": 25,
  "active_users": 18,
  "total_api_calls": 2500,
  "average_response_time": 0.42,
  "period": {
    "start_date": "2023-09-01T00:00:00",
    "end_date": "2023-10-01T00:00:00"
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
- **Message**: "Cannot view other organizations' usage"
- **Condition**: Triggered when a non-superuser attempts to view another organization's usage data.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to get organization usage: {str(e)}"
- **Condition**: Any exception raised during database queries or usage calculation.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/analytics/usage/organization/456e7890-e89b-12d3-a456-426614174001?start_date=2023-09-01T00:00:00&end_date=2023-10-01T00:00:00' -Method GET -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyIiwiaWF0IjoxNjk2MTE4NDAwLCJleHAiOjE2OTYxMjIwMDB9.signature"}
```

### Valid Payload
No payload required for GET request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"organization_id":"456e7890-e89b-12d3-a456-426614174001","total_users":25,"active_users":18,"total_api_calls":2500,"average_response_time":0.42,"period":{...}}
```

Note: The org_id in the URL should be replaced with an actual organization UUID. If no dates are provided, it defaults to the last 30 days. The usage calculation aggregates data from all users in the organization based on audit logs for specific actions.