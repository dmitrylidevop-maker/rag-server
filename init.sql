-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create embedding_store table
CREATE TABLE IF NOT EXISTS embedding_store (
    -- Unique identifier for the embedding record
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identifier for the user who added/owns the data (e.g., a student or employee ID)
    user_id VARCHAR(9) NOT NULL,

    -- The source text content that was embedded
    content TEXT NOT NULL,

    -- The embedding vector itself. 
    -- Using 384 dimensions for all-MiniLM-L6-v2 model (sentence-transformers)
    embedding VECTOR(384) NOT NULL,

    -- Source of the content (e.g., filename, URL, document type)
    source VARCHAR(255),

    -- Additional metadata as JSON (flexible storage for any extra information)
    metadata JSONB,

    -- Timestamp for when the record was created. TIMESTAMPTZ is best practice for time zones.
    created TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index for faster vector similarity searches
CREATE INDEX IF NOT EXISTS embedding_store_embedding_idx ON embedding_store USING hnsw (embedding vector_cosine_ops);

-- Create index on user_id for faster filtering
CREATE INDEX IF NOT EXISTS embedding_store_user_id_idx ON embedding_store (user_id);

-- Create index on source for faster filtering
CREATE INDEX IF NOT EXISTS embedding_store_source_idx ON embedding_store (source);
