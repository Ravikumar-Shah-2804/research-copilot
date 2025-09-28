# Analytics Billing Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/analytics/billing/{org_id}`

### HTTP Method
GET

### Description
This endpoint calculates and returns billing information for a specific organization, including usage metrics, subscription tier details, and cost calculations based on API call overage.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations (queries organization and usage data).
- Calls `usage_analytics_service.calculate_billing_metrics()` from `src/services/usage.py` to compute billing data.
- Queries the `Organization` model to get subscription tier information.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- Any authenticated user can access this endpoint.
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- Users can view billing data for their own organization.
- Superusers can view any organization's billing data.
- Non-superusers attempting to view other organizations' billing will receive a 403 Forbidden response.

## Request

### Request Body Schema
No request body is required for this GET endpoint.

### Path Parameters
- **org_id** (UUID, required): The UUID of the organization whose billing information is being requested.

### Query Parameters
- **billing_period_start** (datetime, optional): Start date for the billing period (ISO format). Defaults to the first day of the current month.
- **billing_period_end** (datetime, optional): End date for the billing period (ISO format). Defaults to current UTC time.

### Content-Type
Not applicable (no request body).

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response provides comprehensive billing information including usage and cost calculations.

- **organization_id** (str): The UUID of the organization as a string.
- **billing_period** (dict): The billing period dates:
  - **start** (str): ISO format start date.
  - **end** (str): ISO format end date.
- **subscription_tier** (str): The organization's subscription tier (e.g., "free", "basic", "premium", "enterprise").
- **usage** (dict): Organization usage data (same as from usage/organization endpoint):
  - **organization_id** (str): Organization UUID.
  - **total_users** (int): Total users in organization.
  - **active_users** (int): Active users in period.
  - **total_api_calls** (int): Total API calls.
  - **average_response_time** (float): Average response time.
  - **period** (dict): Usage period dates.
- **billing** (dict): Billing calculation details:
  - **included_api_calls** (int): Number of API calls included in the subscription tier.
  - **total_api_calls** (int): Actual total API calls made.
  - **overage_calls** (int): Number of calls exceeding the included limit.
  - **price_per_call** (float): Cost per additional API call.
  - **total_cost** (float): Total cost for overage calls.
  - **currency** (str): Currency code (currently "USD").

### Example Response (JSON)
```json
{
  "organization_id": "456e7890-e89b-12d3-a456-426614174001",
  "billing_period": {
    "start": "2023-10-01T00:00:00",
    "end": "2023-10-31T23:59:59"
  },
  "subscription_tier": "basic",
  "usage": {
    "organization_id": "456e7890-e89b-12d3-a456-426614174001",
    "total_users": 25,
    "active_users": 18,
    "total_api_calls": 12500,
    "average_response_time": 0.42,
    "period": {
      "start_date": "2023-10-01T00:00:00",
      "end_date": "2023-10-31T23:59:59"
    }
  },
  "billing": {
    "included_api_calls": 10000,
    "total_api_calls": 12500,
    "overage_calls": 2500,
    "price_per_call": 0.001,
    "total_cost": 2.5,
    "currency": "USD"
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
- **Message**: "Cannot view other organizations' billing"
- **Condition**: Triggered when a non-superuser attempts to view another organization's billing data.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to get billing info: {str(e)}"
- **Condition**: Any exception raised during billing calculation or database queries.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/analytics/billing/456e7890-e89b-12d3-a456-426614174001?billing_period_start=2023-10-01T00:00:00&billing_period_end=2023-10-31T23:59:59' -Method GET -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyIiwiaWF0IjoxNjk2MTE4NDAwLCJleHAiOjE2OTYxMjIwMDB9.signature"}
```

### Valid Payload
No payload required for GET request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"organization_id":"456e7890-e89b-12d3-a456-426614174001","billing_period":{...},"subscription_tier":"basic","usage":{...},"billing":{...}}
```

Note: The org_id in the URL should be replaced with an actual organization UUID. If no billing period dates are provided, it defaults to the current month. Billing calculations are based on predefined pricing tiers and overage costs.