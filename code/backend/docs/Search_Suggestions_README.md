# Search Suggestions Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/search/suggestions`

### HTTP Method
GET

### Description
Get search suggestions based on partial query. This endpoint provides autocomplete-style suggestions for search queries by using OpenSearch completion suggesters on title and author fields. Suggestions are sorted by score and limited to prevent excessive results.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `OpenSearchService` for performing completion suggester queries.
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
- No specific authorization checks beyond authentication; any active user can get search suggestions.

## Request

### Query Parameters
- **q** (str, required): The partial query string for which to generate suggestions. Minimum length 1.
- **limit** (int, optional): Maximum number of suggestions to return. Defaults to 10. Constraints: minimum value 1, maximum value 50.

### Content-Type
- Not applicable (GET request with query parameters)

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response is a JSON object with a single key "suggestions" containing a list of suggestion objects.

Each suggestion object contains:
- **text** (str): The suggested text.
- **score** (float): The relevance score of the suggestion.
- **type** (str): The type of suggestion (e.g., "title", "author").

### Example Response (JSON)
```json
{
  "suggestions": [
    {
      "text": "machine learning",
      "score": 0.95,
      "type": "title"
    },
    {
      "text": "deep learning",
      "score": 0.89,
      "type": "title"
    },
    {
      "text": "John Doe",
      "score": 0.82,
      "type": "author"
    }
  ]
}
```

## Error Responses

### 200 OK (with empty suggestions)
- **Status Code**: 200
- **Message**: N/A (returns `{"suggestions": []}`)
- **Condition**: Any exception during suggestion generation; the endpoint gracefully returns an empty suggestions list instead of failing.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/search/suggestions?q=machine&limit=10' -Method GET -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"}
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"suggestions":[{"text":"machine learning","score":0.95,"type":"title"},...]}
```

Note: Suggestions are generated using OpenSearch completion suggesters on title and author fields. If an error occurs, an empty suggestions list is returned to maintain API stability.