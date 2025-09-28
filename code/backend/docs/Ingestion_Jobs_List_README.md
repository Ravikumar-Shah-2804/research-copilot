# Ingestion Jobs List Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/ingestion/jobs` (assuming the router is mounted at `/api/v1/ingestion` in the main application; the endpoint is defined as `@router.get("/jobs")`)

### HTTP Method
GET

### Description
This endpoint allows authenticated users to retrieve a list of all currently active arXiv ingestion jobs. Active jobs include those in "pending", "running", or other non-completed states. Each job's status and progress information is returned.

### Dependencies
- Relies on `IngestionService` from `src/services/ingestion.py` to retrieve active jobs.
- Calls `ingestion_service.get_active_jobs` to fetch all jobs from the active jobs dictionary.
- Uses `ArxivIngestionStatus` schema from `src/schemas/arxiv.py` for response formatting.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_user` dependency).

## Authorization

### Requirements
- No specific authorization checks beyond authentication; any authenticated user can list active jobs.

## Request

### Content-Type
- No request body or query parameters required.

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
An array of `ArxivIngestionStatus` objects, each containing:

- **job_id** (str): The unique identifier of the ingestion job.
- **status** (str): The current status of the job (e.g., "pending", "running", "completed", "failed", "cancelled").
- **progress** (Dict[str, Any]): Detailed progress information including counts of papers fetched, created, updated, PDFs downloaded, PDFs processed, and errors.
- **created_at** (datetime): The timestamp when the job was created.
- **started_at** (datetime, optional): The timestamp when the job started processing.
- **completed_at** (datetime, optional): The timestamp when the job completed.
- **errors** (List[Dict[str, Any]]): A list of errors encountered during processing.
- **stats** (Dict[str, Any]): Additional statistics about the job.

### Example Response (JSON)
```json
[
  {
    "job_id": "123e4567-e89b-12d3-a456-426614174000",
    "status": "running",
    "progress": {
      "papers_fetched": 50,
      "papers_created": 45,
      "papers_updated": 5,
      "pdfs_downloaded": 40,
      "pdfs_processed": 35,
      "errors": []
    },
    "created_at": "2023-10-01T12:00:00Z",
    "started_at": "2023-10-01T12:00:05Z",
    "completed_at": null,
    "errors": [],
    "stats": {}
  },
  {
    "job_id": "456e7890-e89b-12d3-a456-426614174001",
    "status": "pending",
    "progress": {
      "papers_fetched": 0,
      "papers_created": 0,
      "papers_updated": 0,
      "pdfs_downloaded": 0,
      "pdfs_processed": 0,
      "errors": []
    },
    "created_at": "2023-10-01T12:05:00Z",
    "started_at": null,
    "completed_at": null,
    "errors": [],
    "stats": {}
  }
]
```

## Error Responses

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to list jobs: {error_message}"
- **Condition**: Triggered if an exception occurs during job listing in the service layer.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/ingestion/jobs' -Method GET -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"}
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: [{"job_id":"123e4567-e89b-12d3-a456-426614174000","status":"running","progress":{"papers_fetched":50,"papers_created":45,"papers_updated":5,"pdfs_downloaded":40,"pdfs_processed":35,"errors":[]},"created_at":"2023-10-01T12:00:00Z","started_at":"2023-10-01T12:00:05Z","completed_at":null,"errors":[],"stats":{}},{"job_id":"456e7890-e89b-12d3-a456-426614174001","status":"pending","progress":{"papers_fetched":0,"papers_created":0,"papers_updated":0,"pdfs_downloaded":0,"pdfs_processed":0,"errors":[]},"created_at":"2023-10-01T12:05:00Z","started_at":null,"completed_at":null,"errors":[],"stats":{}}]
```

Note: The response will include all currently active jobs. Completed, failed, or cancelled jobs are not included in this list. Timestamps are in ISO 8601 format.