# Analytics Monitoring Dashboard Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/analytics/monitoring/dashboard`

### HTTP Method
GET

### Description
This endpoint provides comprehensive monitoring dashboard data, aggregating system metrics, performance statistics, search analytics, and user counts. It serves as a centralized data source for monitoring dashboards and administrative interfaces.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations (used to count active users).
- Calls multiple methods from `performance_monitor` (from `src/services/monitoring.py`):
  - `get_performance_metrics()` for overall performance data
  - `get_system_metrics()` for system resource usage
  - `get_search_metrics()` for search analytics
- Queries the `User` model to count active users in the database.

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
The response aggregates data from multiple monitoring sources for dashboard display.

- **timestamp** (str): ISO format timestamp when the dashboard data was generated.
- **system** (dict): Combined system metrics and user count:
  - **cpu_percent** (float): Current CPU usage percentage.
  - **memory_percent** (float): Current memory usage percentage.
  - **memory_used_mb** (float): Memory used in MB.
  - **memory_available_mb** (float): Available memory in MB.
  - **disk_usage_percent** (float): Disk usage percentage.
  - **timestamp** (str): ISO format timestamp.
  - **active_users** (int): Number of users with `is_active = True`.
- **performance** (dict): Performance metrics from `performance_monitor.get_performance_metrics()`:
  - **uptime_seconds** (float): Total uptime in seconds.
  - **total_requests** (int): Total API requests processed.
  - **error_count** (int): Total errors encountered.
  - **error_rate** (float): Error rate as a fraction.
  - **operations** (dict): Operation-specific metrics.
  - **system** (dict): System metrics (duplicated in main system section).
  - **timestamp** (str): ISO format timestamp.
- **search** (dict): Search analytics from `performance_monitor.get_search_metrics()`:
  - **total_searches_24h** (int): Total searches in last 24 hours.
  - **avg_response_time** (float): Average search response time.
  - **popular_queries** (array): List of popular search queries.
  - **search_modes_usage** (dict): Usage by search mode.
  - **timestamp** (str): ISO format timestamp.
- **alerts** (array): Currently empty array, intended for future alerting logic.

### Example Response (JSON)
```json
{
  "timestamp": "2023-10-01T12:00:00Z",
  "system": {
    "cpu_percent": 45.2,
    "memory_percent": 67.8,
    "memory_used_mb": 1024.5,
    "memory_available_mb": 2048.0,
    "disk_usage_percent": 23.4,
    "timestamp": "2023-10-01T12:00:00Z",
    "active_users": 25
  },
  "performance": {
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
  },
  "search": {
    "total_searches_24h": 0,
    "avg_response_time": 0.0,
    "popular_queries": [
      {
        "query": "machine learning",
        "count": 150
      }
    ],
    "search_modes_usage": {
      "hybrid": 0,
      "bm25_only": 0,
      "vector_only": 0
    },
    "timestamp": "2023-10-01T12:00:00Z"
  },
  "alerts": []
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Not authorized" (or similar, depending on auth implementation).
- **Condition**: Triggered when the authenticated user is not an admin.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to get dashboard data: {str(e)}"
- **Condition**: Any exception raised during metrics collection, database queries, or data aggregation.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/analytics/monitoring/dashboard' -Method GET -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"}
```

### Valid Payload
No payload required for GET request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"timestamp":"2023-10-01T12:00:00Z","system":{...},"performance":{...},"search":{...},"alerts":[]}
```

Note: The dashboard data aggregates information from multiple sources. Some metrics (like search analytics) may return placeholder or zero values if proper tracking is not fully implemented. The active_users count is dynamically calculated from the database.