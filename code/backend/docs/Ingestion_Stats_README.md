# Ingestion Stats Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/ingestion/stats` (assuming the router is mounted at `/api/v1/ingestion` in the main application; the endpoint is defined as `@router.get("/stats")`)

### HTTP Method
GET

### Description
This endpoint allows authenticated users to retrieve comprehensive statistics about the paper ingestion pipeline. It provides metrics on total papers, processing status, success rates, and performance indicators.

### Dependencies
- Relies on `PaperRepository` from `src/repositories/paper.py` to aggregate statistics from the database.
- Calls `repo.get_ingestion_stats` to compute and return the statistics.
- Uses `PaperIngestionStats` schema from `src/schemas/paper.py` for response formatting.
- Uses `get_db` dependency for database access.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_user` dependency).

## Authorization

### Requirements
- No specific authorization checks beyond authentication; any authenticated user can view ingestion statistics.

## Request

### Content-Type
- No request body or query parameters required.

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response conforms to the `PaperIngestionStats` schema.

- **total_papers** (int): Total number of papers in the system.
- **processed_papers** (int): Number of papers that have been processed.
- **papers_with_text** (int): Number of papers that have extracted text content.
- **failed_ingestions** (int): Number of papers with failed ingestion.
- **processing_rate** (float): Rate of successful processing (processed_papers / total_papers).
- **text_extraction_rate** (float): Rate of successful text extraction (papers_with_text / processed_papers).
- **average_processing_time** (float, optional): Average time taken to process a paper.
- **last_ingestion_run** (datetime, optional): Timestamp of the last ingestion run.

### Example Response (JSON)
```json
{
  "total_papers": 1000,
  "processed_papers": 950,
  "papers_with_text": 900,
  "failed_ingestions": 50,
  "processing_rate": 0.95,
  "text_extraction_rate": 0.947,
  "average_processing_time": 45.5,
  "last_ingestion_run": "2023-10-01T12:00:00Z"
}
```

## Error Responses

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to get ingestion stats: {error_message}"
- **Condition**: Triggered if an exception occurs during statistics computation in the repository layer.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/ingestion/stats' -Method GET -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"}
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"total_papers":1000,"processed_papers":950,"papers_with_text":900,"failed_ingestions":50,"processing_rate":0.95,"text_extraction_rate":0.947,"average_processing_time":45.5,"last_ingestion_run":"2023-10-01T12:00:00Z"}
```

Note: Statistics are computed in real-time from the database. Rates are calculated as floating-point values between 0 and 1. Timestamps are in ISO 8601 format.