# RAG Server

A REST API server for managing embeddings used in Retrieval-Augmented Generation (RAG) for Large Language Models (LLMs).

## Features

- **Add Content**: Store text content with automatically generated embedding vectors
- **Remove Content**: Delete content by ID
- **Search Content**: Find relevant content using natural language queries
- **Health Check**: Monitor server and database status
- **Automatic Embeddings**: Uses all-MiniLM-L6-v2 model for text-to-vector conversion

## Prerequisites

- Python 3.8 or higher
- Docker
- PostgreSQL with pgvector extension
- Access to a PostgreSQL database server

## Database Setup

The server requires PostgreSQL with the `pgvector` extension installed. The database schema includes:

- **embedding_store** table with columns:
  - `id` (UUID): Unique identifier
  - `user_id` (VARCHAR(9)): User identifier
  - `content` (TEXT): Original text content
  - `embedding` (VECTOR(384)): 384-dimensional embedding vector (all-MiniLM-L6-v2)
  - `source` (VARCHAR(255)): Source of the content (optional)
  - `metadata` (JSONB): Additional metadata as JSON (optional)
  - `created` (TIMESTAMPTZ): Creation timestamp

## Installation

### Quick Setup

1. Clone or download this repository
2. Copy the example environment file and configure with your real credentials:
   ```bash
   cp .env-tmp .env
   ```
   
3. Edit the `.env` file with your PostgreSQL credentials and server port:
   ```
   POSTGRES_HOST=0.0.0.0
   POSTGRES_PORT=5435
   POSTGRES_DB=postgres
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=password
   PORT=8000
   ```

4. Run the installation script:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

The installation script will:
- Test database connectivity
- Check for pgvector extension
- Initialize the database schema
- Create a Python virtual environment
- Install Python dependencies
- Build the Docker image

### Manual Setup

1. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize the database**:
   ```bash
   psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -f init.sql
   ```

4. **Build Docker image** (optional):
   ```bash
   docker build -t rag-server:latest .
   ```

## Running the Server

### Option 1: Run Locally with Python

```bash
source venv/bin/activate
python3 main.py
```

The server will start on `http://localhost:8000`

### Option 2: Run with Docker

```bash
docker run -d -p 8000:8000 \
  --env-file .env \
  --name rag-server \
  rag-server:latest
```

To stop the container:
```bash
docker stop rag-server
docker rm rag-server
```

## API Endpoints

### Health Check
```
GET /health
```
Returns the health status of the service and database connection.

**Response**:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### Add Content
```
POST /content
```
Add new content. The server automatically generates the embedding vector from the provided text.

**Request Body**:
```json
{
  "user_id": "USER12345",
  "content": "This is the text content to store",
  "source": "document.pdf",  // optional
  "metadata": {"page": 1, "section": "intro"}  // optional
}
```

**Response** (201 Created):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "USER12345",
  "content": "This is the text content to store",
  "created": "2024-11-16T15:30:00Z"
}
```

### Remove Content
```
DELETE /content/{content_id}
```
Remove content by its UUID.

**Response**: 200 OK (success) or 404 Not Found

```json
{
  "message": "Content deleted successfully",
  "id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Search Content
```
POST /search
```
Search for relevant content using text query. The server automatically generates the embedding vector from the query text.

**Request Body**:
```json
{
  "query": "Search query text",
  "limit": 10,  // optional, default 10, max 100
  "user_id": "USER12345",  // optional filter
  "source": "document.pdf",  // optional filter
  "distance_threshold": 0.5,  // optional, max cosine distance (default from DISTANCE_THRESHOLD env)
  "created_after": "2024-01-01T00:00:00Z",  // optional, ISO timestamp
  "created_before": "2024-12-31T23:59:59Z"  // optional, ISO timestamp
}
```

**Response**:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "USER12345",
    "content": "Relevant text content",
    "source": "document.pdf",
    "metadata": {"page": 1},
    "distance": 0.123,
    "created": "2024-11-16T15:30:00Z"
  }
]
```

Results are sorted by cosine distance (lower is more similar).

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| POSTGRES_HOST | PostgreSQL host address | 192.168.31.129 |
| POSTGRES_PORT | PostgreSQL port | 5435 |
| POSTGRES_DB | Database name | postgres |
| POSTGRES_USER | Database user | postgres |
| POSTGRES_PASSWORD | Database password | Qwsa2025 |
| PORT | Server port | 8000 |
| DISTANCE_THRESHOLD | Default max distance for search | 0.7 |

## Example Usage with curl

### Health Check
```bash
curl http://localhost:3011/health
```

### Add Content
```bash
curl -X POST http://localhost:8000/content \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER12345",
    "content": "Sample text to store and automatically embed",
    "source": "sample.txt",
    "metadata": {"category": "example"}
  }'
```

### Search
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find relevant content about this topic",
    "limit": 5,
    "distance_threshold": 0.7,
    "source": "sample.txt",
    "created_after": "2024-01-01T00:00:00Z"
  }'
```

### Remove Content
```bash
curl -X DELETE http://localhost:8000/content/550e8400-e29b-41d4-a716-446655440000
```

## Docker Management

### View logs
```bash
docker logs rag-server
```

### Access container shell
```bash
docker exec -it rag-server /bin/bash
```

### Rebuild image
```bash
docker build -t rag-server:latest .
```

### Run with custom environment variables
```bash
docker run -d -p 8000:8000 \
  -e POSTGRES_HOST=your-host \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_DB=your-db \
  -e POSTGRES_USER=your-user \
  -e POSTGRES_PASSWORD=your-password \
  --name rag-server rag-server:latest
```

## Troubleshooting

### Database connection issues
1. Verify PostgreSQL is running: `psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB`
2. Check firewall rules allow connections to the PostgreSQL port
3. Verify credentials in `.env` file

### pgvector extension not found
Install pgvector on your PostgreSQL server: https://github.com/pgvector/pgvector

### Port already in use
Change the port mapping:
```bash
docker run -d -p 8080:8000 --env-file .env --name rag-server rag-server:latest
```

## License

MIT
