"""
Agent orchestration system for coordinating multi-agent compliance analysis.
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..agents.base import AgentOrchestrator as BaseOrchestrator
from ..agents.cc_agent import CCAgent
from ..agents.ra_agent import RAAgent
from ..models.document import SpecificationDocument
from ..models.report import ComplianceReport, FinalComplianceReport
from ..llm.multi_agent_client import MultiAgentLLMClient
from ..knowledge.gdpr_knowledge_base import GDPRKnowledgeBase
from ..exceptions import ModelUnavailableError, DocumentProcessingError
from .session import AnalysisSession, SessionStatus, FeedbackIteration
from .progress import ProgressTracker, AnalysisStage


logger = logging.getLogger(__name__)


class AgentOrchestrator(BaseOrchestrator):
    """
    Orchestrates the multi-agent compliance analysis workflow.
    
    This class coordinates the execution of CC_Agents and RA_Agent, manages
    concurrent execution, handles feedback loops, and provides progress tracking.
    """
    
    def __init__(self,
                 llm_client: MultiAgentLLMClient,
                 gdpr_knowledge_base: GDPRKnowledgeBase,
                 max_feedback_iterations: int = 3,
                 concurrent_execution: bool = True,
                 session_timeout: int = 3600):  # 1 hour timeout
        """
        Initialize the agent orchestrator.
        
        Args:
            llm_client: Multi-agent LLM client for model communication
            gdpr_knowledge_base: GDPR knowledge base for compliance reference
            max_feedback_iterations: Maximum number of feedback iterations
            concurrent_execution: Whether to run CC_Agents concurrently
            session_timeout: Session timeout in seconds
        """
        self.llm_client = llm_client
        self.gdpr_knowledge_base = gdpr_knowledge_base
        self.max_feedback_iterations = max_feedback_iterations
        self.concurrent_execution = concurrent_execution
        self.session_timeout = session_timeout
        
        # Agent instances
        self.cc_agents: Dict[str, CCAgent] = {}
        self.ra_agent: Optional[RAAgent] = None
        
        # Session management
        self.active_sessions: Dict[str, AnalysisSession] = {}
        self.progress_trackers: Dict[str, ProgressTracker] = {}
        
        # Configuration
        self.cc_agent_models = {
            "cc_agent_1": "deepseek-r1:8b",
            "cc_agent_2": "gemma3:27b"
        }
        self.ra_agent_model = "qwq:32b"
        
        # Performance monitoring
        self.performance_metrics: Dict[str, Any] = {
            "total_analyses": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "average_processing_time": 0.0,
            "feedback_iterations_used": []
        }
        
        # Initialize agents
        self._initialize_agents()
    
    def _initialize_agents(self) -> None:
        """Initialize all agents."""
        logger.info("Initializing agent orchestrator")
        
        try:
            # Initialize CC_Agents
            for agent_id, model_name in self.cc_agent_models.items():
                agent = CCAgent(
                    agent_id=agent_id,
                    model_name=model_name,
                    llm_client=self.llm_client,
                    gdpr_knowledge_base=self.gdpr_knowledge_base
                )
                
                if agent.initialize():
                    self.cc_agents[agent_id] = agent
                    logger.info(f"Initialized {agent_id} with model {model_name}")
                else:
                    logger.error(f"Failed to initialize {agent_id}")
                    raise ModelUnavailableError(f"Failed to initialize {agent_id}")
            
            # Initialize RA_Agent
            self.ra_agent = RAAgent(
                llm_client=self.llm_client,
                model_name=self.ra_agent_model
            )
            
            if not self.ra_agent.initialize():
                logger.error("Failed to initialize RA_Agent")
                raise ModelUnavailableError("Failed to initialize RA_Agent")
            
            logger.info("Agent orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agents: {str(e)}")
            raise
    
    def execute_compliance_analysis(self, 
                                   document: SpecificationDocument,
                                   session_id: Optional[str] = None,
                                   progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> FinalComplianceReport:
        """
        Execute the complete multi-agent compliance analysis workflow.
        
        Args:
            document: Specification document to analyze
            session_id: Optional session ID for tracking
            progress_callback: Optional callback for progress updates
            
        Returns:
            FinalComplianceReport with consolidated findings
        """
        # Create or get session
        if session_id and session_id in self.active_sessions:
            session = self.active_sessions[session_id]
        else:
            session = AnalysisSession(
                max_iterations=self.max_feedback_iterations,
                config={
                    "concurrent_execution": self.concurrent_execution,
                    "cc_agent_models": self.cc_agent_models,
                    "ra_agent_model": self.ra_agent_model
                }
            )
            self.active_sessions[session.session_id] = session
        
        # Create progress tracker
        progress_tracker = ProgressTracker()
        if progress_callback:
            progress_tracker.add_progress_callback(progress_callback)
        self.progress_trackers[session.session_id] = progress_tracker
        
        try:
            logger.info(f"Starting compliance analysis for session {session.session_id}")
            
            # Start session and progress tracking
            session.start_session()
            progress_tracker.start_analysis()
            
            # Stage 1: Initialize analysis
            progress_tracker.start_stage(AnalysisStage.INITIALIZATION, "Preparing agents for analysis")
            self._verify_agent_health()
            progress_tracker.complete_stage(AnalysisStage.INITIALIZATION)
            
            # Stage 2: Process document
            progress_tracker.start_stage(AnalysisStage.DOCUMENT_PROCESSING, "Processing specification document")
            session.set_document(document, {
                "filename": document.filename,
                "requirements_count": len(document.requirements),
                "file_size": len(document.content)
            })
            progress_tracker.complete_stage(AnalysisStage.DOCUMENT_PROCESSING)
            
            # Stage 3: Execute CC_Agents
            session.start_cc_agents()
            cc_reports = self._execute_cc_agents(document, session, progress_tracker)
            
            # Stage 4: Execute RA_Agent
            session.start_ra_agent()
            final_report = self._execute_ra_agent(cc_reports, session, progress_tracker)
            
            # Stage 5: Handle feedback loop if needed
            if self._should_perform_feedback_loop(final_report, session):
                final_report = self._handle_feedback_loop(document, cc_reports, final_report, session, progress_tracker)
            
            # Complete analysis
            session.complete_session()
            progress_tracker.complete_analysis()
            
            # Update performance metrics
            self._update_performance_metrics(session, True)
            
            logger.info(f"Compliance analysis completed for session {session.session_id}")
            return final_report
            
        except Exception as e:
            logger.error(f"Compliance analysis failed: {str(e)}")
            session.fail_session(str(e), {"exception_type": type(e).__name__})
            
            if session.session_id in self.progress_trackers:
                progress_tracker = self.progress_trackers[session.session_id]
                if progress_tracker.current_stage:
                    progress_tracker.fail_stage(progress_tracker.current_stage, str(e))
            
            self._update_performance_metrics(session, False)
            raise
        
        finally:
            # Cleanup
            if session.session_id in self.active_sessions:
                if session.is_completed() or session.is_failed():
                    del self.active_sessions[session.session_id]
            
            if session.session_id in self.progress_trackers:
                del self.progress_trackers[session.session_id]
    
    def _verify_agent_health(self) -> None:
        """Verify that all agents are healthy and ready."""
        # Check CC_Agents
        for agent_id, agent in self.cc_agents.items():
            status = agent.get_status()
            if status.get("status") != "ready":
                raise ModelUnavailableError(f"CC_Agent {agent_id} is not ready: {status}")
        
        # Check RA_Agent
        if self.ra_agent:
            status = self.ra_agent.get_status()
            if status.get("status") != "ready":
                raise ModelUnavailableError(f"RA_Agent is not ready: {status}")
        else:
            raise ModelUnavailableError("RA_Agent is not initialized")
    
    def _execute_cc_agents(self, 
                          document: SpecificationDocument,
                          session: AnalysisSession,
                          progress_tracker: ProgressTracker) -> Dict[str, ComplianceReport]:
        """
        Execute CC_Agents to analyze the document.
        
        Args:
            document: Document to analyze
            session: Analysis session
            progress_tracker: Progress tracker
            
        Returns:
            Dictionary of CC_Agent reports
        """
        logger.info("Executing CC_Agents")
        
        if self.concurrent_execution:
            return self._execute_cc_agents_concurrent(document, session, progress_tracker)
        else:
            return self._execute_cc_agents_sequential(document, session, progress_tracker)
    
    def _execute_cc_agents_concurrent(self, 
                                     document: SpecificationDocument,
                                     session: AnalysisSession,
                                     progress_tracker: ProgressTracker) -> Dict[str, ComplianceReport]:
        """Execute CC_Agents concurrently using ThreadPoolExecutor."""
        reports = {}
        
        def analyze_with_agent(agent_id: str, agent: CCAgent) -> tuple[str, ComplianceReport]:
            """Wrapper function for concurrent execution."""
            try:
                logger.info(f"Starting analysis with {agent_id}")
                report = agent.analyze_compliance(document)
                logger.info(f"Completed analysis with {agent_id}")
                return agent_id, report
            except Exception as e:
                logger.error(f"Analysis failed for {agent_id}: {str(e)}")
                raise
        
        # Start both agents concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit tasks
            future_to_agent = {
                executor.submit(analyze_with_agent, agent_id, agent): agent_id
                for agent_id, agent in self.cc_agents.items()
            }
            
            # Track progress for each agent
            agent_stages = {
                "cc_agent_1": AnalysisStage.CC_AGENT_1_ANALYSIS,
                "cc_agent_2": AnalysisStage.CC_AGENT_2_ANALYSIS
            }
            
            # Start progress tracking for both agents
            for agent_id in self.cc_agents.keys():
                stage = agent_stages[agent_id]
                progress_tracker.start_stage(stage, f"Analyzing with {agent_id}")
            
            # Collect results as they complete
            for future in as_completed(future_to_agent, timeout=self.session_timeout):
                agent_id = future_to_agent[future]
                
                try:
                    agent_id, report = future.result()
                    reports[agent_id] = report
                    session.add_cc_agent_report(agent_id, report)
                    
                    # Update progress
                    stage = agent_stages[agent_id]
                    progress_tracker.complete_stage(stage, f"Analysis completed by {agent_id}")
                    
                    logger.info(f"Received report from {agent_id}: {len(report.findings)} findings")
                    
                except Exception as e:
                    logger.error(f"CC_Agent {agent_id} failed: {str(e)}")
                    stage = agent_stages[agent_id]
                    progress_tracker.fail_stage(stage, str(e))
                    raise
        
        return reports
    
    def _execute_cc_agents_sequential(self, 
                                     document: SpecificationDocument,
                                     session: AnalysisSession,
                                     progress_tracker: ProgressTracker) -> Dict[str, ComplianceReport]:
        """Execute CC_Agents sequentially."""
        reports = {}
        
        agent_stages = {
            "cc_agent_1": AnalysisStage.CC_AGENT_1_ANALYSIS,
            "cc_agent_2": AnalysisStage.CC_AGENT_2_ANALYSIS
        }
        
        for agent_id, agent in self.cc_agents.items():
            try:
                stage = agent_stages[agent_id]
                progress_tracker.start_stage(stage, f"Analyzing with {agent_id}")
                
                logger.info(f"Starting analysis with {agent_id}")
                report = agent.analyze_compliance(document)
                
                reports[agent_id] = report
                session.add_cc_agent_report(agent_id, report)
                
                progress_tracker.complete_stage(stage, f"Analysis completed by {agent_id}")
                logger.info(f"Completed analysis with {agent_id}: {len(report.findings)} findings")
                
            except Exception as e:
                logger.error(f"CC_Agent {agent_id} failed: {str(e)}")
                progress_tracker.fail_stage(stage, str(e))
                raise
        
        return reports
    
    def _execute_ra_agent(self, 
                         cc_reports: Dict[str, ComplianceReport],
                         session: AnalysisSession,
                         progress_tracker: ProgressTracker) -> FinalComplianceReport:
        """
        Execute RA_Agent to assess and consolidate CC_Agent reports.
        
        Args:
            cc_reports: Reports from CC_Agents
            session: Analysis session
            progress_tracker: Progress tracker
            
        Returns:
            Final consolidated compliance report
        """
        logger.info("Executing RA_Agent")
        
        try:
            progress_tracker.start_stage(AnalysisStage.RA_AGENT_ASSESSMENT, "Assessing and consolidating reports")
            
            # Convert reports to list for RA_Agent
            reports_list = list(cc_reports.values())
            
            # Execute RA_Agent assessment
            final_report = self.ra_agent.assess_reports(reports_list)
            
            # Update session
            session.set_ra_agent_report(final_report)
            
            progress_tracker.complete_stage(AnalysisStage.RA_AGENT_ASSESSMENT, 
                                          f"Consolidated {len(final_report.consolidated_findings)} findings")
            
            logger.info(f"RA_Agent assessment completed: {len(final_report.consolidated_findings)} consolidated findings")
            return final_report
            
        except Exception as e:
            logger.error(f"RA_Agent execution failed: {str(e)}")
            progress_tracker.fail_stage(AnalysisStage.RA_AGENT_ASSESSMENT, str(e))
            raise
    
    def _should_perform_feedback_loop(self, 
                                     final_report: FinalComplianceReport,
                                     session: AnalysisSession) -> bool:
        """
        Determine if feedback loop should be performed.
        
        Args:
            final_report: Final report from RA_Agent
            session: Analysis session
            
        Returns:
            True if feedback loop should be performed
        """
        # Check if feedback is enabled and iterations are available
        if not session.can_continue_feedback():
            return False
        
        # Check if confidence score is below threshold
        confidence_threshold = 0.8
        if final_report.confidence_score < confidence_threshold:
            logger.info(f"Confidence score {final_report.confidence_score} below threshold {confidence_threshold}, initiating feedback loop")
            return True
        
        # Check if there are critical findings that might benefit from iteration
        critical_findings = final_report.get_critical_findings()
        if len(critical_findings) > 0 and session.current_iteration == 0:
            logger.info(f"Found {len(critical_findings)} critical findings, initiating feedback loop for improvement")
            return True
        
        return False
    
    def _handle_feedback_loop(self, 
                             document: SpecificationDocument,
                             initial_cc_reports: Dict[str, ComplianceReport],
                             initial_final_report: FinalComplianceReport,
                             session: AnalysisSession,
                             progress_tracker: ProgressTracker) -> FinalComplianceReport:
        """
        Handle the feedback loop between RA_Agent and CC_Agents.
        
        Args:
            document: Original document
            initial_cc_reports: Initial CC_Agent reports
            initial_final_report: Initial final report
            session: Analysis session
            progress_tracker: Progress tracker
            
        Returns:
            Final report after feedback iterations
        """
        logger.info("Starting feedback loop")
        
        current_final_report = initial_final_report
        current_cc_reports = initial_cc_reports
        
        for iteration in range(1, self.max_feedback_iterations + 1):
            if not session.can_continue_feedback():
                break
            
            try:
                logger.info(f"Starting feedback iteration {iteration}")
                session.start_feedback_iteration(iteration)
                
                # Stage: Generate feedback
                progress_tracker.start_stage(AnalysisStage.FEEDBACK_GENERATION, 
                                            f"Generating feedback for iteration {iteration}")
                
                feedback_data = self.ra_agent.generate_feedback(list(current_cc_reports.values()))
                
                progress_tracker.complete_stage(AnalysisStage.FEEDBACK_GENERATION)
                
                # Stage: Process feedback
                progress_tracker.start_stage(AnalysisStage.FEEDBACK_PROCESSING, 
                                            f"Processing feedback iteration {iteration}")
                
                # Create feedback iteration record
                feedback_iteration = FeedbackIteration(
                    iteration_number=iteration,
                    feedback_data=feedback_data
                )
                
                # Process feedback with CC_Agents
                updated_cc_reports = self._process_feedback_with_agents(
                    document, feedback_data, session, progress_tracker
                )
                
                feedback_iteration.cc_agent_responses = updated_cc_reports
                
                # Get updated assessment from RA_Agent
                updated_final_report = self.ra_agent.assess_reports(list(updated_cc_reports.values()))
                feedback_iteration.ra_agent_assessment = updated_final_report
                
                # Update session
                session.add_feedback_iteration(feedback_iteration)
                
                progress_tracker.complete_stage(AnalysisStage.FEEDBACK_PROCESSING)
                
                # Check if improvement was achieved
                if self._is_improvement_achieved(current_final_report, updated_final_report):
                    logger.info(f"Improvement achieved in iteration {iteration}")
                    current_final_report = updated_final_report
                    current_cc_reports = updated_cc_reports
                else:
                    logger.info(f"No significant improvement in iteration {iteration}, stopping feedback loop")
                    break
                
                # Check if we should continue
                if not self._should_continue_feedback(updated_final_report, iteration):
                    logger.info(f"Stopping feedback loop after iteration {iteration}")
                    break
                
            except Exception as e:
                logger.error(f"Feedback iteration {iteration} failed: {str(e)}")
                session.add_error(f"Feedback iteration {iteration} failed", {"error": str(e)})
                break
        
        logger.info(f"Feedback loop completed after {session.current_iteration} iterations")
        return current_final_report
    
    def _process_feedback_with_agents(self, 
                                     document: SpecificationDocument,
                                     feedback_data: List[Dict[str, Any]],
                                     session: AnalysisSession,
                                     progress_tracker: ProgressTracker) -> Dict[str, ComplianceReport]:
        """
        Process feedback with CC_Agents and get updated reports.
        
        Args:
            document: Original document
            feedback_data: Feedback from RA_Agent
            session: Analysis session
            progress_tracker: Progress tracker
            
        Returns:
            Updated CC_Agent reports
        """
        updated_reports = {}
        
        # Process feedback for each agent
        for feedback_item in feedback_data:
            target_agent_id = feedback_item.get("target_agent_id")
            feedback_text = feedback_item.get("feedback_text", "")
            
            if target_agent_id in self.cc_agents:
                agent = self.cc_agents[target_agent_id]
                
                try:
                    # Process feedback
                    agent.process_feedback(feedback_text)
                    
                    # Get updated analysis
                    updated_report = agent.analyze_compliance(document)
                    updated_reports[target_agent_id] = updated_report
                    
                    logger.info(f"Processed feedback for {target_agent_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to process feedback for {target_agent_id}: {str(e)}")
                    # Use previous report if feedback processing fails
                    if target_agent_id in session.cc_agent_reports:
                        updated_reports[target_agent_id] = session.cc_agent_reports[target_agent_id]
        
        return updated_reports
    
    def _is_improvement_achieved(self, 
                                previous_report: FinalComplianceReport,
                                current_report: FinalComplianceReport) -> bool:
        """
        Check if improvement was achieved between reports.
        
        Args:
            previous_report: Previous final report
            current_report: Current final report
            
        Returns:
            True if improvement was achieved
        """
        # Check confidence score improvement
        confidence_improvement = current_report.confidence_score > previous_report.confidence_score
        
        # Check if critical findings were reduced
        prev_critical = len(previous_report.get_critical_findings())
        curr_critical = len(current_report.get_critical_findings())
        critical_improvement = curr_critical < prev_critical
        
        # Check overall findings quality (more specific criteria could be added)
        findings_improvement = len(current_report.consolidated_findings) > len(previous_report.consolidated_findings)
        
        return confidence_improvement or critical_improvement or findings_improvement
    
    def _should_continue_feedback(self, 
                                 final_report: FinalComplianceReport,
                                 iteration: int) -> bool:
        """
        Determine if feedback loop should continue.
        
        Args:
            final_report: Current final report
            iteration: Current iteration number
            
        Returns:
            True if feedback should continue
        """
        # Stop if maximum iterations reached
        if iteration >= self.max_feedback_iterations:
            return False
        
        # Stop if confidence is high enough
        if final_report.confidence_score >= 0.9:
            return False
        
        # Stop if no critical findings remain
        if len(final_report.get_critical_findings()) == 0:
            return False
        
        return True
    
    def _update_performance_metrics(self, session: AnalysisSession, success: bool) -> None:
        """Update performance metrics based on session results."""
        self.performance_metrics["total_analyses"] += 1
        
        if success:
            self.performance_metrics["successful_analyses"] += 1
            
            if session.total_processing_time:
                # Update average processing time
                total_time = self.performance_metrics["average_processing_time"] * (self.performance_metrics["successful_analyses"] - 1)
                total_time += session.total_processing_time
                self.performance_metrics["average_processing_time"] = total_time / self.performance_metrics["successful_analyses"]
            
            # Track feedback iterations
            self.performance_metrics["feedback_iterations_used"].append(session.current_iteration)
        else:
            self.performance_metrics["failed_analyses"] += 1
    
    def coordinate_agents(self) -> None:
        """Coordinate the execution of multiple agents."""
        # This method is called by the base class interface
        # The actual coordination happens in execute_compliance_analysis
        pass
    
    def handle_feedback_loop(self, 
                           feedback: List[Dict[str, Any]], 
                           max_iterations: int = 3) -> None:
        """Handle the feedback loop between RA_Agent and CC_Agents."""
        # This method is called by the base class interface
        # The actual feedback handling happens in _handle_feedback_loop
        pass
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific session."""
        if session_id in self.active_sessions:
            return self.active_sessions[session_id].get_status_summary()
        return None
    
    def get_progress_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get progress status of a specific session."""
        if session_id in self.progress_trackers:
            return self.progress_trackers[session_id].get_progress_summary()
        return None
    
    def cancel_session(self, session_id: str) -> bool:
        """Cancel an active session."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            if session.is_active():
                session.cancel_session()
                return True
        return False
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the orchestrator."""
        metrics = self.performance_metrics.copy()
        
        # Add agent health status
        metrics["agent_health"] = {
            "cc_agents": {
                agent_id: agent.get_status()
                for agent_id, agent in self.cc_agents.items()
            },
            "ra_agent": self.ra_agent.get_status() if self.ra_agent else None
        }
        
        # Add session statistics
        metrics["session_stats"] = {
            "active_sessions": len(self.active_sessions),
            "total_sessions": metrics["total_analyses"]
        }
        
        return metrics
    
    def cleanup_completed_sessions(self) -> int:
        """Clean up completed sessions and return count of cleaned sessions."""
        cleaned_count = 0
        session_ids_to_remove = []
        
        for session_id, session in self.active_sessions.items():
            if session.is_completed() or session.is_failed():
                # Check if session is old enough to clean up (e.g., 1 hour after completion)
                if session.end_time:
                    time_since_completion = (datetime.now() - session.end_time).total_seconds()
                    if time_since_completion > 3600:  # 1 hour
                        session_ids_to_remove.append(session_id)
        
        for session_id in session_ids_to_remove:
            del self.active_sessions[session_id]
            if session_id in self.progress_trackers:
                del self.progress_trackers[session_id]
            cleaned_count += 1
        
        return cleaned_count