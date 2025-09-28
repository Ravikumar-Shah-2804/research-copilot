-- Migration script to update research_papers table for comprehensive ingestion support
-- Run this after backing up your database

-- Add new columns for enhanced paper model
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS raw_text TEXT;
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS sections JSONB;
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS references JSONB;
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS parser_used VARCHAR(50);
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS parser_metadata JSONB;
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS pdf_processed BOOLEAN DEFAULT FALSE;
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS pdf_processing_date TIMESTAMP WITH TIME ZONE;
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS pdf_file_size VARCHAR(50);
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS pdf_page_count VARCHAR(10);
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS tags JSONB;
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS keywords JSONB;
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS journal_ref VARCHAR(500);
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS comments TEXT;
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS ingestion_status VARCHAR(50) DEFAULT 'pending';
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS ingestion_attempts VARCHAR(10) DEFAULT '0';
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS last_ingestion_attempt TIMESTAMP WITH TIME ZONE;
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS ingestion_errors JSONB;
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS source VARCHAR(100) DEFAULT 'arxiv';
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS quality_score VARCHAR(10);
ALTER TABLE research_papers ADD COLUMN IF NOT EXISTS duplicate_of UUID REFERENCES research_papers(id);

-- Update existing records to have proper status
UPDATE research_papers SET ingestion_status = 'completed' WHERE full_text IS NOT NULL;
UPDATE research_papers SET pdf_processed = TRUE WHERE full_text IS NOT NULL;

-- Migrate existing full_text to raw_text for backward compatibility
UPDATE research_papers SET raw_text = full_text WHERE full_text IS NOT NULL AND raw_text IS NULL;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_research_papers_arxiv_id ON research_papers(arxiv_id);
CREATE INDEX IF NOT EXISTS idx_research_papers_doi ON research_papers(doi);
CREATE INDEX IF NOT EXISTS idx_research_papers_ingestion_status ON research_papers(ingestion_status);
CREATE INDEX IF NOT EXISTS idx_research_papers_pdf_processed ON research_papers(pdf_processed);
CREATE INDEX IF NOT EXISTS idx_research_papers_published_date ON research_papers(published_date DESC);
CREATE INDEX IF NOT EXISTS idx_research_papers_created_at ON research_papers(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_papers_categories ON research_papers USING GIN (categories);
CREATE INDEX IF NOT EXISTS idx_research_papers_authors ON research_papers USING GIN (authors);

-- Create partial indexes for common queries
CREATE INDEX IF NOT EXISTS idx_research_papers_unprocessed ON research_papers(arxiv_id) WHERE pdf_processed = FALSE;
CREATE INDEX IF NOT EXISTS idx_research_papers_failed ON research_papers(last_ingestion_attempt DESC) WHERE ingestion_status = 'failed';

-- Add comments for documentation
COMMENT ON COLUMN research_papers.raw_text IS 'Full text content extracted from PDF';
COMMENT ON COLUMN research_papers.sections IS 'Structured sections extracted from PDF';
COMMENT ON COLUMN research_papers.references IS 'References extracted from paper';
COMMENT ON COLUMN research_papers.parser_used IS 'PDF parser used (docling, pypdf, etc.)';
COMMENT ON COLUMN research_papers.ingestion_status IS 'Current ingestion status (pending, processing, completed, failed)';
COMMENT ON COLUMN research_papers.source IS 'Data source (arxiv, manual, etc.)';