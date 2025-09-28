# Analytics Circuit Breakers Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/analytics/circuit-breakers`

### HTTP Method
GET

### Description
This endpoint retrieves statistics for all registered circuit breakers in the system, including their current state, failure counts, success rates, and configuration details. It provides visibility into the resilience mechanisms protecting the application.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations (though not directly used in this endpoint).
- Calls `circuit_breaker_registry.get_all_stats()` from `src/services/circuit_breaker.py` to retrieve circuit breaker data.
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
No request body is required for this GET endpoint.

### Content-Type
Not applicable (no request body).

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response is a dictionary where each key is a circuit breaker name and the value contains detailed statistics.

Each circuit breaker's statistics include:
- **name** (str): Circuit breaker identifier.
- **state** (str): Current state ("closed", "open", or "half_open").
- **total_requests** (int): Total number of requests processed.
- **total_failures** (int): Total number of failed requests.
- **total_successes** (int): Total number of successful requests.
- **total_timeouts** (int): Number of requests that timed out.
- **total_slow_calls** (int): Number of slow calls (above threshold).
- **consecutive_failures** (int): Current consecutive failure count.
- **consecutive_successes** (int): Current consecutive success count.
- **avg_response_time** (float): Average response time.
- **slow_call_rate** (float): Rate of slow calls (0.0-1.0).
- **last_failure_time** (float, optional): Unix timestamp of last failure.
- **last_success_time** (float, optional): Unix timestamp of last success.
- **config** (dict): Circuit breaker configuration:
  - **failure_threshold** (int): Failures before opening.
  - **recovery_timeout** (float): Seconds to wait before retry.
  - **success_threshold** (int): Successes needed to close.
  - **timeout** (float): Request timeout.
  - **slow_call_duration_threshold** (float): Slow call threshold.
  - **slow_call_rate_threshold** (float): Slow call rate threshold.

### Example Response (JSON)
```json
{
  "search_service": {
    "name": "search_service",
    "state": "closed",
    "total_requests": 1000,
    "total_failures": 15,
    "total_successes": 985,
    "total_timeouts": 5,
    "total_slow_calls": 20,
    "consecutive_failures": 0,
    "consecutive_successes": 10,
    "avg_response_time": 0.45,
    "slow_call_rate": 0.02,
    "last_failure_time": 1696117200.0,
    "last_success_time": 1696118400.0,
    "config": {
      "failure_threshold": 5,
      "recovery_timeout": 60.0,
      "success_threshold": 3,
      "timeout": 10.0,
      "slow_call_duration_threshold": 5.0,
      "slow_call_rate_threshold": 0.5
    }
  },
  "rag_service": {
    "name": "rag_service",
    "state": "open",
    "total_requests": 500,
    "total_failures": 8,
    "total_successes": 492,
    "total_timeouts": 3,
    "total_slow_calls": 15,
    "consecutive_failures": 6,
    "consecutive_successes": 0,
    "avg_response_time": 2.1,
    "slow_call_rate": 0.03,
    "last_failure_time": 1696118500.0,
    "last_success_time": 1696118000.0,
    "config": {
      "failure_threshold": 5,
      "recovery_timeout": 60.0,
      "success_threshold": 3,
      "timeout": 10.0,
      "slow_call_duration_threshold": 5.0,
      "slow_call_rate_threshold": 0.5
    }
  }
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Not authorized" (or similar, depending on auth implementation).
- **Condition**: Triggered when the authenticated user is not an admin.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to get circuit breaker stats: {str(e)}"
- **Condition**: Any exception raised during statistics retrieval.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/analytics/circuit-breakers' -Method GET -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"}
```

### Valid Payload
No payload required for GET request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"search_service":{...},"rag_service":{...}}
```

Note: The response includes statistics for all registered circuit breakers. Empty object returned if no circuit breakers are registered. States indicate "closed" (normal), "open" (failing), or "half_open" (testing recovery).