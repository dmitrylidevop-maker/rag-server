# RAG Server - AI Coding Agent Instructions

## Project Overview
FastAPI-based REST server for managing 384-dimensional embeddings in PostgreSQL with pgvector extension. Uses `all-MiniLM-L6-v2` model from sentence-transformers for automatic text-to-vector conversion. Designed for RAG (Retrieval-Augmented Generation) applications with LLMs.

## Architecture

### Core Components
- **FastAPI Application** (`main.py`): Single-file REST API with 4 endpoints
- **Embedding Service** (`embedding_service.py`): Text-to-vector conversion using sentence-transformers
- **PostgreSQL + pgvector**: External database (not containerized) with HNSW indexing
- **Docker**: Standalone container (no docker-compose) connecting to external DB

### Database Schema
Table: `embedding_store`
- `id` (UUID): Auto-generated primary key
- `user_id` (VARCHAR(9)): User identifier for filtering
- `content` (TEXT): Original text content
- `embedding` (VECTOR(384)): Auto-generated from text using all-MiniLM-L6-v2
- `source` (VARCHAR(255)): Source of content (optional)
- `metadata` (JSONB): Additional metadata as JSON (optional)
- `created` (TIMESTAMPTZ): Auto-timestamp with timezone

**Indexes:**
- HNSW index on `embedding` using `vector_cosine_ops` for fast similarity search
- B-tree index on `user_id` for filtering
- B-tree index on `source` for filtering

## Development Workflow

### Environment Setup
1. Copy `.env-tmp` to `.env` and configure real credentials
2. Run `./install.sh` which creates a Python virtual environment in `venv/`
3. Always activate venv before running: `source venv/bin/activate`

### Running the Server
**Local:** `source venv/bin/activate && python3 main.py`
**Docker:** `docker run -d -p 8000:8000 --env-file .env --name rag-server rag-server:latest`

### Configuration
All config via environment variables (see `.env-tmp`):
- `POSTGRES_*`: External DB connection (host at 192.168.31.129:5435)
- `PORT`: Server port (default: 8000)

## Code Patterns

### Embedding Service
- Global singleton pattern: `get_embedding_service()` returns cached instance
- Model loaded once at startup in lifespan context manager
- `encode(text)` converts single text to 384-dim vector
- `encode_batch(texts)` for multiple texts (more efficient)
- Model: `all-MiniLM-L6-v2` (sentence-transformers)

### Database Connection
- Direct `psycopg2` connections (no ORM)
- Connection created per request, no connection pooling
- Use `RealDictCursor` for dict-like results
- Explicit `conn.commit()` and `conn.close()` required

### Vector Handling
```python
# Convert Python list to pgvector format
embedding_str = "[" + ",".join(map(str, embedding_list)) + "]"
# Use ::vector cast in SQL
cur.execute("... %s::vector", (embedding_str,))
```

### Search Pattern
Uses cosine distance operator `<=>` which returns lower values for more similar vectors:
```python
embedding <=> %s::vector AS distance
ORDER BY distance  # Lower is more similar
```

### Lifespan Management
FastAPI `@asynccontextmanager` for startup/shutdown:
- Tests DB connection on startup
- Loads embedding model on startup (prints dimension info)
- Does not fail fast if errors occur

## API Endpoints

1. **POST /content**: Add content (accepts text + optional source/metadata, auto-generates embedding) → 201 Created
2. **DELETE /content/{id}**: Remove by UUID → 200 OK with response message (or 404)
3. **POST /search**: Search by query text with optional filters:
   - `user_id`: Filter by user
   - `source`: Filter by source
   - `distance_threshold`: Maximum cosine distance (uses DISTANCE_THRESHOLD env default if omitted)
   - `created_after`: Filter by creation timestamp (ISO format, optional)
   - `created_before`: Filter by creation timestamp (ISO format, optional)
4. **GET /health**: Health check returning DB connection status

**Key changes from typical embedding APIs:**
- Clients send **text**, not vectors
- Server handles all embedding generation internally
- Search accepts query text, not embedding vectors
- Supports metadata storage and filtering
- Timestamp-based filtering for temporal queries

Interactive docs: `/docs` (Swagger UI) and `/redoc`

## Dependencies
- **FastAPI 0.104.1**: Web framework
- **uvicorn 0.24.0**: ASGI server
- **psycopg2-binary 2.9.9**: PostgreSQL driver
- **pydantic 2.5.0**: Validation (included with FastAPI)
- **sentence-transformers 2.7.0**: Embedding model library
- **torch 2.9.1**: PyTorch (required by sentence-transformers)
- **numpy <2.0.0**: Numerical operations (1.26.4 compatible with torch 2.2.0)

## Docker Specifics
- Uses `python:3.11-slim` base image
- Installs `gcc` and `postgresql-client` system dependencies
- Port configured via `${PORT:-8000}` shell expansion in CMD
- Uses `sh -c` wrapper to evaluate PORT variable

## Key Conventions

### Error Handling
- Catch all database exceptions as `HTTPException(500)`
- 404 for missing content in DELETE
- Pydantic validates request bodies (automatic 422 on validation errors)
- DELETE returns 200 OK with JSON response: `{"message": "Content deleted successfully", "id": "uuid"}`

### Data Validation
- Embedding must be exactly 384 floats (auto-generated, not validated in API)
- `user_id` max 9 characters
- Search `limit` between 1-100, default 10
- Content text has no length limit (TEXT field)
- `created_after`/`created_before` must be valid ISO timestamp strings (converted to timestamptz in SQL)
- `distance_threshold` uses environment default (DISTANCE_THRESHOLD=0.7) if not provided

### File Structure
Two main Python files:
- `main.py`: FastAPI application with all endpoints
- `embedding_service.py`: Singleton service for text-to-vector conversion

## Common Tasks

**Add new endpoint:** Add function with `@app.get/post/delete` decorator in `main.py`
**Change vector dimension:** Update VECTOR(384) in `init.sql`, change model in `embedding_service.py`
**Modify index:** Edit `CREATE INDEX` statement in `init.sql` (currently HNSW with cosine ops)
**Update dependencies:** Edit `requirements.txt`, rebuild venv and Docker image
**Change embedding model:** Modify `model_name` parameter in `EmbeddingService.__init__()` and update vector dimension

## External Dependencies
- PostgreSQL server must have `pgvector` extension pre-installed
- Database initialization via `init.sql` (run by `install.sh` or manually with `psql`)
- No migrations framework - schema changes applied directly via SQL
