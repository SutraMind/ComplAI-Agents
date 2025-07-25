"""
Session management for tracking analysis progress and state.
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from ..models.document import SpecificationDocument
from ..models.report import ComplianceReport, FinalComplianceReport


class SessionStatus(Enum):
    """Enumeration for analysis session status."""
    CREATED = "created"
    INITIALIZING = "initializing"
    DOCUMENT_PROCESSING = "document_processing"
    CC_AGENTS_RUNNING = "cc_agents_running"
    RA_AGENT_ASSESSING = "ra_agent_assessing"
    FEEDBACK_PROCESSING = "feedback_processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FeedbackIteration:
    """Represents a single feedback iteration."""
    iteration_number: int
    feedback_data: List[Dict[str, Any]]
    cc_agent_responses: Dict[str, ComplianceReport] = field(default_factory=dict)
    ra_agent_assessment: Optional[FinalComplianceReport] = None
    timestamp: datetime = field(default_factory=datetime.now)
    processing_time: Optional[float] = None


@dataclass
class AnalysisSession:
    """
    Manages the state and progress of a multi-agent compliance analysis session.
    
    This class tracks the entire lifecycle of an analysis from document upload
    through final report generation, including feedback iterations.
    """
    
    # Session identification
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Session status and progress
    status: SessionStatus = SessionStatus.CREATED
    current_stage: str = "initialization"
    progress_percentage: float = 0.0
    
    # Document information
    document: Optional[SpecificationDocument] = None
    document_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Agent execution tracking
    cc_agent_reports: Dict[str, ComplianceReport] = field(default_factory=dict)
    ra_agent_report: Optional[FinalComplianceReport] = None
    
    # Feedback loop tracking
    feedback_iterations: List[FeedbackIteration] = field(default_factory=list)
    current_iteration: int = 0
    max_iterations: int = 3
    
    # Timing and performance
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_processing_time: Optional[float] = None
    
    # Error tracking
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    
    def start_session(self) -> None:
        """Start the analysis session."""
        self.start_time = datetime.now()
        self.status = SessionStatus.INITIALIZING
        self.current_stage = "initializing_agents"
        self.progress_percentage = 5.0
        self._update_timestamp()
    
    def set_document(self, document: SpecificationDocument, metadata: Dict[str, Any] = None) -> None:
        """Set the document to be analyzed."""
        self.document = document
        self.document_metadata = metadata or {}
        self.status = SessionStatus.DOCUMENT_PROCESSING
        self.current_stage = "processing_document"
        self.progress_percentage = 15.0
        self._update_timestamp()
    
    def start_cc_agents(self) -> None:
        """Mark the start of CC_Agent execution."""
        self.status = SessionStatus.CC_AGENTS_RUNNING
        self.current_stage = "cc_agents_analyzing"
        self.progress_percentage = 25.0
        self._update_timestamp()
    
    def add_cc_agent_report(self, agent_id: str, report: ComplianceReport) -> None:
        """Add a CC_Agent report to the session."""
        self.cc_agent_reports[agent_id] = report
        
        # Update progress based on completed agents
        expected_agents = 2  # CC_Agent_1 and CC_Agent_2
        completed_agents = len(self.cc_agent_reports)
        agent_progress = (completed_agents / expected_agents) * 40  # 40% of total progress for CC agents
        self.progress_percentage = 25.0 + agent_progress
        
        if completed_agents == expected_agents:
            self.current_stage = "cc_agents_completed"
            self.progress_percentage = 65.0
        
        self._update_timestamp()
    
    def start_ra_agent(self) -> None:
        """Mark the start of RA_Agent execution."""
        self.status = SessionStatus.RA_AGENT_ASSESSING
        self.current_stage = "ra_agent_assessing"
        self.progress_percentage = 70.0
        self._update_timestamp()
    
    def set_ra_agent_report(self, report: FinalComplianceReport) -> None:
        """Set the RA_Agent final report."""
        self.ra_agent_report = report
        self.current_stage = "ra_agent_completed"
        self.progress_percentage = 85.0
        self._update_timestamp()
    
    def start_feedback_iteration(self, iteration_number: int) -> None:
        """Start a new feedback iteration."""
        self.current_iteration = iteration_number
        self.status = SessionStatus.FEEDBACK_PROCESSING
        self.current_stage = f"feedback_iteration_{iteration_number}"
        
        # Adjust progress for feedback iterations
        base_progress = 85.0
        iteration_progress = (iteration_number / self.max_iterations) * 10  # 10% for feedback
        self.progress_percentage = base_progress + iteration_progress
        
        self._update_timestamp()
    
    def add_feedback_iteration(self, iteration: FeedbackIteration) -> None:
        """Add a completed feedback iteration."""
        self.feedback_iterations.append(iteration)
        self.current_iteration = iteration.iteration_number
        self._update_timestamp()
    
    def complete_session(self) -> None:
        """Mark the session as completed."""
        self.end_time = datetime.now()
        self.status = SessionStatus.COMPLETED
        self.current_stage = "completed"
        self.progress_percentage = 100.0
        
        if self.start_time:
            self.total_processing_time = (self.end_time - self.start_time).total_seconds()
        
        self._update_timestamp()
    
    def fail_session(self, error: str, error_details: Dict[str, Any] = None) -> None:
        """Mark the session as failed."""
        self.end_time = datetime.now()
        self.status = SessionStatus.FAILED
        self.current_stage = "failed"
        
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error": error,
            "details": error_details or {},
            "stage": self.current_stage
        }
        self.errors.append(error_entry)
        
        if self.start_time:
            self.total_processing_time = (self.end_time - self.start_time).total_seconds()
        
        self._update_timestamp()
    
    def cancel_session(self) -> None:
        """Cancel the session."""
        self.end_time = datetime.now()
        self.status = SessionStatus.CANCELLED
        self.current_stage = "cancelled"
        
        if self.start_time:
            self.total_processing_time = (self.end_time - self.start_time).total_seconds()
        
        self._update_timestamp()
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the session."""
        self.warnings.append(f"[{datetime.now().isoformat()}] {warning}")
        self._update_timestamp()
    
    def add_error(self, error: str, error_details: Dict[str, Any] = None) -> None:
        """Add an error to the session without failing it."""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error": error,
            "details": error_details or {},
            "stage": self.current_stage
        }
        self.errors.append(error_entry)
        self._update_timestamp()
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session status."""
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "current_stage": self.current_stage,
            "progress_percentage": self.progress_percentage,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_processing_time": self.total_processing_time,
            "current_iteration": self.current_iteration,
            "max_iterations": self.max_iterations,
            "cc_agents_completed": len(self.cc_agent_reports),
            "ra_agent_completed": self.ra_agent_report is not None,
            "feedback_iterations_completed": len(self.feedback_iterations),
            "error_count": len(self.errors),
            "warning_count": len(self.warnings)
        }
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed status including all session data."""
        status = self.get_status_summary()
        
        # Add detailed information
        status.update({
            "document_metadata": self.document_metadata,
            "cc_agent_reports": {
                agent_id: {
                    "findings_count": len(report.findings),
                    "confidence_score": report.confidence_score,
                    "processing_time": report.processing_time,
                    "iteration_number": report.iteration_number
                }
                for agent_id, report in self.cc_agent_reports.items()
            },
            "ra_agent_report": {
                "findings_count": len(self.ra_agent_report.consolidated_findings),
                "confidence_score": self.ra_agent_report.confidence_score,
                "feedback_iterations": self.ra_agent_report.feedback_iterations
            } if self.ra_agent_report else None,
            "feedback_iterations": [
                {
                    "iteration_number": iteration.iteration_number,
                    "timestamp": iteration.timestamp.isoformat(),
                    "processing_time": iteration.processing_time,
                    "agents_responded": len(iteration.cc_agent_responses)
                }
                for iteration in self.feedback_iterations
            ],
            "errors": self.errors,
            "warnings": self.warnings,
            "config": self.config
        })
        
        return status
    
    def is_active(self) -> bool:
        """Check if the session is currently active."""
        active_statuses = {
            SessionStatus.INITIALIZING,
            SessionStatus.DOCUMENT_PROCESSING,
            SessionStatus.CC_AGENTS_RUNNING,
            SessionStatus.RA_AGENT_ASSESSING,
            SessionStatus.FEEDBACK_PROCESSING
        }
        return self.status in active_statuses
    
    def is_completed(self) -> bool:
        """Check if the session is completed."""
        return self.status == SessionStatus.COMPLETED
    
    def is_failed(self) -> bool:
        """Check if the session has failed."""
        return self.status == SessionStatus.FAILED
    
    def can_continue_feedback(self) -> bool:
        """Check if feedback iterations can continue."""
        return (
            self.current_iteration < self.max_iterations and
            self.status in {SessionStatus.RA_AGENT_ASSESSING, SessionStatus.FEEDBACK_PROCESSING, SessionStatus.CREATED} and
            not self.is_failed()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization."""
        data = asdict(self)
        
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        
        # Convert enum to string
        data["status"] = self.status.value
        
        # Handle complex objects
        if self.document:
            data["document"] = asdict(self.document)
        
        if self.cc_agent_reports:
            data["cc_agent_reports"] = {
                agent_id: asdict(report) 
                for agent_id, report in self.cc_agent_reports.items()
            }
        
        if self.ra_agent_report:
            data["ra_agent_report"] = asdict(self.ra_agent_report)
        
        if self.feedback_iterations:
            data["feedback_iterations"] = [
                asdict(iteration) for iteration in self.feedback_iterations
            ]
        
        return data
    
    def save_to_file(self, filepath: str) -> None:
        """Save session to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'AnalysisSession':
        """Load session from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Convert string timestamps back to datetime objects
        datetime_fields = ['created_at', 'updated_at', 'start_time', 'end_time']
        for field in datetime_fields:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        
        # Convert status string back to enum
        if 'status' in data:
            data['status'] = SessionStatus(data['status'])
        
        # TODO: Reconstruct complex objects (document, reports, etc.)
        # This would require more sophisticated deserialization
        
        return cls(**data)
    
    def _update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        self.updated_at = datetime.now()