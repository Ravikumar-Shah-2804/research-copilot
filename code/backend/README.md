# Research Copilot

Enterprise-grade Research Copilot system with OpenRouter DeepSeek integration for intelligent research paper analysis and retrieval.

## Features

- **FastAPI Backend**: High-performance async API with automatic OpenAPI documentation
- **JWT Authentication**: Secure user authentication and authorization
- **PostgreSQL Database**: Robust data storage with SQLAlchemy ORM
- **OpenSearch**: Hybrid search capabilities (text + vector)
- **Redis Caching**: High-performance caching layer
- **OpenRouter DeepSeek**: Advanced LLM integration for RAG
- **Enterprise Security**: Rate limiting, CORS, security headers
- **Monitoring**: Prometheus metrics, health checks, structured logging
- **Docker Compose**: Complete containerized deployment

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   PostgreSQL    │    │    OpenSearch   │
│                 │    │                 │    │                 │
│ - REST API      │◄──►│ - User Data     │    │ - Hybrid Search │
│ - Auth & Authz  │    │ - Paper Data    │    │ - Vector Index  │
│ - RAG Engine    │    │ - Search Logs   │    │ - Text Index    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                    ┌─────────────────┐    ┌─────────────────┐
                    │      Redis      │    │   OpenRouter    │
                    │                 │    │   DeepSeek      │
                    │ - Cache Layer   │    │                 │
                    │ - Session Store │    │ - LLM Service   │
                    └─────────────────┘    │ - RAG Generation│
                                           └─────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.9+ (for local development)
- OpenRouter API key

### Setup

1. **Clone and navigate to the project**
   ```bash
   cd research-copilot
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenRouter API key and other settings
   ```

3. **Start the services**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - OpenSearch Dashboard: http://localhost:5601

### Local Development

1. **Install dependencies**
   ```bash
   pip install -e .
   ```

2. **Run the application**
   ```bash
   uvicorn src.main:app --reload
   ```

## API Endpoints

### Authentication
- `POST /api/v1/auth/token` - Login
- `POST /api/v1/auth/register` - Register
- `GET /api/v1/auth/me` - Get current user

### Research Papers
- `GET /api/v1/papers/` - List papers
- `POST /api/v1/papers/` - Create paper
- `GET /api/v1/papers/{id}` - Get paper
- `PUT /api/v1/papers/{id}` - Update paper
- `DELETE /api/v1/papers/{id}` - Delete paper

### Search & RAG
- `POST /api/v1/search/text` - Text search
- `POST /api/v1/search/hybrid` - Hybrid search
- `POST /api/v1/search/rag` - RAG query

### Health & Monitoring
- `GET /health` - Health check
- `GET /api/v1/ping` - Simple ping
- `GET /metrics` - Prometheus metrics

### Admin (Superuser only)
- `GET /api/v1/admin/stats` - System statistics
- `POST /api/v1/admin/cache/clear` - Clear cache

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment (development/production) | development |
| `DATABASE_URL` | PostgreSQL connection URL | - |
| `REDIS_URL` | Redis connection URL | redis://localhost:6379 |
| `OPENSEARCH_URL` | OpenSearch URL | http://localhost:9200 |
| `OPENROUTER_API_KEY` | OpenRouter API key | - |
| `JWT_SECRET_KEY` | JWT secret key | - |
| `LOG_LEVEL` | Logging level | INFO |

### Services Configuration

- **FastAPI**: Port 8000
- **PostgreSQL**: Port 5432, Database: research_copilot
- **Redis**: Port 6379
- **OpenSearch**: Port 9200
- **Prometheus Metrics**: Port 8001

## Development

### Project Structure

```
research-copilot/
├── src/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── database.py          # Database connection
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── routers/             # API endpoints
│   ├── services/            # Business logic
│   ├── middlewares/         # Custom middleware
│   └── utils/               # Utilities
├── tests/                   # Test suite
├── docker-compose.yml       # Docker services
├── Dockerfile              # Application container
├── pyproject.toml          # Python dependencies
└── .env.example            # Environment template
```

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

### Code Quality

```bash
# Format code
black src/

# Sort imports
isort src/

# Type checking
mypy src/

# Linting
flake8 src/
```

## Deployment

### Production Deployment

1. **Update environment variables**
   ```bash
   # Set production values in .env
   ENVIRONMENT=production
   DEBUG=False
   ```

2. **Build and deploy**
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

3. **Scale services**
   ```bash
   docker-compose up -d --scale api=3
   ```

### Monitoring

- **Health Checks**: `/health` endpoint
- **Metrics**: `/metrics` endpoint (Prometheus format)
- **Logs**: Structured JSON logging
- **OpenSearch Dashboard**: Service monitoring

## Security

- JWT-based authentication
- Password hashing with bcrypt
- Rate limiting (60 requests/minute)
- CORS protection
- Security headers (HSTS, CSP, etc.)
- Input validation with Pydantic

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For support and questions:
- Documentation: https://research-copilot.com/docs
- Issues: https://github.com/research-copilot/issues
- Email: support@researchcopilot.com