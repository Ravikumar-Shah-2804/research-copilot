# Auth Logout Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/auth/logout`

### HTTP Method
POST

### Description
This endpoint allows authenticated users to logout by revoking a specific refresh token. The access token remains valid until expiration, but the refresh token can no longer be used to obtain new tokens.

### Dependencies
- Uses `get_current_user` dependency from `src/services/auth.py` to authenticate the request.
- Calls `revoke_refresh_token` from `src/services/auth.py` to revoke the specified token.
- Utilizes `audit_logger` from `src/utils/security_logging.py` for audit event logging.
- Relies on `AsyncSession` from `get_db` for database operations.

## Authentication

### Requirements
Authentication is mandatory and handled via the `get_current_user` dependency.
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user exists.

### Required Headers
- `Authorization`: Bearer token (required for authentication; validated via `get_current_user` dependency).

## Authorization

### Requirements
- The authenticated user can only revoke their own refresh tokens.
- No additional permission checks are performed beyond authentication.

## Request

### Request Body Schema
The request body must conform to the `RefreshTokenRequest` schema (from `src/schemas/auth.py`).

- **refresh_token** (str, required): The refresh token to revoke. Cannot be empty or contain only whitespace.

### Content-Type
- `application/json`

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
A simple JSON object with a success message.

- **message** (str): Confirmation message indicating successful logout.

### Example Response (JSON)
```json
{
  "message": "Successfully logged out"
}
```

## Error Responses

### 401 Unauthorized
- **Status Code**: 401
- **Message**: "Could not validate credentials"
- **Condition**: Triggered when the JWT token is missing, invalid, expired, or the user does not exist.

### 400 Bad Request
- **Status Code**: 400
- **Message**: "Refresh token cannot be empty"
- **Condition**: Triggered when the refresh_token field is empty or contains only whitespace.

### 503 Service Unavailable
- **Status Code**: 503
- **Message**: "Service temporarily unavailable"
- **Condition**: Triggered when database operations fail during token revocation.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Logout failed"
- **Condition**: Triggered for unexpected errors during the logout process.

## Testing Example

### Example Command
```bash
curl -X POST 'http://localhost:8000/api/v1/auth/logout' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImV4cCI6MTY5NjE2MDAwMH0.example' \
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
  "message": "Successfully logged out"
}
```

Note: After successful logout, the specified refresh token is revoked and cannot be used for token refresh operations. The access token remains valid until it expires.