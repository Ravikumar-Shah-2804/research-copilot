# Admin Health Detailed Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/admin/health/detailed` (assuming the admin router is mounted at `/api/v1/admin` in the main application; the endpoint is defined as `@router.get("/health/detailed")`)

### HTTP Method
GET

### Description
This endpoint provides a comprehensive health check for all system components including database connectivity, Redis cache, OpenSearch cluster, system metrics, and performance statistics. It returns detailed health status for each service and an overall system health indicator.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database health checks.
- Uses `RedisCache` from `src/services/cache/client.py` for Redis connectivity verification.
- Uses `OpenSearchService` from `src/services/opensearch/client.py` for cluster health assessment.
- Calls `performance_monitor.get_system_metrics()` and `performance_monitor.get_performance_metrics()` from `src/services/monitoring.py` for system and performance data.
- Uses SQLAlchemy for database connectivity testing.

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
The response is a JSON object containing comprehensive health information. No Pydantic schema is used; the structure is built dynamically.

- **overall_healthy** (bool): Overall system health status (true if all services are healthy).
- **timestamp** (float): Unix timestamp when the health check was performed.
- **services** (dict): Dictionary containing health status for each service:
  - **database** (dict): Database health with "healthy" (bool) and "response_time" (float) fields.
  - **redis** (dict): Redis cache health with "healthy" (bool) and "response_time" (float) fields.
  - **opensearch** (dict): OpenSearch health with "healthy" (bool), "status" (str), and "response_time" (float) fields.
- **system** (dict): System metrics from performance monitor (structure varies based on available metrics).
- **performance** (dict): Performance metrics including "uptime_seconds" (float), "total_requests" (int), and "error_rate" (float).

### Example Response (JSON)
```json
{
  "overall_healthy": true,
  "timestamp": 1696185600.0,
  "services": {
    "database": {
      "healthy": true,
      "response_time": 0.005
    },
    "redis": {
      "healthy": true,
      "response_time": 0.002
    },
    "opensearch": {
      "healthy": true,
      "status": "green",
      "response_time": 0.015
    }
  },
  "system": {
    "cpu_usage": 45.2,
    "memory_usage": 68.7,
    "disk_usage": 52.1
  },
  "performance": {
    "uptime_seconds": 86400.0,
    "total_requests": 12500,
    "error_rate": 0.02
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
- **Message**: "Failed to perform health check: {error_message}"
- **Condition**: Any exception during service health checks, performance metric retrieval, or response construction.

## Testing Example

### Example Command
```bash
curl -X GET "http://localhost:8000/api/v1/admin/health/detailed" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"
```

### Valid Payload
No payload required for GET request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"overall_healthy":true,"timestamp":1696185600.0,"services":{"database":{"healthy":true,"response_time":0.005},"redis":{"healthy":true,"response_time":0.002},"opensearch":{"healthy":true,"status":"green","response_time":0.015}},"system":{"cpu_usage":45.2,"memory_usage":68.7},"performance":{"uptime_seconds":86400.0,"total_requests":12500,"error_rate":0.02}}
```

Note: The actual values will vary based on current system state and service availability. The overall_healthy field will be false if any service reports unhealthy status. The JWT token in the example is a placeholder and should be replaced with a valid superuser token.