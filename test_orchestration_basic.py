#!/usr/bin/env python3
"""
Basic test of the orchestration system components without full integration.
"""

from compliance_checker.orchestration.session import AnalysisSession, SessionStatus
from compliance_checker.orchestration.progress import ProgressTracker, AnalysisStage
from compliance_checker.models.document import SpecificationDocument, Requirement
from compliance_checker.models.report import ComplianceReport, FinalComplianceReport, ComplianceFinding, ComplianceStatus, SeverityLevel


def test_session_management():
    """Test session management functionality."""
    print("Testing Session Management...")
    
    # Create session
    session = AnalysisSession()
    print(f"✓ Created session: {session.session_id}")
    
    # Test lifecycle
    session.start_session()
    print(f"✓ Started session: {session.status.value}")
    
    # Create sample document
    requirements = [
        Requirement(
            id="REQ-001",
            text="The system shall collect user personal data only with explicit consent",
            section="privacy",
            category="privacy"
        )
    ]
    
    document = SpecificationDocument(
        content="Test document content",
        metadata={"test": "metadata"},
        document_id="test-doc",
        filename="test.txt",
        requirements=requirements
    )
    
    session.set_document(document)
    print(f"✓ Set document: {session.progress_percentage}% progress")
    
    # Simulate CC agent execution
    session.start_cc_agents()
    
    # Add mock reports
    report = ComplianceReport(
        agent_id="cc_agent_1",
        model_used="test-model",
        findings=[],
        overall_assessment="Test assessment",
        confidence_score=0.8
    )
    
    session.add_cc_agent_report("cc_agent_1", report)
    print(f"✓ Added CC agent report: {session.progress_percentage}% progress")
    
    # Complete session
    session.complete_session()
    print(f"✓ Completed session: {session.status.value}")
    
    return True


def test_progress_tracking():
    """Test progress tracking functionality."""
    print("\nTesting Progress Tracking...")
    
    # Create progress tracker
    tracker = ProgressTracker()
    print("✓ Created progress tracker")
    
    # Start analysis
    tracker.start_analysis()
    print("✓ Started analysis tracking")
    
    # Simulate stages
    stages = [
        AnalysisStage.INITIALIZATION,
        AnalysisStage.DOCUMENT_PROCESSING,
        AnalysisStage.CC_AGENT_1_ANALYSIS
    ]
    
    for stage in stages:
        tracker.start_stage(stage, f"Processing {stage.value}")
        tracker.update_stage_progress(stage, 50.0, "Halfway done")
        tracker.complete_stage(stage, f"Completed {stage.value}")
        print(f"✓ Completed stage: {stage.value} - Overall: {tracker.overall_progress:.1f}%")
    
    # Complete analysis
    tracker.complete_analysis()
    print(f"✓ Analysis completed: {tracker.overall_progress}%")
    
    return True


def test_data_models():
    """Test data model functionality."""
    print("\nTesting Data Models...")
    
    # Test ComplianceFinding
    finding = ComplianceFinding(
        requirement_id="REQ-001",
        requirement_text="Test requirement",
        compliance_status=ComplianceStatus.NON_COMPLIANT,
        gdpr_articles=["Article 6"],
        reasoning="Test reasoning",
        severity=SeverityLevel.HIGH,
        recommendations=["Test recommendation"],
        confidence_score=0.8
    )
    print(f"✓ Created compliance finding: {finding.compliance_status.value}")
    
    # Test ComplianceReport
    report = ComplianceReport(
        agent_id="cc_agent_1",
        model_used="test-model",
        findings=[finding],
        overall_assessment="Test assessment",
        confidence_score=0.8
    )
    print(f"✓ Created compliance report: {len(report.findings)} findings")
    
    # Test FinalComplianceReport
    final_report = FinalComplianceReport(
        consolidated_findings=[finding],
        overall_compliance_status="Test status",
        confidence_score=0.85,
        source_reports=["cc_agent_1"]
    )
    print(f"✓ Created final report: {len(final_report.consolidated_findings)} consolidated findings")
    
    # Test summary methods
    summary = final_report.get_compliance_summary()
    print(f"✓ Generated summary: {summary['compliance_percentage']:.1f}% compliant")
    
    return True


def main():
    """Run all basic tests."""
    print("Agent Orchestration System - Basic Component Tests")
    print("=" * 60)
    
    tests = [
        ("Session Management", test_session_management),
        ("Progress Tracking", test_progress_tracking),
        ("Data Models", test_data_models)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
            if success:
                print(f"✓ {test_name} test completed successfully")
            else:
                print(f"✗ {test_name} test failed")
        except Exception as e:
            print(f"✗ {test_name} test failed with exception: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    successful = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{test_name:.<40} {status}")
    
    print(f"\nOverall: {successful}/{total} tests passed")
    
    if successful == total:
        print("🎉 All basic component tests passed!")
        print("\nThe orchestration system components are working correctly.")
    else:
        print("⚠️  Some tests failed.")
        print("Please check the error messages above.")
    
    return successful == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)