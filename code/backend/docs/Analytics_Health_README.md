# Analytics Health Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/analytics/health`

### HTTP Method
GET

### Description
This endpoint provides system health check information, including the overall status and health of various services. It returns a comprehensive health report that can be used for monitoring and alerting purposes.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations (though not directly used in this endpoint).
- Calls `performance_monitor.get_system_metrics()` from `src/services/monitoring.py` to retrieve system resource metrics.
- Currently returns placeholder status for external services (database, OpenSearch, Redis, embeddings) as full health checks are not implemented.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- Any authenticated user can access this endpoint.
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- Any authenticated user can access this endpoint.
- No additional authorization checks beyond authentication.

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
The response provides comprehensive health information about the system.

- **status** (str): Overall system health status (currently always "healthy").
- **services** (dict): Health status of individual services:
  - **database** (str): Database health status (currently "unknown" as health check not implemented).
  - **opensearch** (str): OpenSearch health status (currently "unknown" as health check not implemented).
  - **redis** (str): Redis health status (currently "unknown" as health check not implemented).
  - **embeddings** (str): Embedding service health status (currently "unknown" as health check not implemented).
- **metrics** (dict): System resource metrics from `performance_monitor.get_system_metrics()`:
  - **cpu_percent** (float): Current CPU usage percentage.
  - **memory_percent** (float): Current memory usage percentage.
  - **memory_used_mb** (float): Memory used in MB.
  - **memory_available_mb** (float): Available memory in MB.
  - **disk_usage_percent** (float): Disk usage percentage.
  - **timestamp** (str): ISO format timestamp.

### Example Response (JSON)
```json
{
  "status": "healthy",
  "services": {
    "database": "unknown",
    "opensearch": "unknown",
    "redis": "unknown",
    "embeddings": "unknown"
  },
  "metrics": {
    "cpu_percent": 45.2,
    "memory_percent": 67.8,
    "memory_used_mb": 1024.5,
    "memory_available_mb": 2048.0,
    "disk_usage_percent": 23.4,
    "timestamp": "2023-10-01T12:00:00Z"
  }
}
```

## Error Responses

### 401 Unauthorized
- **Status Code**: 401
- **Message**: "Not authenticated" (or similar, depending on auth implementation).
- **Condition**: Triggered when no valid authentication token is provided.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Health check failed: {str(e)}"
- **Condition**: Any exception raised during health check or metrics collection.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/analytics/health' -Method GET -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyIiwiaWF0IjoxNjk2MTE4NDAwLCJleHAiOjE2OTYxMjIwMDB9.signature"}
```

### Valid Payload
No payload required for GET request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"status":"healthy","services":{"database":"unknown","opensearch":"unknown","redis":"unknown","embeddings":"unknown"},"metrics":{"cpu_percent":45.2,"memory_percent":67.8,"memory_used_mb":1024.5,"memory_available_mb":2048.0,"disk_usage_percent":23.4,"timestamp":"2023-10-01T12:00:00Z"}}
```

Note: The service health statuses are currently placeholder values. Full implementation would include actual health checks for each service. System metrics are dynamically generated based on current resource usage.