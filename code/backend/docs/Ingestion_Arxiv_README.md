# Ingestion Arxiv Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/ingestion/arxiv` (assuming the router is mounted at `/api/v1/ingestion` in the main application; the endpoint is defined as `@router.post("/arxiv")`)

### HTTP Method
POST

### Description
This endpoint allows authenticated users to start an arXiv data ingestion job. It initiates a background process to fetch research papers from arXiv based on the provided search criteria and process them for inclusion in the system. The job runs asynchronously, and users can monitor progress via other endpoints.

### Dependencies
- Relies on `IngestionService` from `src/services/ingestion.py` to handle the ingestion job orchestration.
- Calls `ingestion_service.start_ingestion_job` to create and start the background job.
- Uses `ArxivIngestionRequest` and `ArxivIngestionResponse` schemas from `src/schemas/arxiv.py` for request/response validation.
- Adds a background task for optional logging via `log_ingestion_start`.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_user` dependency).

## Authorization

### Requirements
- No specific authorization checks beyond authentication; any authenticated user can start an ingestion job.

## Request

### Request Body Schema
The request body must conform to the `ArxivIngestionRequest` schema (from `src/schemas/arxiv.py`). All fields are validated using Pydantic.

- **search_query** (ArxivSearchQuery, required): The search criteria for arXiv papers.
  - query (str, optional): General search query string.
  - category (str, optional): arXiv category filter.
  - author (str, optional): Author name filter.
  - title (str, optional): Paper title filter.
  - abstract (str, optional): Abstract content filter.
  - from_date (str, optional): Start date in YYYYMMDD format.
  - to_date (str, optional): End date in YYYYMMDD format.
  - max_results (int, default 100, constraints: 1-2000): Maximum results per API request.
  - start (int, default 0, constraints: >=0): Starting index for pagination.
  - sort_by (str, default "submittedDate", pattern: ^(submittedDate|lastUpdatedDate|relevance)$): Sort field.
  - sort_order (str, default "descending", pattern: ^(ascending|descending)$): Sort order.
- **batch_size** (int, default 50, constraints: 1-200): Number of papers to process in each batch.
- **max_papers** (int, optional, constraints: 1-10000): Maximum total number of papers to ingest.
- **process_pdfs** (bool, default True): Whether to download and process PDFs after fetching metadata.
- **skip_duplicates** (bool, default True): Whether to skip papers already existing in the system.
- **priority** (str, default "normal", pattern: ^(low|normal|high)$): Job processing priority.

### Content-Type
- `application/json`

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response conforms to the `ArxivIngestionResponse` schema.

- **job_id** (str): The unique identifier of the ingestion job.
- **status** (str): The initial status of the job (always "started" for successful initiation).
- **message** (str): A descriptive message about the job initiation.
- **estimated_papers** (int, optional): A rough estimate of the number of papers to be processed.
- **search_criteria** (Dict[str, Any]): The search criteria used for the job.

### Example Response (JSON)
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "started",
  "message": "Ingestion job started with ID: 123e4567-e89b-12d3-a456-426614174000",
  "estimated_papers": 100,
  "search_criteria": {
    "query": "machine learning",
    "max_results": 100,
    "start": 0,
    "sort_by": "submittedDate",
    "sort_order": "descending"
  }
}
```

## Error Responses

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to start ingestion: {error_message}"
- **Condition**: Triggered if an exception occurs during job initiation in the `IngestionService.start_ingestion_job` method.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/ingestion/arxiv' -Method POST -ContentType 'application/json' -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"} -Body '{"search_query": {"query": "machine learning", "max_results": 10}, "batch_size": 5, "max_papers": 10}'
```

### Valid Payload
```json
{
  "search_query": {
    "query": "machine learning",
    "max_results": 10
  },
  "batch_size": 5,
  "max_papers": 10
}
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"job_id":"b3a5fd31-4444-42e0-8e53-08eb6d821cd0","status":"started","message":"Ingestion job started with ID: b3a5fd31-4444-42e0-8e53-08eb6d821cd0","estimated_papers":10,"search_criteria":{"query":"machine learning","category":null,"author":null,"title":null,"abstract":null,"from_date":null,"to_date":null,"max_results":10,"start":0,"sort_by":"submittedDate","sort_order":"descending"}}
```

Note: The job_id is dynamically generated as a UUID. The background task is added for audit logging. The job runs asynchronously, and progress can be monitored using the job status endpoint.