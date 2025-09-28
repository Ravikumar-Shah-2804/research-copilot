"""
PDF parsing service using Docling for scientific document processing
"""
import logging
from pathlib import Path
from typing import Optional, List

import pypdfium2 as pdfium
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from ..config import Settings
from ..schemas.pdf_parser import (
    ParserType,
    PdfContent,
    PaperSection,
    PaperReference,
    PdfProcessingRequest,
    PdfProcessingResponse,
    PdfValidationResult
)
from ..services.circuit_breaker import (
    ResilienceManager,
    CircuitBreakerConfig,
    RetryConfig,
    FallbackConfig,
    resilience_registry
)
from ..utils.exceptions import PDFParsingException, PDFValidationError

logger = logging.getLogger(__name__)


class DoclingPDFParser:
    """Docling PDF parser for scientific document processing with enterprise-grade resilience."""

    def __init__(self, settings: Settings):
        """Initialize DocumentConverter with optimized pipeline options and resilience."""
        self._settings = settings

        # Configure pipeline options
        pipeline_options = PdfPipelineOptions(
            do_table_structure=self._settings.pdf_do_table_structure,
            do_ocr=self._settings.pdf_do_ocr,
        )

        self._converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )
        self._warmed_up = False

        # Initialize resilience manager for PDF parsing
        circuit_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=300.0,  # 5 minutes
            timeout=self._settings.pdf_timeout_seconds,
            expected_exception=(PDFParsingException, PDFValidationError, Exception)
        )

        retry_config = RetryConfig(
            max_attempts=2,  # Limited retries for PDF parsing
            base_delay=2.0,
            max_delay=10.0,
            retry_on_exceptions=(PDFParsingException, Exception)
        )

        fallback_config = FallbackConfig(
            enabled=True,
            fallback_timeout=30.0,
            cache_fallback_results=False  # Don't cache fallback results for PDFs
        )

        self._resilience_manager = resilience_registry.get_or_create(
            "pdf_parser_docling",
            circuit_config,
            retry_config,
            fallback_config
        )

    def _warm_up_models(self):
        """Pre-warm the models with a small dummy document to avoid cold start."""
        if not self._warmed_up:
            self._warmed_up = True
            logger.info("Warming up Docling models...")

    def _parse_markdown_table(self, markdown_table: str) -> List[List[str]]:
        """Parse markdown table string into list of lists format."""
        lines = [line.strip() for line in markdown_table.split('\n') if line.strip()]
        if not lines:
            return []

        # Remove separator line (usually second line with ---)
        if len(lines) > 1 and '|' in lines[1] and '-' in lines[1]:
            lines.pop(1)

        table_data = []
        for line in lines:
            if '|' in line:
                # Split by | and strip whitespace
                cells = [cell.strip() for cell in line.split('|')[1:-1]]  # Skip first and last empty elements
                table_data.append(cells)

        return table_data

    def _validate_pdf(self, pdf_path: Path) -> PdfValidationResult:
        """Comprehensive PDF validation including size and page limits."""
        try:
            # Check file exists and is not empty
            if pdf_path.stat().st_size == 0:
                raise PDFValidationError(f"PDF file is empty: {pdf_path}")

            file_size = pdf_path.stat().st_size

            # Check file size limit
            if file_size > self._settings.pdf_max_file_size_mb * 1024 * 1024:
                raise PDFValidationError(
                    f"PDF file too large: {file_size / 1024 / 1024:.1f}MB > {self._settings.pdf_max_file_size_mb}MB"
                )

            # Check if file starts with PDF header
            with open(pdf_path, "rb") as f:
                header = f.read(8)
                if not header.startswith(b"%PDF-"):
                    raise PDFValidationError(f"File does not have PDF header: {pdf_path}")

            # Check page count limit
            pdf_doc = pdfium.PdfDocument(str(pdf_path))
            actual_pages = len(pdf_doc)
            pdf_doc.close()

            if actual_pages > self._settings.pdf_max_pages:
                raise PDFValidationError(
                    f"PDF has too many pages: {actual_pages} > {self._settings.pdf_max_pages}"
                )

            return PdfValidationResult(
                is_valid=True,
                file_size_bytes=file_size,
                page_count=actual_pages,
                metadata={"format": "PDF", "pages": actual_pages, "size_mb": file_size / 1024 / 1024}
            )

        except PDFValidationError:
            raise
        except Exception as e:
            logger.error(f"Error validating PDF {pdf_path}: {e}")
            raise PDFValidationError(f"Error validating PDF {pdf_path}: {e}")

    async def process_pdf(self, request: PdfProcessingRequest) -> PdfProcessingResponse:
        """Process PDF using Docling parser with resilience."""
        import time
        start_time = time.time()

        try:
            pdf_path = Path(request.pdf_path)

            # Validate PDF first (not wrapped in resilience as it's fast and local)
            validation = self._validate_pdf(pdf_path)

            # Define the core parsing function for resilience
            async def _parse_pdf_core():
                # Warm up models on first use
                self._warm_up_models()

                # Convert PDF using Docling
                result = self._converter.convert(
                    str(pdf_path),
                    max_num_pages=self._settings.pdf_max_pages,
                    max_file_size=self._settings.pdf_max_file_size_mb * 1024 * 1024
                )
                return result

            # Execute parsing with resilience
            result = await self._resilience_manager.execute_resilient(_parse_pdf_core)

            # Extract structured content
            doc = result.document

            # Extract sections from document structure with improved hierarchy detection
            sections = []
            current_section = {"title": "Content", "content": "", "level": 1}

            for element in doc.texts:
                if hasattr(element, "label"):
                    # Check for section headers with hierarchy
                    if element.label in ["title", "section_header"]:
                        # Save previous section if it has content
                        if current_section["content"].strip():
                            sections.append(PaperSection(
                                title=current_section["title"],
                                content=current_section["content"].strip(),
                                level=current_section["level"]
                            ))

                        # Determine section level based on text patterns or element properties
                        title_text = element.text.strip()
                        level = 1

                        # Try to infer level from formatting or numbering
                        if hasattr(element, 'heading_level'):
                            level = element.heading_level
                        elif title_text and any(title_text.upper().startswith(prefix) for prefix in ['I.', 'II.', 'III.', 'IV.', 'V.']):
                            level = 1  # Roman numerals for main sections
                        elif title_text and any(title_text.startswith(prefix) for prefix in ['1.', '2.', '3.', '4.', '5.']):
                            level = 2  # Numbered subsections
                        elif title_text and any(title_text.startswith(prefix) for prefix in ['1.1', '2.1', '1.2']):
                            level = 3  # Sub-subsections
                        elif title_text and title_text[0].isupper() and len(title_text.split()) <= 10:
                            # Short uppercase titles are likely main sections
                            level = 1
                        else:
                            level = 2  # Default to subsection level

                        # Start new section
                        current_section = {"title": title_text, "content": "", "level": level}
                    elif element.label == "caption":
                        # Captions might indicate figure/table sections, but add to current content
                        if hasattr(element, "text") and element.text:
                            current_section["content"] += f"[Caption: {element.text}]\n"
                    else:
                        # Add content to current section
                        if hasattr(element, "text") and element.text:
                            current_section["content"] += element.text + "\n"
                else:
                    # Add content to current section
                    if hasattr(element, "text") and element.text:
                        current_section["content"] += element.text + "\n"

            # Add final section
            if current_section["content"].strip():
                sections.append(PaperSection(
                    title=current_section["title"],
                    content=current_section["content"].strip(),
                    level=current_section["level"]
                ))

            # Extract tables if table structure is enabled
            tables = []
            if self._settings.pdf_do_table_structure and hasattr(doc, 'tables'):
                for table_idx, table in enumerate(doc.tables):
                    try:
                        # Get table caption if available
                        caption = ""
                        if hasattr(table, 'caption') and table.caption:
                            caption = table.caption
                        else:
                            caption = f"Table {table_idx + 1}"

                        # Export table to markdown and convert to list of lists
                        table_markdown = table.export_to_markdown()
                        table_content = self._parse_markdown_table(table_markdown)

                        tables.append(PaperTable(
                            caption=caption,
                            content=table_content,
                            page_number=getattr(table, 'page_no', 1),  # Default to page 1 if not available
                            bounding_box=None  # Could be extracted if available
                        ))
                    except Exception as e:
                        logger.warning(f"Failed to extract table {table_idx}: {e}")
                        continue

            # Create PDF content
            content = PdfContent(
                sections=sections,
                figures=[],  # Figure extraction not implemented yet
                tables=tables,
                raw_text=doc.export_to_text(),
                references=[],  # Reference extraction not implemented yet
                parser_used=ParserType.DOCLING,
                metadata={
                    "source": "docling",
                    "processing_time_seconds": time.time() - start_time,
                    "file_size_bytes": validation.file_size_bytes,
                    "page_count": validation.page_count,
                    "tables_extracted": len(tables)
                },
                processing_time_seconds=time.time() - start_time,
                page_count=validation.page_count,
                file_size_bytes=validation.file_size_bytes
            )

            return PdfProcessingResponse(
                paper_id=request.paper_id,
                success=True,
                content=content,
                processing_time_seconds=time.time() - start_time,
                parser_used=ParserType.DOCLING
            )

        except PDFValidationError as e:
            error_msg = str(e).lower()
            if "too large" in error_msg or "too many pages" in error_msg:
                logger.info(f"Skipping PDF processing due to limits: {e}")
                return PdfProcessingResponse(
                    paper_id=request.paper_id,
                    success=False,
                    error_message=str(e),
                    processing_time_seconds=time.time() - start_time,
                    parser_used=ParserType.DOCLING
                )
            else:
                raise
        except Exception as e:
            logger.error(f"Failed to parse PDF {request.pdf_path}: {e}")
            error_msg = str(e).lower()

            # Handle specific error types
            if "timeout" in error_msg:
                error_message = f"PDF processing timed out: {request.pdf_path}"
            elif "memory" in error_msg or "ram" in error_msg:
                error_message = f"Out of memory processing PDF: {request.pdf_path}"
            elif "max_num_pages" in error_msg or "page" in error_msg:
                error_message = f"PDF processing failed, possibly due to page limit ({self._settings.pdf_max_pages} pages)"
            else:
                error_message = f"Failed to parse PDF with Docling: {e}"

            return PdfProcessingResponse(
                paper_id=request.paper_id,
                success=False,
                error_message=error_message,
                processing_time_seconds=time.time() - start_time,
                parser_used=ParserType.DOCLING
            )


class PDFParserFactory:
    """Factory for creating PDF parsers."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._parsers = {}

    def get_parser(self, parser_type: ParserType = ParserType.DOCLING):
        """Get or create a PDF parser instance."""
        if parser_type not in self._parsers:
            if parser_type == ParserType.DOCLING:
                self._parsers[parser_type] = DoclingPDFParser(self._settings)
            else:
                raise ValueError(f"Unsupported parser type: {parser_type}")

        return self._parsers[parser_type]