# Auth Refresh Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/auth/refresh`

### HTTP Method
POST

### Description
This endpoint allows users to obtain a new access token using a valid refresh token. It validates the refresh token, ensures the associated user is active, and generates a new access token while optionally providing a new refresh token.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `refresh_access_token` from `src/services/auth.py` to perform token refresh logic.
- Utilizes `audit_logger` from `src/utils/security_logging.py` for audit event logging.

## Authentication

### Requirements
No authentication header is required. Authentication is performed using the refresh token provided in the request body.

### Required Headers
None

## Authorization

### Requirements
- The refresh token must be valid and not expired or revoked.
- The user associated with the refresh token must exist and be active.

## Request

### Request Body Schema
The request body must conform to the `RefreshTokenRequest` schema (from `src/schemas/auth.py`).

- **refresh_token** (str, required): The refresh token obtained during login. Cannot be empty or contain only whitespace.

### Content-Type
- `application/json`

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response conforms to the `Token` schema (from `src/schemas/auth.py`).

- **access_token** (str): The new JWT access token.
- **token_type** (str): The token type, always "bearer".
- **refresh_token** (str, optional): A new refresh token (may reuse the existing one).
- **expires_in** (int, optional): The access token expiration time in seconds.

### Example Response (JSON)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImV4cCI6MTY5NjE3NDAwMH0.example",
  "token_type": "bearer",
  "refresh_token": "new_refresh_token_example_string",
  "expires_in": 1800
}
```

## Error Responses

### 400 Bad Request
- **Status Code**: 400
- **Message**: "Refresh token cannot be empty"
- **Condition**: Triggered when the refresh_token field is empty or contains only whitespace.

### 401 Unauthorized
- **Status Code**: 401
- **Message**: "Invalid refresh token"
- **Condition**: Triggered when the refresh token is invalid, expired, revoked, or the associated user is not found or inactive.

### 503 Service Unavailable
- **Status Code**: 503
- **Message**: "Service temporarily unavailable"
- **Condition**: Triggered when database operations fail during token validation or refresh.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Token refresh failed"
- **Condition**: Triggered for unexpected errors during the token refresh process.

## Testing Example

### Example Command
```bash
curl -X POST 'http://localhost:8000/api/v1/auth/refresh' \
  -H 'Content-Type: application/json' \
  -d '{
    "refresh_token": "refresh_token_example_string"
  }'
```

### Valid Payload
```json
{
  "refresh_token": "refresh_token_example_string"
}
```

### Expected Output
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImV4cCI6MTY5NjE3NDAwMH0.example",
  "token_type": "bearer",
  "refresh_token": "new_refresh_token_example_string",
  "expires_in": 1800
}
```

Note: The new `access_token` and potentially new `refresh_token` will be dynamically generated. The `expires_in` value depends on the JWT access token expiration setting.