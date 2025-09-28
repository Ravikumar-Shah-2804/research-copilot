# Analytics Performance Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/analytics/performance`

### HTTP Method
GET

### Description
This endpoint retrieves comprehensive system performance metrics, including uptime, request counts, error rates, operation-specific metrics, and system resource usage. It provides real-time insights into the application's performance and health.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations (though not directly used in this endpoint).
- Calls `performance_monitor.get_performance_metrics()` from `src/services/monitoring.py` to gather performance data.
- Uses system monitoring via `psutil` for resource metrics.

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
The response conforms to the performance metrics structure returned by `performance_monitor.get_performance_metrics()`. All fields are dynamically generated.

- **uptime_seconds** (float): Total uptime of the performance monitor in seconds.
- **total_requests** (int): Total number of API requests processed.
- **error_count** (int): Total number of errors encountered.
- **error_rate** (float): Error rate as a fraction (error_count / max(total_requests, 1)).
- **operations** (dict): Dictionary of operation-specific metrics, where each key is an operation name and value contains:
  - **count** (int): Number of times the operation was executed.
  - **total_time** (float): Total time spent on the operation.
  - **avg_time** (float): Average time per operation execution.
  - **min_time** (float): Minimum execution time.
  - **max_time** (float): Maximum execution time.
  - **last_updated** (str): ISO format timestamp of last update.
  - **metadata** (dict, optional): Additional metadata if available.
- **system** (dict): System resource metrics:
  - **cpu_percent** (float): Current CPU usage percentage.
  - **memory_percent** (float): Current memory usage percentage.
  - **memory_used_mb** (float): Memory used in MB.
  - **memory_available_mb** (float): Available memory in MB.
  - **disk_usage_percent** (float): Disk usage percentage.
  - **timestamp** (str): ISO format timestamp.
- **timestamp** (str): ISO format timestamp when metrics were collected.

### Example Response (JSON)
```json
{
  "uptime_seconds": 3600.5,
  "total_requests": 1500,
  "error_count": 15,
  "error_rate": 0.01,
  "operations": {
    "api_request_GET": {
      "count": 1000,
      "total_time": 45.67,
      "avg_time": 0.04567,
      "min_time": 0.01,
      "max_time": 2.5,
      "last_updated": "2023-10-01T12:00:00Z"
    }
  },
  "system": {
    "cpu_percent": 45.2,
    "memory_percent": 67.8,
    "memory_used_mb": 1024.5,
    "memory_available_mb": 2048.0,
    "disk_usage_percent": 23.4,
    "timestamp": "2023-10-01T12:00:00Z"
  },
  "timestamp": "2023-10-01T12:00:00Z"
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Not authorized" (or similar, depending on auth implementation).
- **Condition**: Triggered when the authenticated user is not an admin.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to get performance metrics: {str(e)}"
- **Condition**: Any exception raised during metrics collection or system monitoring.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/analytics/performance' -Method GET -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"}
```

### Valid Payload
No payload required for GET request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"uptime_seconds":3600.5,"total_requests":1500,"error_count":15,"error_rate":0.01,"operations":{...},"system":{...},"timestamp":"2023-10-01T12:00:00Z"}
```

Note: The full JSON response includes all performance metrics as per the schema. Values are dynamically generated based on current system state and usage history.