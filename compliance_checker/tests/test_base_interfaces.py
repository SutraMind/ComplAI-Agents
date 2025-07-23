"""
Tests for base interfaces and abstract classes.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from ..agents.base import BaseAgent, ComplianceCheckerAgent, ReportAssessorAgent
from ..processors.base import DocumentProcessor, ChainOfThoughtProcessor, ReportGenerator
from ..models.document import SpecificationDocument, Requirement
from ..models.report import ComplianceReport, ComplianceFinding, ComplianceStatus, SeverityLevel
from ..models.gdpr import GDPRArticle


class TestBaseAgent:
    """Test the BaseAgent abstract class."""
    
    def test_base_agent_initialization(self):
        """Test that BaseAgent can be initialized with required parameters."""
        
        class ConcreteAgent(BaseAgent):
            def initialize(self):
                return True
            
            def get_status(self):
                return {"status": "active"}
        
        agent = ConcreteAgent("test-model", "test-agent-1")
        
        assert agent.model_name == "test-model"
        assert agent.agent_id == "test-agent-1"
        assert agent.status == "initialized"
        assert isinstance(agent.created_at, datetime)
        assert agent.initialize() is True
        assert agent.get_status() == {"status": "active"}


class TestComplianceCheckerAgent:
    """Test the ComplianceCheckerAgent abstract class."""
    
    def test_cc_agent_interface(self):
        """Test that CC_Agent interface is properly defined."""
        
        class ConcreteCCAgent(ComplianceCheckerAgent):
            def initialize(self):
                return True
            
            def get_status(self):
                return {"status": "ready"}
            
            def analyze_compliance(self, document, gdpr_context):
                return Mock(spec=ComplianceReport)
            
            def process_feedback(self, feedback):
                pass
        
        agent = ConcreteCCAgent("deepseek-r1:8b", "cc_agent_1")
        
        # Test inheritance
        assert isinstance(agent, BaseAgent)
        assert agent.model_name == "deepseek-r1:8b"
        assert agent.agent_id == "cc_agent_1"
        
        # Test interface methods
        mock_document = Mock(spec=SpecificationDocument)
        mock_gdpr_articles = [Mock(spec=GDPRArticle)]
        
        result = agent.analyze_compliance(mock_document, mock_gdpr_articles)
        assert result is not None
        
        agent.process_feedback("test feedback")  # Should not raise


class TestReportAssessorAgent:
    """Test the ReportAssessorAgent abstract class."""
    
    def test_ra_agent_interface(self):
        """Test that RA_Agent interface is properly defined."""
        
        class ConcreteRAAgent(ReportAssessorAgent):
            def initialize(self):
                return True
            
            def get_status(self):
                return {"status": "ready"}
            
            def assess_reports(self, reports):
                return Mock()
            
            def generate_feedback(self, reports):
                return [{"agent_id": "cc_agent_1", "feedback": "test"}]
        
        agent = ConcreteRAAgent("qwq:32b", "ra_agent")
        
        # Test inheritance
        assert isinstance(agent, BaseAgent)
        assert agent.model_name == "qwq:32b"
        assert agent.agent_id == "ra_agent"
        
        # Test interface methods
        mock_reports = [Mock(spec=ComplianceReport)]
        
        result = agent.assess_reports(mock_reports)
        assert result is not None
        
        feedback = agent.generate_feedback(mock_reports)
        assert isinstance(feedback, list)
        assert len(feedback) == 1


class TestDocumentProcessor:
    """Test the DocumentProcessor abstract class."""
    
    def test_document_processor_interface(self):
        """Test that DocumentProcessor interface is properly defined."""
        
        class ConcreteDocumentProcessor(DocumentProcessor):
            def parse_specification(self, file_path):
                return Mock(spec=SpecificationDocument)
            
            def extract_requirements(self, document):
                return [Mock(spec=Requirement)]
            
            def validate_document_format(self, file_path):
                return True
            
            def get_supported_formats(self):
                return [".pdf", ".docx", ".txt"]
        
        processor = ConcreteDocumentProcessor()
        
        # Test interface methods
        from pathlib import Path
        mock_path = Path("test.pdf")
        
        doc = processor.parse_specification(mock_path)
        assert doc is not None
        
        requirements = processor.extract_requirements(Mock())
        assert isinstance(requirements, list)
        
        assert processor.validate_document_format(mock_path) is True
        
        formats = processor.get_supported_formats()
        assert isinstance(formats, list)
        assert ".pdf" in formats


class TestDataModels:
    """Test the data models work correctly."""
    
    def test_specification_document_model(self):
        """Test SpecificationDocument model."""
        doc = SpecificationDocument(
            content="Test content",
            metadata={"author": "test"},
            document_id="doc-1"
        )
        
        assert doc.content == "Test content"
        assert doc.metadata["author"] == "test"
        assert doc.document_id == "doc-1"
        assert isinstance(doc.processed_at, datetime)
    
    def test_compliance_finding_model(self):
        """Test ComplianceFinding model."""
        finding = ComplianceFinding(
            requirement_id="req-1",
            requirement_text="Test requirement",
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            gdpr_articles=["Article 6"],
            reasoning="Test reasoning",
            severity=SeverityLevel.HIGH
        )
        
        assert finding.requirement_id == "req-1"
        assert finding.compliance_status == ComplianceStatus.NON_COMPLIANT
        assert finding.severity == SeverityLevel.HIGH
        assert "Article 6" in finding.gdpr_articles
    
    def test_compliance_report_model(self):
        """Test ComplianceReport model."""
        finding = ComplianceFinding(
            requirement_id="req-1",
            requirement_text="Test requirement",
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            gdpr_articles=["Article 6"],
            reasoning="Test reasoning",
            severity=SeverityLevel.HIGH
        )
        
        report = ComplianceReport(
            agent_id="cc_agent_1",
            model_used="deepseek-r1:8b",
            findings=[finding],
            overall_assessment="Non-compliant",
            confidence_score=0.85
        )
        
        assert report.agent_id == "cc_agent_1"
        assert len(report.findings) == 1
        assert report.confidence_score == 0.85
        
        # Test utility methods
        non_compliant = report.get_non_compliant_findings()
        assert len(non_compliant) == 1
        
        high_severity = report.get_findings_by_severity(SeverityLevel.HIGH)
        assert len(high_severity) == 1
        
        stats = report.get_summary_stats()
        assert stats["total_findings"] == 1
        assert stats["non_compliant"] == 1