# Auth Register Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/auth/register`

### HTTP Method
POST

### Description
This endpoint allows new users to register an account by providing email, username, and password. It performs comprehensive input validation, checks for existing users, and creates a new user record in the database with proper security measures including password hashing and audit logging.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Uses `User` model from `src/models/user.py` for database interactions.
- Calls `get_password_hash` from `src/services/auth.py` for secure password hashing.
- Utilizes `audit_logger` and `security_logger` from `src/utils/security_logging.py` for security monitoring and audit trails.

## Authentication

### Requirements
No authentication is required for user registration.

### Required Headers
None

## Authorization

### Requirements
No authorization checks are performed for user registration.

## Request

### Request Body Schema
The request body must conform to the `UserCreate` schema (from `src/schemas/auth.py`). All fields are validated using Pydantic.

- **email** (EmailStr, required): The user's email address. Must be a valid email format.
- **username** (str, required): The user's username. Constraints: minimum length 3, maximum length 50.
- **password** (str, required): The user's password. Constraints: minimum length 8.
- **full_name** (str, optional): The user's full name. Defaults to `None`.

### Content-Type
- `application/json`

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response conforms to the `UserResponse` schema (from `src/schemas/auth.py`).

- **id** (UUID): The unique identifier of the newly created user.
- **email** (EmailStr): The user's email address.
- **username** (str): The user's username.
- **full_name** (str, optional): The user's full name.
- **is_active** (bool): Whether the user account is active. Always `True` for newly registered users.
- **is_superuser** (bool): Whether the user has superuser privileges. Always `False` for newly registered users.
- **organization_id** (UUID, optional): The user's organization ID. `None` for newly registered users.
- **created_at** (datetime): The account creation timestamp.
- **updated_at** (datetime): The last update timestamp (same as `created_at` for new users).

### Example Response (JSON)
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "username": "testuser",
  "full_name": "Test User",
  "is_active": true,
  "is_superuser": false,
  "organization_id": null,
  "created_at": "2023-10-01T12:00:00Z",
  "updated_at": "2023-10-01T12:00:00Z"
}
```

## Error Responses

### 400 Bad Request
- **Status Code**: 400
- **Message**: "Username cannot be empty"
- **Condition**: Triggered when the username field is empty or contains only whitespace.

### 400 Bad Request
- **Status Code**: 400
- **Message**: "Email cannot be empty"
- **Condition**: Triggered when the email field is empty or contains only whitespace.

### 400 Bad Request
- **Status Code**: 400
- **Message**: "Password cannot be empty"
- **Condition**: Triggered when the password field is empty or contains only whitespace.

### 400 Bad Request
- **Status Code**: 400
- **Message**: "Username must be between 3 and 50 characters"
- **Condition**: Triggered when the username length is less than 3 or greater than 50 characters.

### 400 Bad Request
- **Status Code**: 400
- **Message**: "Password must be at least 8 characters long"
- **Condition**: Triggered when the password length is less than 8 characters.

### 400 Bad Request
- **Status Code**: 400
- **Message**: "Username or email already registered"
- **Condition**: Triggered when a user with the same username or email already exists in the database.

### 503 Service Unavailable
- **Status Code**: 503
- **Message**: "Service temporarily unavailable"
- **Condition**: Triggered when database operations fail due to SQLAlchemy errors during user creation.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Registration failed"
- **Condition**: Triggered for any unexpected errors during the registration process.

## Testing Example

### Example Command
```bash
curl -X POST 'http://localhost:8000/api/v1/auth/register' \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "newuser@example.com",
    "username": "newuser",
    "password": "securepassword123",
    "full_name": "New User"
  }'
```

### Valid Payload
```json
{
  "email": "newuser@example.com",
  "username": "newuser",
  "password": "securepassword123",
  "full_name": "New User"
}
```

### Expected Output
```json
{
  "id": "456e7890-e89b-12d3-a456-426614174001",
  "email": "newuser@example.com",
  "username": "newuser",
  "full_name": "New User",
  "is_active": true,
  "is_superuser": false,
  "organization_id": null,
  "created_at": "2023-10-01T12:00:00Z",
  "updated_at": "2023-10-01T12:00:00Z"
}
```

Note: The `id`, `created_at`, and `updated_at` fields will be dynamically generated. The response includes all fields from the `UserResponse` schema.