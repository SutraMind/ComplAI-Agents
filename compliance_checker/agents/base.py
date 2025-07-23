"""
Base interfaces and abstract classes for compliance checker agents.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.document import SpecificationDocument
from ..models.report import ComplianceReport, FinalComplianceReport
from ..models.gdpr import GDPRArticle


class BaseAgent(ABC):
    """Abstract base class for all compliance checker agents."""
    
    def __init__(self, model_name: str, agent_id: str):
        self.model_name = model_name
        self.agent_id = agent_id
        self.created_at = datetime.now()
        self.status = "initialized"
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the agent and verify model availability."""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status and health information."""
        pass


class ComplianceCheckerAgent(BaseAgent):
    """Abstract base class for CC_Agents (Compliance Checker Agents)."""
    
    @abstractmethod
    def analyze_compliance(
        self, 
        document: SpecificationDocument, 
        gdpr_context: List[GDPRArticle]
    ) -> ComplianceReport:
        """Analyze document for GDPR compliance and generate report."""
        pass
    
    @abstractmethod
    def process_feedback(self, feedback: str) -> None:
        """Process feedback from RA_Agent and adjust analysis approach."""
        pass


class ReportAssessorAgent(BaseAgent):
    """Abstract base class for RA_Agent (Report Assessor Agent)."""
    
    @abstractmethod
    def assess_reports(self, reports: List[ComplianceReport]) -> FinalComplianceReport:
        """Assess and consolidate multiple compliance reports."""
        pass
    
    @abstractmethod
    def generate_feedback(self, reports: List[ComplianceReport]) -> List[Dict[str, Any]]:
        """Generate feedback for CC_Agents based on their reports."""
        pass


class AgentOrchestrator(ABC):
    """Abstract base class for agent orchestration."""
    
    @abstractmethod
    def execute_compliance_analysis(
        self, 
        document: SpecificationDocument
    ) -> FinalComplianceReport:
        """Execute the complete multi-agent compliance analysis workflow."""
        pass
    
    @abstractmethod
    def coordinate_agents(self) -> None:
        """Coordinate the execution of multiple agents."""
        pass
    
    @abstractmethod
    def handle_feedback_loop(
        self, 
        feedback: List[Dict[str, Any]], 
        max_iterations: int = 3
    ) -> None:
        """Handle the feedback loop between RA_Agent and CC_Agents."""
        pass