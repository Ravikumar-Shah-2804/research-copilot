# RAG Models Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/rag/models`

### HTTP Method
GET

### Description
This endpoint retrieves the list of available LLM models for RAG operations, filtered to include only DeepSeek models.

### Dependencies
- Uses `LLMFactory` from `src/services/llm/factory.py` to create the LLM service.
- Calls `llm_service.get_available_models()` to fetch models from the provider.

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
Custom response structure.

- **models** (List[Dict]): List of available DeepSeek models. Each model is a dictionary with provider-specific fields (e.g., id, name).
- **default_model** (str): The default model identifier, set to "deepseek/deepseek-chat".

### Example Response (JSON)
```json
{
  "models": [
    {
      "id": "deepseek/deepseek-chat",
      "name": "DeepSeek Chat"
    },
    {
      "id": "deepseek/deepseek-coder",
      "name": "DeepSeek Coder"
    }
  ],
  "default_model": "deepseek/deepseek-chat"
}
```

## Error Responses

### 200 OK (with error)
- **Status Code**: 200
- **Response**: `{"models": [], "error": "{error message}"}`
- **Condition**: When an exception occurs during model retrieval, returns an empty models list with the error message.

## Testing Example

### Example Command
```bash
curl -X GET http://localhost:8000/api/v1/rag/models \
  -H "Authorization: Bearer <your-jwt-token>"
```

### Expected Output
```json
{
  "models": [
    {
      "id": "deepseek/deepseek-chat",
      "name": "DeepSeek Chat"
    }
  ],
  "default_model": "deepseek/deepseek-chat"
}