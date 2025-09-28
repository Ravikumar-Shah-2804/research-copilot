# Analytics Search Analytics Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/analytics/search-analytics`

### HTTP Method
GET

### Description
This endpoint provides analytics and usage statistics specifically for search operations, including total searches, response times, popular queries, and search mode usage patterns. It helps administrators understand search behavior and performance.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations (though not directly used in this endpoint).
- Calls `search_analytics.get_search_metrics()` from `src/services/monitoring.py` to retrieve search analytics data.
- Uses Redis cache for storing and retrieving search analytics (if available).

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
The response conforms to the search metrics structure returned by `search_analytics.get_search_metrics()`. All fields are dynamically generated.

- **total_searches_24h** (int): Total number of searches in the last 24 hours (currently returns 0 as proper tracking needs implementation).
- **avg_response_time** (float): Average response time for search operations (currently returns 0.0 as proper tracking needs implementation).
- **popular_queries** (array): List of most popular search queries, each containing:
  - **query** (str): The search query text.
  - **count** (int): Number of times this query was searched.
- **search_modes_usage** (dict): Usage statistics for different search modes:
  - **hybrid** (int): Number of hybrid searches (currently returns 0 as proper tracking needs implementation).
  - **bm25_only** (int): Number of BM25-only searches (currently returns 0 as proper tracking needs implementation).
  - **vector_only** (int): Number of vector-only searches (currently returns 0 as proper tracking needs implementation).
- **timestamp** (str): ISO format timestamp when metrics were collected.

### Example Response (JSON)
```json
{
  "total_searches_24h": 0,
  "avg_response_time": 0.0,
  "popular_queries": [
    {
      "query": "machine learning",
      "count": 150
    },
    {
      "query": "deep learning",
      "count": 120
    },
    {
      "query": "neural networks",
      "count": 95
    },
    {
      "query": "computer vision",
      "count": 80
    },
    {
      "query": "nlp",
      "count": 75
    }
  ],
  "search_modes_usage": {
    "hybrid": 0,
    "bm25_only": 0,
    "vector_only": 0
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
- **Message**: "Failed to get search analytics: {str(e)}"
- **Condition**: Any exception raised during analytics retrieval or cache operations.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/analytics/search-analytics' -Method GET -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"}
```

### Valid Payload
No payload required for GET request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"total_searches_24h":0,"avg_response_time":0.0,"popular_queries":[...],"search_modes_usage":{...},"timestamp":"2023-10-01T12:00:00Z"}
```

Note: The full JSON response includes search analytics metrics as per the schema. Popular queries are currently placeholder data, and usage tracking metrics return 0 as they require additional implementation for proper tracking.