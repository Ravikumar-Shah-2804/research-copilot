# Papers Create Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/papers/` (assuming the router is mounted at `/api/v1/papers` in the main application; the endpoint is defined as `@router.post("/")`)

### HTTP Method
POST

### Description
This endpoint allows authenticated users to create a new research paper. The paper is created with initial metadata and set to "pending" ingestion status. The endpoint enforces authentication and performs database validation to ensure data integrity.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `PaperRepository.create` (from `src/repositories/paper.py`) to perform the creation logic, which validates uniqueness by arXiv ID and sets default values.
- Uses Pydantic schemas from `src/schemas/paper.py` for validation.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- No specific authorization checks beyond authentication; any active authenticated user can create papers.

## Request

### Request Body Schema
The request body must conform to the `PaperCreate` schema (from `src/schemas/paper.py`). All fields are validated using Pydantic.

- **arxiv_id** (str, required): The arXiv identifier for the paper.
- **title** (str, required): The title of the research paper.
- **authors** (List[str], required): A list of author names.
- **abstract** (str, required): The abstract or summary of the paper.
- **categories** (List[str], required): A list of arXiv category codes.
- **published_date** (datetime, required): The publication date and time.
- **pdf_url** (str, required): The URL to the PDF file.
- **doi** (str, optional): The Digital Object Identifier. Defaults to `None`.
- **journal_ref** (str, optional): Journal reference information. Defaults to `None`.
- **comments** (str, optional): Additional comments. Defaults to `None`.
- **source** (str, optional): The source of the paper. Defaults to `"arxiv"`.
- **tags** (List[str], optional): User-defined tags. Defaults to `None`.
- **keywords** (List[str], optional): Keywords associated with the paper. Defaults to `None`.

### Content-Type
- `application/json`

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response conforms to the `PaperResponse` schema (from `src/schemas/paper.py`).

- **id** (UUID): The unique identifier of the paper.
- **arxiv_id** (str): The arXiv identifier.
- **doi** (str, optional): The DOI.
- **title** (str): The paper title.
- **authors** (List[str]): List of authors.
- **abstract** (str): The abstract.
- **categories** (List[str]): List of categories.
- **published_date** (datetime): Publication date.
- **pdf_url** (str): PDF URL.
- **raw_text** (str, optional): Extracted text content. `None` for new papers.
- **sections** (List[PaperSection], optional): Structured sections. `None` for new papers.
- **references** (List[PaperReference], optional): Extracted references. `None` for new papers.
- **parser_used** (ParserType, optional): PDF parser used. `None` for new papers.
- **parser_metadata** (Dict[str, Any], optional): Parser metadata. `None` for new papers.
- **pdf_processed** (bool): Whether PDF has been processed. `False` for new papers.
- **pdf_processing_date** (datetime, optional): Processing date. `None` for new papers.
- **pdf_file_size** (str, optional): PDF file size. `None` for new papers.
- **pdf_page_count** (int, optional): Number of pages. `None` for new papers.
- **tags** (List[str], optional): Tags.
- **keywords** (List[str], optional): Keywords.
- **journal_ref** (str, optional): Journal reference.
- **comments** (str, optional): Comments.
- **ingestion_status** (IngestionStatus): Status, set to `"pending"` for new papers.
- **ingestion_attempts** (int): Number of ingestion attempts. `0` for new papers.
- **last_ingestion_attempt** (datetime, optional): Last attempt timestamp. `None` for new papers.
- **ingestion_errors** (List[Dict[str, Any]], optional): Ingestion errors. `None` for new papers.
- **created_at** (datetime): Creation timestamp.
- **updated_at** (datetime): Last update timestamp.
- **created_by** (UUID): User who created the paper.
- **last_modified_by** (UUID, optional): User who last modified. `None` for new papers.
- **source** (str): Source of the paper.
- **quality_score** (float, optional): Quality score. `None` for new papers.
- **duplicate_of** (UUID, optional): Duplicate reference. `None` for new papers.

### Example Response (JSON)
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "arxiv_id": "2101.12345",
  "doi": null,
  "title": "Sample Research Paper",
  "authors": ["Author One", "Author Two"],
  "abstract": "This is a sample abstract...",
  "categories": ["cs.AI"],
  "published_date": "2021-01-15T00:00:00Z",
  "pdf_url": "https://arxiv.org/pdf/2101.12345.pdf",
  "raw_text": null,
  "sections": null,
  "references": null,
  "parser_used": null,
  "parser_metadata": null,
  "pdf_processed": false,
  "pdf_processing_date": null,
  "pdf_file_size": null,
  "pdf_page_count": null,
  "tags": null,
  "keywords": null,
  "journal_ref": null,
  "comments": null,
  "ingestion_status": "pending",
  "ingestion_attempts": 0,
  "last_ingestion_attempt": null,
  "ingestion_errors": null,
  "created_at": "2023-10-01T12:00:00Z",
  "updated_at": "2023-10-01T12:00:00Z",
  "created_by": "456e7890-e89b-12d3-a456-426614174001",
  "last_modified_by": null,
  "source": "arxiv",
  "quality_score": null,
  "duplicate_of": null
}
```

## Error Responses

### 400 Bad Request
- **Status Code**: 400
- **Message**: "Failed to create paper: {error details}"
- **Condition**: Triggered when the `PaperRepository.create` method raises an exception, such as integrity errors (duplicate arXiv ID) or validation failures.

## Testing Example

### Example Command
```bash
curl -X POST 'http://localhost:8000/api/v1/papers/' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I' \
  -d '{
    "arxiv_id": "2101.12345",
    "title": "Sample Research Paper",
    "authors": ["Author One", "Author Two"],
    "abstract": "This is a sample abstract for testing.",
    "categories": ["cs.AI"],
    "published_date": "2021-01-15T00:00:00Z",
    "pdf_url": "https://arxiv.org/pdf/2101.12345.pdf"
  }'
```

### Valid Payload
```json
{
  "arxiv_id": "2101.12345",
  "title": "Sample Research Paper",
  "authors": ["Author One", "Author Two"],
  "abstract": "This is a sample abstract for testing.",
  "categories": ["cs.AI"],
  "published_date": "2021-01-15T00:00:00Z",
  "pdf_url": "https://arxiv.org/pdf/2101.12345.pdf"
}
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"id":"123e4567-e89b-12d3-a456-426614174000","arxiv_id":"2101.12345","doi":null,"title":"Sample Research Paper","authors":["Author One","Author Two"],"abstract":"This is a sample abstract for testing.","categories":["cs.AI"],"published_date":"2021-01-15T00:00:00Z","pdf_url":"https://arxiv.org/pdf/2101.12345.pdf","raw_text":null,"sections":null,"references":null,"parser_used":null,"parser_metadata":null,"pdf_processed":false,"pdf_processing_date":null,"pdf_file_size":null,"pdf_page_count":null,"tags":null,"keywords":null,"journal_ref":null,"comments":null,"ingestion_status":"pending","ingestion_attempts":0,"last_ingestion_attempt":null,"ingestion_errors":null,"created_at":"2023-10-01T12:00:00Z","updated_at":"2023-10-01T12:00:00Z","created_by":"456e7890-e89b-12d3-a456-426614174001","last_modified_by":null,"source":"arxiv","quality_score":null,"duplicate_of":null}
```

Note: The full JSON response includes all fields as per the `PaperResponse` schema. Timestamps (`created_at`, `updated_at`) and UUIDs (`id`, `created_by`) will be dynamically generated. The `ingestion_status` is set to `"pending"` for newly created papers.