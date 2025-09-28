# Search Popular Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/search/popular`

### HTTP Method
GET

### Description
Get popular search queries. This endpoint returns a list of predefined popular search terms. Currently returns hardcoded popular queries as analytics tracking is not yet implemented. The list is limited based on the provided limit parameter.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Uses `RedisCache` for potential future caching of popular searches.
- Uses Pydantic query parameter validation with `Query` from FastAPI.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- No specific authorization checks beyond authentication; any active user can get popular searches.

## Request

### Query Parameters
- **limit** (int, optional): Maximum number of popular searches to return. Defaults to 10. Constraints: minimum value 1, maximum value 50.

### Content-Type
- Not applicable (GET request with query parameters)

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response is a JSON object with a single key "popular_searches" containing a list of strings.

- **popular_searches** (List[str]): List of popular search query strings.

### Example Response (JSON)
```json
{
  "popular_searches": [
    "machine learning",
    "deep learning",
    "neural networks",
    "computer vision",
    "natural language processing",
    "reinforcement learning",
    "artificial intelligence",
    "data science",
    "quantum computing",
    "blockchain"
  ]
}
```

## Error Responses

### 200 OK (with empty list)
- **Status Code**: 200
- **Message**: N/A (returns `{"popular_searches": []}`)
- **Condition**: Any exception during popular searches retrieval; the endpoint gracefully returns an empty list instead of failing.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/search/popular?limit=10' -Method GET -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"}
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"popular_searches":["machine learning","deep learning",...]}
```

Note: Currently returns a hardcoded list of popular searches. Future implementation will track actual search analytics. If an error occurs, an empty list is returned to maintain API stability.