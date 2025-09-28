# Analytics Billing Invoice Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/analytics/billing/invoice/{org_id}`

### HTTP Method
GET

### Description
This endpoint generates a detailed invoice document for a specific organization, including billing period, usage summary, cost breakdown, and payment due date. It provides a complete billing statement for accounting and payment purposes.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations (queries organization and billing data).
- Calls `usage_analytics_service.calculate_billing_metrics()` from `src/services/usage.py` to compute billing data.
- Queries the `Organization` model to get organization details.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- Any authenticated user can access this endpoint.
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- Users can generate invoices for their own organization.
- Superusers can generate invoices for any organization.
- Non-superusers attempting to generate invoices for other organizations will receive a 403 Forbidden response.

## Request

### Request Body Schema
No request body is required for this GET endpoint.

### Path Parameters
- **org_id** (UUID, required): The UUID of the organization for which to generate the invoice.

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
The response provides a complete invoice document with all billing details.

- **invoice_number** (str): Unique invoice identifier (format: "INV-{org_id}-{YYYYMM}").
- **organization** (dict): Organization details:
  - **id** (str): Organization UUID.
  - **name** (str): Organization name.
  - **subscription_tier** (str): Subscription tier.
- **billing_period** (dict): Invoice period:
  - **start** (str): ISO format start date.
  - **end** (str): ISO format end date.
- **usage** (dict): Detailed usage statistics (same as organization usage endpoint).
- **billing** (dict): Cost breakdown (same as billing endpoint).
- **generated_at** (str): ISO format timestamp when invoice was generated.
- **due_date** (str): ISO format payment due date (30 days after billing period end).

### Example Response (JSON)
```json
{
  "invoice_number": "INV-456e7890-e89b-12d3-a456-426614174001-202310",
  "organization": {
    "id": "456e7890-e89b-12d3-a456-426614174001",
    "name": "Example Corp",
    "subscription_tier": "basic"
  },
  "billing_period": {
    "start": "2023-10-01T00:00:00",
    "end": "2023-10-31T23:59:59"
  },
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
  },
  "generated_at": "2023-11-01T10:00:00",
  "due_date": "2023-11-30T23:59:59"
}
```

## Error Responses

### 401 Unauthorized
- **Status Code**: 401
- **Message**: "Not authenticated" (or similar, depending on auth implementation).
- **Condition**: Triggered when no valid authentication token is provided.

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Cannot generate invoices for other organizations"
- **Condition**: Triggered when a non-superuser attempts to generate an invoice for another organization.

### 404 Not Found
- **Status Code**: 404
- **Message**: "Organization not found"
- **Condition**: Triggered when the specified organization UUID does not exist.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to generate invoice: {str(e)}"
- **Condition**: Any exception raised during invoice generation or database queries.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/analytics/billing/invoice/456e7890-e89b-12d3-a456-426614174001?billing_period_start=2023-10-01T00:00:00&billing_period_end=2023-10-31T23:59:59' -Method GET -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyIiwiaWF0IjoxNjk2MTE4NDAwLCJleHAiOjE2OTYxMjIwMDB9.signature"}
```

### Valid Payload
No payload required for GET request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"invoice_number":"INV-456e7890-e89b-12d3-a456-426614174001-202310","organization":{...},"billing_period":{...},"usage":{...},"billing":{...},"generated_at":"2023-11-01T10:00:00","due_date":"2023-11-30T23:59:59"}
```

Note: The org_id in the URL should be replaced with an actual organization UUID. The invoice number is auto-generated based on organization ID and billing period. Due date is automatically calculated as 30 days after the billing period end.