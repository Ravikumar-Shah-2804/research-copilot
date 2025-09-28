# API Keys Create Endpoint Documentation

## Endpoint Overview

### URL Path
`/api-keys/` (assuming the router is mounted at `/api-keys` in the main application; the endpoint is defined as `@router.post("/")`)

### HTTP Method
POST

### Description
This endpoint allows authenticated users to create a new API key for a specified organization. The API key is generated securely and returned in the response only once, after which it cannot be retrieved again. The endpoint enforces strict authentication and authorization checks to ensure only authorized users can create keys.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `api_key_service.create_api_key` (from `src/services/api_key.py`) to perform the creation logic, which generates the key and stores it securely.
- Uses Pydantic schemas from `src/schemas/role.py` for validation.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency, which decodes and verifies a JWT token).

## Authorization

### Requirements
- If the user is a superuser (`current_user.is_superuser` is `True`), no additional checks are performed; they can create API keys for any organization.
- For non-superusers:
  - The user's `organization_id` must match the `organization_id` in the request body.
  - The user must have the "api_keys" resource with "write" action permission (checked via `current_user.has_permission("api_keys", "write")`).

## Request

### Request Body Schema
The request body must conform to the `APIKeyCreate` schema (from `src/schemas/role.py`). All fields are validated using Pydantic.

- **name** (str, required): The name of the API key. Constraints: minimum length 1, maximum length 100.
- **organization_id** (UUID, required): The UUID of the organization to which the API key belongs.
- **description** (str, optional): A description of the API key. Defaults to `None`.
- **expires_at** (datetime, optional): The expiration date and time for the API key. Defaults to `None` (no expiration).
- **permissions** (List[str], optional): A list of permission strings associated with the API key. Defaults to an empty list (`[]`).
- **rate_limit** (int, optional): The rate limit for the API key (requests per unit time, assumed). Constraints: minimum value 1, maximum value 100000. Defaults to 1000.

### Content-Type
- `application/json`

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response conforms to the `APIKeyWithSecret` schema (extends `APIKeyResponse` and adds the `key` field). This is returned only upon successful creation, and the `key` field contains the plain-text API key (shown only once).

- **id** (UUID): The unique identifier of the API key.
- **organization_id** (UUID): The UUID of the associated organization.
- **created_by** (UUID): The UUID of the user who created the API key.
- **is_active** (bool): Whether the API key is active. Always `True` for newly created keys.
- **last_used_at** (datetime, optional): The last usage timestamp. `None` for newly created keys.
- **created_at** (datetime): The creation timestamp.
- **updated_at** (datetime): The last update timestamp (same as `created_at` for new keys).
- **name** (str): The name of the API key.
- **description** (str, optional): The description of the API key.
- **expires_at** (datetime, optional): The expiration timestamp.
- **permissions** (List[str]): The list of permissions.
- **rate_limit** (int): The rate limit value.
- **key** (str): The plain-text API key value (e.g., a generated secret string; only included in this response and not retrievable later).

### Example Response (JSON)
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "organization_id": "456e7890-e89b-12d3-a456-426614174001",
  "created_by": "789e0123-e89b-12d3-a456-426614174002",
  "is_active": true,
  "last_used_at": null,
  "created_at": "2023-10-01T12:00:00Z",
  "updated_at": "2023-10-01T12:00:00Z",
  "name": "My API Key",
  "description": "Key for testing",
  "expires_at": null,
  "permissions": ["read", "write"],
  "rate_limit": 1000,
  "key": "sk-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Cannot create API keys for other organizations"
- **Condition**: Triggered if the authenticated user is not a superuser and their `organization_id` does not match the `organization_id` in the request body.

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Insufficient permissions to create API keys"
- **Condition**: Triggered if the authenticated user is not a superuser, belongs to the correct organization, but lacks the "api_keys:write" permission.

### 400 Bad Request
- **Status Code**: 400
- **Message**: Dynamic string based on the exception from `api_key_service.create_api_key` (e.g., validation errors, database issues, or service-specific failures).
- **Condition**: Any exception raised during API key creation in the service layer.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/api-keys/' -Method POST -ContentType 'application/json' -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"} -Body '{"name": "Test API Key", "organization_id": "03c25acb-1b03-4f35-ac62-7c112d096114"}'
```

### Valid Payload
```json
{
  "name": "Test API Key",
  "organization_id": "03c25acb-1b03-4f35-ac62-7c112d096114"
}
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"name":"Test API Key","description":null,"expires_at":null,"permissions":[],"rate_limit":1000,"id":"b3a5fd31-4444-42e0-8e53-08eb6d821cd0","organization_id":"03c25acb-1b03-4f35-ac62-7c112d096114","created_by":"...","is_active":true,"last_used_at":null,"created_at":"...","updated_at":"...","key":"..."}
```

Note: The full JSON response includes all fields as per the `APIKeyWithSecret` schema. The `key` field is included only in this creation response and cannot be retrieved later. Timestamps (`created_at`, `updated_at`) and UUIDs (`id`, `created_by`) will be dynamically generated.