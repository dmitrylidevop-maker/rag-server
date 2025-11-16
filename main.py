from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import uvicorn
from contextlib import asynccontextmanager
from embedding_service import get_embedding_service

# Database connection settings from environment variables
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "192.168.31.129"),
    "port": int(os.getenv("POSTGRES_PORT", "5435")),
    "database": os.getenv("POSTGRES_DB", "postgres"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "Qwsa2025")
}

# Server port from environment
SERVER_PORT = int(os.getenv("PORT", "8000"))

# Default distance threshold from environment
DEFAULT_DISTANCE_THRESHOLD = float(os.getenv("DISTANCE_THRESHOLD", "0.7"))

def get_db_connection():
    """Create and return a database connection"""
    return psycopg2.connect(**DB_CONFIG)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Test database connection and load embedding model
    try:
        conn = get_db_connection()
        conn.close()
        print("Database connection successful")
    except Exception as e:
        print(f"Database connection failed: {e}")
    
    # Load embedding model
    try:
        embedding_service = get_embedding_service()
        print(f"Embedding service initialized (dimension: {embedding_service.get_dimension()})")
    except Exception as e:
        print(f"Embedding service initialization failed: {e}")
    
    yield
    # Shutdown
    print("Shutting down...")

app = FastAPI(
    title="RAG Server",
    description="REST API for managing embeddings for LLM RAG applications",
    version="1.0.0",
    lifespan=lifespan
)

# Pydantic models
class AddContentRequest(BaseModel):
    user_id: str = Field(..., max_length=9, description="User identifier (max 9 characters)")
    content: str = Field(..., description="The text content to store and embed")
    source: Optional[str] = Field(None, max_length=255, description="Source of the content (e.g., filename, URL)")
    metadata: Optional[dict] = Field(None, description="Additional metadata as JSON")

class ContentResponse(BaseModel):
    id: str
    user_id: str
    content: str
    source: Optional[str] = None
    metadata: Optional[dict] = None
    created: str

class SearchRequest(BaseModel):
    query: str = Field(..., description="Query text to search for")
    limit: Optional[int] = Field(10, ge=1, le=100, description="Maximum number of results to return")
    user_id: Optional[str] = Field(None, max_length=9, description="Filter by user_id (optional)")
    source: Optional[str] = Field(None, max_length=255, description="Filter by source (optional)")
    distance_threshold: Optional[float] = Field(None, ge=0.0, le=2.0, description="Maximum cosine distance threshold (optional, uses env default if not provided)")
    created_after: Optional[str] = Field(None, description="Filter records created after this timestamp (ISO format, optional)")
    created_before: Optional[str] = Field(None, description="Filter records created before this timestamp (ISO format, optional)")

class SearchResult(BaseModel):
    id: str
    user_id: str
    content: str
    source: Optional[str] = None
    metadata: Optional[dict] = None
    distance: float
    created: str

class DeleteResponse(BaseModel):
    message: str
    id: str

class HealthResponse(BaseModel):
    status: str
    database: str

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check the health status of the service and database connection"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return HealthResponse(status="healthy", database="connected")
    except Exception as e:
        return HealthResponse(status="unhealthy", database=f"error: {str(e)}")

@app.post("/content", response_model=ContentResponse, status_code=status.HTTP_201_CREATED, tags=["Content"])
async def add_content(request: AddContentRequest):
    """Add new content with automatically generated embedding to the store"""
    try:
        # Generate embedding from text
        embedding_service = get_embedding_service()
        embedding = embedding_service.encode(request.content)
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Convert embedding list to PostgreSQL vector format
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
        
        # Convert metadata dict to JSON string if provided
        import json
        metadata_json = json.dumps(request.metadata) if request.metadata else None
        
        cur.execute(
            """
            INSERT INTO embedding_store (user_id, content, embedding, source, metadata)
            VALUES (%s, %s, %s::vector, %s, %s::jsonb)
            RETURNING id, user_id, content, source, metadata, created
            """,
            (request.user_id, request.content, embedding_str, request.source, metadata_json)
        )
        
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        return ContentResponse(
            id=str(result["id"]),
            user_id=result["user_id"],
            content=result["content"],
            source=result["source"],
            metadata=result["metadata"],
            created=result["created"].isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.delete("/content/{content_id}", response_model=DeleteResponse, tags=["Content"])
async def remove_content(content_id: str):
    """Remove content by its ID"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "DELETE FROM embedding_store WHERE id = %s",
            (content_id,)
        )
        
        if cur.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Content not found")
        
        conn.commit()
        cur.close()
        conn.close()
        
        return DeleteResponse(
            message="Content deleted successfully",
            id=content_id
        )
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/search", response_model=List[SearchResult], tags=["Search"])
async def search_content(request: SearchRequest):
    """Search for relevant content using vector similarity (cosine distance)"""
    try:
        # Generate embedding from query text
        embedding_service = get_embedding_service()
        embedding = embedding_service.encode(request.query)
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Convert embedding list to PostgreSQL vector format
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
        
        # Build query with optional filters
        filters = []
        params = [embedding_str]
        
        if request.user_id:
            filters.append("user_id = %s")
            params.append(request.user_id)
        
        if request.source:
            filters.append("source = %s")
            params.append(request.source)
        
        if request.created_after:
            filters.append("created >= %s::timestamptz")
            params.append(request.created_after)
        
        if request.created_before:
            filters.append("created <= %s::timestamptz")
            params.append(request.created_before)
        
        # Use environment default if distance_threshold not provided
        distance_threshold = request.distance_threshold if request.distance_threshold is not None else DEFAULT_DISTANCE_THRESHOLD
        if distance_threshold is not None:
            filters.append(f"(embedding <=> '{embedding_str}'::vector) <= %s")
            params.append(distance_threshold)
        
        where_clause = "WHERE " + " AND ".join(filters) if filters else ""
        
        query = f"""
            SELECT id, user_id, content, source, metadata, created,
                   embedding <=> %s::vector AS distance
            FROM embedding_store
            {where_clause}
            ORDER BY distance
            LIMIT %s
        """
        
        # Build final params: embedding_str first, then filters, then limit
        final_params = [embedding_str] + params[1:] + [request.limit]
        
        cur.execute(query, final_params)
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        return [
            SearchResult(
                id=str(row["id"]),
                user_id=row["user_id"],
                content=row["content"],
                source=row["source"],
                metadata=row["metadata"],
                distance=float(row["distance"]),
                created=row["created"].isoformat()
            )
            for row in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT)
