# Admin Search Stats Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/admin/search/stats` (assuming the admin router is mounted at `/api/v1/admin` in the main application; the endpoint is defined as `@router.get("/search/stats")`)

### HTTP Method
GET

### Description
This endpoint allows superuser administrators to retrieve comprehensive search statistics including query volumes, performance metrics, popular search categories, success rates, and index information. The endpoint analyzes audit logs and performance data to provide insights into search system usage and effectiveness.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations to query audit logs for search actions and success rates.
- Calls `performance_monitor.get_performance_metrics()` from `src/services/monitoring.py` to retrieve average query time metrics.
- Uses SQLAlchemy for complex aggregation queries on audit log data.
- Uses Pydantic schemas from `src/schemas/admin.py` for response validation.

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
The response conforms to the `SearchStats` schema (from `src/schemas/admin.py`). All fields are calculated dynamically from audit logs and performance metrics.

- **total_queries** (int): Total number of search queries performed (counted from AuditLog entries with action 'search_perform').
- **average_query_time** (float): Average time taken to process search queries in seconds (retrieved from performance metrics for 'api_request_get' operations).
- **popular_categories** (Dict[str, int]): Dictionary mapping category names to their search frequency (aggregated from AuditLog request_data.categories, handling both single categories and arrays, limited to top 10).
- **search_success_rate** (float): Percentage of successful search queries (calculated as successful queries / total queries * 100, where success is determined by AuditLog.success field).
- **index_size** (int): Size of the search index (currently a placeholder value of 0; would be retrieved from OpenSearch cluster statistics in production).

### Example Response (JSON)
```json
{
  "total_queries": 25000,
  "average_query_time": 0.085,
  "popular_categories": {
    "machine learning": 5200,
    "artificial intelligence": 4800,
    "computer science": 4200,
    "neural networks": 3800,
    "data science": 3500
  },
  "search_success_rate": 94.5,
  "index_size": 0
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Not enough permissions"
- **Condition**: Triggered when the authenticated user is not a superuser (checked by `get_current_superuser` dependency).

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to retrieve search stats: {error_message}"
- **Condition**: Any exception during database queries, performance metric retrieval, or response construction.

## Testing Example

### Example Command
```bash
curl -X GET "http://localhost:8000/api/v1/admin/search/stats" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"
```

### Valid Payload
No payload required for GET request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"total_queries":25000,"average_query_time":0.085,"popular_categories":{"machine learning":5200,"artificial intelligence":4800},"search_success_rate":94.5,"index_size":0}
```

Note: The actual values will vary based on current search activity and audit log data. The index_size is currently a placeholder. The JWT token in the example is a placeholder and should be replaced with a valid superuser token.