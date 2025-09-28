# Auth Login Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/auth/token`

### HTTP Method
POST

### Description
This endpoint provides OAuth2 compatible token generation for user authentication. It accepts username and password credentials, validates them against the database, and returns both access and refresh tokens upon successful authentication. The endpoint includes comprehensive security logging and audit trails.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `authenticate_user` from `src/services/auth.py` to verify credentials.
- Uses `create_refresh_token_for_user` from `src/services/auth.py` to generate tokens.
- Utilizes `security_logger` from `src/utils/security_logging.py` for authentication failure logging.
- Uses `audit_logger` from `src/utils/security_logging.py` for audit event logging.

## Authentication

### Requirements
No authentication is required as this is the login endpoint.

### Required Headers
None

## Authorization

### Requirements
No authorization checks are performed for token generation.

## Request

### Request Body Schema
The request uses OAuth2PasswordRequestForm (form-encoded data) with the following fields:

- **username** (str, required): The user's username or email address. Cannot be empty. Maximum length 254 characters (RFC 5321 email limit).
- **password** (str, required): The user's password. Cannot be empty. Maximum length 128 characters.

### Content-Type
- `application/x-www-form-urlencoded`

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response conforms to the `Token` schema (from `src/schemas/auth.py`).

- **access_token** (str): The JWT access token for API authentication.
- **token_type** (str): The token type, always "bearer".
- **refresh_token** (str, optional): The refresh token for obtaining new access tokens.
- **expires_in** (int, optional): The access token expiration time in seconds (calculated as `settings.jwt_access_token_expire_minutes * 60`).

### Example Response (JSON)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImV4cCI6MTY5NjE2MDAwMH0.example",
  "token_type": "bearer",
  "refresh_token": "refresh_token_example_string",
  "expires_in": 1800
}
```

## Error Responses

### 400 Bad Request
- **Status Code**: 400
- **Message**: "Username cannot be empty"
- **Condition**: Triggered when the username field is empty or contains only whitespace.

### 400 Bad Request
- **Status Code**: 400
- **Message**: "Password cannot be empty"
- **Condition**: Triggered when the password field is empty or contains only whitespace.

### 400 Bad Request
- **Status Code**: 400
- **Message**: "Username too long"
- **Condition**: Triggered when the username exceeds 254 characters.

### 400 Bad Request
- **Status Code**: 400
- **Message**: "Password too long"
- **Condition**: Triggered when the password exceeds 128 characters.

### 401 Unauthorized
- **Status Code**: 401
- **Message**: "Incorrect username or password"
- **Condition**: Triggered when the provided credentials are invalid (user not found or password mismatch).

### 401 Unauthorized
- **Status Code**: 401
- **Message**: "User not found"
- **Condition**: Triggered when the authenticated user object cannot be retrieved from the database.

### 503 Service Unavailable
- **Status Code**: 503
- **Message**: "Service temporarily unavailable"
- **Condition**: Triggered when database operations fail during authentication or token creation.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Token generation failed"
- **Condition**: Triggered when JWT encoding fails or unexpected errors occur during token creation.

## Testing Example

### Example Command
```bash
curl -X POST 'http://localhost:8000/api/v1/auth/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=testuser&password=securepassword123'
```

### Valid Payload
```
username=testuser&password=securepassword123
```

### Expected Output
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImV4cCI6MTY5NjE2MDAwMH0.example",
  "token_type": "bearer",
  "refresh_token": "refresh_token_example_string",
  "expires_in": 1800
}
```

Note: The `access_token` and `refresh_token` values will be dynamically generated JWT strings. The `expires_in` value depends on the `jwt_access_token_expire_minutes` setting (default 30 minutes = 1800 seconds).