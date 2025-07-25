"""
Integration tests for the agent orchestration system.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from ..orchestration.orchestrator import AgentOrchestrator
from ..orchestration.session import AnalysisSession, SessionStatus, FeedbackIteration
from ..orchestration.progress import ProgressTracker, AnalysisStage
from ..models.document import SpecificationDocument, Requirement
from ..models.report import ComplianceReport, FinalComplianceReport, ComplianceFinding, ComplianceStatus, SeverityLevel
from ..llm.multi_agent_client import MultiAgentLLMClient
from ..knowledge.gdpr_knowledge_base import GDPRKnowledgeBase
from ..exceptions import ModelUnavailableError


class TestAnalysisSession:
    """Test cases for AnalysisSession."""
    
    def test_session_initialization(self):
        """Test session initialization."""
        session = AnalysisSession()
        
        assert session.session_id is not None
        assert session.status == SessionStatus.CREATED
        assert session.current_stage == "initialization"
        assert session.progress_percentage == 0.0
        assert session.current_iteration == 0
        assert session.max_iterations == 3
        assert len(session.cc_agent_reports) == 0
        assert session.ra_agent_report is None
        assert len(session.feedback_iterations) == 0
        assert len(session.errors) == 0
        assert len(session.warnings) == 0
    
    def test_session_lifecycle(self):
        """Test complete session lifecycle."""
        session = AnalysisSession()
        
        # Start session
        session.start_session()
        assert session.status == SessionStatus.INITIALIZING
        assert session.start_time is not None
        assert session.progress_percentage == 5.0
        
        # Set document
        document = SpecificationDocument(
            content="Test content",
            metadata={"test": "metadata"},
            document_id="test-doc",
            filename="test.txt",
            requirements=[]
        )
        session.set_document(document, {"test": "metadata"})
        assert session.status == SessionStatus.DOCUMENT_PROCESSING
        assert session.document == document
        assert session.document_metadata == {"test": "metadata"}
        assert session.progress_percentage == 15.0
        
        # Start CC agents
        session.start_cc_agents()
        assert session.status == SessionStatus.CC_AGENTS_RUNNING
        assert session.progress_percentage == 25.0
        
        # Add CC agent reports
        report1 = ComplianceReport(
            agent_id="cc_agent_1",
            model_used="test-model",
            findings=[],
            overall_assessment="Test assessment",
            confidence_score=0.8
        )
        session.add_cc_agent_report("cc_agent_1", report1)
        assert len(session.cc_agent_reports) == 1
        assert session.progress_percentage == 45.0  # 25 + (1/2 * 40)
        
        report2 = ComplianceReport(
            agent_id="cc_agent_2",
            model_used="test-model",
            findings=[],
            overall_assessment="Test assessment",
            confidence_score=0.8
        )
        session.add_cc_agent_report("cc_agent_2", report2)
        assert len(session.cc_agent_reports) == 2
        assert session.progress_percentage == 65.0
        
        # Start RA agent
        session.start_ra_agent()
        assert session.status == SessionStatus.RA_AGENT_ASSESSING
        assert session.progress_percentage == 70.0
        
        # Set RA agent report
        final_report = FinalComplianceReport(
            consolidated_findings=[],
            overall_compliance_status="Test status",
            confidence_score=0.85
        )
        session.set_ra_agent_report(final_report)
        assert session.ra_agent_report == final_report
        assert session.progress_percentage == 85.0
        
        # Complete session
        session.complete_session()
        assert session.status == SessionStatus.COMPLETED
        assert session.end_time is not None
        assert session.progress_percentage == 100.0
        assert session.total_processing_time is not None
    
    def test_feedback_iterations(self):
        """Test feedback iteration management."""
        session = AnalysisSession()
        
        # Start feedback iteration
        session.start_feedback_iteration(1)
        assert session.current_iteration == 1
        assert session.status == SessionStatus.FEEDBACK_PROCESSING
        
        # Add feedback iteration
        feedback_iteration = FeedbackIteration(
            iteration_number=1,
            feedback_data=[{"test": "feedback"}]
        )
        session.add_feedback_iteration(feedback_iteration)
        assert len(session.feedback_iterations) == 1
        assert session.current_iteration == 1
    
    def test_error_handling(self):
        """Test error handling in session."""
        session = AnalysisSession()
        
        # Add warning
        session.add_warning("Test warning")
        assert len(session.warnings) == 1
        assert "Test warning" in session.warnings[0]
        
        # Add error
        session.add_error("Test error", {"detail": "test"})
        assert len(session.errors) == 1
        assert session.errors[0]["error"] == "Test error"
        assert session.errors[0]["details"]["detail"] == "test"
        
        # Fail session
        session.fail_session("Critical error")
        assert session.status == SessionStatus.FAILED
        assert session.end_time is not None
        assert len(session.errors) == 2  # Previous error + failure error
    
    def test_session_status_checks(self):
        """Test session status check methods."""
        session = AnalysisSession()
        
        # Initial state
        assert not session.is_active()
        assert not session.is_completed()
        assert not session.is_failed()
        
        # Active state
        session.start_session()
        assert session.is_active()
        assert not session.is_completed()
        assert not session.is_failed()
        
        # Completed state
        session.complete_session()
        assert not session.is_active()
        assert session.is_completed()
        assert not session.is_failed()
        
        # Failed state
        session2 = AnalysisSession()
        session2.fail_session("Test error")
        assert not session2.is_active()
        assert not session2.is_completed()
        assert session2.is_failed()
    
    def test_feedback_continuation_check(self):
        """Test feedback continuation logic."""
        session = AnalysisSession(max_iterations=2)
        
        # Can continue initially
        session.status = SessionStatus.RA_AGENT_ASSESSING
        assert session.can_continue_feedback()
        
        # Cannot continue after max iterations
        session.current_iteration = 2
        assert not session.can_continue_feedback()
        
        # Cannot continue if failed
        session.current_iteration = 0
        session.status = SessionStatus.FAILED
        assert not session.can_continue_feedback()


class TestProgressTracker:
    """Test cases for ProgressTracker."""
    
    def test_progress_tracker_initialization(self):
        """Test progress tracker initialization."""
        tracker = ProgressTracker()
        
        assert tracker.overall_progress == 0.0
        assert tracker.current_stage is None
        assert tracker.start_time is None
        assert len(tracker.stages) == len(AnalysisStage)
        
        # Check all stages are initialized
        for stage in AnalysisStage:
            assert stage in tracker.stages
            assert tracker.stages[stage].status == "pending"
    
    def test_stage_lifecycle(self):
        """Test stage lifecycle management."""
        tracker = ProgressTracker()
        
        # Start analysis
        tracker.start_analysis()
        assert tracker.start_time is not None
        assert tracker.overall_progress == 0.0
        
        # Start stage
        tracker.start_stage(AnalysisStage.INITIALIZATION, "Starting initialization")
        assert tracker.current_stage == AnalysisStage.INITIALIZATION
        assert tracker.stages[AnalysisStage.INITIALIZATION].status == "running"
        assert tracker.stages[AnalysisStage.INITIALIZATION].start_time is not None
        assert tracker.overall_progress > 0.0
        
        # Update stage progress
        tracker.update_stage_progress(AnalysisStage.INITIALIZATION, 50.0, "Half done")
        assert tracker.stages[AnalysisStage.INITIALIZATION].progress_percentage == 50.0
        assert tracker.stages[AnalysisStage.INITIALIZATION].details == "Half done"
        
        # Complete stage
        tracker.complete_stage(AnalysisStage.INITIALIZATION, "Completed")
        assert tracker.stages[AnalysisStage.INITIALIZATION].status == "completed"
        assert tracker.stages[AnalysisStage.INITIALIZATION].end_time is not None
        assert tracker.stages[AnalysisStage.INITIALIZATION].progress_percentage == 100.0
        
        # Fail stage
        tracker.fail_stage(AnalysisStage.DOCUMENT_PROCESSING, "Test error", "Error details")
        assert tracker.stages[AnalysisStage.DOCUMENT_PROCESSING].status == "failed"
        assert tracker.stages[AnalysisStage.DOCUMENT_PROCESSING].error == "Test error"
    
    def test_progress_callbacks(self):
        """Test progress callback functionality."""
        tracker = ProgressTracker()
        callback_data = []
        
        def test_callback(data):
            callback_data.append(data)
        
        # Add callback
        tracker.add_progress_callback(test_callback)
        
        # Start analysis should trigger callback
        tracker.start_analysis()
        assert len(callback_data) == 1
        
        # Stage operations should trigger callbacks
        tracker.start_stage(AnalysisStage.INITIALIZATION)
        assert len(callback_data) == 2
        
        tracker.complete_stage(AnalysisStage.INITIALIZATION)
        assert len(callback_data) == 3
        
        # Remove callback
        tracker.remove_progress_callback(test_callback)
        tracker.start_stage(AnalysisStage.DOCUMENT_PROCESSING)
        assert len(callback_data) == 3  # No new callback
    
    def test_progress_summary(self):
        """Test progress summary generation."""
        tracker = ProgressTracker()
        tracker.start_analysis()
        tracker.start_stage(AnalysisStage.INITIALIZATION)
        
        summary = tracker.get_progress_summary()
        
        assert "overall_progress" in summary
        assert "current_stage" in summary
        assert "start_time" in summary
        assert "stages" in summary
        assert summary["current_stage"] == AnalysisStage.INITIALIZATION.value
        
        detailed = tracker.get_detailed_progress()
        assert "performance_metrics" in detailed
        assert "stage_details" in detailed
    
    def test_status_checks(self):
        """Test status check methods."""
        tracker = ProgressTracker()
        
        # Initial state
        assert not tracker.is_completed()
        assert not tracker.has_failed_stages()
        
        # Complete analysis
        tracker.complete_analysis()
        assert tracker.is_completed()
        assert tracker.overall_progress == 100.0
        
        # Failed stage
        tracker.fail_stage(AnalysisStage.INITIALIZATION, "Test error")
        assert tracker.has_failed_stages()
        
        failed_stages = tracker.get_failed_stages()
        assert len(failed_stages) == 1
        assert failed_stages[0].stage == AnalysisStage.INITIALIZATION


class TestAgentOrchestrator:
    """Test cases for AgentOrchestrator."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = Mock(spec=MultiAgentLLMClient)
        client.verify_model_availability.return_value = {
            "deepseek-r1:8b": True,
            "gemma3:27b": True,
            "qwq:32b": True
        }
        return client
    
    @pytest.fixture
    def mock_gdpr_kb(self):
        """Create mock GDPR knowledge base."""
        return Mock(spec=GDPRKnowledgeBase)
    
    @pytest.fixture
    def sample_document(self):
        """Create sample document for testing."""
        requirements = [
            Requirement(
                id="req-1",
                text="The system shall protect user data",
                section="security",
                category="security"
            ),
            Requirement(
                id="req-2", 
                text="Users must provide consent",
                section="privacy",
                category="privacy"
            )
        ]
        
        return SpecificationDocument(
            content="Test document content",
            metadata={"test": "metadata"},
            document_id="test-doc",
            filename="test.txt",
            requirements=requirements
        )
    
    @pytest.fixture
    def sample_cc_report(self):
        """Create sample CC agent report."""
        finding = ComplianceFinding(
            requirement_id="req-1",
            requirement_text="The system shall protect user data",
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            gdpr_articles=["Article 6"],
            reasoning="Test reasoning",
            severity=SeverityLevel.HIGH,
            recommendations=["Test recommendation"],
            confidence_score=0.8,
            model_used="test-model"
        )
        
        return ComplianceReport(
            agent_id="cc_agent_1",
            model_used="test-model",
            findings=[finding],
            overall_assessment="Test assessment",
            confidence_score=0.8
        )
    
    def test_orchestrator_initialization(self, mock_llm_client, mock_gdpr_kb):
        """Test orchestrator initialization."""
        with patch('compliance_checker.orchestration.orchestrator.CCAgent') as mock_cc_agent, \
             patch('compliance_checker.orchestration.orchestrator.RAAgent') as mock_ra_agent:
            
            # Mock agent initialization
            mock_cc_instance = Mock()
            mock_cc_instance.initialize.return_value = True
            mock_cc_agent.return_value = mock_cc_instance
            
            mock_ra_instance = Mock()
            mock_ra_instance.initialize.return_value = True
            mock_ra_agent.return_value = mock_ra_instance
            
            orchestrator = AgentOrchestrator(
                llm_client=mock_llm_client,
                gdpr_knowledge_base=mock_gdpr_kb
            )
            
            assert len(orchestrator.cc_agents) == 2
            assert orchestrator.ra_agent is not None
            assert orchestrator.max_feedback_iterations == 3
            assert orchestrator.concurrent_execution is True
    
    def test_orchestrator_initialization_failure(self, mock_llm_client, mock_gdpr_kb):
        """Test orchestrator initialization failure."""
        with patch('compliance_checker.orchestration.orchestrator.CCAgent') as mock_cc_agent:
            # Mock agent initialization failure
            mock_cc_instance = Mock()
            mock_cc_instance.initialize.return_value = False
            mock_cc_agent.return_value = mock_cc_instance
            
            with pytest.raises(ModelUnavailableError):
                AgentOrchestrator(
                    llm_client=mock_llm_client,
                    gdpr_knowledge_base=mock_gdpr_kb
                )
    
    def test_agent_health_verification(self, mock_llm_client, mock_gdpr_kb):
        """Test agent health verification."""
        with patch('compliance_checker.orchestration.orchestrator.CCAgent') as mock_cc_agent, \
             patch('compliance_checker.orchestration.orchestrator.RAAgent') as mock_ra_agent:
            
            # Mock healthy agents
            mock_cc_instance = Mock()
            mock_cc_instance.initialize.return_value = True
            mock_cc_instance.get_status.return_value = {"status": "ready"}
            mock_cc_agent.return_value = mock_cc_instance
            
            mock_ra_instance = Mock()
            mock_ra_instance.initialize.return_value = True
            mock_ra_instance.get_status.return_value = {"status": "ready"}
            mock_ra_agent.return_value = mock_ra_instance
            
            orchestrator = AgentOrchestrator(
                llm_client=mock_llm_client,
                gdpr_knowledge_base=mock_gdpr_kb
            )
            
            # Should not raise exception
            orchestrator._verify_agent_health()
            
            # Test unhealthy agent
            mock_cc_instance.get_status.return_value = {"status": "error"}
            
            with pytest.raises(ModelUnavailableError):
                orchestrator._verify_agent_health()
    
    def test_concurrent_cc_agent_execution(self, mock_llm_client, mock_gdpr_kb, sample_document, sample_cc_report):
        """Test concurrent CC agent execution."""
        with patch('compliance_checker.orchestration.orchestrator.CCAgent') as mock_cc_agent, \
             patch('compliance_checker.orchestration.orchestrator.RAAgent') as mock_ra_agent:
            
            # Mock CC agents
            mock_cc_instance1 = Mock()
            mock_cc_instance1.initialize.return_value = True
            mock_cc_instance1.get_status.return_value = {"status": "ready"}
            mock_cc_instance1.analyze_compliance.return_value = sample_cc_report
            
            mock_cc_instance2 = Mock()
            mock_cc_instance2.initialize.return_value = True
            mock_cc_instance2.get_status.return_value = {"status": "ready"}
            mock_cc_instance2.analyze_compliance.return_value = sample_cc_report
            
            mock_cc_agent.side_effect = [mock_cc_instance1, mock_cc_instance2]
            
            # Mock RA agent
            mock_ra_instance = Mock()
            mock_ra_instance.initialize.return_value = True
            mock_ra_instance.get_status.return_value = {"status": "ready"}
            mock_ra_agent.return_value = mock_ra_instance
            
            orchestrator = AgentOrchestrator(
                llm_client=mock_llm_client,
                gdpr_knowledge_base=mock_gdpr_kb,
                concurrent_execution=True
            )
            
            session = AnalysisSession()
            progress_tracker = ProgressTracker()
            
            reports = orchestrator._execute_cc_agents_concurrent(
                sample_document, session, progress_tracker
            )
            
            assert len(reports) == 2
            assert "cc_agent_1" in reports
            assert "cc_agent_2" in reports
            
            # Verify both agents were called
            mock_cc_instance1.analyze_compliance.assert_called_once_with(sample_document)
            mock_cc_instance2.analyze_compliance.assert_called_once_with(sample_document)
    
    def test_sequential_cc_agent_execution(self, mock_llm_client, mock_gdpr_kb, sample_document, sample_cc_report):
        """Test sequential CC agent execution."""
        with patch('compliance_checker.orchestration.orchestrator.CCAgent') as mock_cc_agent, \
             patch('compliance_checker.orchestration.orchestrator.RAAgent') as mock_ra_agent:
            
            # Mock CC agents
            mock_cc_instance1 = Mock()
            mock_cc_instance1.initialize.return_value = True
            mock_cc_instance1.get_status.return_value = {"status": "ready"}
            mock_cc_instance1.analyze_compliance.return_value = sample_cc_report
            
            mock_cc_instance2 = Mock()
            mock_cc_instance2.initialize.return_value = True
            mock_cc_instance2.get_status.return_value = {"status": "ready"}
            mock_cc_instance2.analyze_compliance.return_value = sample_cc_report
            
            mock_cc_agent.side_effect = [mock_cc_instance1, mock_cc_instance2]
            
            # Mock RA agent
            mock_ra_instance = Mock()
            mock_ra_instance.initialize.return_value = True
            mock_ra_instance.get_status.return_value = {"status": "ready"}
            mock_ra_agent.return_value = mock_ra_instance
            
            orchestrator = AgentOrchestrator(
                llm_client=mock_llm_client,
                gdpr_knowledge_base=mock_gdpr_kb,
                concurrent_execution=False
            )
            
            session = AnalysisSession()
            progress_tracker = ProgressTracker()
            
            reports = orchestrator._execute_cc_agents_sequential(
                sample_document, session, progress_tracker
            )
            
            assert len(reports) == 2
            assert "cc_agent_1" in reports
            assert "cc_agent_2" in reports
    
    def test_ra_agent_execution(self, mock_llm_client, mock_gdpr_kb, sample_cc_report):
        """Test RA agent execution."""
        with patch('compliance_checker.orchestration.orchestrator.CCAgent') as mock_cc_agent, \
             patch('compliance_checker.orchestration.orchestrator.RAAgent') as mock_ra_agent:
            
            # Mock CC agents
            mock_cc_instance = Mock()
            mock_cc_instance.initialize.return_value = True
            mock_cc_instance.get_status.return_value = {"status": "ready"}
            mock_cc_agent.return_value = mock_cc_instance
            
            # Mock RA agent
            final_report = FinalComplianceReport(
                consolidated_findings=[],
                overall_compliance_status="Test status",
                confidence_score=0.85
            )
            
            mock_ra_instance = Mock()
            mock_ra_instance.initialize.return_value = True
            mock_ra_instance.get_status.return_value = {"status": "ready"}
            mock_ra_instance.assess_reports.return_value = final_report
            mock_ra_agent.return_value = mock_ra_instance
            
            orchestrator = AgentOrchestrator(
                llm_client=mock_llm_client,
                gdpr_knowledge_base=mock_gdpr_kb
            )
            
            session = AnalysisSession()
            progress_tracker = ProgressTracker()
            cc_reports = {"cc_agent_1": sample_cc_report}
            
            result = orchestrator._execute_ra_agent(cc_reports, session, progress_tracker)
            
            assert result == final_report
            assert session.ra_agent_report == final_report
            mock_ra_instance.assess_reports.assert_called_once()
    
    def test_feedback_loop_decision(self, mock_llm_client, mock_gdpr_kb):
        """Test feedback loop decision logic."""
        with patch('compliance_checker.orchestration.orchestrator.CCAgent') as mock_cc_agent, \
             patch('compliance_checker.orchestration.orchestrator.RAAgent') as mock_ra_agent:
            
            # Mock agents
            mock_cc_instance = Mock()
            mock_cc_instance.initialize.return_value = True
            mock_cc_instance.get_status.return_value = {"status": "ready"}
            mock_cc_agent.return_value = mock_cc_instance
            
            mock_ra_instance = Mock()
            mock_ra_instance.initialize.return_value = True
            mock_ra_instance.get_status.return_value = {"status": "ready"}
            mock_ra_agent.return_value = mock_ra_instance
            
            orchestrator = AgentOrchestrator(
                llm_client=mock_llm_client,
                gdpr_knowledge_base=mock_gdpr_kb
            )
            
            session = AnalysisSession()
            
            # Test low confidence score triggers feedback
            low_confidence_report = FinalComplianceReport(
                consolidated_findings=[],
                overall_compliance_status="Test",
                confidence_score=0.6  # Below 0.8 threshold
            )
            
            assert orchestrator._should_perform_feedback_loop(low_confidence_report, session)
            
            # Test high confidence score doesn't trigger feedback
            high_confidence_report = FinalComplianceReport(
                consolidated_findings=[],
                overall_compliance_status="Test",
                confidence_score=0.9
            )
            
            assert not orchestrator._should_perform_feedback_loop(high_confidence_report, session)
            
            # Test critical findings trigger feedback
            critical_finding = ComplianceFinding(
                requirement_id="req-1",
                requirement_text="Test",
                compliance_status=ComplianceStatus.NON_COMPLIANT,
                gdpr_articles=["Article 6"],
                reasoning="Test",
                severity=SeverityLevel.CRITICAL,
                confidence_score=0.8
            )
            
            critical_report = FinalComplianceReport(
                consolidated_findings=[critical_finding],
                overall_compliance_status="Test",
                confidence_score=0.85
            )
            
            assert orchestrator._should_perform_feedback_loop(critical_report, session)
    
    def test_improvement_detection(self, mock_llm_client, mock_gdpr_kb):
        """Test improvement detection between reports."""
        with patch('compliance_checker.orchestration.orchestrator.CCAgent') as mock_cc_agent, \
             patch('compliance_checker.orchestration.orchestrator.RAAgent') as mock_ra_agent:
            
            # Mock agents
            mock_cc_instance = Mock()
            mock_cc_instance.initialize.return_value = True
            mock_cc_instance.get_status.return_value = {"status": "ready"}
            mock_cc_agent.return_value = mock_cc_instance
            
            mock_ra_instance = Mock()
            mock_ra_instance.initialize.return_value = True
            mock_ra_instance.get_status.return_value = {"status": "ready"}
            mock_ra_agent.return_value = mock_ra_instance
            
            orchestrator = AgentOrchestrator(
                llm_client=mock_llm_client,
                gdpr_knowledge_base=mock_gdpr_kb
            )
            
            # Previous report with lower confidence
            previous_report = FinalComplianceReport(
                consolidated_findings=[],
                overall_compliance_status="Test",
                confidence_score=0.7
            )
            
            # Current report with higher confidence
            current_report = FinalComplianceReport(
                consolidated_findings=[],
                overall_compliance_status="Test",
                confidence_score=0.8
            )
            
            assert orchestrator._is_improvement_achieved(previous_report, current_report)
            
            # Test no improvement
            assert not orchestrator._is_improvement_achieved(current_report, previous_report)
    
    def test_session_management(self, mock_llm_client, mock_gdpr_kb):
        """Test session management functionality."""
        with patch('compliance_checker.orchestration.orchestrator.CCAgent') as mock_cc_agent, \
             patch('compliance_checker.orchestration.orchestrator.RAAgent') as mock_ra_agent:
            
            # Mock agents
            mock_cc_instance = Mock()
            mock_cc_instance.initialize.return_value = True
            mock_cc_instance.get_status.return_value = {"status": "ready"}
            mock_cc_agent.return_value = mock_cc_instance
            
            mock_ra_instance = Mock()
            mock_ra_instance.initialize.return_value = True
            mock_ra_instance.get_status.return_value = {"status": "ready"}
            mock_ra_agent.return_value = mock_ra_instance
            
            orchestrator = AgentOrchestrator(
                llm_client=mock_llm_client,
                gdpr_knowledge_base=mock_gdpr_kb
            )
            
            # Create test session
            session = AnalysisSession()
            orchestrator.active_sessions[session.session_id] = session
            
            # Test session status retrieval
            status = orchestrator.get_session_status(session.session_id)
            assert status is not None
            assert status["session_id"] == session.session_id
            
            # Test non-existent session
            assert orchestrator.get_session_status("non-existent") is None
            
            # Test session cancellation
            session.start_session()  # Make it active
            assert orchestrator.cancel_session(session.session_id)
            assert session.status == SessionStatus.CANCELLED
            
            # Test cancelling non-existent session
            assert not orchestrator.cancel_session("non-existent")
    
    def test_performance_metrics(self, mock_llm_client, mock_gdpr_kb):
        """Test performance metrics tracking."""
        with patch('compliance_checker.orchestration.orchestrator.CCAgent') as mock_cc_agent, \
             patch('compliance_checker.orchestration.orchestrator.RAAgent') as mock_ra_agent:
            
            # Mock agents
            mock_cc_instance = Mock()
            mock_cc_instance.initialize.return_value = True
            mock_cc_instance.get_status.return_value = {"status": "ready"}
            mock_cc_agent.return_value = mock_cc_instance
            
            mock_ra_instance = Mock()
            mock_ra_instance.initialize.return_value = True
            mock_ra_instance.get_status.return_value = {"status": "ready"}
            mock_ra_agent.return_value = mock_ra_instance
            
            orchestrator = AgentOrchestrator(
                llm_client=mock_llm_client,
                gdpr_knowledge_base=mock_gdpr_kb
            )
            
            # Test initial metrics
            metrics = orchestrator.get_performance_metrics()
            assert metrics["total_analyses"] == 0
            assert metrics["successful_analyses"] == 0
            assert metrics["failed_analyses"] == 0
            assert "agent_health" in metrics
            assert "session_stats" in metrics
            
            # Test metrics update after successful analysis
            session = AnalysisSession()
            session.total_processing_time = 10.0
            orchestrator._update_performance_metrics(session, True)
            
            metrics = orchestrator.get_performance_metrics()
            assert metrics["total_analyses"] == 1
            assert metrics["successful_analyses"] == 1
            assert metrics["average_processing_time"] == 10.0
            
            # Test metrics update after failed analysis
            orchestrator._update_performance_metrics(session, False)
            
            metrics = orchestrator.get_performance_metrics()
            assert metrics["total_analyses"] == 2
            assert metrics["failed_analyses"] == 1
    
    def test_session_cleanup(self, mock_llm_client, mock_gdpr_kb):
        """Test session cleanup functionality."""
        with patch('compliance_checker.orchestration.orchestrator.CCAgent') as mock_cc_agent, \
             patch('compliance_checker.orchestration.orchestrator.RAAgent') as mock_ra_agent:
            
            # Mock agents
            mock_cc_instance = Mock()
            mock_cc_instance.initialize.return_value = True
            mock_cc_instance.get_status.return_value = {"status": "ready"}
            mock_cc_agent.return_value = mock_cc_instance
            
            mock_ra_instance = Mock()
            mock_ra_instance.initialize.return_value = True
            mock_ra_instance.get_status.return_value = {"status": "ready"}
            mock_ra_agent.return_value = mock_ra_instance
            
            orchestrator = AgentOrchestrator(
                llm_client=mock_llm_client,
                gdpr_knowledge_base=mock_gdpr_kb
            )
            
            # Create old completed session
            old_session = AnalysisSession()
            old_session.complete_session()
            old_session.end_time = datetime.now() - timedelta(hours=2)  # 2 hours ago
            
            # Create recent completed session
            recent_session = AnalysisSession()
            recent_session.complete_session()
            recent_session.end_time = datetime.now() - timedelta(minutes=30)  # 30 minutes ago
            
            # Create active session
            active_session = AnalysisSession()
            active_session.start_session()
            
            orchestrator.active_sessions[old_session.session_id] = old_session
            orchestrator.active_sessions[recent_session.session_id] = recent_session
            orchestrator.active_sessions[active_session.session_id] = active_session
            
            # Cleanup should remove only old completed session
            cleaned_count = orchestrator.cleanup_completed_sessions()
            
            assert cleaned_count == 1
            assert old_session.session_id not in orchestrator.active_sessions
            assert recent_session.session_id in orchestrator.active_sessions
            assert active_session.session_id in orchestrator.active_sessions


if __name__ == "__main__":
    pytest.main([__file__])