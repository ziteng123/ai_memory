"""
Error Handler for Memory MCP Server

Provides standardized error response formatting and comprehensive
error handling for all server operations.
"""

import logging
import traceback
from typing import Any, Dict, List, Optional
from enum import Enum
from mcp.types import TextContent

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """Standardized error codes for the Memory MCP Server."""
    
    # Configuration errors
    CONFIG_INVALID = "CONFIG_INVALID"
    CONFIG_MISSING = "CONFIG_MISSING"
    CONFIG_VALIDATION_FAILED = "CONFIG_VALIDATION_FAILED"
    
    # Connection errors
    REDIS_CONNECTION_FAILED = "REDIS_CONNECTION_FAILED"
    REDIS_CONNECTION_LOST = "REDIS_CONNECTION_LOST"
    REDIS_TIMEOUT = "REDIS_TIMEOUT"
    
    # Memory operation errors
    MEMORY_NOT_FOUND = "MEMORY_NOT_FOUND"
    MEMORY_ADD_FAILED = "MEMORY_ADD_FAILED"
    MEMORY_SEARCH_FAILED = "MEMORY_SEARCH_FAILED"
    MEMORY_DELETE_FAILED = "MEMORY_DELETE_FAILED"
    
    # Validation errors
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_USER_ID = "INVALID_USER_ID"
    INVALID_CONTENT = "INVALID_CONTENT"
    INVALID_METADATA = "INVALID_METADATA"
    INVALID_MEMORY_ID = "INVALID_MEMORY_ID"
    
    # Server errors
    SERVER_NOT_INITIALIZED = "SERVER_NOT_INITIALIZED"
    SERVER_INITIALIZATION_FAILED = "SERVER_INITIALIZATION_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    
    # MCP protocol errors
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"
    MCP_PROTOCOL_ERROR = "MCP_PROTOCOL_ERROR"


class MCPError(Exception):
    """Base exception class for MCP server errors."""
    
    def __init__(self, code: ErrorCode, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize MCP error.
        
        Args:
            code: Error code from ErrorCode enum
            message: Human-readable error message
            details: Optional additional error details
        """
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ValidationError(MCPError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        
        super().__init__(ErrorCode.INVALID_INPUT, message, details)


class ConnectionError(MCPError):
    """Raised when connection operations fail."""
    
    def __init__(self, message: str, connection_type: str = "redis"):
        details = {"connection_type": connection_type}
        super().__init__(ErrorCode.REDIS_CONNECTION_FAILED, message, details)


class MemoryError(MCPError):
    """Raised when memory operations fail."""
    
    def __init__(self, code: ErrorCode, message: str, memory_id: Optional[str] = None, user_id: Optional[str] = None):
        details = {}
        if memory_id:
            details["memory_id"] = memory_id
        if user_id:
            details["user_id"] = user_id
        
        super().__init__(code, message, details)


class ErrorHandler:
    """Handles error formatting and logging for the MCP server."""
    
    def __init__(self, logger_name: str = __name__):
        """Initialize error handler.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = logging.getLogger(logger_name)
    
    def format_error_response(self, error: Exception, include_traceback: bool = False) -> List[TextContent]:
        """Format an error as an MCP TextContent response.
        
        Args:
            error: The exception to format
            include_traceback: Whether to include traceback in response
            
        Returns:
            List[TextContent]: Formatted error response
        """
        if isinstance(error, MCPError):
            return self._format_mcp_error(error, include_traceback)
        else:
            return self._format_generic_error(error, include_traceback)
    
    def _format_mcp_error(self, error: MCPError, include_traceback: bool = False) -> List[TextContent]:
        """Format an MCPError as a response.
        
        Args:
            error: The MCPError to format
            include_traceback: Whether to include traceback
            
        Returns:
            List[TextContent]: Formatted error response
        """
        error_dict = {
            "error": {
                "code": error.code.value,
                "message": error.message,
                "details": error.details
            }
        }
        
        if include_traceback:
            error_dict["error"]["traceback"] = traceback.format_exc()
        
        # Log the error
        self.logger.error(f"MCP Error [{error.code.value}]: {error.message}", extra={"details": error.details})
        
        # Format as user-friendly text
        text = f"Error [{error.code.value}]: {error.message}"
        
        if error.details:
            text += f"\nDetails: {error.details}"
        
        return [TextContent(type="text", text=text)]
    
    def _format_generic_error(self, error: Exception, include_traceback: bool = False) -> List[TextContent]:
        """Format a generic exception as a response.
        
        Args:
            error: The exception to format
            include_traceback: Whether to include traceback
            
        Returns:
            List[TextContent]: Formatted error response
        """
        error_code = self._classify_error(error)
        error_message = str(error) or "An unexpected error occurred"
        
        error_dict = {
            "error": {
                "code": error_code.value,
                "message": error_message,
                "type": type(error).__name__
            }
        }
        
        if include_traceback:
            error_dict["error"]["traceback"] = traceback.format_exc()
        
        # Log the error
        self.logger.error(f"Unhandled Error [{error_code.value}]: {error_message}", exc_info=True)
        
        # Format as user-friendly text
        text = f"Error [{error_code.value}]: {error_message}"
        
        return [TextContent(type="text", text=text)]
    
    def _classify_error(self, error: Exception) -> ErrorCode:
        """Classify a generic exception into an appropriate error code.
        
        Args:
            error: The exception to classify
            
        Returns:
            ErrorCode: Appropriate error code
        """
        error_type = type(error).__name__.lower()
        error_message = str(error).lower()
        
        # Connection-related errors
        if "connection" in error_type or "connection" in error_message:
            return ErrorCode.REDIS_CONNECTION_FAILED
        
        if "timeout" in error_type or "timeout" in error_message:
            return ErrorCode.REDIS_TIMEOUT
        
        # Validation errors
        if "validation" in error_type or "invalid" in error_message:
            return ErrorCode.INVALID_INPUT
        
        # Memory operation errors
        if "not found" in error_message:
            return ErrorCode.MEMORY_NOT_FOUND
        
        # Default to internal error
        return ErrorCode.INTERNAL_ERROR
    
    def log_operation(self, operation: str, user_id: str, details: Optional[Dict[str, Any]] = None):
        """Log a successful operation.
        
        Args:
            operation: Name of the operation
            user_id: User ID associated with the operation
            details: Optional additional details
        """
        log_details = {"user_id": user_id}
        if details:
            log_details.update(details)
        
        self.logger.info(f"Operation '{operation}' completed successfully", extra=log_details)
    
    def log_operation_start(self, operation: str, user_id: str, details: Optional[Dict[str, Any]] = None):
        """Log the start of an operation.
        
        Args:
            operation: Name of the operation
            user_id: User ID associated with the operation
            details: Optional additional details
        """
        log_details = {"user_id": user_id}
        if details:
            log_details.update(details)
        
        self.logger.debug(f"Starting operation '{operation}'", extra=log_details)
    
    def log_validation_error(self, field: str, value: Any, reason: str):
        """Log a validation error.
        
        Args:
            field: Field that failed validation
            value: Value that failed validation
            reason: Reason for validation failure
        """
        self.logger.warning(
            f"Validation failed for field '{field}': {reason}",
            extra={"field": field, "value": str(value), "reason": reason}
        )
    
    def log_connection_event(self, event: str, connection_type: str = "redis", details: Optional[Dict[str, Any]] = None):
        """Log a connection-related event.
        
        Args:
            event: Description of the connection event
            connection_type: Type of connection (e.g., 'redis')
            details: Optional additional details
        """
        log_details = {"connection_type": connection_type}
        if details:
            log_details.update(details)
        
        self.logger.info(f"Connection event: {event}", extra=log_details)


def setup_logging(log_level: str = "INFO", log_format: Optional[str] = None) -> logging.Logger:
    """Set up logging configuration for the MCP server.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Optional custom log format
        
    Returns:
        logging.Logger: Configured logger instance
    """
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(),
        ]
    )
    
    # Get logger for the MCP server
    logger = logging.getLogger("memory_mcp_server")
    
    # Add structured logging for JSON output if needed
    try:
        import json
        
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": self.formatTime(record),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                
                # Add extra fields if present
                if hasattr(record, 'user_id'):
                    log_entry["user_id"] = record.user_id
                if hasattr(record, 'details'):
                    log_entry["details"] = record.details
                
                return json.dumps(log_entry)
        
        # Optionally add JSON handler for structured logging
        # json_handler = logging.StreamHandler()
        # json_handler.setFormatter(JSONFormatter())
        # logger.addHandler(json_handler)
        
    except ImportError:
        # JSON logging not available, continue with standard logging
        pass
    
    logger.info(f"Logging configured with level: {log_level}")
    return logger


# Global error handler instance
error_handler = ErrorHandler()