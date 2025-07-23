"""
Unit tests for RA_Agent (Report Assessor Agent).
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List, Dict, Any

from compliance_checker.agents.ra_agent import RAAgent
from compliance_checker.models.report import (
    ComplianceReport, FinalComplianceReport, ComplianceFinding,
    ComplianceStatus, SeverityLevel
)
from compliance_checker.llm.multi_agent_client import (
    MultiAgentLLMClient, AgentType, ChainOfThoughtResponse
)
from compliance_checker.exceptions import ModelUnavailableError


class TestRAAgent:
    """Test cases for RA_Agent functionality."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = Mock(spec=MultiAgentLLMClient)
        client.verify_model_availability.return_value = {"qwq:32b": True}
        client.generate.return_value = Mock(success=True, content="Test response", error=None)
        return client
    
    @pytest.fixture
    def ra_agent(self, mock_llm_client):
        """Create an RA_Agent instance for testing."""
        return RAAgent(llm_client=mock_llm_client)
    
    @pytest.fixture
    def sample_compliance_finding(self):
        """Create a sample compliance finding."""
        return ComplianceFinding(
            requirement_id="REQ_001",
            requirement_text="System shall implement user authentication",
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            gdpr_articles=["Article 32"],
            reasoning="Authentication mechanism lacks proper security measures",
            severity=SeverityLevel.HIGH,
            recommendations=["Implement multi-factor authentication"],
            confidence_score=0.8,
            model_used="deepseek-r1:8b"
        )
    
    @pytest.fixture
    def sample_compliance_report(self, sample_compliance_finding):
        """Create a sample compliance report."""
        return ComplianceReport(
            agent_id="cc_agent_1",
            model_used="deepseek-r1:8b",
            findings=[sample_compliance_finding],
            overall_assessment="Non-compliant requirements found",
            confidence_score=0.75,
            document_id="doc_001",
            document_filename="test_spec.pdf",
            processing_time=10.5,
            total_requirements_analyzed=5,
            iteration_number=1
        )
    
    @pytest.fixture
    def conflicting_reports(self):
        """Create conflicting compliance reports for testing."""
        finding1 = ComplianceFinding(
            requirement_id="REQ_001",
            requirement_text="System shall implement user authentication",
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            gdpr_articles=["Article 32"],
            reasoning="Authentication mechanism is inadequate",
            severity=SeverityLevel.HIGH,
            recommendations=["Implement MFA"],
            confidence_score=0.8,
            model_used="deepseek-r1:8b"
        )
        
        finding2 = ComplianceFinding(
            requirement_id="REQ_001",
            requirement_text="System shall implement user authentication",
            compliance_status=ComplianceStatus.COMPLIANT,
            gdpr_articles=["Article 32"],
            reasoning="Authentication mechanism meets GDPR requirements",
            severity=SeverityLevel.LOW,
            recommendations=["Monitor implementation"],
            confidence_score=0.7,
            model_used="gemma3:27b"
        )
        
        report1 = ComplianceReport(
            agent_id="cc_agent_1",
            model_used="deepseek-r1:8b",
            findings=[finding1],
            overall_assessment="Non-compliant",
            confidence_score=0.8
        )
        
        report2 = ComplianceReport(
            agent_id="cc_agent_2",
            model_used="gemma3:27b",
            findings=[finding2],
            overall_assessment="Compliant",
            confidence_score=0.7
        )
        
        return [report1, report2]
    
    def test_ra_agent_initialization_success(self, mock_llm_client):
        """Test successful RA_Agent initialization."""
        agent = RAAgent(llm_client=mock_llm_client)
        
        assert agent.agent_id == "ra_agent"
        assert agent.model_name == "qwq:32b"
        assert agent.agent_type == AgentType.RA_AGENT
        assert agent.status == "ready"
        assert agent.feedback_enabled is True
        
        # Verify model availability was checked
        mock_llm_client.verify_model_availability.assert_called_once_with(["qwq:32b"])
    
    def test_ra_agent_initialization_model_unavailable(self, mock_llm_client):
        """Test RA_Agent initialization when model is unavailable."""
        mock_llm_client.verify_model_availability.return_value = {"qwq:32b": False}
        
        with pytest.raises(ModelUnavailableError):
            RAAgent(llm_client=mock_llm_client)
    
    def test_get_status(self, ra_agent):
        """Test getting agent status."""
        status = ra_agent.get_status()
        
        assert status["agent_id"] == "ra_agent"
        assert status["model_name"] == "qwq:32b"
        assert status["agent_type"] == "ra_agent"
        assert status["status"] == "ready"
        assert "created_at" in status
        assert status["feedback_enabled"] is True
        assert status["conflict_resolution_strategy"] == "conservative"
    
    def test_assess_reports_empty_list(self, ra_agent):
        """Test assessing empty report list."""
        final_report = ra_agent.assess_reports([])
        
        assert isinstance(final_report, FinalComplianceReport)
        assert len(final_report.consolidated_findings) == 0
        assert "No reports provided" in final_report.overall_compliance_status
        assert final_report.confidence_score == 0.0
    
    def test_assess_single_report(self, ra_agent, sample_compliance_report):
        """Test assessing a single report."""
        final_report = ra_agent.assess_reports([sample_compliance_report])
        
        assert isinstance(final_report, FinalComplianceReport)
        assert len(final_report.consolidated_findings) == 1
        assert final_report.source_reports == ["cc_agent_1"]
        assert "Single-agent assessment" in final_report.overall_compliance_status
        assert final_report.confidence_score < sample_compliance_report.confidence_score  # Reduced for single agent
    
    def test_identify_conflicts_status_conflict(self, ra_agent, conflicting_reports):
        """Test identifying status conflicts between reports."""
        conflicts = ra_agent._identify_conflicts(conflicting_reports)
        
        assert len(conflicts) > 0
        status_conflicts = [c for c in conflicts if c["type"] == "status_conflict"]
        assert len(status_conflicts) == 1
        
        conflict = status_conflicts[0]
        assert conflict["requirement_id"] == "REQ_001"
        assert "non_compliant" in conflict["statuses"]
        assert "compliant" in conflict["statuses"]
    
    def test_identify_conflicts_no_conflicts(self, ra_agent, sample_compliance_report):
        """Test identifying conflicts when there are none."""
        # Create identical reports
        report2 = ComplianceReport(
            agent_id="cc_agent_2",
            model_used="gemma3:27b",
            findings=sample_compliance_report.findings.copy(),
            overall_assessment="Same assessment",
            confidence_score=0.75
        )
        
        conflicts = ra_agent._identify_conflicts([sample_compliance_report, report2])
        
        # Should have no conflicts since findings are identical
        assert len(conflicts) == 0
    
    def test_has_reasoning_conflict(self, ra_agent):
        """Test detecting reasoning conflicts."""
        conflicting_reasonings = [
            "The system is compliant with GDPR requirements",
            "The system fails to meet GDPR standards"
        ]
        
        assert ra_agent._has_reasoning_conflict(conflicting_reasonings) is True
        
        similar_reasonings = [
            "The system meets GDPR requirements",
            "The system satisfies GDPR standards"
        ]
        
        assert ra_agent._has_reasoning_conflict(similar_reasonings) is False
    
    @patch.object(RAAgent, '_resolve_single_conflict')
    def test_resolve_conflicts(self, mock_resolve, ra_agent, conflicting_reports):
        """Test conflict resolution process."""
        # Mock successful conflict resolution
        resolved_finding = ComplianceFinding(
            requirement_id="REQ_001",
            requirement_text="System shall implement user authentication",
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            gdpr_articles=["Article 32"],
            reasoning="Resolved: Authentication mechanism needs improvement",
            severity=SeverityLevel.MEDIUM,
            recommendations=["Implement enhanced authentication"],
            confidence_score=0.75,
            model_used="qwq:32b"
        )
        mock_resolve.return_value = resolved_finding
        
        conflicts = ra_agent._identify_conflicts(conflicting_reports)
        resolved_findings = ra_agent._resolve_conflicts(conflicting_reports, conflicts)
        
        assert len(resolved_findings) > 0
        assert resolved_findings[0].model_used == "qwq:32b"
        mock_resolve.assert_called()
    
    def test_choose_most_restrictive_finding(self, ra_agent):
        """Test choosing the most restrictive finding."""
        findings = [
            ComplianceFinding(
                requirement_id="REQ_001",
                requirement_text="Test",
                compliance_status=ComplianceStatus.COMPLIANT,
                gdpr_articles=[],
                reasoning="Compliant",
                severity=SeverityLevel.LOW,
                recommendations=[]
            ),
            ComplianceFinding(
                requirement_id="REQ_001",
                requirement_text="Test",
                compliance_status=ComplianceStatus.NON_COMPLIANT,
                gdpr_articles=[],
                reasoning="Non-compliant",
                severity=SeverityLevel.HIGH,
                recommendations=[]
            )
        ]
        
        restrictive = ra_agent._choose_most_restrictive_finding(findings)
        assert restrictive.compliance_status == ComplianceStatus.NON_COMPLIANT
    
    def test_choose_most_permissive_finding(self, ra_agent):
        """Test choosing the most permissive finding."""
        findings = [
            ComplianceFinding(
                requirement_id="REQ_001",
                requirement_text="Test",
                compliance_status=ComplianceStatus.COMPLIANT,
                gdpr_articles=[],
                reasoning="Compliant",
                severity=SeverityLevel.LOW,
                recommendations=[]
            ),
            ComplianceFinding(
                requirement_id="REQ_001",
                requirement_text="Test",
                compliance_status=ComplianceStatus.NON_COMPLIANT,
                gdpr_articles=[],
                reasoning="Non-compliant",
                severity=SeverityLevel.HIGH,
                recommendations=[]
            )
        ]
        
        permissive = ra_agent._choose_most_permissive_finding(findings)
        assert permissive.compliance_status == ComplianceStatus.COMPLIANT
    
    def test_consolidate_findings(self, ra_agent, conflicting_reports):
        """Test consolidating findings from multiple reports."""
        # Create resolved findings
        resolved_findings = [
            ComplianceFinding(
                requirement_id="REQ_001",
                requirement_text="Test",
                compliance_status=ComplianceStatus.PARTIALLY_COMPLIANT,
                gdpr_articles=["Article 32"],
                reasoning="Resolved conflict",
                severity=SeverityLevel.MEDIUM,
                recommendations=["Improve implementation"],
                confidence_score=0.8,
                model_used="qwq:32b"
            )
        ]
        
        consolidated = ra_agent._consolidate_findings(conflicting_reports, resolved_findings)
        
        assert len(consolidated) == 1  # Should have one consolidated finding
        assert consolidated[0].requirement_id == "REQ_001"
        assert consolidated[0].model_used == "qwq:32b"
    
    def test_merge_compatible_findings(self, ra_agent):
        """Test merging compatible findings."""
        finding1 = ComplianceFinding(
            requirement_id="REQ_001",
            requirement_text="Test",
            compliance_status=ComplianceStatus.COMPLIANT,
            gdpr_articles=["Article 32"],
            reasoning="First analysis",
            severity=SeverityLevel.LOW,
            recommendations=["Rec 1"],
            confidence_score=0.8,
            model_used="model1"
        )
        
        finding2 = ComplianceFinding(
            requirement_id="REQ_001",
            requirement_text="Test",
            compliance_status=ComplianceStatus.COMPLIANT,
            gdpr_articles=["Article 33"],
            reasoning="Second analysis",
            severity=SeverityLevel.LOW,
            recommendations=["Rec 2"],
            confidence_score=0.7,
            model_used="model2"
        )
        
        merged = ra_agent._merge_compatible_findings(finding1, finding2)
        
        assert merged.requirement_id == "REQ_001"
        assert "Article 32" in merged.gdpr_articles
        assert "Article 33" in merged.gdpr_articles
        assert "Rec 1" in merged.recommendations
        assert "Rec 2" in merged.recommendations
        assert "model1, model2" in merged.model_used
    
    def test_generate_overall_status_critical_issues(self, ra_agent):
        """Test generating overall status with critical issues."""
        findings = [
            ComplianceFinding(
                requirement_id="REQ_001",
                requirement_text="Test",
                compliance_status=ComplianceStatus.NON_COMPLIANT,
                gdpr_articles=[],
                reasoning="Critical issue",
                severity=SeverityLevel.CRITICAL,
                recommendations=[]
            )
        ]
        
        status = ra_agent._generate_overall_status(findings)
        
        assert "CRITICAL GDPR COMPLIANCE ISSUES" in status
        assert "1 critical findings" in status
    
    def test_generate_overall_status_compliant(self, ra_agent):
        """Test generating overall status when compliant."""
        findings = [
            ComplianceFinding(
                requirement_id="REQ_001",
                requirement_text="Test",
                compliance_status=ComplianceStatus.COMPLIANT,
                gdpr_articles=[],
                reasoning="Compliant",
                severity=SeverityLevel.LOW,
                recommendations=[]
            )
        ]
        
        status = ra_agent._generate_overall_status(findings)
        
        assert "GDPR COMPLIANT" in status
        assert "100.0%" in status
    
    def test_calculate_final_confidence(self, ra_agent, conflicting_reports):
        """Test calculating final confidence score."""
        consolidated_findings = [
            ComplianceFinding(
                requirement_id="REQ_001",
                requirement_text="Test",
                compliance_status=ComplianceStatus.COMPLIANT,
                gdpr_articles=[],
                reasoning="Test",
                severity=SeverityLevel.LOW,
                recommendations=[],
                confidence_score=0.8
            )
        ]
        
        confidence = ra_agent._calculate_final_confidence(conflicting_reports, consolidated_findings)
        
        assert 0.0 <= confidence <= 1.0
        assert isinstance(confidence, float)
    
    def test_calculate_agreement_bonus(self, ra_agent):
        """Test calculating agreement bonus."""
        # High agreement (similar confidence scores)
        reports_high_agreement = [
            Mock(confidence_score=0.8),
            Mock(confidence_score=0.82)
        ]
        
        bonus_high = ra_agent._calculate_agreement_bonus(reports_high_agreement)
        
        # Low agreement (different confidence scores)
        reports_low_agreement = [
            Mock(confidence_score=0.9),
            Mock(confidence_score=0.5)
        ]
        
        bonus_low = ra_agent._calculate_agreement_bonus(reports_low_agreement)
        
        assert bonus_high > bonus_low
    
    def test_generate_consolidation_notes(self, ra_agent, conflicting_reports):
        """Test generating consolidation notes."""
        conflicts = ra_agent._identify_conflicts(conflicting_reports)
        resolved_findings = []
        
        notes = ra_agent._generate_consolidation_notes(conflicting_reports, conflicts, resolved_findings)
        
        assert "Consolidated 2 compliance reports" in notes
        assert "cc_agent_1" in notes
        assert "cc_agent_2" in notes
        if conflicts:
            assert "Resolved" in notes
        else:
            assert "No conflicts detected" in notes
    
    @patch.object(RAAgent, '_generate_agent_feedback')
    def test_generate_feedback(self, mock_generate, ra_agent, conflicting_reports):
        """Test generating feedback for agents."""
        # Mock feedback generation
        mock_feedback = {
            "target_agent_id": "cc_agent_1",
            "feedback_text": "Test feedback",
            "improvement_suggestions": ["Improve analysis"],
            "iteration_number": 1
        }
        mock_generate.return_value = mock_feedback
        
        feedback_list = ra_agent.generate_feedback(conflicting_reports)
        
        assert len(feedback_list) == 2  # One for each report
        assert mock_generate.call_count == 2
        assert len(ra_agent.feedback_history) == 2
    
    def test_generate_feedback_disabled(self, ra_agent, conflicting_reports):
        """Test feedback generation when disabled."""
        ra_agent.feedback_enabled = False
        
        feedback_list = ra_agent.generate_feedback(conflicting_reports)
        
        assert len(feedback_list) == 0
    
    def test_create_feedback_prompt(self, ra_agent, sample_compliance_report):
        """Test creating feedback prompt."""
        other_reports = []
        
        prompt = ra_agent._create_feedback_prompt(sample_compliance_report, other_reports)
        
        assert "FEEDBACK GENERATION TASK" in prompt
        assert sample_compliance_report.agent_id in prompt
        assert sample_compliance_report.model_used in prompt
        assert "improvement_suggestions" in prompt
    
    def test_extract_resolution_from_response(self, ra_agent):
        """Test extracting resolution from chain-of-thought response."""
        # Test with valid JSON conclusion
        valid_response = ChainOfThoughtResponse(
            reasoning_steps=["Step 1", "Step 2"],
            conclusion='{"resolved_finding": {"compliance_status": "non_compliant", "severity": "high"}}',
            confidence_score=0.8,
            raw_response="Test response",
            model="qwq:32b",
            success=True
        )
        
        resolution = ra_agent._extract_resolution_from_response(valid_response)
        
        assert "resolved_finding" in resolution
        assert resolution["resolved_finding"]["compliance_status"] == "non_compliant"
        assert resolution["resolved_finding"]["severity"] == "high"
    
    def test_extract_resolution_from_response_fallback(self, ra_agent):
        """Test extracting resolution with fallback parsing."""
        # Test with invalid JSON
        invalid_response = ChainOfThoughtResponse(
            reasoning_steps=["Step 1"],
            conclusion="Invalid JSON",
            confidence_score=0.5,
            raw_response="Invalid response",
            model="qwq:32b",
            success=True
        )
        
        resolution = ra_agent._extract_resolution_from_response(invalid_response)
        
        # Should return default fallback
        assert "resolved_finding" in resolution
        assert resolution["resolved_finding"]["compliance_status"] == "unclear"
    
    def test_extract_feedback_from_response(self, ra_agent):
        """Test extracting feedback from chain-of-thought response."""
        # Test with valid JSON conclusion
        valid_response = ChainOfThoughtResponse(
            reasoning_steps=["Step 1"],
            conclusion='{"overall_feedback": "Good analysis", "improvement_suggestions": ["Improve X"]}',
            confidence_score=0.8,
            raw_response="Test response",
            model="qwq:32b",
            success=True
        )
        
        feedback = ra_agent._extract_feedback_from_response(valid_response)
        
        assert feedback["overall_feedback"] == "Good analysis"
        assert "Improve X" in feedback["improvement_suggestions"]
    
    def test_severity_sort_key(self, ra_agent):
        """Test severity sorting key generation."""
        assert ra_agent._severity_sort_key(SeverityLevel.CRITICAL) == 0
        assert ra_agent._severity_sort_key(SeverityLevel.HIGH) == 1
        assert ra_agent._severity_sort_key(SeverityLevel.MEDIUM) == 2
        assert ra_agent._severity_sort_key(SeverityLevel.LOW) == 3
    
    def test_create_empty_final_report(self, ra_agent):
        """Test creating empty final report."""
        reason = "Test reason"
        report = ra_agent._create_empty_final_report(reason)
        
        assert isinstance(report, FinalComplianceReport)
        assert len(report.consolidated_findings) == 0
        assert reason in report.overall_compliance_status
        assert report.confidence_score == 0.0
    
    def test_create_error_final_report(self, ra_agent):
        """Test creating error final report."""
        error = "Test error"
        report = ra_agent._create_error_final_report(error)
        
        assert isinstance(report, FinalComplianceReport)
        assert len(report.consolidated_findings) == 0
        assert error in report.overall_compliance_status
        assert report.confidence_score == 0.0


class TestRAAgentIntegration:
    """Integration tests for RA_Agent with mocked LLM responses."""
    
    @pytest.fixture
    def mock_llm_client_with_responses(self):
        """Create a mock LLM client with realistic responses."""
        client = Mock(spec=MultiAgentLLMClient)
        client.verify_model_availability.return_value = {"qwq:32b": True}
        client.generate.return_value = Mock(success=True, content="Test response", error=None)
        
        # Mock chain-of-thought responses
        def mock_cot_response(prompt, agent_type, system_prompt=None, temperature=0.2):
            if "CONFLICT RESOLUTION" in prompt:
                return ChainOfThoughtResponse(
                    reasoning_steps=["Analyzed conflict", "Applied strategy", "Reached conclusion"],
                    conclusion='{"resolved_finding": {"compliance_status": "non_compliant", "severity": "high", "gdpr_articles": ["Article 32"], "consolidated_reasoning": "Resolved conflict reasoning", "recommendations": ["Implement security measures"], "confidence_score": 0.8}}',
                    confidence_score=0.8,
                    raw_response="Conflict resolution response",
                    model="qwq:32b",
                    success=True
                )
            elif "FEEDBACK GENERATION" in prompt:
                return ChainOfThoughtResponse(
                    reasoning_steps=["Analyzed report", "Identified improvements"],
                    conclusion='{"overall_feedback": "Good analysis overall", "improvement_suggestions": ["More detailed reasoning", "Better GDPR coverage"], "strengths": ["Clear structure"], "priority_areas": ["reasoning", "coverage"]}',
                    confidence_score=0.7,
                    raw_response="Feedback generation response",
                    model="qwq:32b",
                    success=True
                )
            else:
                return ChainOfThoughtResponse(
                    reasoning_steps=["Generic step"],
                    conclusion="Generic conclusion",
                    confidence_score=0.5,
                    raw_response="Generic response",
                    model="qwq:32b",
                    success=True
                )
        
        client.execute_chain_of_thought.side_effect = mock_cot_response
        return client
    
    @pytest.fixture
    def ra_agent_with_responses(self, mock_llm_client_with_responses):
        """Create RA_Agent with mocked responses."""
        return RAAgent(llm_client=mock_llm_client_with_responses)
    
    @pytest.fixture
    def realistic_conflicting_reports(self):
        """Create realistic conflicting reports for integration testing."""
        finding1 = ComplianceFinding(
            requirement_id="REQ_AUTH_001",
            requirement_text="The system shall implement secure user authentication mechanisms",
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            gdpr_articles=["Article 32", "Article 25"],
            reasoning="The current authentication system lacks multi-factor authentication and proper password policies, which are required for adequate security measures under GDPR Article 32.",
            severity=SeverityLevel.HIGH,
            recommendations=[
                "Implement multi-factor authentication",
                "Enforce strong password policies",
                "Add account lockout mechanisms"
            ],
            confidence_score=0.85,
            model_used="deepseek-r1:8b"
        )
        
        finding2 = ComplianceFinding(
            requirement_id="REQ_AUTH_001",
            requirement_text="The system shall implement secure user authentication mechanisms",
            compliance_status=ComplianceStatus.PARTIALLY_COMPLIANT,
            gdpr_articles=["Article 32"],
            reasoning="The authentication system has basic security measures in place but could be enhanced with additional security layers to fully comply with GDPR requirements.",
            severity=SeverityLevel.MEDIUM,
            recommendations=[
                "Consider implementing additional security measures",
                "Review current authentication policies"
            ],
            confidence_score=0.75,
            model_used="gemma3:27b"
        )
        
        report1 = ComplianceReport(
            agent_id="cc_agent_1",
            model_used="deepseek-r1:8b",
            findings=[finding1],
            overall_assessment="Critical GDPR compliance issues identified in authentication mechanisms",
            confidence_score=0.85,
            document_id="spec_001",
            document_filename="auth_requirements.pdf",
            processing_time=15.2,
            total_requirements_analyzed=10,
            iteration_number=1
        )
        
        report2 = ComplianceReport(
            agent_id="cc_agent_2",
            model_used="gemma3:27b",
            findings=[finding2],
            overall_assessment="Partial GDPR compliance with room for improvement in authentication",
            confidence_score=0.75,
            document_id="spec_001",
            document_filename="auth_requirements.pdf",
            processing_time=12.8,
            total_requirements_analyzed=10,
            iteration_number=1
        )
        
        return [report1, report2]
    
    def test_full_assessment_workflow(self, ra_agent_with_responses, realistic_conflicting_reports):
        """Test the complete assessment workflow with realistic data."""
        final_report = ra_agent_with_responses.assess_reports(realistic_conflicting_reports)
        
        # Verify final report structure
        assert isinstance(final_report, FinalComplianceReport)
        assert len(final_report.consolidated_findings) > 0
        assert len(final_report.source_reports) == 2
        assert "cc_agent_1" in final_report.source_reports
        assert "cc_agent_2" in final_report.source_reports
        
        # Verify consolidation occurred
        assert final_report.confidence_score > 0
        assert final_report.total_processing_time > 0
        assert final_report.consolidation_notes
        
        # Verify consolidated finding
        consolidated_finding = final_report.consolidated_findings[0]
        assert consolidated_finding.requirement_id == "REQ_AUTH_001"
        assert consolidated_finding.model_used == "qwq:32b"  # Resolved by RA_Agent
        assert consolidated_finding.confidence_score > 0
    
    def test_feedback_generation_workflow(self, ra_agent_with_responses, realistic_conflicting_reports):
        """Test the complete feedback generation workflow."""
        feedback_list = ra_agent_with_responses.generate_feedback(realistic_conflicting_reports)
        
        # Verify feedback was generated for each agent
        assert len(feedback_list) == 2
        
        # Verify feedback structure
        for feedback in feedback_list:
            assert "target_agent_id" in feedback
            assert feedback["target_agent_id"] in ["cc_agent_1", "cc_agent_2"]
            assert "feedback_text" in feedback
            assert "improvement_suggestions" in feedback
            assert "iteration_number" in feedback
            assert feedback["feedback_type"] == "improvement"
            assert feedback["confidence_score"] > 0
        
        # Verify feedback history was updated
        assert len(ra_agent_with_responses.feedback_history) == 2
    
    def test_conflict_resolution_conservative_strategy(self, ra_agent_with_responses, realistic_conflicting_reports):
        """Test conflict resolution with conservative strategy."""
        ra_agent_with_responses.conflict_resolution_strategy = "conservative"
        
        final_report = ra_agent_with_responses.assess_reports(realistic_conflicting_reports)
        
        # With conservative strategy, should lean towards more restrictive assessment
        consolidated_finding = final_report.consolidated_findings[0]
        # The resolved finding should reflect the conservative approach
        assert consolidated_finding.compliance_status in [ComplianceStatus.NON_COMPLIANT, ComplianceStatus.PARTIALLY_COMPLIANT]
    
    def test_error_handling_in_assessment(self, mock_llm_client_with_responses):
        """Test error handling during assessment process."""
        # Mock LLM client to fail
        mock_llm_client_with_responses.execute_chain_of_thought.side_effect = Exception("LLM error")
        
        ra_agent = RAAgent(llm_client=mock_llm_client_with_responses)
        
        # Create simple reports
        reports = [
            ComplianceReport(
                agent_id="cc_agent_1",
                model_used="test_model",
                findings=[],
                overall_assessment="Test",
                confidence_score=0.5
            )
        ]
        
        final_report = ra_agent.assess_reports(reports)
        
        # Should handle error gracefully
        assert isinstance(final_report, FinalComplianceReport)
        # Should fall back to single report assessment
        assert "Single-agent assessment" in final_report.overall_compliance_status