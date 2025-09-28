"""
Intelligent text chunking service for document processing
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import nltk
from nltk.tokenize import sent_tokenize

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a text chunk with metadata"""
    content: str
    chunk_id: str
    start_pos: int
    end_pos: int
    section: Optional[str] = None
    page_number: Optional[int] = None
    word_count: int = 0
    sentence_count: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        self.word_count = len(self.content.split())
        self.sentence_count = len(sent_tokenize(self.content)) if self.content else 0


class TextChunker:
    """Intelligent text chunking service"""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
        max_chunk_size: int = 2000,
        preserve_sections: bool = True,
        preserve_sentences: bool = True
    ):
        """
        Initialize text chunker

        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks in characters
            min_chunk_size: Minimum chunk size
            max_chunk_size: Maximum chunk size
            preserve_sections: Try to preserve document sections
            preserve_sentences: Try to preserve sentence boundaries
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.preserve_sections = preserve_sections
        self.preserve_sentences = preserve_sentences

        # Download NLTK punkt if not available
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)

    def _split_into_sections(self, text: str) -> List[Tuple[str, str]]:
        """Split text into sections based on common academic paper structure"""
        sections = []

        # Common section patterns in academic papers
        section_patterns = [
            (r'\b(?:abstract|introduction|background|related work|methodology|methods|experiments|results|discussion|conclusion|references)\b',
             'section_header'),
            (r'\n\s*(?:\d+\.|\([a-z]\)|\[.*?\])\s+', 'numbered_item'),
            (r'\n\s*[A-Z][^.!?]*[:;]\s*', 'subsection_header')
        ]

        # Simple section detection - split on common headers
        current_section = "main_content"
        current_content = []

        lines = text.split('\n')
        for line in lines:
            line_lower = line.lower().strip()

            # Check if line looks like a section header
            is_header = False
            for pattern, _ in section_patterns:
                if re.search(pattern, line_lower, re.IGNORECASE):
                    # Save previous section
                    if current_content:
                        sections.append((current_section, '\n'.join(current_content)))
                        current_content = []

                    # Start new section
                    current_section = line.strip()
                    is_header = True
                    break

            if not is_header:
                current_content.append(line)

        # Add remaining content
        if current_content:
            sections.append((current_section, '\n'.join(current_content)))

        return sections

    def _find_sentence_boundary(self, text: str, target_pos: int) -> int:
        """Find the nearest sentence boundary to target position"""
        if not self.preserve_sentences:
            return target_pos

        try:
            sentences = sent_tokenize(text)
            cumulative_pos = 0

            for sentence in sentences:
                sentence_start = cumulative_pos
                sentence_end = cumulative_pos + len(sentence)

                # If target is within this sentence, return sentence end
                if sentence_start <= target_pos <= sentence_end:
                    return sentence_end

                cumulative_pos = sentence_end + 1  # +1 for space/newline

            return target_pos

        except Exception as e:
            logger.warning(f"Sentence boundary detection failed: {e}")
            return target_pos

    def _create_chunk(
        self,
        text: str,
        start_pos: int,
        end_pos: int,
        chunk_id: str,
        section: Optional[str] = None,
        page_number: Optional[int] = None
    ) -> TextChunk:
        """Create a text chunk with metadata"""
        content = text[start_pos:end_pos].strip()

        # Skip empty chunks
        if not content:
            return None

        return TextChunk(
            content=content,
            chunk_id=chunk_id,
            start_pos=start_pos,
            end_pos=end_pos,
            section=section,
            page_number=page_number,
            metadata={
                "chunk_strategy": "sliding_window",
                "overlap_size": self.chunk_overlap,
                "target_chunk_size": self.chunk_size
            }
        )

    def chunk_text(
        self,
        text: str,
        paper_id: str = None,
        sections: Optional[List[Tuple[str, str]]] = None
    ) -> List[TextChunk]:
        """
        Chunk text into smaller pieces with overlap

        Args:
            text: Full text to chunk
            paper_id: Optional paper identifier for chunk IDs
            sections: Optional pre-split sections

        Returns:
            List of TextChunk objects
        """
        if not text or not text.strip():
            return []

        chunks = []
        chunk_counter = 0

        # Split into sections if not provided
        if sections is None and self.preserve_sections:
            sections = self._split_into_sections(text)
        elif sections is None:
            sections = [("full_text", text)]

        for section_name, section_text in sections:
            if not section_text.strip():
                continue

            # Sliding window chunking within section
            pos = 0
            section_start = text.find(section_text)

            while pos < len(section_text):
                # Calculate chunk boundaries
                chunk_start = pos
                chunk_end = min(pos + self.chunk_size, len(section_text))

                # Try to find sentence boundary if preserving sentences
                if self.preserve_sentences and chunk_end < len(section_text):
                    chunk_end = self._find_sentence_boundary(section_text, chunk_end)

                # Ensure minimum chunk size
                if chunk_end - chunk_start < self.min_chunk_size and chunk_end < len(section_text):
                    chunk_end = min(chunk_end + (self.min_chunk_size - (chunk_end - chunk_start)),
                                  len(section_text))

                # Create chunk
                global_start = section_start + chunk_start if section_start >= 0 else chunk_start

                chunk_id = f"{paper_id or 'unknown'}_chunk_{chunk_counter}"
                chunk = self._create_chunk(
                    text=section_text,
                    start_pos=chunk_start,
                    end_pos=chunk_end,
                    chunk_id=chunk_id,
                    section=section_name
                )

                if chunk:
                    chunks.append(chunk)
                    chunk_counter += 1

                # Move position with overlap
                pos = chunk_end - self.chunk_overlap

                # Ensure progress
                if pos <= chunk_start:
                    pos = chunk_end

        return chunks

    def chunk_document(
        self,
        document: Dict[str, Any],
        content_field: str = "content",
        title_field: str = "title",
        paper_id_field: str = "paper_id"
    ) -> Dict[str, Any]:
        """
        Chunk a document and add chunks to it

        Args:
            document: Document dictionary
            content_field: Field containing the main content
            title_field: Field containing the title
            paper_id_field: Field containing the paper ID

        Returns:
            Document with chunks added
        """
        content = document.get(content_field, "")
        paper_id = document.get(paper_id_field, "unknown")

        if not content:
            document["chunks"] = []
            return document

        # Chunk the content
        chunks = self.chunk_text(content, paper_id=paper_id)

        # Convert chunks to dictionaries for JSON serialization
        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = {
                "chunk_id": chunk.chunk_id,
                "content": chunk.content,
                "chunk_index": len(chunk_dicts),
                "total_chunks": len(chunks),
                "page_number": chunk.page_number,
                "section": chunk.section,
                "word_count": chunk.word_count,
                "start_pos": chunk.start_pos,
                "end_pos": chunk.end_pos,
                "metadata": chunk.metadata
            }
            chunk_dicts.append(chunk_dict)

        document["chunks"] = chunk_dicts
        document["chunk_count"] = len(chunks)
        document["chunking_metadata"] = {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "strategy": "intelligent_section_aware"
        }

        return document

    def chunk_batch(
        self,
        documents: List[Dict[str, Any]],
        content_field: str = "content",
        paper_id_field: str = "paper_id"
    ) -> List[Dict[str, Any]]:
        """Chunk multiple documents"""
        chunked_documents = []

        for doc in documents:
            try:
                chunked_doc = self.chunk_document(
                    doc,
                    content_field=content_field,
                    paper_id_field=paper_id_field
                )
                chunked_documents.append(chunked_doc)
            except Exception as e:
                logger.error(f"Failed to chunk document {doc.get(paper_id_field, 'unknown')}: {e}")
                # Add empty chunks on failure
                doc["chunks"] = []
                doc["chunk_count"] = 0
                chunked_documents.append(doc)

        return chunked_documents


class SemanticChunker(TextChunker):
    """Semantic-aware text chunking using embeddings"""

    def __init__(self, embedding_service=None, **kwargs):
        super().__init__(**kwargs)
        self.embedding_service = embedding_service

    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two text pieces"""
        if not self.embedding_service:
            return 0.0

        try:
            # This would use embeddings to find semantic boundaries
            # For now, return a placeholder
            return 0.5
        except Exception:
            return 0.0

    def chunk_text(self, text: str, paper_id: str = None, **kwargs) -> List[TextChunk]:
        """Semantic-aware chunking"""
        # For now, fall back to regular chunking
        # TODO: Implement semantic boundary detection
        return super().chunk_text(text, paper_id, **kwargs)