# RAG Usage Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/rag/usage`

### HTTP Method
GET

### Description
This endpoint retrieves usage statistics for the RAG LLM service, such as token counts, costs, or other metrics.

### Dependencies
- Uses `LLMFactory` from `src/services/llm/factory.py` to create the LLM service.
- Calls `llm_service.get_usage_stats()` to fetch usage data.

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
The response is a usage statistics dictionary returned by `llm_service.get_usage_stats()`. Structure depends on the LLM provider (e.g., tokens used, costs, requests count).

- **total_tokens** (int, optional): Total tokens used.
- **total_cost** (float, optional): Total cost incurred.
- **requests_count** (int, optional): Number of requests made.
- Additional fields depend on the provider's API.

### Example Response (JSON)
```json
{
  "total_tokens": 15000,
  "total_cost": 0.5,
  "requests_count": 100
}
```

## Error Responses

### 200 OK (with error)
- **Status Code**: 200
- **Response**: `{"error": "{error message}"}`
- **Condition**: When an exception occurs during usage retrieval.

## Testing Example

### Example Command
```bash
curl -X GET http://localhost:8000/api/v1/rag/usage \
  -H "Authorization: Bearer <your-jwt-token>"
```

### Expected Output
```json
{
  "total_tokens": 15000,
  "total_cost": 0.5,
  "requests_count": 100
}