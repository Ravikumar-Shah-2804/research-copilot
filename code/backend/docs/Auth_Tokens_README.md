# Auth Tokens Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/auth/tokens`

### HTTP Method
GET

### Description
This endpoint retrieves a list of all refresh tokens associated with the currently authenticated user. It provides detailed information about each token including creation time, expiration, revocation status, and device information.

### Dependencies
- Uses `get_current_active_user` dependency from `src/services/auth.py` to authenticate and authorize the request.
- Calls `refresh_token_service.get_user_tokens` from `src/services/refresh_token.py` to retrieve token information.
- Relies on `AsyncSession` from `get_db` for database operations.

## Authentication

### Requirements
Authentication is mandatory and handled via the `get_current_active_user` dependency.
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user exists and is authenticated.

### Required Headers
- `Authorization`: Bearer token (required for authentication; validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- The authenticated user must be active (`user.is_active` must be `True`).
- No additional permission checks are performed.

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
The response is a list of `TokenInfo` objects (from `src/schemas/auth.py`).

Each `TokenInfo` object contains:
- **id** (UUID): The unique identifier of the refresh token.
- **user_id** (UUID): The ID of the user who owns the token.
- **expires_at** (datetime): The expiration timestamp of the token.
- **revoked_at** (datetime, optional): The revocation timestamp if the token has been revoked.
- **revoked_reason** (str, optional): The reason for token revocation.
- **device_info** (str, optional): Information about the device used when creating the token.
- **ip_address** (str, optional): The IP address from which the token was created.
- **user_agent** (str, optional): The user agent string from the request that created the token.
- **created_at** (datetime): The token creation timestamp.
- **last_used_at** (datetime, optional): The timestamp of the last token usage.

### Example Response (JSON)
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "456e7890-e89b-12d3-a456-426614174001",
    "expires_at": "2023-10-31T12:00:00Z",
    "revoked_at": null,
    "revoked_reason": null,
    "device_info": "Chrome/91.0",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "created_at": "2023-10-01T12:00:00Z",
    "last_used_at": "2023-10-15T10:30:00Z"
  },
  {
    "id": "789e0123-e89b-12d3-a456-426614174002",
    "user_id": "456e7890-e89b-12d3-a456-426614174001",
    "expires_at": "2023-11-15T12:00:00Z",
    "revoked_at": "2023-10-20T14:00:00Z",
    "revoked_reason": "User logout",
    "device_info": "Mobile App",
    "ip_address": "10.0.0.50",
    "user_agent": "Custom Mobile App/1.0",
    "created_at": "2023-10-10T08:00:00Z",
    "last_used_at": "2023-10-19T16:45:00Z"
  }
]
```

## Error Responses

### 401 Unauthorized
- **Status Code**: 401
- **Message**: "Could not validate credentials"
- **Condition**: Triggered when the JWT token is missing, invalid, expired, or the user does not exist.

### 400 Bad Request
- **Status Code**: 400
- **Message**: "Inactive user"
- **Condition**: Triggered when the authenticated user account is not active (`is_active` is `False`).

## Testing Example

### Example Command
```bash
curl -X GET 'http://localhost:8000/api/v1/auth/tokens' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImV4cCI6MTY5NjE2MDAwMH0.example'
```

### Valid Payload
No payload required.

### Expected Output
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "456e7890-e89b-12d3-a456-426614174001",
    "expires_at": "2023-10-31T12:00:00Z",
    "revoked_at": null,
    "revoked_reason": null,
    "device_info": "Chrome/91.0",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "created_at": "2023-10-01T12:00:00Z",
    "last_used_at": "2023-10-15T10:30:00Z"
  }
]
```

Note: The response is an array of `TokenInfo` objects. The actual data will reflect the authenticated user's refresh tokens. Revoked tokens are included with `revoked_at` and `revoked_reason` populated.