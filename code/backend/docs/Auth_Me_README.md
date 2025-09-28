# Auth Me Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/auth/me`

### HTTP Method
GET

### Description
This endpoint retrieves the profile information of the currently authenticated user. It validates the JWT token and returns the user's details if the user is active.

### Dependencies
- Uses `get_current_active_user` dependency from `src/services/auth.py` to authenticate and authorize the request.
- Relies on `AsyncSession` from `get_db` for database operations (via the dependency chain).

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
The response conforms to the `UserResponse` schema (from `src/schemas/auth.py`).

- **id** (UUID): The unique identifier of the user.
- **email** (EmailStr): The user's email address.
- **username** (str): The user's username.
- **full_name** (str, optional): The user's full name.
- **is_active** (bool): Whether the user account is active.
- **is_superuser** (bool): Whether the user has superuser privileges.
- **organization_id** (UUID, optional): The user's organization ID.
- **created_at** (datetime): The account creation timestamp.
- **updated_at** (datetime): The last update timestamp.

### Example Response (JSON)
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "username": "testuser",
  "full_name": "Test User",
  "is_active": true,
  "is_superuser": false,
  "organization_id": "456e7890-e89b-12d3-a456-426614174001",
  "created_at": "2023-10-01T12:00:00Z",
  "updated_at": "2023-10-01T12:00:00Z"
}
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
curl -X GET 'http://localhost:8000/api/v1/auth/me' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImV4cCI6MTY5NjE2MDAwMH0.example'
```

### Valid Payload
No payload required.

### Expected Output
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "username": "testuser",
  "full_name": "Test User",
  "is_active": true,
  "is_superuser": false,
  "organization_id": "456e7890-e89b-12d3-a456-426614174001",
  "created_at": "2023-10-01T12:00:00Z",
  "updated_at": "2023-10-01T12:00:00Z"
}
```

Note: The response includes all fields from the `UserResponse` schema. The actual values will reflect the authenticated user's data.