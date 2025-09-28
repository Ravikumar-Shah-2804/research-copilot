# Research Copilot RAG System

## Overview

The Research Copilot RAG (Retrieval-Augmented Generation) system provides intelligent question-answering capabilities for research papers using OpenRouter's DeepSeek LLM models. The system combines advanced search capabilities with state-of-the-art language models to deliver accurate, contextual answers based on research literature.

## Architecture

### Core Components

1. **OpenRouter DeepSeek Client** (`src/services/openrouter.py`)
   - Enhanced HTTP client with retry logic and error handling
   - Rate limiting and quota management
   - Streaming response support
   - Usage tracking and cost monitoring

2. **RAG Pipeline** (`src/services/rag_pipeline.py`)
   - Orchestrates the entire RAG process
   - Context retrieval from OpenSearch
   - Intelligent prompt engineering
   - Confidence scoring and result formatting

3. **LLM Service Architecture** (`src/services/llm/`)
   - Factory pattern for LLM service creation
   - Abstract base class for extensibility
   - Support for multiple LLM providers
   - Standardized interface for all LLM operations

4. **RAG API Endpoints** (`src/routers/rag.py`)
   - `/api/v1/rag/generate` - Generate answers
   - `/api/v1/rag/stream` - Streaming responses
   - `/api/v1/rag/batch` - Batch processing
   - `/api/v1/rag/models` - Available models
   - `/api/v1/rag/health` - System health
   - `/api/v1/rag/usage` - Usage statistics

## Key Features

### Enterprise Features
- **Rate Limiting**: Configurable rate limits for different operations
- **Audit Logging**: Comprehensive logging of all RAG operations
- **Usage Tracking**: Token usage and cost monitoring
- **Health Monitoring**: Real-time system health checks
- **Error Handling**: Robust error handling with fallback mechanisms

### Performance Optimizations
- **Context Compression**: Intelligent context size management
- **Response Caching**: Multi-level caching for improved performance
- **Batch Processing**: Efficient handling of multiple queries
- **Streaming Support**: Real-time response generation

### Search Integration
- **Hybrid Search**: Combines BM25 and vector search
- **Context Retrieval**: Retrieves relevant documents from OpenSearch
- **Relevance Scoring**: Advanced scoring for context quality
- **Source Attribution**: Clear citation of source documents

## Configuration

### Environment Variables

```bash
# OpenRouter Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEEPSEEK_MODEL=deepseek/deepseek-chat

# RAG Settings
RAG_DEFAULT_MODEL=deepseek/deepseek-chat
RAG_MAX_CONTEXT_DOCS=5
RAG_CONTEXT_WINDOW_SIZE=8192
RAG_DEFAULT_TEMPERATURE=0.7
RAG_DEFAULT_MAX_TOKENS=1000
RAG_CACHE_TTL=1800

# Rate Limiting
RAG_RATE_LIMIT_REQUESTS_PER_MINUTE=5
RAG_RATE_LIMIT_STREAMING_REQUESTS_PER_MINUTE=3
RAG_RATE_LIMIT_BATCH_MAX_QUERIES_PER_MINUTE=10
```

### API Usage Examples

#### Generate Answer
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/rag/generate",
    json={
        "query": "What is the difference between supervised and unsupervised learning?",
        "context_limit": 5,
        "max_tokens": 1000,
        "temperature": 0.7
    },
    headers={"Authorization": "Bearer your_token"}
)

result = response.json()
print(f"Answer: {result['answer']}")
print(f"Confidence: {result['confidence']}")
print(f"Sources: {len(result['sources'])}")
```

#### Streaming Response
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/rag/stream",
    json={
        "query": "Explain transformer architecture",
        "context_limit": 3,
        "max_tokens": 1500
    },
    headers={"Authorization": "Bearer your_token"},
    stream=True
)

for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
```

#### Batch Processing
```python
response = requests.post(
    "http://localhost:8000/api/v1/rag/batch",
    json={
        "queries": [
            "What is machine learning?",
            "What is deep learning?",
            "What is reinforcement learning?"
        ],
        "context_limit": 3,
        "max_tokens": 800
    },
    headers={"Authorization": "Bearer your_token"}
)

results = response.json()
for result in results['results']:
    print(f"Q: {result['query']}")
    print(f"A: {result['answer'][:100]}...")
```

## API Reference

### RAG Endpoints

#### POST `/api/v1/rag/generate`
Generate an answer for a single query.

**Request Body:**
```json
{
  "query": "string",
  "context_limit": 5,
  "max_tokens": 1000,
  "temperature": 0.7,
  "search_mode": "hybrid"
}
```

**Response:**
```json
{
  "query": "string",
  "answer": "string",
  "sources": [...],
  "confidence": 0.85,
  "tokens_used": 150,
  "generation_time": 1.2,
  "model": "deepseek/deepseek-chat",
  "context_length": 800,
  "timestamp": "2024-01-01T00:00:00"
}
```

#### POST `/api/v1/rag/stream`
Stream an answer generation.

**Request Body:** Same as `/generate`

**Response:** Server-sent events stream

#### POST `/api/v1/rag/batch`
Process multiple queries in batch.

**Request Body:**
```json
{
  "queries": ["string"],
  "context_limit": 5,
  "max_tokens": 1000,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "results": [...],
  "total_queries": 3,
  "total_tokens": 450,
  "total_time": 3.5,
  "timestamp": "2024-01-01T00:00:00"
}
```

#### GET `/api/v1/rag/models`
Get available LLM models.

**Response:**
```json
{
  "models": [...],
  "default_model": "deepseek/deepseek-chat",
  "timestamp": "2024-01-01T00:00:00"
}
```

#### GET `/api/v1/rag/health`
Get system health status.

**Response:**
```json
{
  "overall_healthy": true,
  "services": {...},
  "timestamp": "2024-01-01T00:00:00"
}
```

#### GET `/api/v1/rag/usage`
Get usage statistics.

**Response:**
```json
{
  "total_requests": 100,
  "total_tokens": 15000,
  "total_cost": 1.5,
  "errors": 2,
  "last_reset": "2024-01-01T00:00:00",
  "timestamp": "2024-01-01T00:00:00"
}
```

## Testing

### Unit Tests
```bash
# Run RAG-specific unit tests
pytest tests/unit/test_openrouter_client.py -v
pytest tests/unit/test_rag_pipeline.py -v
pytest tests/unit/test_llm_factory.py -v
```

### Integration Tests
```bash
# Run RAG API integration tests
pytest tests/integration/test_rag_api.py -v
```

### Test Coverage
```bash
# Run all tests with coverage
pytest --cov=src --cov-report=html
```

## Monitoring and Observability

### Metrics
- Request latency and throughput
- Token usage and costs
- Error rates and types
- Cache hit rates
- Search performance metrics

### Logging
- Structured JSON logging
- Request/response logging
- Error tracking with context
- Audit trails for compliance

### Health Checks
- LLM service connectivity
- Search service availability
- Cache service status
- Database connectivity

## Security Considerations

### Authentication
- JWT-based authentication
- User-specific rate limiting
- Request validation and sanitization

### Data Protection
- Input validation and sanitization
- Secure API key management
- Audit logging for compliance

### Rate Limiting
- Configurable rate limits per user/endpoint
- Burst allowance for legitimate traffic spikes
- Graceful degradation under load

## Performance Tuning

### Caching Strategy
- Multi-level caching (memory, Redis)
- TTL-based cache expiration
- Cache key optimization
- Cache size management

### Context Optimization
- Intelligent context compression
- Relevance-based document ranking
- Token limit management
- Memory-efficient processing

### Concurrent Processing
- Async/await for non-blocking operations
- Connection pooling for external services
- Batch processing for efficiency
- Resource limit management

## Troubleshooting

### Common Issues

1. **Rate Limit Exceeded**
   - Check rate limit configuration
   - Implement exponential backoff
   - Monitor usage patterns

2. **Context Too Long**
   - Adjust `context_limit` parameter
   - Enable context compression
   - Check token limits

3. **Low Confidence Scores**
   - Review search quality
   - Adjust search parameters
   - Check data quality

4. **Slow Response Times**
   - Enable caching
   - Optimize search queries
   - Check system resources

### Debug Mode
Enable debug logging for detailed troubleshooting:
```bash
export LOG_LEVEL=DEBUG
```

## Contributing

### Code Style
- Follow PEP 8 guidelines
- Use type hints for all functions
- Write comprehensive docstrings
- Add unit tests for new features

### Testing
- Maintain >80% test coverage
- Write both unit and integration tests
- Test error conditions and edge cases
- Use fixtures for test data

### Documentation
- Update API documentation for new endpoints
- Maintain changelog for version updates
- Document configuration options
- Provide usage examples

## License

This project is licensed under the MIT License. See the LICENSE file for details.