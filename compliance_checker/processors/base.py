"""
Base interfaces and abstract classes for document processors.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..models.document import SpecificationDocument, Requirement, DocumentSection
from ..models.report import ComplianceReport, FinalComplianceReport
from ..models.gdpr import GDPRArticle


class DocumentProcessor(ABC):
    """Abstract base class for document processing."""
    
    @abstractmethod
    def parse_specification(self, file_path: Path) -> SpecificationDocument:
        """Parse a specification document from file."""
        pass
    
    @abstractmethod
    def extract_requirements(self, document: SpecificationDocument) -> List[Requirement]:
        """Extract requirements from a specification document."""
        pass
    
    @abstractmethod
    def validate_document_format(self, file_path: Path) -> bool:
        """Validate that the document format is supported."""
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Get list of supported document formats."""
        pass


class ChainOfThoughtProcessor(ABC):
    """Abstract base class for chain-of-thought reasoning."""
    
    @abstractmethod
    def generate_reasoning_chain(
        self, 
        requirement: Requirement, 
        gdpr_articles: List[GDPRArticle]
    ) -> Dict[str, Any]:
        """Generate a chain-of-thought reasoning for compliance assessment."""
        pass
    
    @abstractmethod
    def evaluate_compliance_step_by_step(
        self, 
        reasoning_chain: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate compliance using step-by-step reasoning."""
        pass


class ReportGenerator(ABC):
    """Abstract base class for report generation."""
    
    @abstractmethod
    def generate_cc_report(
        self, 
        analysis_result: Dict[str, Any]
    ) -> ComplianceReport:
        """Generate a compliance report from CC_Agent analysis."""
        pass
    
    @abstractmethod
    def consolidate_reports(
        self, 
        reports: List[ComplianceReport]
    ) -> FinalComplianceReport:
        """Consolidate multiple compliance reports into a final report."""
        pass
    
    @abstractmethod
    def format_report(
        self, 
        report: ComplianceReport, 
        format_type: str
    ) -> str:
        """Format a report in the specified format (JSON, PDF, HTML)."""
        pass
    
    @abstractmethod
    def export_report(
        self, 
        report: ComplianceReport, 
        output_path: Path, 
        format_type: str
    ) -> bool:
        """Export a report to file in the specified format."""
        pass


class KnowledgeBaseProcessor(ABC):
    """Abstract base class for GDPR knowledge base processing."""
    
    @abstractmethod
    def build_vector_store(self, gdpr_docs_path: Path) -> None:
        """Build the FAISS vector store from GDPR documents."""
        pass
    
    @abstractmethod
    def query_relevant_articles(
        self, 
        query: str, 
        top_k: int = 5
    ) -> List[GDPRArticle]:
        """Query the knowledge base for relevant GDPR articles."""
        pass
    
    @abstractmethod
    def update_knowledge_base(self) -> None:
        """Update the knowledge base with new or modified documents."""
        pass
    
    @abstractmethod
    def validate_knowledge_base(self) -> bool:
        """Validate the integrity of the knowledge base."""
        pass