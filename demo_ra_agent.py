#!/usr/bin/env python3
"""
Demo script for RA_Agent (Report Assessor Agent) functionality.

This script demonstrates the RA_Agent's capabilities including:
- Report assessment and consolidation
- Conflict resolution between CC_Agent reports
- Feedback generation for CC_Agents
- Confidence scoring and overall status generation
"""

import sys
import os
import logging
from datetime import datetime
from typing import List

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from compliance_checker.agents.ra_agent import RAAgent
from compliance_checker.llm.multi_agent_client import MultiAgentLLMClient
from compliance_checker.models.report import (
    ComplianceReport, ComplianceFinding, ComplianceStatus, SeverityLevel
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_reports() -> List[ComplianceReport]:
    """Create sample compliance reports for demonstration."""
    
    # Create conflicting findings for the same requirement
    finding1_auth = ComplianceFinding(
        requirement_id="REQ_AUTH_001",
        requirement_text="The system shall implement secure user authentication with multi-factor authentication support",
        compliance_status=ComplianceStatus.NON_COMPLIANT,
        gdpr_articles=["Article 32", "Article 25"],
        reasoning="The authentication system lacks proper multi-factor authentication implementation. Current password-only authentication is insufficient for protecting personal data as required by GDPR Article 32 (Security of processing). The system does not implement data protection by design principles from Article 25.",
        severity=SeverityLevel.CRITICAL,
        recommendations=[
            "Implement multi-factor authentication (MFA) for all user accounts",
            "Add support for hardware security keys",
            "Implement account lockout mechanisms after failed attempts",
            "Add audit logging for authentication events"
        ],
        confidence_score=0.9,
        model_used="deepseek-r1:8b"
    )
    
    finding2_auth = ComplianceFinding(
        requirement_id="REQ_AUTH_001",
        requirement_text="The system shall implement secure user authentication with multi-factor authentication support",
        compliance_status=ComplianceStatus.PARTIALLY_COMPLIANT,
        gdpr_articles=["Article 32"],
        reasoning="The authentication system has basic security measures in place including password complexity requirements and session management. However, multi-factor authentication is not fully implemented across all user types. The system partially meets GDPR Article 32 requirements but needs enhancement.",
        severity=SeverityLevel.HIGH,
        recommendations=[
            "Complete MFA implementation for all user roles",
            "Review and strengthen password policies",
            "Implement additional security monitoring"
        ],
        confidence_score=0.75,
        model_used="gemma3:27b"
    )
    
    # Create non-conflicting findings
    finding1_data = ComplianceFinding(
        requirement_id="REQ_DATA_001",
        requirement_text="The system shall implement data encryption for personal data at rest and in transit",
        compliance_status=ComplianceStatus.COMPLIANT,
        gdpr_articles=["Article 32", "Article 34"],
        reasoning="The system implements AES-256 encryption for data at rest and TLS 1.3 for data in transit. This meets the technical and organizational measures required by GDPR Article 32 for ensuring appropriate security of personal data.",
        severity=SeverityLevel.LOW,
        recommendations=[
            "Maintain current encryption standards",
            "Regular security audits of encryption implementation"
        ],
        confidence_score=0.85,
        model_used="deepseek-r1:8b"
    )
    
    finding2_consent = ComplianceFinding(
        requirement_id="REQ_CONSENT_001",
        requirement_text="The system shall provide mechanisms for users to give, withdraw, and manage consent for data processing",
        compliance_status=ComplianceStatus.NON_COMPLIANT,
        gdpr_articles=["Article 7", "Article 17"],
        reasoning="The system lacks proper consent management mechanisms. Users cannot easily withdraw consent, and there is no clear audit trail of consent decisions. This violates GDPR Article 7 (Conditions for consent) and Article 17 (Right to erasure).",
        severity=SeverityLevel.HIGH,
        recommendations=[
            "Implement comprehensive consent management system",
            "Add consent withdrawal mechanisms",
            "Create audit trail for consent decisions",
            "Implement data deletion capabilities"
        ],
        confidence_score=0.8,
        model_used="gemma3:27b"
    )
    
    # Create compliance reports
    report1 = ComplianceReport(
        agent_id="cc_agent_1",
        model_used="deepseek-r1:8b",
        findings=[finding1_auth, finding1_data],
        overall_assessment="Critical GDPR compliance issues identified. The authentication system requires immediate attention due to lack of multi-factor authentication. Data encryption implementation is compliant.",
        confidence_score=0.87,
        document_id="spec_demo_001",
        document_filename="demo_specification.pdf",
        processing_time=18.5,
        total_requirements_analyzed=15,
        iteration_number=1,
        timestamp=datetime.now()
    )
    
    report2 = ComplianceReport(
        agent_id="cc_agent_2",
        model_used="gemma3:27b",
        findings=[finding2_auth, finding2_consent],
        overall_assessment="Mixed GDPR compliance results. Authentication system shows partial compliance but needs improvement. Consent management system requires significant work to meet GDPR requirements.",
        confidence_score=0.77,
        document_id="spec_demo_001",
        document_filename="demo_specification.pdf",
        processing_time=22.3,
        total_requirements_analyzed=15,
        iteration_number=1,
        timestamp=datetime.now()
    )
    
    return [report1, report2]


def demonstrate_ra_agent():
    """Demonstrate RA_Agent functionality."""
    
    print("=" * 80)
    print("RA_AGENT (REPORT ASSESSOR AGENT) DEMONSTRATION")
    print("=" * 80)
    
    try:
        # Initialize LLM client
        print("\n1. Initializing Multi-Agent LLM Client...")
        llm_client = MultiAgentLLMClient()
        
        # Check model availability
        print("   Checking model availability...")
        availability = llm_client.verify_model_availability(["qwq:32b"])
        if not availability.get("qwq:32b", False):
            print("   ⚠️  Warning: qwq:32b model not available. Demo will use mock responses.")
            # Continue with demo using mock client
        else:
            print("   ✅ qwq:32b model is available")
        
        # Initialize RA_Agent
        print("\n2. Initializing RA_Agent...")
        ra_agent = RAAgent(llm_client=llm_client)
        
        # Display agent status
        status = ra_agent.get_status()
        print(f"   Agent ID: {status['agent_id']}")
        print(f"   Model: {status['model_name']}")
        print(f"   Status: {status['status']}")
        print(f"   Conflict Resolution Strategy: {status['conflict_resolution_strategy']}")
        print(f"   Feedback Enabled: {status['feedback_enabled']}")
        
        # Create sample reports
        print("\n3. Creating Sample Compliance Reports...")
        reports = create_sample_reports()
        
        print(f"   Created {len(reports)} compliance reports:")
        for report in reports:
            print(f"   - {report.agent_id} ({report.model_used}): {len(report.findings)} findings")
            print(f"     Overall Assessment: {report.overall_assessment[:100]}...")
            print(f"     Confidence: {report.confidence_score:.2f}")
        
        # Demonstrate conflict identification
        print("\n4. Identifying Conflicts Between Reports...")
        conflicts = ra_agent._identify_conflicts(reports)
        
        print(f"   Found {len(conflicts)} conflicts:")
        for conflict in conflicts:
            print(f"   - {conflict['type']} in requirement {conflict['requirement_id']}")
            print(f"     Agents: {', '.join(conflict['agents'])}")
            if conflict['type'] == 'status_conflict':
                print(f"     Conflicting statuses: {', '.join(conflict['statuses'])}")
        
        # Demonstrate report assessment
        print("\n5. Performing Report Assessment and Consolidation...")
        print("   This may take a moment as the RA_Agent processes the reports...")
        
        final_report = ra_agent.assess_reports(reports)
        
        print(f"   ✅ Assessment completed in {final_report.total_processing_time:.2f} seconds")
        print(f"   Consolidated {len(final_report.consolidated_findings)} findings")
        print(f"   Final confidence score: {final_report.confidence_score:.2f}")
        
        # Display consolidated findings
        print("\n6. Consolidated Findings Summary:")
        print("-" * 60)
        
        for i, finding in enumerate(final_report.consolidated_findings, 1):
            print(f"   Finding {i}: {finding.requirement_id}")
            print(f"   Status: {finding.compliance_status.value.upper()}")
            print(f"   Severity: {finding.severity.value.upper()}")
            print(f"   GDPR Articles: {', '.join(finding.gdpr_articles)}")
            print(f"   Confidence: {finding.confidence_score:.2f}")
            print(f"   Reasoning: {finding.reasoning[:150]}...")
            print(f"   Recommendations: {len(finding.recommendations)} items")
            print("-" * 60)
        
        # Display overall assessment
        print("\n7. Overall Compliance Assessment:")
        print(f"   {final_report.overall_compliance_status}")
        
        # Display consolidation notes
        print("\n8. Consolidation Process Notes:")
        print(f"   {final_report.consolidation_notes}")
        
        # Demonstrate feedback generation
        print("\n9. Generating Feedback for CC_Agents...")
        feedback_list = ra_agent.generate_feedback(reports)
        
        print(f"   Generated feedback for {len(feedback_list)} agents:")
        for feedback in feedback_list:
            print(f"\n   Feedback for {feedback['target_agent_id']}:")
            print(f"   Type: {feedback['feedback_type']}")
            print(f"   Iteration: {feedback['iteration_number']}")
            print(f"   Confidence: {feedback['confidence_score']:.2f}")
            print(f"   Feedback: {feedback['feedback_text'][:200]}...")
            
            if feedback.get('improvement_suggestions'):
                print(f"   Improvement Suggestions:")
                for suggestion in feedback['improvement_suggestions'][:3]:
                    print(f"   - {suggestion}")
            
            if feedback.get('strengths'):
                print(f"   Strengths Identified:")
                for strength in feedback['strengths'][:2]:
                    print(f"   - {strength}")
        
        # Display final statistics
        print("\n10. Final Statistics:")
        compliance_summary = final_report.get_compliance_summary()
        print(f"    Total Findings: {compliance_summary['total_findings']}")
        print(f"    Non-Compliant: {compliance_summary['non_compliant_count']}")
        print(f"    Compliance Rate: {compliance_summary['compliance_percentage']:.1f}%")
        print(f"    Critical Issues: {compliance_summary['critical_issues']}")
        print(f"    Overall Status: {compliance_summary['overall_status']}")
        
        print("\n" + "=" * 80)
        print("RA_AGENT DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        return final_report, feedback_list
        
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}")
        print(f"\n❌ Demo failed with error: {str(e)}")
        print("\nThis might be due to:")
        print("- Ollama server not running")
        print("- Required models not installed")
        print("- Network connectivity issues")
        print("\nPlease check your Ollama setup and try again.")
        return None, None


def demonstrate_conflict_resolution_strategies():
    """Demonstrate different conflict resolution strategies."""
    
    print("\n" + "=" * 80)
    print("CONFLICT RESOLUTION STRATEGIES DEMONSTRATION")
    print("=" * 80)
    
    try:
        llm_client = MultiAgentLLMClient()
        reports = create_sample_reports()
        
        strategies = ["conservative", "liberal", "balanced"]
        
        for strategy in strategies:
            print(f"\n--- Testing {strategy.upper()} Strategy ---")
            
            ra_agent = RAAgent(llm_client=llm_client)
            ra_agent.conflict_resolution_strategy = strategy
            
            final_report = ra_agent.assess_reports(reports)
            
            print(f"Strategy: {strategy}")
            print(f"Consolidated Findings: {len(final_report.consolidated_findings)}")
            print(f"Confidence Score: {final_report.confidence_score:.2f}")
            
            # Show how conflicts were resolved
            auth_finding = next(
                (f for f in final_report.consolidated_findings if f.requirement_id == "REQ_AUTH_001"),
                None
            )
            
            if auth_finding:
                print(f"Auth Requirement Resolution:")
                print(f"  Status: {auth_finding.compliance_status.value}")
                print(f"  Severity: {auth_finding.severity.value}")
                print(f"  Confidence: {auth_finding.confidence_score:.2f}")
        
    except Exception as e:
        print(f"Strategy demonstration failed: {str(e)}")


if __name__ == "__main__":
    # Run the main demonstration
    final_report, feedback_list = demonstrate_ra_agent()
    
    # Run conflict resolution strategies demonstration
    if final_report is not None:
        demonstrate_conflict_resolution_strategies()
    
    print("\nDemo completed. Check the logs above for detailed results.")