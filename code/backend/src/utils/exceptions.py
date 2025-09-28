"""
Custom exceptions for the Research Copilot system
"""


class ResearchCopilotException(Exception):
    """Base exception for Research Copilot"""
    pass


class ArxivAPIException(ResearchCopilotException):
    """Exception raised for arXiv API errors"""
    pass


class ArxivAPITimeoutError(ArxivAPIException):
    """Exception raised for arXiv API timeout errors"""
    pass


class ArxivParseError(ArxivAPIException):
    """Exception raised for arXiv XML parsing errors"""
    pass


class PDFDownloadException(ResearchCopilotException):
    """Exception raised for PDF download errors"""
    pass


class PDFDownloadTimeoutError(PDFDownloadException):
    """Exception raised for PDF download timeout errors"""
    pass


class PDFParsingException(ResearchCopilotException):
    """Exception raised for PDF parsing errors"""
    pass


class PDFValidationError(ResearchCopilotException):
    """Exception raised for PDF validation errors"""
    pass


class IngestionException(ResearchCopilotException):
    """Exception raised for data ingestion errors"""
    pass


class DuplicateDetectionException(ResearchCopilotException):
    """Exception raised for duplicate detection errors"""
    pass


class QualityValidationException(ResearchCopilotException):
    """Exception raised for data quality validation errors"""
    pass


class DatabaseException(ResearchCopilotException):
    """Exception raised for database operation errors"""
    pass


class ConfigurationException(ResearchCopilotException):
    """Exception raised for configuration errors"""
    pass


class NotFoundError(ResearchCopilotException):
    """Exception raised when a resource is not found"""
    pass


class ValidationError(ResearchCopilotException):
    """Exception raised for validation errors"""
    pass


class PermissionDeniedError(ResearchCopilotException):
    """Exception raised when permission is denied"""
    pass


class AuthenticationError(ResearchCopilotException):
    """Exception raised for authentication failures"""
    pass


class AuthorizationError(ResearchCopilotException):
    """Exception raised for authorization failures"""
    pass