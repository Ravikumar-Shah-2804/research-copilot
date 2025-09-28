# Analytics Circuit Breakers Reset Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/analytics/circuit-breakers/reset`

### HTTP Method
POST

### Description
This endpoint resets all registered circuit breakers to their closed state, clearing failure counts and allowing normal operation to resume. This is an administrative action that can be used to manually recover from widespread service failures.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations (though not directly used in this endpoint).
- Calls `circuit_breaker_registry.reset_all()` from `src/services/circuit_breaker.py` to reset all circuit breakers.
- Uses the global circuit breaker registry to access all configured breakers.

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

- **message** (str): Confirmation message indicating all circuit breakers have been reset, formatted as "All circuit breakers reset successfully".

### Example Response (JSON)
```json
{
  "message": "All circuit breakers reset successfully"
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Not authorized" (or similar, depending on auth implementation).
- **Condition**: Triggered when the authenticated user is not an admin.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to reset circuit breakers: {str(e)}"
- **Condition**: Any exception raised during circuit breaker reset operations.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/analytics/circuit-breakers/reset' -Method POST -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"}
```

### Valid Payload
No payload required for POST request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"message":"All circuit breakers reset successfully"}
```

Note: This endpoint resets all circuit breakers in the system to their closed state, clearing consecutive failure counts and allowing requests to flow normally again. Use with caution as it may allow traffic to failing services.