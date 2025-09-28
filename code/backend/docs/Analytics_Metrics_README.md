# Analytics Metrics Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/analytics/metrics`

### HTTP Method
GET

### Description
This endpoint exposes Prometheus metrics for monitoring and alerting. It returns metrics data in the standard Prometheus exposition format, including request counts, latency histograms, business metrics, system metrics, and custom application metrics.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations (though not directly used in this endpoint).
- Uses `prometheus_client.generate_latest()` to collect and format all registered Prometheus metrics.
- Requires Prometheus client library to be installed and configured.

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
- **Content-Type**: `text/plain; version=0.0.4; charset=utf-8` (Prometheus exposition format)

### Response Schema
The response is in Prometheus exposition format (plain text), containing various metric types:

- **Counter metrics**: Total counts that only increase (e.g., http_requests_total, search_requests_total)
- **Histogram metrics**: Request latency distributions (e.g., http_request_duration_seconds)
- **Gauge metrics**: Current values that can go up or down (e.g., active_users, system_cpu_usage_percent)
- **Summary metrics**: Similar to histograms but with quantiles
- **Info metrics**: Static information (e.g., build_info)

Common metrics include:
- HTTP request counts and latency by method, endpoint, and status code
- Search and RAG request counts
- API key usage
- System resource usage (CPU, memory, disk)
- Database connection and query metrics
- Cache hit/miss ratios
- Error counts by type and endpoint
- User registration and paper ingestion counts

### Example Response (Plain Text)
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/v1/search",status_code="200",user_type="authenticated",organization="org123"} 1500
http_requests_total{method="POST",endpoint="/api/v1/rag",status_code="200",user_type="authenticated",organization="org123"} 300

# HELP http_request_duration_seconds HTTP request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET",endpoint="/api/v1/search",status_code="200",le="0.1"} 1200
http_request_duration_seconds_bucket{method="GET",endpoint="/api/v1/search",status_code="200",le="0.5"} 1450
http_request_duration_seconds_bucket{method="GET",endpoint="/api/v1/search",status_code="200",le="1.0"} 1490
http_request_duration_seconds_bucket{method="GET",endpoint="/api/v1/search",status_code="200",le="+Inf"} 1500
http_request_duration_seconds_sum{method="GET",endpoint="/api/v1/search",status_code="200"} 450.5
http_request_duration_seconds_count{method="GET",endpoint="/api/v1/search",status_code="200"} 1500

# HELP active_users Number of active users
# TYPE active_users gauge
active_users{organization="org123"} 25

# HELP system_cpu_usage_percent System CPU usage percentage
# TYPE system_cpu_usage_percent gauge
system_cpu_usage_percent 45.2
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Not authorized" (or similar, depending on auth implementation).
- **Condition**: Triggered when the authenticated user is not an admin.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to get metrics: {str(e)}"
- **Condition**: Any exception raised during metrics collection or formatting.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/analytics/metrics' -Method GET -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"}
```

### Valid Payload
No payload required for GET request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content-Type: text/plain; version=0.0.4; charset=utf-8
Content: # HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/v1/search",status_code="200",user_type="authenticated",organization="org123"} 1500
...
```

Note: The response is in Prometheus exposition format (plain text), not JSON. This endpoint is designed for Prometheus servers to scrape metrics automatically. The exact metrics and values will vary based on system activity and configuration.