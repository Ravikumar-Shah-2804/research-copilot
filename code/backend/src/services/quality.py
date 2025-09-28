"""
Data quality validation and duplicate detection service
"""
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from ..config import Settings
from ..database import async_session
from ..models.paper import ResearchPaper
from ..repositories.paper import PaperRepository
from ..schemas.paper import PaperCreate
from ..utils.exceptions import QualityValidationException, DuplicateDetectionException

logger = logging.getLogger(__name__)


class DataQualityValidator:
    """Service for validating data quality of research papers."""

    def __init__(self, settings: Settings):
        self._settings = settings

    def validate_paper_data(self, paper_data: PaperCreate) -> Dict[str, Any]:
        """
        Validate paper data quality.

        Returns:
            Dict with validation results and any issues found
        """
        issues = []
        warnings = []
        score = 100  # Start with perfect score

        # Title validation
        title_issues = self._validate_title(paper_data.title)
        issues.extend(title_issues["errors"])
        warnings.extend(title_issues["warnings"])
        score -= len(title_issues["errors"]) * 20 + len(title_issues["warnings"]) * 5

        # Abstract validation
        abstract_issues = self._validate_abstract(paper_data.abstract)
        issues.extend(abstract_issues["errors"])
        warnings.extend(abstract_issues["warnings"])
        score -= len(abstract_issues["errors"]) * 15 + len(abstract_issues["warnings"]) * 3

        # Authors validation
        authors_issues = self._validate_authors(paper_data.authors)
        issues.extend(authors_issues["errors"])
        warnings.extend(authors_issues["warnings"])
        score -= len(authors_issues["errors"]) * 10 + len(authors_issues["warnings"]) * 2

        # Categories validation
        categories_issues = self._validate_categories(paper_data.categories)
        issues.extend(categories_issues["errors"])
        warnings.extend(categories_issues["warnings"])
        score -= len(categories_issues["errors"]) * 5 + len(categories_issues["warnings"]) * 1

        # DOI validation
        if paper_data.doi:
            doi_issues = self._validate_doi(paper_data.doi)
            issues.extend(doi_issues["errors"])
            warnings.extend(doi_issues["warnings"])
            score -= len(doi_issues["errors"]) * 10

        # arXiv ID validation
        arxiv_issues = self._validate_arxiv_id(paper_data.arxiv_id)
        issues.extend(arxiv_issues["errors"])
        warnings.extend(arxiv_issues["warnings"])
        score -= len(arxiv_issues["errors"]) * 15

        # Ensure score doesn't go below 0
        score = max(0, score)

        return {
            "is_valid": len(issues) == 0,
            "quality_score": score,
            "issues": issues,
            "warnings": warnings,
            "recommendations": self._generate_recommendations(issues, warnings)
        }

    def _validate_title(self, title: str) -> Dict[str, List[str]]:
        """Validate paper title."""
        errors = []
        warnings = []

        if not title or not title.strip():
            errors.append("Title is empty")
            return {"errors": errors, "warnings": warnings}

        title = title.strip()

        if len(title) < self._settings.quality_min_title_length:
            errors.append(f"Title too short (minimum {self._settings.quality_min_title_length} characters)")

        if len(title) > self._settings.quality_max_title_length:
            errors.append(f"Title too long (maximum {self._settings.quality_max_title_length} characters)")

        # Check for suspicious patterns
        if re.search(r'[<>]', title):
            errors.append("Title contains HTML tags")

        if title.count('.') > 5:
            warnings.append("Title contains many periods (possible formatting issue)")

        # Check for all caps
        if title.isupper() and len(title) > 10:
            warnings.append("Title is all uppercase")

        return {"errors": errors, "warnings": warnings}

    def _validate_abstract(self, abstract: Optional[str]) -> Dict[str, List[str]]:
        """Validate paper abstract."""
        errors = []
        warnings = []

        if not abstract or not abstract.strip():
            errors.append("Abstract is empty")
            return {"errors": errors, "warnings": warnings}

        abstract = abstract.strip()

        if len(abstract) < self._settings.quality_min_abstract_length:
            errors.append(f"Abstract too short (minimum {self._settings.quality_min_abstract_length} characters)")

        if len(abstract) > self._settings.quality_max_abstract_length:
            errors.append(f"Abstract too long (maximum {self._settings.quality_max_abstract_length} characters)")

        # Check for suspicious patterns
        if re.search(r'[<>]', abstract):
            errors.append("Abstract contains HTML tags")

        # Check for excessive whitespace
        if '\n\n\n' in abstract:
            warnings.append("Abstract contains excessive line breaks")

        # Check for very short words ratio (might indicate poor quality)
        words = abstract.split()
        if len(words) > 10:
            short_words = [w for w in words if len(w) <= 2]
            if len(short_words) / len(words) > 0.4:
                warnings.append("Abstract contains high ratio of short words")

        return {"errors": errors, "warnings": warnings}

    def _validate_authors(self, authors: List[str]) -> Dict[str, List[str]]:
        """Validate authors list."""
        errors = []
        warnings = []

        if not authors or len(authors) == 0:
            errors.append("No authors specified")
            return {"errors": errors, "warnings": warnings}

        if len(authors) > 20:
            warnings.append("Unusually high number of authors")

        for i, author in enumerate(authors):
            author = author.strip()
            if not author:
                errors.append(f"Author {i+1} is empty")
                continue

            # Check for suspicious patterns
            if re.search(r'[<>]', author):
                errors.append(f"Author {i+1} contains HTML tags")

            if len(author) < 2:
                errors.append(f"Author {i+1} name too short")

            if len(author) > 100:
                warnings.append(f"Author {i+1} name unusually long")

            # Check for numbers in names (might indicate parsing error)
            if re.search(r'\d', author):
                warnings.append(f"Author {i+1} contains numbers")

        return {"errors": errors, "warnings": warnings}

    def _validate_categories(self, categories: List[str]) -> Dict[str, List[str]]:
        """Validate arXiv categories."""
        errors = []
        warnings = []

        if not categories or len(categories) == 0:
            warnings.append("No categories specified")
            return {"errors": errors, "warnings": warnings}

        # Basic arXiv category validation (simplified)
        valid_prefixes = ['cs', 'math', 'physics', 'q-bio', 'q-fin', 'stat', 'cond-mat', 'nlin', 'astro-ph', 'hep-']

        for category in categories:
            if '.' not in category:
                warnings.append(f"Category '{category}' missing subcategory")
            else:
                prefix = category.split('.')[0]
                if prefix not in valid_prefixes:
                    warnings.append(f"Category '{category}' has unrecognized prefix")

        return {"errors": errors, "warnings": warnings}

    def _validate_doi(self, doi: str) -> Dict[str, List[str]]:
        """Validate DOI format."""
        errors = []
        warnings = []

        # Basic DOI pattern validation
        doi_pattern = r'^10\.\d{4,9}/[-._;()/:A-Z0-9]+$'
        if not re.match(doi_pattern, doi, re.IGNORECASE):
            errors.append("DOI format appears invalid")

        return {"errors": errors, "warnings": warnings}

    def _validate_arxiv_id(self, arxiv_id: str) -> Dict[str, List[str]]:
        """Validate arXiv ID format."""
        errors = []
        warnings = []

        # arXiv ID patterns: YYMM.NNNNN or archive/YYMMNNN
        patterns = [
            r'^\d{4}\.\d{5}$',  # 1402.12345
            r'^\d{4}\.\d{5}v\d+$',  # 1402.12345v1
            r'^[a-z-]+/\d{7}$',  # math/0211159
        ]

        if not any(re.match(pattern, arxiv_id) for pattern in patterns):
            errors.append("arXiv ID format appears invalid")

        return {"errors": errors, "warnings": warnings}

    def _generate_recommendations(self, issues: List[str], warnings: List[str]) -> List[str]:
        """Generate recommendations based on issues and warnings."""
        recommendations = []

        if any("empty" in issue.lower() for issue in issues):
            recommendations.append("Ensure all required fields are populated")

        if any("short" in issue.lower() for issue in issues):
            recommendations.append("Expand brief descriptions where possible")

        if any("html" in issue.lower() for issue in issues):
            recommendations.append("Remove HTML tags from text fields")

        if any("format" in issue.lower() for issue in issues):
            recommendations.append("Verify ID formats match expected patterns")

        if warnings:
            recommendations.append("Review warnings to improve data quality")

        return recommendations


class DuplicateDetector:
    """Service for detecting duplicate research papers."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=1000
        )

    async def find_duplicates(self, paper_data: PaperCreate) -> List[Dict[str, Any]]:
        """
        Find potential duplicate papers in the database.

        Returns:
            List of potential duplicates with similarity scores
        """
        try:
            async with async_session() as session:
                repo = PaperRepository(session)

                # First, check for exact arXiv ID or DOI matches
                exact_matches = []
                if paper_data.arxiv_id:
                    existing = repo.get_by_arxiv_id(paper_data.arxiv_id)
                    if existing:
                        exact_matches.append({
                            "paper": existing,
                            "similarity": 1.0,
                            "match_type": "exact_arxiv_id"
                        })

                if paper_data.doi:
                    existing = repo.get_by_doi(paper_data.doi)
                    if existing and existing not in [m["paper"] for m in exact_matches]:
                        exact_matches.append({
                            "paper": existing,
                            "similarity": 1.0,
                            "match_type": "exact_doi"
                        })

                if exact_matches:
                    return exact_matches

                # If no exact matches, check for similar papers
                candidates = repo.get_duplicate_candidates(
                    paper_data.arxiv_id,
                    paper_data.title,
                    paper_data.authors
                )

                if not candidates:
                    return []

                # Calculate similarity scores
                similarities = self._calculate_similarities(paper_data, candidates)

                # Filter by threshold and sort
                duplicates = [
                    {
                        "paper": candidate,
                        "similarity": score,
                        "match_type": "similarity"
                    }
                    for candidate, score in similarities.items()
                    if score >= self._settings.quality_duplicate_similarity_threshold
                ]

                duplicates.sort(key=lambda x: x["similarity"], reverse=True)
                return duplicates[:10]  # Return top 10 matches

        except Exception as e:
            logger.error(f"Error detecting duplicates: {e}")
            raise DuplicateDetectionException(f"Failed to detect duplicates: {e}")

    def _calculate_similarities(self, new_paper: PaperCreate, candidates: List[ResearchPaper]) -> Dict[ResearchPaper, float]:
        """Calculate similarity scores between new paper and candidates."""
        similarities = {}

        # Prepare texts for comparison
        new_text = f"{new_paper.title} {' '.join(new_paper.authors)} {new_paper.abstract or ''}"

        for candidate in candidates:
            candidate_text = f"{candidate.title} {' '.join(candidate.authors)} {candidate.abstract or ''}"

            # Calculate multiple similarity metrics
            title_sim = SequenceMatcher(None, new_paper.title.lower(), candidate.title.lower()).ratio()

            # Author similarity (Jaccard similarity)
            new_authors = set(a.lower() for a in new_paper.authors)
            cand_authors = set(a.lower() for a in candidate.authors)
            author_sim = len(new_authors & cand_authors) / len(new_authors | cand_authors) if (new_authors | cand_authors) else 0

            # Abstract similarity (if both have abstracts)
            abstract_sim = 0
            if new_paper.abstract and candidate.abstract:
                abstract_sim = SequenceMatcher(None,
                    new_paper.abstract.lower(),
                    candidate.abstract.lower()
                ).ratio()

            # Combined similarity score
            # Weight: title 40%, authors 30%, abstract 30%
            combined_sim = (title_sim * 0.4) + (author_sim * 0.3) + (abstract_sim * 0.3)

            similarities[candidate] = combined_sim

        return similarities

    async def check_and_handle_duplicates(self, paper_data: PaperCreate, user_id: str) -> Dict[str, Any]:
        """
        Check for duplicates and return handling recommendations.

        Returns:
            Dict with duplicate information and recommendations
        """
        duplicates = await self.find_duplicates(paper_data)

        if not duplicates:
            return {"has_duplicates": False, "action": "proceed"}

        # Get the best match
        best_match = duplicates[0]

        if best_match["similarity"] >= 0.95:  # Very high similarity
            return {
                "has_duplicates": True,
                "action": "reject",
                "reason": "Very high similarity to existing paper",
                "duplicate": best_match,
                "all_duplicates": duplicates
            }
        elif best_match["similarity"] >= 0.85:  # High similarity
            return {
                "has_duplicates": True,
                "action": "review",
                "reason": "High similarity to existing paper - manual review recommended",
                "duplicate": best_match,
                "all_duplicates": duplicates
            }
        else:  # Moderate similarity
            return {
                "has_duplicates": True,
                "action": "proceed_with_note",
                "reason": "Moderate similarity to existing paper - proceed but note duplicate",
                "duplicate": best_match,
                "all_duplicates": duplicates
            }