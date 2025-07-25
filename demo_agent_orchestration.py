#!/usr/bin/env python3
"""
Demo script for the agent orchestration system.

This script demonstrates the complete multi-agent compliance analysis workflow
including concurrent execution, session management, progress tracking, and
feedback loops.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any

from compliance_checker.orchestration.orchestrator import AgentOrchestrator
from compliance_checker.orchestration.session import AnalysisSession, SessionStatus
from compliance_checker.orchestration.progress import ProgressTracker, AnalysisStage
from compliance_checker.models.document import SpecificationDocument, Requirement
from compliance_checker.llm.multi_agent_client import MultiAgentLLMClient
from compliance_checker.knowledge.gdpr_knowledge_base import GDPRKnowledgeBase
from compliance_checker.config.manager import ConfigurationManager


def create_sample_document() -> SpecificationDocument:
    """Create a sample specification document for testing."""
    requirements = [
        Requirement(
            id="REQ-001",
            text="The system shall collect user personal data only with explicit consent",
            category="privacy",
            metadata={
                "priority": "high",
                "keywords": ["consent", "personal data", "collection"]
            }
        ),
        Requirement(
            id="REQ-002", 
            text="User data must be encrypted at rest and in transit",
            category="security",
            metadata={
                "priority": "critical",
                "keywords": ["encryption", "data protection", "security"]
            }
        ),
        Requirement(
            id="REQ-003",
            text="Users shall have the right to access their personal data",
            category="privacy",
            metadata={
                "priority": "high",
                "keywords": ["data access", "user rights", "GDPR"]
            }
        ),
        Requirement(
            id="REQ-004",
            text="The system shall provide data portability functionality",
            category="privacy",
            metadata={
                "priority": "medium",
                "keywords": ["data portability", "export", "user rights"]
            }
        ),
        Requirement(
            id="REQ-005",
            text="Personal data shall be deleted upon user request",
            category="privacy",
            metadata={
                "priority": "high",
                "keywords": ["data deletion", "right to be forgotten", "GDPR"]
            }
        ),
        Requirement(
            id="REQ-006",
            text="The system shall log all data processing activities",
            category="compliance",
            metadata={
                "priority": "medium",
                "keywords": ["logging", "audit trail", "processing activities"]
            }
        ),
        Requirement(
            id="REQ-007",
            text="Data breach notifications must be sent within 72 hours",
            category="compliance",
            metadata={
                "priority": "critical",
                "keywords": ["breach notification", "incident response", "GDPR"]
            }
        ),
        Requirement(
            id="REQ-008",
            text="The system shall implement privacy by design principles",
            category="privacy",
            metadata={
                "priority": "high",
                "keywords": ["privacy by design", "data protection", "architecture"]
            }
        )
    ]
    
    document_content = """
# Sample Application Specification

## Overview
This document specifies the requirements for a user data management system
that must comply with GDPR regulations.

## Privacy Requirements
The system must implement comprehensive privacy protection measures including
consent management, data access rights, and deletion capabilities.

## Security Requirements  
All user data must be protected through encryption and secure processing.

## Compliance Requirements
The system must maintain audit logs and support regulatory compliance reporting.
"""
    
    return SpecificationDocument(
        document_id="sample-spec-001",
        filename="sample_specification.md",
        content=document_content,
        requirements=requirements,
        metadata={
            "version": "1.0",
            "created_date": datetime.now().isoformat(),
            "document_type": "specification",
            "compliance_framework": "GDPR"
        }
    )


class ProgressMonitor:
    """Monitor and display progress updates."""
    
    def __init__(self):
        self.last_update = None
        self.start_time = time.time()
    
    def progress_callback(self, progress_data: Dict[str, Any]) -> None:
        """Handle progress updates."""
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        print(f"\n[{elapsed:.1f}s] Progress Update:")
        print(f"  Overall Progress: {progress_data['overall_progress']:.1f}%")
        print(f"  Current Stage: {progress_data.get('current_stage', 'Unknown')}")
        
        if progress_data.get('estimated_completion'):
            print(f"  Estimated Completion: {progress_data['estimated_completion']}")
        
        # Show stage details
        stages = progress_data.get('stages', {})
        active_stages = {k: v for k, v in stages.items() if v['status'] in ['running', 'completed']}
        
        if active_stages:
            print("  Stage Status:")
            for stage_name, stage_info in active_stages.items():
                status_icon = "✓" if stage_info['status'] == 'completed' else "⏳"
                print(f"    {status_icon} {stage_name}: {stage_info['progress']:.1f}% - {stage_info.get('details', '')}")
        
        self.last_update = current_time


def demonstrate_basic_orchestration():
    """Demonstrate basic orchestration functionality."""
    print("=" * 60)
    print("DEMO: Basic Agent Orchestration")
    print("=" * 60)
    
    try:
        # Initialize components
        print("1. Initializing components...")
        config_manager = ConfigurationManager()
        
        llm_client = MultiAgentLLMClient(config_manager)
        gdpr_kb = GDPRKnowledgeBase()
        
        # Initialize orchestrator
        print("2. Creating agent orchestrator...")
        orchestrator = AgentOrchestrator(
            llm_client=llm_client,
            gdpr_knowledge_base=gdpr_kb,
            max_feedback_iterations=2,
            concurrent_execution=True
        )
        
        # Create sample document
        print("3. Creating sample document...")
        document = create_sample_document()
        print(f"   Document: {document.filename}")
        print(f"   Requirements: {len(document.requirements)}")
        
        # Set up progress monitoring
        progress_monitor = ProgressMonitor()
        
        # Execute analysis
        print("4. Starting compliance analysis...")
        print("   (This may take several minutes depending on model availability)")
        
        start_time = time.time()
        
        final_report = orchestrator.execute_compliance_analysis(
            document=document,
            progress_callback=progress_monitor.progress_callback
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Display results
        print(f"\n5. Analysis completed in {processing_time:.1f} seconds")
        print(f"   Consolidated Findings: {len(final_report.consolidated_findings)}")
        print(f"   Overall Confidence: {final_report.confidence_score:.2f}")
        print(f"   Feedback Iterations: {final_report.feedback_iterations}")
        
        # Show findings summary
        if final_report.consolidated_findings:
            print("\n   Findings Summary:")
            for finding in final_report.consolidated_findings[:3]:  # Show first 3
                print(f"     • {finding.requirement_id}: {finding.compliance_status.value}")
                print(f"       Severity: {finding.severity.value}")
                print(f"       GDPR Articles: {', '.join(finding.gdpr_articles)}")
        
        print(f"\n   Overall Assessment:")
        print(f"   {final_report.overall_compliance_status}")
        
        return True
        
    except Exception as e:
        print(f"Demo failed: {str(e)}")
        return False


def demonstrate_session_management():
    """Demonstrate session management capabilities."""
    print("\n" + "=" * 60)
    print("DEMO: Session Management")
    print("=" * 60)
    
    try:
        # Create session
        print("1. Creating analysis session...")
        session = AnalysisSession(max_iterations=3)
        print(f"   Session ID: {session.session_id}")
        print(f"   Status: {session.status.value}")
        
        # Simulate session lifecycle
        print("2. Simulating session lifecycle...")
        
        session.start_session()
        print(f"   Started: {session.status.value} - Progress: {session.progress_percentage}%")
        
        # Simulate document processing
        document = create_sample_document()
        session.set_document(document, {"source": "demo"})
        print(f"   Document set: {session.status.value} - Progress: {session.progress_percentage}%")
        
        # Simulate CC agent execution
        session.start_cc_agents()
        print(f"   CC agents started: {session.status.value} - Progress: {session.progress_percentage}%")
        
        # Add some warnings and errors for demonstration
        session.add_warning("Model response time is slower than expected")
        session.add_error("Temporary network timeout", {"retry_count": 1})
        
        # Complete session
        session.complete_session()
        print(f"   Completed: {session.status.value} - Progress: {session.progress_percentage}%")
        
        # Display session summary
        print("3. Session summary:")
        summary = session.get_status_summary()
        for key, value in summary.items():
            if key not in ['session_id']:  # Skip ID as already shown
                print(f"   {key}: {value}")
        
        # Test session serialization
        print("4. Testing session serialization...")
        session_dict = session.to_dict()
        print(f"   Serialized session size: {len(json.dumps(session_dict))} bytes")
        
        return True
        
    except Exception as e:
        print(f"Session management demo failed: {str(e)}")
        return False


def demonstrate_progress_tracking():
    """Demonstrate progress tracking functionality."""
    print("\n" + "=" * 60)
    print("DEMO: Progress Tracking")
    print("=" * 60)
    
    try:
        # Create progress tracker
        print("1. Creating progress tracker...")
        tracker = ProgressTracker()
        
        # Set up callback
        def demo_callback(data):
            print(f"   Callback: {data['current_stage']} - {data['overall_progress']:.1f}%")
        
        tracker.add_progress_callback(demo_callback)
        
        # Simulate analysis stages
        print("2. Simulating analysis stages...")
        
        tracker.start_analysis()
        
        # Simulate each stage
        stages_to_simulate = [
            (AnalysisStage.INITIALIZATION, "Initializing agents", 2.0),
            (AnalysisStage.DOCUMENT_PROCESSING, "Processing document", 1.5),
            (AnalysisStage.CC_AGENT_1_ANALYSIS, "CC Agent 1 analyzing", 5.0),
            (AnalysisStage.CC_AGENT_2_ANALYSIS, "CC Agent 2 analyzing", 5.0),
            (AnalysisStage.RA_AGENT_ASSESSMENT, "RA Agent assessing", 3.0),
            (AnalysisStage.CONSOLIDATION, "Consolidating results", 1.0)
        ]
        
        for stage, description, duration in stages_to_simulate:
            tracker.start_stage(stage, description)
            
            # Simulate progress within stage
            for progress in [25, 50, 75, 100]:
                time.sleep(duration / 4)  # Simulate work
                tracker.update_stage_progress(stage, progress, f"{description} - {progress}%")
            
            tracker.complete_stage(stage, f"{description} completed")
        
        tracker.complete_analysis()
        
        # Display final progress summary
        print("3. Final progress summary:")
        summary = tracker.get_detailed_progress()
        
        print(f"   Overall Progress: {summary['overall_progress']}%")
        print(f"   Total Elapsed Time: {summary['performance_metrics']['total_elapsed_time']:.1f}s")
        print(f"   Completed Stages: {summary['performance_metrics']['completed_stages']}")
        print(f"   Average Stage Duration: {summary['performance_metrics']['average_stage_duration']:.1f}s")
        
        return True
        
    except Exception as e:
        print(f"Progress tracking demo failed: {str(e)}")
        return False


def demonstrate_error_handling():
    """Demonstrate error handling and recovery."""
    print("\n" + "=" * 60)
    print("DEMO: Error Handling and Recovery")
    print("=" * 60)
    
    try:
        # Create session with error scenarios
        print("1. Testing error scenarios...")
        session = AnalysisSession()
        
        session.start_session()
        
        # Simulate various error conditions
        session.add_warning("Model availability check took longer than expected")
        session.add_error("Temporary model timeout", {
            "model": "deepseek-r1:8b",
            "timeout_duration": 30,
            "retry_attempted": True
        })
        
        session.add_warning("GDPR knowledge base query returned partial results")
        session.add_error("Network connectivity issue", {
            "endpoint": "model_api",
            "error_code": "TIMEOUT",
            "retry_count": 2
        })
        
        # Test session failure
        session.fail_session("Critical model failure", {
            "model": "qwq:32b",
            "error_type": "MODEL_UNAVAILABLE",
            "fallback_attempted": False
        })
        
        print("2. Error summary:")
        print(f"   Session Status: {session.status.value}")
        print(f"   Total Errors: {len(session.errors)}")
        print(f"   Total Warnings: {len(session.warnings)}")
        
        print("3. Error details:")
        for i, error in enumerate(session.errors, 1):
            print(f"   Error {i}: {error['error']}")
            print(f"     Stage: {error['stage']}")
            print(f"     Time: {error['timestamp']}")
            if error['details']:
                print(f"     Details: {error['details']}")
        
        print("4. Warning details:")
        for i, warning in enumerate(session.warnings, 1):
            print(f"   Warning {i}: {warning}")
        
        return True
        
    except Exception as e:
        print(f"Error handling demo failed: {str(e)}")
        return False


def main():
    """Run all demonstrations."""
    print("Agent Orchestration System Demo")
    print("=" * 60)
    print("This demo showcases the multi-agent compliance checker orchestration system.")
    print("Features demonstrated:")
    print("• Concurrent agent execution")
    print("• Session management and tracking")
    print("• Progress monitoring and callbacks")
    print("• Error handling and recovery")
    print("• Feedback loop coordination")
    print()
    
    # Run demonstrations
    demos = [
        ("Session Management", demonstrate_session_management),
        ("Progress Tracking", demonstrate_progress_tracking),
        ("Error Handling", demonstrate_error_handling),
        ("Basic Orchestration", demonstrate_basic_orchestration)  # Run last as it's most complex
    ]
    
    results = []
    
    for demo_name, demo_func in demos:
        print(f"\nRunning {demo_name} demo...")
        try:
            success = demo_func()
            results.append((demo_name, success))
            if success:
                print(f"✓ {demo_name} demo completed successfully")
            else:
                print(f"✗ {demo_name} demo failed")
        except Exception as e:
            print(f"✗ {demo_name} demo failed with exception: {str(e)}")
            results.append((demo_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("DEMO SUMMARY")
    print("=" * 60)
    
    successful = sum(1 for _, success in results if success)
    total = len(results)
    
    for demo_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{demo_name:.<40} {status}")
    
    print(f"\nOverall: {successful}/{total} demos passed")
    
    if successful == total:
        print("🎉 All demonstrations completed successfully!")
        print("\nThe agent orchestration system is ready for use.")
    else:
        print("⚠️  Some demonstrations failed.")
        print("Please check the error messages above and ensure all dependencies are available.")


if __name__ == "__main__":
    main()