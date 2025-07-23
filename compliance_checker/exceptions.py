"""
Custom exceptions for the compliance checker system.
"""


class ComplianceCheckerError(Exception):
    """Base exception for compliance checker errors."""
    pass


class ConfigurationError(ComplianceCheckerError):
    """Raised when there are configuration-related errors."""
    pass


class ModelUnavailableError(ComplianceCheckerError):
    """Raised when required Ollama model is not available."""
    
    def __init__(self, model_name: str, message: str = None):
        self.model_name = model_name
        if message is None:
            message = f"Model '{model_name}' is not available"
        super().__init__(message)


class DocumentProcessingError(ComplianceCheckerError):
    """Raised when document cannot be processed."""
    
    def __init__(self, filename: str, message: str = None):
        self.filename = filename
        if message is None:
            message = f"Failed to process document '{filename}'"
        super().__init__(message)


class VectorStoreError(ComplianceCheckerError):
    """Raised when vector database operations fail."""
    pass


class AgentExecutionError(ComplianceCheckerError):
    """Raised when agent execution fails."""
    
    def __init__(self, agent_id: str, message: str = None):
        self.agent_id = agent_id
        if message is None:
            message = f"Agent '{agent_id}' execution failed"
        super().__init__(message)


class ValidationError(ComplianceCheckerError):
    """Raised when input validation fails."""
    pass


class TimeoutError(ComplianceCheckerError):
    """Raised when operations timeout."""
    pass


class InsufficientResourcesError(ComplianceCheckerError):
    """Raised when system resources are insufficient."""
    pass