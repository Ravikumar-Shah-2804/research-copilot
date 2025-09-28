"""
arXiv API client for fetching research papers
"""
import asyncio
import logging
import time
import xml.etree.ElementTree as ET
from functools import cached_property
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote, urlencode

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import Settings
from ..schemas.arxiv import ArxivPaper, ArxivSearchQuery
from ..utils.exceptions import ArxivAPIException, ArxivAPITimeoutError, ArxivParseError, PDFDownloadException, PDFDownloadTimeoutError

logger = logging.getLogger(__name__)


class ArxivClient:
    """Client for fetching papers from arXiv API with rate limiting and error handling."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._last_request_time: Optional[float] = None

    @cached_property
    def pdf_cache_dir(self) -> Path:
        """PDF cache directory."""
        cache_dir = Path(self._settings.pdf_cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @property
    def base_url(self) -> str:
        return self._settings.arxiv_base_url

    @property
    def namespaces(self) -> dict:
        return self._settings.arxiv_namespaces

    @property
    def rate_limit_delay(self) -> float:
        return self._settings.arxiv_rate_limit_delay

    @property
    def timeout_seconds(self) -> int:
        return self._settings.arxiv_timeout_seconds

    @property
    def max_results(self) -> int:
        return self._settings.arxiv_max_results_per_request

    @property
    def max_concurrent_downloads(self) -> int:
        return self._settings.arxiv_max_concurrent_downloads

    @property
    def max_concurrent_parsing(self) -> int:
        return self._settings.arxiv_max_concurrent_parsing

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError))
    )
    async def fetch_papers(self, query: ArxivSearchQuery) -> List[ArxivPaper]:
        """
        Fetch papers from arXiv using search query parameters.

        Args:
            query: Search query parameters

        Returns:
            List of ArxivPaper objects
        """
        # Build search query
        search_query = self._build_search_query(query)

        params = {
            "search_query": search_query,
            "start": query.start,
            "max_results": min(query.max_results, self.max_results),
            "sortBy": query.sort_by,
            "sortOrder": query.sort_order,
        }

        safe = ":+[]"  # Don't encode :, +, [, ] characters needed for arXiv queries
        url = f"{self.base_url}?{urlencode(params, quote_via=quote, safe=safe)}"

        try:
            logger.info(f"Fetching {query.max_results} papers from arXiv with query: {search_query}")

            # Add rate limiting delay between requests
            await self._apply_rate_limit()

            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url)
                response.raise_for_status()
                xml_data = response.text

            papers = self._parse_response(xml_data)
            logger.info(f"Fetched {len(papers)} papers from arXiv")

            return papers

        except httpx.TimeoutException as e:
            logger.error(f"arXiv API timeout: {e}")
            raise ArxivAPITimeoutError(f"arXiv API request timed out: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"arXiv API HTTP error: {e}")
            raise ArxivAPIException(f"arXiv API returned error {e.response.status_code}: {e}")
        except Exception as e:
            logger.error(f"Failed to fetch papers from arXiv: {e}")
            raise ArxivAPIException(f"Unexpected error fetching papers from arXiv: {e}")

    async def fetch_paper_by_id(self, arxiv_id: str) -> Optional[ArxivPaper]:
        """
        Fetch a specific paper by its arXiv ID.

        Args:
            arxiv_id: arXiv paper ID (e.g., "2507.17748v1" or "2507.17748")

        Returns:
            ArxivPaper object or None if not found
        """
        # Clean the arXiv ID (remove version if needed for search)
        clean_id = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id
        params = {"id_list": clean_id, "max_results": 1}

        safe = ":+[]*"  # Don't encode :, +, [, ], *, characters needed for arXiv queries
        url = f"{self.base_url}?{urlencode(params, quote_via=quote, safe=safe)}"

        try:
            await self._apply_rate_limit()

            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url)
                response.raise_for_status()
                xml_data = response.text

            papers = self._parse_response(xml_data)

            if papers:
                return papers[0]
            else:
                logger.warning(f"Paper {arxiv_id} not found")
                return None

        except httpx.TimeoutException as e:
            logger.error(f"arXiv API timeout for paper {arxiv_id}: {e}")
            raise ArxivAPITimeoutError(f"arXiv API request timed out for paper {arxiv_id}: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"arXiv API HTTP error for paper {arxiv_id}: {e}")
            raise ArxivAPIException(f"arXiv API returned error {e.response.status_code} for paper {arxiv_id}: {e}")
        except Exception as e:
            logger.error(f"Failed to fetch paper {arxiv_id} from arXiv: {e}")
            raise ArxivAPIException(f"Unexpected error fetching paper {arxiv_id} from arXiv: {e}")

    async def download_pdf(self, paper: ArxivPaper, force_download: bool = False) -> Optional[Path]:
        """
        Download PDF for a given paper to local cache.

        Args:
            paper: ArxivPaper object containing PDF URL
            force_download: Force re-download even if file exists

        Returns:
            Path to downloaded PDF file or None if download failed
        """
        if not paper.pdf_url:
            logger.error(f"No PDF URL for paper {paper.arxiv_id}")
            return None

        pdf_path = self._get_pdf_path(paper.arxiv_id)

        # Return cached PDF if exists and not forcing download
        if pdf_path.exists() and not force_download:
            logger.info(f"Using cached PDF: {pdf_path.name}")
            return pdf_path

        # Download with retry
        if await self._download_with_retry(paper.pdf_url, pdf_path):
            return pdf_path
        else:
            return None

    async def _apply_rate_limit(self):
        """Apply rate limiting delay between requests."""
        if self._last_request_time is not None:
            time_since_last = time.time() - self._last_request_time
            if time_since_last < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - time_since_last
                await asyncio.sleep(sleep_time)

        self._last_request_time = time.time()

    def _build_search_query(self, query: ArxivSearchQuery) -> str:
        """Build arXiv search query from parameters."""
        query_parts = []

        # Add category filter
        if query.category:
            query_parts.append(f"cat:{query.category}")

        # Add text search fields
        if query.query:
            query_parts.append(query.query)
        if query.author:
            query_parts.append(f"au:{query.author}")
        if query.title:
            query_parts.append(f"ti:{query.title}")
        if query.abstract:
            query_parts.append(f"abs:{query.abstract}")

        # Join with AND
        search_query = " AND ".join(query_parts) if query_parts else f"cat:{self._settings.arxiv_default_category}"

        # Add date filtering if provided
        if query.from_date or query.to_date:
            date_from = f"{query.from_date}0000" if query.from_date else "*"
            date_to = f"{query.to_date}2359" if query.to_date else "*"
            search_query += f" AND submittedDate:[{date_from}+TO+{date_to}]"

        return search_query

    def _parse_response(self, xml_data: str) -> List[ArxivPaper]:
        """
        Parse arXiv API XML response into ArxivPaper objects.

        Args:
            xml_data: Raw XML response from arXiv API

        Returns:
            List of parsed ArxivPaper objects
        """
        try:
            root = ET.fromstring(xml_data)
            entries = root.findall("atom:entry", self.namespaces)

            papers = []
            for entry in entries:
                paper = self._parse_single_entry(entry)
                if paper:
                    papers.append(paper)

            return papers

        except ET.ParseError as e:
            logger.error(f"Failed to parse arXiv XML response: {e}")
            raise ArxivParseError(f"Failed to parse arXiv XML response: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing arXiv response: {e}")
            raise ArxivParseError(f"Unexpected error parsing arXiv response: {e}")

    def _parse_single_entry(self, entry: ET.Element) -> Optional[ArxivPaper]:
        """
        Parse a single entry from arXiv XML response.

        Args:
            entry: XML entry element

        Returns:
            ArxivPaper object or None if parsing fails
        """
        try:
            # Extract basic metadata
            arxiv_id = self._get_arxiv_id(entry)
            if not arxiv_id:
                return None

            title = self._get_text(entry, "atom:title", clean_newlines=True)
            authors = self._get_authors(entry)
            abstract = self._get_text(entry, "atom:summary", clean_newlines=True)
            published = self._get_published_date(entry)
            categories = self._get_categories(entry)
            pdf_url = self._get_pdf_url(entry)
            doi = self._get_doi(entry)
            journal_ref = self._get_journal_ref(entry)
            comments = self._get_comments(entry)
            updated = self._get_updated_date(entry)

            return ArxivPaper(
                arxiv_id=arxiv_id,
                title=title,
                authors=authors,
                abstract=abstract,
                published_date=published,
                categories=categories,
                pdf_url=pdf_url,
                doi=doi,
                journal_ref=journal_ref,
                comments=comments,
                updated_date=updated,
            )

        except Exception as e:
            logger.error(f"Failed to parse entry: {e}")
            return None

    def _get_text(self, element: ET.Element, path: str, clean_newlines: bool = False) -> str:
        """Extract text from XML element safely."""
        elem = element.find(path, self.namespaces)
        if elem is None or elem.text is None:
            return ""

        text = elem.text.strip()
        return text.replace("\n", " ") if clean_newlines else text

    def _get_arxiv_id(self, entry: ET.Element) -> Optional[str]:
        """Extract arXiv ID from entry."""
        id_elem = entry.find("atom:id", self.namespaces)
        if id_elem is None or id_elem.text is None:
            return None
        return id_elem.text.split("/")[-1]

    def _get_authors(self, entry: ET.Element) -> List[str]:
        """Extract author names from entry."""
        authors = []
        for author in entry.findall("atom:author", self.namespaces):
            name = self._get_text(author, "atom:name")
            if name:
                authors.append(name)
        return authors

    def _get_categories(self, entry: ET.Element) -> List[str]:
        """Extract categories from entry."""
        categories = []
        for category in entry.findall("atom:category", self.namespaces):
            term = category.get("term")
            if term:
                categories.append(term)
        return categories

    def _get_pdf_url(self, entry: ET.Element) -> str:
        """Extract PDF URL from entry links."""
        for link in entry.findall("atom:link", self.namespaces):
            if link.get("type") == "application/pdf":
                url = link.get("href", "")
                # Convert HTTP to HTTPS for arXiv URLs
                if url.startswith("http://arxiv.org/"):
                    url = url.replace("http://arxiv.org/", "https://arxiv.org/")
                return url
        return ""

    def _get_published_date(self, entry: ET.Element) -> Optional[str]:
        """Extract published date from entry."""
        published_elem = entry.find("atom:published", self.namespaces)
        return published_elem.text if published_elem is not None else None

    def _get_updated_date(self, entry: ET.Element) -> Optional[str]:
        """Extract updated date from entry."""
        updated_elem = entry.find("atom:updated", self.namespaces)
        return updated_elem.text if updated_elem is not None else None

    def _get_doi(self, entry: ET.Element) -> Optional[str]:
        """Extract DOI from entry."""
        # DOI is typically in the arXiv namespace
        doi_elem = entry.find("arxiv:doi", self.namespaces)
        return doi_elem.text if doi_elem is not None else None

    def _get_journal_ref(self, entry: ET.Element) -> Optional[str]:
        """Extract journal reference from entry."""
        journal_elem = entry.find("arxiv:journal_ref", self.namespaces)
        return journal_elem.text if journal_elem is not None else None

    def _get_comments(self, entry: ET.Element) -> Optional[str]:
        """Extract comments from entry."""
        comments_elem = entry.find("arxiv:comment", self.namespaces)
        return comments_elem.text if comments_elem is not None else None

    def _get_pdf_path(self, arxiv_id: str) -> Path:
        """Get the local path for a PDF file."""
        safe_filename = arxiv_id.replace("/", "_") + ".pdf"
        return self.pdf_cache_dir / safe_filename

    async def _download_with_retry(self, url: str, path: Path) -> bool:
        """Download a file with retry logic and exponential backoff."""
        max_retries = self._settings.arxiv_max_retries
        retry_delay_base = self._settings.arxiv_retry_delay_base

        logger.info(f"Downloading PDF from {url}")

        # Respect rate limits
        await asyncio.sleep(self.rate_limit_delay)

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    async with client.stream("GET", url) as response:
                        response.raise_for_status()
                        with open(path, "wb") as f:
                            async for chunk in response.aiter_bytes():
                                f.write(chunk)
                logger.info(f"Successfully downloaded to {path.name}")
                return True

            except httpx.TimeoutException as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay_base * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"PDF download timeout (attempt {attempt + 1}/{max_retries}): {e}")
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"PDF download failed after {max_retries} attempts due to timeout: {e}")
                    raise PDFDownloadTimeoutError(f"PDF download timed out after {max_retries} attempts: {e}")
            except httpx.HTTPError as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay_base * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Download failed (attempt {attempt + 1}/{max_retries}): {e}")
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed after {max_retries} attempts: {e}")
                    raise PDFDownloadException(f"PDF download failed after {max_retries} attempts: {e}")
            except Exception as e:
                logger.error(f"Unexpected download error: {e}")
                raise PDFDownloadException(f"Unexpected error during PDF download: {e}")

        # Clean up partial download
        if path.exists():
            path.unlink()

        return False

    async def download_pdfs_batch(self, papers: List[ArxivPaper], force_download: bool = False) -> Dict[str, Optional[Path]]:
        """
        Download PDFs for multiple papers concurrently with controlled parallelism.

        Args:
            papers: List of ArxivPaper objects
            force_download: Force re-download even if files exist

        Returns:
            Dictionary mapping arxiv_id to downloaded Path or None if failed
        """
        if not papers:
            return {}

        results = {}
        logger.info(f"Starting concurrent PDF download for {len(papers)} papers")
        logger.info(f"Max concurrent downloads: {self.max_concurrent_downloads}")

        # Create semaphore for controlling concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent_downloads)

        async def download_with_semaphore(paper: ArxivPaper) -> tuple:
            """Download a single paper with semaphore control."""
            async with semaphore:
                try:
                    pdf_path = await self.download_pdf(paper, force_download)
                    return (paper.arxiv_id, pdf_path)
                except Exception as e:
                    logger.error(f"Failed to download PDF for {paper.arxiv_id}: {e}")
                    return (paper.arxiv_id, None)

        # Start all downloads concurrently
        download_tasks = [download_with_semaphore(paper) for paper in papers]
        download_results = await asyncio.gather(*download_tasks, return_exceptions=True)

        # Process results
        successful_downloads = 0
        failed_downloads = 0

        for result in download_results:
            if isinstance(result, Exception):
                logger.error(f"Download task failed with exception: {result}")
                continue

            arxiv_id, pdf_path = result
            results[arxiv_id] = pdf_path

            if pdf_path:
                successful_downloads += 1
            else:
                failed_downloads += 1

        logger.info(f"Batch download complete: {successful_downloads} successful, {failed_downloads} failed")

        return results