-- Create dataset first (once):
-- CREATE SCHEMA IF NOT EXISTS `biomind_corpus` OPTIONS(location="us");

-- Papers table
CREATE TABLE IF NOT EXISTS `biomind_corpus.papers` (
  id STRING,
  title STRING,
  abstract STRING,
  doi STRING,
  source STRING,
  url STRING,
  published DATE,
  journal STRING,
  authors ARRAY<STRING>,
  pdf_gcs_uri STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Chunks table
CREATE TABLE IF NOT EXISTS `biomind_corpus.chunks` (
  id STRING,
  paper_id STRING,
  section STRING,
  position INT64,
  text STRING,
  token_count INT64,
  url STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Optional search index (see BigQuery vector/SEARCH availability)
-- CREATE SEARCH INDEX IF NOT EXISTS idx_chunks_text ON `biomind_corpus.chunks`(text) OPTIONS({tokenLimit: 200000});

-- Corpus table used by the API to map vector IDs to text and metadata
CREATE TABLE IF NOT EXISTS `biomind_corpus.corpus` (
  id STRING,
  text STRING,
  source STRING,
  url STRING
);
