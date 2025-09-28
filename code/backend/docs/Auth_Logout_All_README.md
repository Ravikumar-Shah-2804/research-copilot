# Auth Logout All Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/auth/logout-all`

### HTTP Method
POST

### Description
This endpoint allows authenticated users to logout from all devices by revoking all their refresh tokens. This provides a security feature to invalidate all active sessions across different devices.

### Dependencies
- Uses `get_current_user` dependency from `src/services/auth.py` to authenticate the request.
- Calls `revoke_all_user_tokens` from `src/services/auth.py` to revoke all tokens for the user.
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
No request body is required for this endpoint.

### Content-Type
Not applicable

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
A simple JSON object with a success message.

- **message** (str): Confirmation message indicating successful logout from all devices.

### Example Response (JSON)
```json
{
  "message": "Successfully logged out from all devices"
}
```

## Error Responses

### 401 Unauthorized
- **Status Code**: 401
- **Message**: "Could not validate credentials"
- **Condition**: Triggered when the JWT token is missing, invalid, expired, or the user does not exist.

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
curl -X POST 'http://localhost:8000/api/v1/auth/logout-all' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImV4cCI6MTY5NjE2MDAwMH0.example'
```

### Valid Payload
No payload required.

### Expected Output
```json
{
  "message": "Successfully logged out from all devices"
}
```

Note: After successful logout, all refresh tokens for the user are revoked. This will invalidate sessions on all devices, requiring re-authentication to obtain new tokens.