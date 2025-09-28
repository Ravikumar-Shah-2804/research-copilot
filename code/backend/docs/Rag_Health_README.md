# RAG Health Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/rag/health`

### HTTP Method
GET

### Description
This endpoint checks the health status of the RAG system, including pipeline and dependencies.

### Dependencies
- Uses `RAGPipeline` from `src/services/rag_pipeline.py` to get health status via `get_health_status()`.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication).

## Authorization

### Requirements
- No specific authorization checks beyond authentication; any active user can access this endpoint.

## Request

### Request Body Schema
No request body required for this GET endpoint.

### Content-Type
- Not applicable.

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response is a health status dictionary returned by `RAGPipeline.get_health_status()`. Typical structure includes overall health and component statuses.

- **overall_healthy** (bool): Whether the system is healthy.
- Additional fields depend on the health check implementation (e.g., database status, LLM availability).

### Example Response (JSON)
```json
{
  "overall_healthy": true,
  "database": "healthy",
  "llm_service": "healthy",
  "timestamp": 1640995200.0
}
```

## Error Responses

### 200 OK (with error)
- **Status Code**: 200
- **Response**: `{"overall_healthy": false, "error": "{error message}", "timestamp": {unix timestamp}}`
- **Condition**: When an exception occurs during health check.

## Testing Example

### Example Command
```bash
curl -X GET http://localhost:8000/api/v1/rag/health \
  -H "Authorization: Bearer <your-jwt-token>"
```

### Expected Output
```json
{
  "overall_healthy": true,
  "database": "healthy",
  "llm_service": "healthy",
  "timestamp": 1640995200.0
}