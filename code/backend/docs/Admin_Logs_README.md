# Admin Logs Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/admin/logs` (assuming the admin router is mounted at `/api/v1/admin` in the main application; the endpoint is defined as `@router.get("/logs")`)

### HTTP Method
GET

### Description
This endpoint allows superuser administrators to retrieve recent system log entries from the application log files. It reads from the logs directory, finds the most recent log file, and returns the last N lines formatted as structured log entries with timestamps, levels, and messages.

### Dependencies
- Reads from the local `logs/` directory in the project root.
- Uses Python's `os` and `glob` modules for file system operations.
- Uses `datetime` for timestamp parsing and formatting.
- No database or external service dependencies.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_superuser` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is authenticated and active.
- The user must have superuser privileges (`current_user.is_superuser` must be `True`).

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_superuser` dependency, which internally uses `get_current_user` to decode and verify a JWT token).

## Authorization

### Requirements
- Only superusers can access this endpoint.
- The `get_current_superuser` dependency checks if `current_user.is_superuser` is `True`.
- Non-superusers will receive a 403 Forbidden response.

## Request

### Request Body Schema
No request body is required for this GET endpoint.

### Query Parameters
- **lines** (int, optional): Number of log lines to retrieve from the end of the log file. Defaults to 100. Maximum allowed value is 1000 (enforced server-side to prevent abuse).

### Content-Type
Not applicable (no request body).

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response is a JSON object containing formatted log entries and metadata.

- **logs** (List[dict]): Array of log entry objects, each containing:
  - **timestamp** (str): ISO format timestamp (current time if parsing fails).
  - **level** (str): Log level (defaults to "INFO" if not parseable).
  - **message** (str): The log message content.
- **total_lines** (int): Total number of log lines returned.
- **source_file** (str): Name of the log file that was read (e.g., "app.log").

### Example Response (JSON)
```json
{
  "logs": [
    {
      "timestamp": "2023-10-01T12:00:00Z",
      "level": "INFO",
      "message": "Admin endpoint /stats called"
    },
    {
      "timestamp": "2023-10-01T12:00:05Z",
      "level": "INFO",
      "message": "System stats retrieved successfully"
    },
    {
      "timestamp": "2023-10-01T12:00:10Z",
      "level": "WARNING",
      "message": "Cache miss for key: user_123"
    }
  ],
  "total_lines": 3,
  "source_file": "app.log"
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Not enough permissions"
- **Condition**: Triggered when the authenticated user is not a superuser (checked by `get_current_superuser` dependency).

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to retrieve system logs: {error_message}"
- **Condition**: Any exception during file reading, directory access, or log parsing.

## Testing Example

### Example Command
```bash
curl -X GET "http://localhost:8000/api/v1/admin/logs?lines=50" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"
```

### Valid Payload
No payload required for GET request.

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"logs":[{"timestamp":"2023-10-01T12:00:00Z","level":"INFO","message":"Admin endpoint /stats called"},{"timestamp":"2023-10-01T12:00:05Z","level":"INFO","message":"System stats retrieved successfully"}],"total_lines":2,"source_file":"app.log"}
```

Note: The actual log content will vary based on the current log file contents. If no logs directory exists or no .log files are found, the response will contain an empty logs array with an appropriate message. The lines parameter is capped at 1000 to prevent excessive data retrieval. The JWT token in the example is a placeholder and should be replaced with a valid superuser token.