"""
Unit tests for CC_Agent (Compliance Checker Agent).
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from pathlib import Path

from compliance_checker.agents.cc_agent import CCAgent
from compliance_checker.models.document import SpecificationDocument, Requirement, DocumentSection
from compliance_checker.models.report import ComplianceReport, ComplianceFinding, ComplianceStatus, SeverityLevel
from compliance_checker.models.gdpr import GDPRArticle
from compliance_checker.llm.multi_agent_client import MultiAgentLLMClient, AgentType, ChainOfThoughtResponse
from compliance_checker.knowledge.gdpr_knowledge_base import GDPRKnowledgeBase
from compliance_checker.exceptions import ModelUnavailableError


class TestCCAgent:
    """Test suite for CC_Agent class."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = Mock(spec=MultiAgentLLMClient)
        client.verify_model_availability.return_value = {"deepseek-r1:8b": True, "gemma3:27b": True}
        client.generate.return_value = Mock(success=True, content="Test response", error=None)
        return client
    
    @pytest.fixture
    def mock_gdpr_knowledge_base(self):
        """Create mock GDPR knowledge base."""
        kb = Mock(spec=GDPRKnowledgeBase)
        
        # Mock GDPR articles
        article_6 = GDPRArticle(
            article_number="6",
            title="Lawfulness of processing",
            content="Processing shall be lawful only if and to the extent that at least one of the following applies...",
            keywords=["lawful basis", "processing", "consent"]
        )
        
        article_7 = GDPRArticle(
            article_number="7",
            title="Conditions for consent",
            content="Where processing is based on consent, the controller shall be able to demonstrate...",
            keywords=["consent", "controller", "demonstrate"]
        )
        
        kb.query_relevant_articles.return_value = [article_6, article_7]
        return kb
    
    @pytest.fixture
    def sample_document(self):
        """Create sample specification document."""
        requirements = [
            Requirement(
                id="req_1",
                text="The system shall collect user email addresses for authentication purposes",
                section="authentication",
                category="functional",
                metadata={"keywords": ["email", "authentication", "user data"], "gdpr_relevant": True}
            ),
            Requirement(
                id="req_2",
                text="The application must store user preferences in the database",
                section="user_management",
                category="data",
                metadata={"keywords": ["user preferences", "database", "storage"], "gdpr_relevant": True}
            )
        ]
        
        sections = [
            DocumentSection(
                id="auth_section",
                title="Authentication",
                content="This section describes authentication requirements...",
                level=1
            )
        ]
        
        return SpecificationDocument(
            content="Sample specification document content...",
            metadata={"filename": "test_spec.pdf", "processed_at": datetime.now().isoformat()},
            requirements=requirements,
            sections=sections,
            document_id="doc_123",
            filename="test_spec.pdf"
        )
    
    @pytest.fixture
    def cc_agent_1(self, mock_llm_client, mock_gdpr_knowledge_base):
        """Create CC_Agent instance for testing."""
        return CCAgent(
            agent_id="cc_agent_1",
            model_name="deepseek-r1:8b",
            llm_client=mock_llm_client,
            gdpr_knowledge_base=mock_gdpr_knowledge_base
        )
    
    @pytest.fixture
    def cc_agent_2(self, mock_llm_client, mock_gdpr_knowledge_base):
        """Create second CC_Agent instance for testing."""
        return CCAgent(
            agent_id="cc_agent_2",
            model_name="gemma3:27b",
            llm_client=mock_llm_client,
            gdpr_knowledge_base=mock_gdpr_knowledge_base
        )
    
    def test_cc_agent_initialization_success(self, cc_agent_1):
        """Test successful CC_Agent initialization."""
        assert cc_agent_1.agent_id == "cc_agent_1"
        assert cc_agent_1.model_name == "deepseek-r1:8b"
        assert cc_agent_1.agent_type == AgentType.CC_AGENT_1
        assert cc_agent_1.status == "ready"
        assert cc_agent_1.iteration_count == 0
        assert len(cc_agent_1.feedback_history) == 0
    
    def test_cc_agent_2_initialization(self, cc_agent_2):
        """Test CC_Agent_2 initialization with different model."""
        assert cc_agent_2.agent_id == "cc_agent_2"
        assert cc_agent_2.model_name == "gemma3:27b"
        assert cc_agent_2.agent_type == AgentType.CC_AGENT_2
        assert cc_agent_2.status == "ready"
    
    def test_initialization_model_unavailable(self, mock_llm_client, mock_gdpr_knowledge_base):
        """Test initialization failure when model is unavailable."""
        mock_llm_client.verify_model_availability.return_value = {"deepseek-r1:8b": False}
        
        agent = CCAgent(
            agent_id="cc_agent_1",
            model_name="deepseek-r1:8b",
            llm_client=mock_llm_client,
            gdpr_knowledge_base=mock_gdpr_knowledge_base
        )
        
        assert agent.status == "error"
    
    def test_get_status(self, cc_agent_1):
        """Test get_status method."""
        status = cc_agent_1.get_status()
        
        assert status["agent_id"] == "cc_agent_1"
        assert status["model_name"] == "deepseek-r1:8b"
        assert status["agent_type"] == "cc_agent_1"
        assert status["status"] == "ready"
        assert status["iteration_count"] == 0
        assert status["feedback_count"] == 0
        assert "created_at" in status
    
    def test_analyze_compliance_success(self, cc_agent_1, sample_document, mock_llm_client):
        """Test successful compliance analysis."""
        # Mock chain-of-thought response
        mock_cot_response = ChainOfThoughtResponse(
            reasoning_steps=[
                "Step 1: Identified email collection for authentication",
                "Step 2: Checked GDPR Article 6 for lawful basis",
                "Step 3: Determined legitimate interest applies",
                "Step 4: No consent mechanism specified - potential issue"
            ],
            conclusion=json.dumps({
                "compliance_status": "partially_compliant",
                "severity": "medium",
                "gdpr_articles_referenced": ["Article 6", "Article 7"],
                "issues_identified": ["No explicit consent mechanism"],
                "recommendations": ["Implement clear consent collection", "Add privacy notice"]
            }),
            confidence_score=0.8,
            raw_response="Full analysis response...",
            model="deepseek-r1:8b",
            success=True
        )
        
        mock_llm_client.execute_chain_of_thought.return_value = mock_cot_response
        
        # Perform analysis
        report = cc_agent_1.analyze_compliance(sample_document)
        
        # Verify report structure
        assert isinstance(report, ComplianceReport)
        assert report.agent_id == "cc_agent_1"
        assert report.model_used == "deepseek-r1:8b"
        assert report.document_id == "doc_123"
        assert report.document_filename == "test_spec.pdf"
        assert report.iteration_number == 1
        assert report.total_requirements_analyzed == 2
        assert len(report.findings) > 0
        assert report.confidence_score > 0
        assert "compliance" in report.overall_assessment.lower()
    
    def test_analyze_compliance_no_requirements(self, cc_agent_1, mock_gdpr_knowledge_base):
        """Test analysis with document containing no requirements."""
        empty_document = SpecificationDocument(
            content="Document with no requirements",
            metadata={"filename": "empty.pdf"},
            requirements=[],
            sections=[],
            document_id="empty_doc",
            filename="empty.pdf"
        )
        
        report = cc_agent_1.analyze_compliance(empty_document)
        
        assert isinstance(report, ComplianceReport)
        assert len(report.findings) == 0
        assert report.total_requirements_analyzed == 0
        assert "no requirements" in report.overall_assessment.lower()
        assert report.confidence_score == 0.0
    
    def test_analyze_requirement_compliance(self, cc_agent_1, mock_llm_client):
        """Test analysis of individual requirement."""
        requirement = Requirement(
            id="test_req",
            text="The system shall process personal data with user consent",
            section="data_processing",
            category="data",
            metadata={"keywords": ["personal data", "consent"], "gdpr_relevant": True}
        )
        
        # Mock successful chain-of-thought response
        mock_cot_response = ChainOfThoughtResponse(
            reasoning_steps=["Step 1: Identified consent requirement", "Step 2: Checked GDPR compliance"],
            conclusion=json.dumps({
                "compliance_status": "compliant",
                "severity": "low",
                "gdpr_articles_referenced": ["Article 6", "Article 7"],
                "issues_identified": [],
                "recommendations": []
            }),
            confidence_score=0.9,
            raw_response="Analysis complete",
            model="deepseek-r1:8b",
            success=True
        )
        
        mock_llm_client.execute_chain_of_thought.return_value = mock_cot_response
        
        # Test the private method through analyze_compliance
        document = SpecificationDocument(
            content="Test document",
            metadata={},
            requirements=[requirement],
            sections=[],
            document_id="test_doc"
        )
        
        report = cc_agent_1.analyze_compliance(document)
        
        assert len(report.findings) == 1
        finding = report.findings[0]
        assert finding.requirement_id == "test_req"
        assert finding.compliance_status == ComplianceStatus.COMPLIANT
        assert finding.severity == SeverityLevel.LOW
        assert "Article 6" in finding.gdpr_articles
    
    def test_get_relevant_gdpr_articles(self, cc_agent_1, mock_gdpr_knowledge_base):
        """Test GDPR article retrieval for requirements."""
        requirement = Requirement(
            id="test_req",
            text="System processes user data",
            section="data",
            category="data",
            metadata={"keywords": ["user data", "processing"]}
        )
        
        # The method is private, so we test it through analyze_compliance
        # The mock should be called with the requirement text
        document = SpecificationDocument(
            content="Test",
            metadata={},
            requirements=[requirement],
            sections=[]
        )
        
        cc_agent_1.analyze_compliance(document)
        
        # Verify GDPR knowledge base was queried
        mock_gdpr_knowledge_base.query_relevant_articles.assert_called()
        call_args = mock_gdpr_knowledge_base.query_relevant_articles.call_args
        assert "user data" in call_args[1]["query"]
    
    def test_process_feedback(self, cc_agent_1):
        """Test feedback processing."""
        feedback1 = "Please focus more on data retention requirements"
        feedback2 = "Consider international data transfer implications"
        
        # Process first feedback
        cc_agent_1.process_feedback(feedback1)
        assert len(cc_agent_1.feedback_history) == 1
        assert cc_agent_1.feedback_history[0] == feedback1
        assert cc_agent_1.status == "feedback_processed"
        
        # Process second feedback
        cc_agent_1.process_feedback(feedback2)
        assert len(cc_agent_1.feedback_history) == 2
        assert cc_agent_1.feedback_history[1] == feedback2
    
    def test_feedback_history_limit(self, cc_agent_1):
        """Test that feedback history is limited to prevent prompt bloat."""
        # Add more than 5 feedback items
        for i in range(7):
            cc_agent_1.process_feedback(f"Feedback {i}")
        
        # Should keep only the last 5
        assert len(cc_agent_1.feedback_history) == 5
        assert cc_agent_1.feedback_history[0] == "Feedback 2"  # First kept item
        assert cc_agent_1.feedback_history[-1] == "Feedback 6"  # Last item
    
    def test_chain_of_thought_analysis_with_feedback(self, cc_agent_1, mock_llm_client):
        """Test that feedback is included in chain-of-thought analysis."""
        # Add some feedback
        cc_agent_1.process_feedback("Focus on consent mechanisms")
        cc_agent_1.process_feedback("Check data retention policies")
        
        requirement = Requirement(
            id="test_req",
            text="System stores user data",
            section="data",
            category="data"
        )
        
        gdpr_articles = [
            GDPRArticle(
                article_number="6",
                title="Lawfulness",
                content="Processing must be lawful",
                keywords=["lawful", "processing"]
            )
        ]
        
        # Mock response
        mock_cot_response = ChainOfThoughtResponse(
            reasoning_steps=["Analysis step"],
            conclusion='{"compliance_status": "compliant", "severity": "low"}',
            confidence_score=0.8,
            raw_response="Response",
            model="deepseek-r1:8b",
            success=True
        )
        mock_llm_client.execute_chain_of_thought.return_value = mock_cot_response
        
        # Analyze (this will call the private method)
        document = SpecificationDocument(
            content="Test",
            metadata={},
            requirements=[requirement],
            sections=[]
        )
        
        cc_agent_1.analyze_compliance(document)
        
        # Verify that execute_chain_of_thought was called
        mock_llm_client.execute_chain_of_thought.assert_called()
        call_args = mock_llm_client.execute_chain_of_thought.call_args
        
        # Check that feedback was included in the prompt
        prompt = call_args[1]["prompt"]
        assert "Previous feedback" in prompt
        assert "consent mechanisms" in prompt
    
    def test_overall_assessment_generation(self, cc_agent_1, sample_document, mock_llm_client):
        """Test overall assessment generation with different finding types."""
        # Mock responses for different compliance statuses
        responses = [
            # Non-compliant finding
            ChainOfThoughtResponse(
                reasoning_steps=["Found compliance issue"],
                conclusion=json.dumps({
                    "compliance_status": "non_compliant",
                    "severity": "critical",
                    "gdpr_articles_referenced": ["Article 6"],
                    "issues_identified": ["No lawful basis"],
                    "recommendations": ["Add consent mechanism"]
                }),
                confidence_score=0.9,
                raw_response="Non-compliant",
                model="deepseek-r1:8b",
                success=True
            ),
            # Compliant finding
            ChainOfThoughtResponse(
                reasoning_steps=["Requirement is compliant"],
                conclusion=json.dumps({
                    "compliance_status": "compliant",
                    "severity": "low",
                    "gdpr_articles_referenced": ["Article 6"],
                    "issues_identified": [],
                    "recommendations": []
                }),
                confidence_score=0.8,
                raw_response="Compliant",
                model="deepseek-r1:8b",
                success=True
            )
        ]
        
        mock_llm_client.execute_chain_of_thought.side_effect = responses
        
        report = cc_agent_1.analyze_compliance(sample_document)
        
        # Should identify compliance issues
        assert "compliance issues identified" in report.overall_assessment.lower()
        assert "critical issues require immediate attention" in report.overall_assessment
    
    def test_confidence_score_calculation(self, cc_agent_1, sample_document, mock_llm_client):
        """Test confidence score calculation."""
        # Mock high-confidence response
        mock_cot_response = ChainOfThoughtResponse(
            reasoning_steps=["High confidence analysis"],
            conclusion=json.dumps({
                "compliance_status": "compliant",
                "severity": "low"
            }),
            confidence_score=0.95,
            raw_response="High confidence",
            model="deepseek-r1:8b",
            success=True
        )
        
        mock_llm_client.execute_chain_of_thought.return_value = mock_cot_response
        
        report = cc_agent_1.analyze_compliance(sample_document)
        
        # Confidence should be high but adjusted by model reliability
        assert report.confidence_score > 0.7
        assert report.confidence_score <= 1.0
    
    def test_error_handling_in_analysis(self, cc_agent_1, sample_document, mock_llm_client):
        """Test error handling during analysis."""
        # Mock LLM client to raise exception
        mock_llm_client.execute_chain_of_thought.side_effect = Exception("LLM error")
        
        report = cc_agent_1.analyze_compliance(sample_document)
        
        # Should return report with no findings due to errors
        assert isinstance(report, ComplianceReport)
        assert "no compliance findings generated" in report.overall_assessment.lower()
        assert report.confidence_score == 0.0
        assert len(report.findings) == 0
    
    def test_chain_of_thought_failure_handling(self, cc_agent_1, mock_llm_client):
        """Test handling of chain-of-thought analysis failures."""
        requirement = Requirement(
            id="test_req",
            text="Test requirement",
            section="test",
            category="functional"
        )
        
        # Mock failed chain-of-thought response
        mock_cot_response = ChainOfThoughtResponse(
            reasoning_steps=[],
            conclusion="",
            confidence_score=0.0,
            raw_response="",
            model="deepseek-r1:8b",
            success=False,
            error="Analysis failed"
        )
        
        mock_llm_client.execute_chain_of_thought.return_value = mock_cot_response
        
        document = SpecificationDocument(
            content="Test",
            metadata={},
            requirements=[requirement],
            sections=[]
        )
        
        report = cc_agent_1.analyze_compliance(document)
        
        # Should handle failure gracefully
        assert isinstance(report, ComplianceReport)
        # Findings might be empty due to analysis failure
        assert report.total_requirements_analyzed == 1
    
    def test_json_parsing_fallback(self, cc_agent_1, mock_llm_client):
        """Test fallback when JSON parsing fails."""
        requirement = Requirement(
            id="test_req",
            text="Test requirement",
            section="test",
            category="functional"
        )
        
        # Mock response with invalid JSON
        mock_cot_response = ChainOfThoughtResponse(
            reasoning_steps=["Step 1", "Step 2"],
            conclusion="Invalid JSON response",
            confidence_score=0.7,
            raw_response="This is not valid JSON",
            model="deepseek-r1:8b",
            success=True
        )
        
        mock_llm_client.execute_chain_of_thought.return_value = mock_cot_response
        
        document = SpecificationDocument(
            content="Test",
            metadata={},
            requirements=[requirement],
            sections=[]
        )
        
        report = cc_agent_1.analyze_compliance(document)
        
        # Should create finding with fallback parsing
        assert len(report.findings) == 1
        finding = report.findings[0]
        assert finding.compliance_status == ComplianceStatus.UNCLEAR
        # The confidence score comes from the original response, not fallback
        assert finding.confidence_score == 0.7
        assert len(finding.reasoning) > 0
    
    def test_iteration_count_increment(self, cc_agent_1, sample_document, mock_llm_client):
        """Test that iteration count increments with each analysis."""
        mock_cot_response = ChainOfThoughtResponse(
            reasoning_steps=["Analysis"],
            conclusion='{"compliance_status": "compliant", "severity": "low"}',
            confidence_score=0.8,
            raw_response="Response",
            model="deepseek-r1:8b",
            success=True
        )
        mock_llm_client.execute_chain_of_thought.return_value = mock_cot_response
        
        # First analysis
        report1 = cc_agent_1.analyze_compliance(sample_document)
        assert report1.iteration_number == 1
        assert cc_agent_1.iteration_count == 1
        
        # Second analysis
        report2 = cc_agent_1.analyze_compliance(sample_document)
        assert report2.iteration_number == 2
        assert cc_agent_1.iteration_count == 2
    
    @pytest.mark.parametrize("agent_id,expected_type", [
        ("cc_agent_1", AgentType.CC_AGENT_1),
        ("cc_agent_2", AgentType.CC_AGENT_2),
        ("test_cc_agent_1", AgentType.CC_AGENT_1),
        ("another_cc_agent_2", AgentType.CC_AGENT_2),
    ])
    def test_agent_type_detection(self, agent_id, expected_type, mock_llm_client, mock_gdpr_knowledge_base):
        """Test agent type detection from agent ID."""
        agent = CCAgent(
            agent_id=agent_id,
            model_name="deepseek-r1:8b",
            llm_client=mock_llm_client,
            gdpr_knowledge_base=mock_gdpr_knowledge_base
        )
        
        assert agent.agent_type == expected_type


class TestCCAgentIntegration:
    """Integration tests for CC_Agent with real-like scenarios."""
    
    @pytest.fixture
    def integration_setup(self):
        """Setup for integration tests."""
        mock_llm_client = Mock(spec=MultiAgentLLMClient)
        mock_llm_client.verify_model_availability.return_value = {"deepseek-r1:8b": True}
        mock_llm_client.generate.return_value = Mock(success=True, content="Test", error=None)
        
        mock_gdpr_kb = Mock(spec=GDPRKnowledgeBase)
        mock_gdpr_kb.query_relevant_articles.return_value = [
            GDPRArticle(
                article_number="6",
                title="Lawfulness of processing",
                content="Processing shall be lawful only if...",
                keywords=["lawful", "processing", "consent"]
            )
        ]
        
        agent = CCAgent(
            agent_id="cc_agent_1",
            model_name="deepseek-r1:8b",
            llm_client=mock_llm_client,
            gdpr_knowledge_base=mock_gdpr_kb
        )
        
        return agent, mock_llm_client, mock_gdpr_kb
    
    def test_full_analysis_workflow(self, integration_setup):
        """Test complete analysis workflow from document to report."""
        agent, mock_llm_client, mock_gdpr_kb = integration_setup
        
        # Create realistic document
        document = SpecificationDocument(
            content="E-commerce system specification...",
            metadata={"filename": "ecommerce_spec.pdf"},
            requirements=[
                Requirement(
                    id="req_user_registration",
                    text="The system shall collect user email, name, and address during registration",
                    section="user_management",
                    category="data",
                    metadata={"keywords": ["email", "personal data", "registration"], "gdpr_relevant": True}
                ),
                Requirement(
                    id="req_payment_processing",
                    text="The system shall securely process payment information using encryption",
                    section="payment",
                    category="security",
                    metadata={"keywords": ["payment", "encryption", "security"], "gdpr_relevant": False}
                )
            ],
            document_id="ecommerce_doc_001",
            filename="ecommerce_spec.pdf"
        )
        
        # Mock realistic chain-of-thought responses
        responses = [
            # Response for user registration requirement
            ChainOfThoughtResponse(
                reasoning_steps=[
                    "Identified collection of personal data (email, name, address)",
                    "Checked GDPR Article 6 for lawful basis requirements",
                    "Registration likely qualifies as contract performance (Article 6(1)(b))",
                    "No explicit consent mechanism mentioned - potential issue",
                    "Data minimization principle should be considered",
                    "Privacy notice and data subject rights not specified"
                ],
                conclusion=json.dumps({
                    "compliance_status": "partially_compliant",
                    "severity": "medium",
                    "gdpr_articles_referenced": ["Article 6", "Article 13", "Article 5"],
                    "issues_identified": [
                        "No explicit privacy notice mentioned",
                        "Data subject rights implementation unclear",
                        "Data retention period not specified"
                    ],
                    "recommendations": [
                        "Add privacy notice during registration",
                        "Implement data subject rights (access, rectification, erasure)",
                        "Define data retention periods",
                        "Consider data minimization - collect only necessary data"
                    ]
                }),
                confidence_score=0.85,
                raw_response="Detailed analysis of user registration requirement...",
                model="deepseek-r1:8b",
                success=True
            ),
            # Response for payment processing requirement
            ChainOfThoughtResponse(
                reasoning_steps=[
                    "Identified payment data processing with encryption",
                    "Payment data is sensitive personal data under GDPR",
                    "Encryption provides technical safeguards (Article 32)",
                    "Contract performance is likely lawful basis",
                    "PCI DSS compliance may be required",
                    "Data retention for payment data has specific requirements"
                ],
                conclusion=json.dumps({
                    "compliance_status": "compliant",
                    "severity": "low",
                    "gdpr_articles_referenced": ["Article 6", "Article 32", "Article 9"],
                    "issues_identified": [],
                    "recommendations": [
                        "Ensure PCI DSS compliance",
                        "Document encryption standards used",
                        "Define payment data retention policy"
                    ]
                }),
                confidence_score=0.90,
                raw_response="Analysis of payment processing requirement...",
                model="deepseek-r1:8b",
                success=True
            )
        ]
        
        mock_llm_client.execute_chain_of_thought.side_effect = responses
        
        # Perform analysis
        report = agent.analyze_compliance(document)
        
        # Verify comprehensive report
        assert isinstance(report, ComplianceReport)
        assert report.agent_id == "cc_agent_1"
        assert report.model_used == "deepseek-r1:8b"
        assert report.document_id == "ecommerce_doc_001"
        assert report.total_requirements_analyzed == 2
        assert len(report.findings) == 2
        
        # Verify findings
        user_reg_finding = next(f for f in report.findings if f.requirement_id == "req_user_registration")
        payment_finding = next(f for f in report.findings if f.requirement_id == "req_payment_processing")
        
        assert user_reg_finding.compliance_status == ComplianceStatus.PARTIALLY_COMPLIANT
        assert user_reg_finding.severity == SeverityLevel.MEDIUM
        assert "Article 6" in user_reg_finding.gdpr_articles
        assert len(user_reg_finding.recommendations) > 0
        
        assert payment_finding.compliance_status == ComplianceStatus.COMPLIANT
        assert payment_finding.severity == SeverityLevel.LOW
        
        # Verify overall assessment
        assert "partial gdpr compliance" in report.overall_assessment.lower()
        assert report.confidence_score > 0.8
        
        # Verify GDPR knowledge base was queried
        assert mock_gdpr_kb.query_relevant_articles.call_count == 2
    
    def test_feedback_integration_workflow(self, integration_setup):
        """Test feedback processing and iterative improvement."""
        agent, mock_llm_client, mock_gdpr_kb = integration_setup
        
        # Simple document for testing
        document = SpecificationDocument(
            content="Test document",
            metadata={},
            requirements=[
                Requirement(
                    id="test_req",
                    text="System processes user data",
                    section="data",
                    category="data"
                )
            ],
            document_id="test_doc"
        )
        
        # First analysis (without feedback)
        mock_llm_client.execute_chain_of_thought.return_value = ChainOfThoughtResponse(
            reasoning_steps=["Initial analysis"],
            conclusion='{"compliance_status": "unclear", "severity": "medium"}',
            confidence_score=0.6,
            raw_response="Initial response",
            model="deepseek-r1:8b",
            success=True
        )
        
        report1 = agent.analyze_compliance(document)
        assert report1.iteration_number == 1
        assert report1.confidence_score < 0.8
        
        # Process feedback
        feedback = "Focus on data retention requirements and consider Article 17 (right to erasure)"
        agent.process_feedback(feedback)
        
        # Second analysis (with feedback)
        mock_llm_client.execute_chain_of_thought.return_value = ChainOfThoughtResponse(
            reasoning_steps=["Improved analysis with feedback"],
            conclusion='{"compliance_status": "non_compliant", "severity": "high"}',
            confidence_score=0.9,
            raw_response="Improved response",
            model="deepseek-r1:8b",
            success=True
        )
        
        report2 = agent.analyze_compliance(document)
        assert report2.iteration_number == 2
        assert report2.confidence_score > report1.confidence_score
        
        # Verify feedback was included in prompt
        call_args = mock_llm_client.execute_chain_of_thought.call_args
        prompt = call_args[1]["prompt"]
        assert "Previous feedback" in prompt
        assert "Article 17" in prompt