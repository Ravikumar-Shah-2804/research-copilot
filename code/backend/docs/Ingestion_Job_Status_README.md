# Ingestion Job Status Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/ingestion/job/{job_id}` (assuming the router is mounted at `/api/v1/ingestion` in the main application; the endpoint is defined as `@router.get("/job/{job_id}")`)

### HTTP Method
GET

### Description
This endpoint allows authenticated users to retrieve the current status and progress of a specific arXiv ingestion job. It provides detailed information about the job's state, including progress metrics, timestamps, and any errors encountered during processing.

### Dependencies
- Relies on `IngestionService` from `src/services/ingestion.py` to retrieve job status.
- Calls `ingestion_service.get_job_status` to fetch the job details from the active jobs dictionary.
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
- No specific authorization checks beyond authentication; any authenticated user can view job status.

## Request

### Path Parameters
- **job_id** (str, required): The unique identifier of the ingestion job to retrieve status for.

### Content-Type
- No request body required.

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response conforms to the `ArxivIngestionStatus` schema.

- **job_id** (str): The unique identifier of the ingestion job.
- **status** (str): The current status of the job (e.g., "pending", "running", "completed", "failed", "cancelled").
- **progress** (Dict[str, Any]): Detailed progress information including counts of papers fetched, created, updated, PDFs downloaded, PDFs processed, and errors.
- **created_at** (datetime): The timestamp when the job was created.
- **started_at** (datetime, optional): The timestamp when the job started processing.
- **completed_at** (datetime, optional): The timestamp when the job completed.
- **errors** (List[Dict[str, Any]]): A list of errors encountered during processing, each with timestamp, error message, and stage.
- **stats** (Dict[str, Any]): Additional statistics about the job.

### Example Response (JSON)
```json
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
}
```

## Error Responses

### 404 Not Found
- **Status Code**: 404
- **Message**: "Job not found"
- **Condition**: Triggered if the specified `job_id` does not exist in the active jobs.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to get job status: {error_message}"
- **Condition**: Triggered if an exception occurs during status retrieval in the service layer.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/ingestion/job/123e4567-e89b-12d3-a456-426614174000' -Method GET -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"}
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"job_id":"123e4567-e89b-12d3-a456-426614174000","status":"running","progress":{"papers_fetched":50,"papers_created":45,"papers_updated":5,"pdfs_downloaded":40,"pdfs_processed":35,"errors":[]},"created_at":"2023-10-01T12:00:00Z","started_at":"2023-10-01T12:00:05Z","completed_at":null,"errors":[],"stats":{}}
```

Note: The response will vary based on the actual job state. If the job is not found, a 404 error will be returned. Timestamps are in ISO 8601 format.