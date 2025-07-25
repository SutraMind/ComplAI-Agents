#!/usr/bin/env python3
"""
Demo script for RA_Agent (Report Assessor Agent) functionality.

This script demonstrates the key capabilities of the RA_Agent:
1. Report assessment and consolidation
2. Conflict resolution between CC_Agent reports
3. Confidence scoring for final reports
4. Feedback generation for CC_Agents
"""

import sys
import logging
from typing import List
from unittest.mock import Mock

# Add the project root to the path
sys.path.append('.')

from compliance_checker.agents.ra_agent import RAAgent
from compliance_checker.models.report import (
    ComplianceReport, ComplianceFinding, ComplianceStatus, SeverityLevel
)
from compliance_checker.llm.multi_agent_client import (
    MultiAgentLLMClient, ChainOfThoughtResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_mock_llm_client():
    """Create a mock LLM client for demonstration."""
    client = Mock(spec=MultiAgentLLMClient)
    client.verify_model_availability.return_value = {"qwq:32b": True}
    client.generate.return_value = Mock(success=True, content="Test response", error=None)
    
    # Mock chain-of-thought responses for conflict resolution
    def mock_cot_response(prompt, agent_type, system_prompt=None, temperature=0.2):
        if "CONFLICT RESOLUTION" in prompt:
            return ChainOfThoughtResponse(
                reasoning_steps=[
                    "Analyzed conflicting findings from different agents",
                    "Evaluated evidence quality and GDPR article references",
                    "Applied conservative resolution strategy",
                    "Determined most restrictive assessment is appropriate",
                    "Generated consolidated reasoning and recommendations"
                ],
                conclusion='{"resolved_finding": {"compliance_status": "non_compliant", "severity": "high", "gdpr_articles": ["Article 32", "Article 25"], "consolidated_reasoning": "After careful analysis of both assessments, the authentication system lacks critical security measures required by GDPR Article 32. While basic authentication exists, the absence of multi-factor authentication and proper password policies creates significant compliance risks.", "recommendations": ["Implement multi-factor authentication immediately", "Establish strong password policies", "Add account lockout mechanisms", "Conduct security audit of authentication system"], "confidence_score": 0.85}}',
                confidence_score=0.85,
                raw_response="Conflict resolution analysis complete",
                model="qwq:32b",
                success=True
            )
        elif "FEEDBACK GENERATION" in prompt:
            return ChainOfThoughtResponse(
                reasoning_steps=[
                    "Analyzed target agent's report quality and thoroughness",
                    "Compared findings with other agent reports",
                    "Identified areas for improvement in analysis approach"
                ],
                conclusion='{"overall_feedback": "Good analysis with clear reasoning, but could benefit from more comprehensive GDPR article coverage", "improvement_suggestions": ["Include more specific GDPR article references", "Provide more detailed risk assessment", "Consider additional security measures"], "strengths": ["Clear identification of security gaps", "Well-structured reasoning"], "priority_areas": ["gdpr_coverage", "risk_assessment"]}',
                confidence_score=0.75,
                raw_response="Feedback generation complete",
                model="qwq:32b",
                success=True
            )
        else:
            return ChainOfThoughtResponse(
                reasoning_steps=["Generic analysis step"],
                conclusion="Generic conclusion",
                confidence_score=0.6,
                raw_response="Generic response",
                model="qwq:32b",
                success=True
            )
    
    client.execute_chain_of_thought.side_effect = mock_cot_response
    return client


def create_sample_reports() -> List[ComplianceReport]:
    """Create sample conflicting compliance reports for demonstration."""
    
    # Report 1: More restrictive assessment
    finding1 = ComplianceFinding(
        requirement_id="REQ_AUTH_001",
        requirement_text="The system shall implement secure user authentication mechanisms compliant with GDPR requirements",
        compliance_status=ComplianceStatus.NON_COMPLIANT,
        gdpr_articles=["Article 32", "Article 25"],
        reasoning="The current authentication system lacks multi-factor authentication and proper password policies. This creates significant security vulnerabilities that violate GDPR Article 32 requirements for appropriate technical measures.",
        severity=SeverityLevel.HIGH,
        recommendations=[
            "Implement multi-factor authentication",
            "Enforce strong password policies with complexity requirements",
            "Add account lockout mechanisms after failed attempts",
            "Implement session timeout controls"
        ],
        confidence_score=0.88,
        model_used="deepseek-r1:8b"
    )
    
    report1 = ComplianceReport(
        agent_id="cc_agent_1",
        model_used="deepseek-r1:8b",
        findings=[finding1],
        overall_assessment="Critical GDPR compliance violations identified in authentication system",
        confidence_score=0.88,
        document_id="auth_spec_001",
        document_filename="authentication_requirements.pdf",
        processing_time=18.5,
        total_requirements_analyzed=12,
        iteration_number=1
    )
    
    # Report 2: More permissive assessment
    finding2 = ComplianceFinding(
        requirement_id="REQ_AUTH_001",
        requirement_text="The system shall implement secure user authentication mechanisms compliant with GDPR requirements",
        compliance_status=ComplianceStatus.PARTIALLY_COMPLIANT,
        gdpr_articles=["Article 32"],
        reasoning="The authentication system has basic security measures in place including password requirements and user account management. While improvements could be made, the current implementation provides a reasonable level of security for GDPR compliance.",
        severity=SeverityLevel.MEDIUM,
        recommendations=[
            "Consider implementing additional security layers",
            "Review and update password policies periodically",
            "Monitor authentication logs for suspicious activity"
        ],
        confidence_score=0.72,
        model_used="gemma3:27b"
    )
    
    report2 = ComplianceReport(
        agent_id="cc_agent_2",
        model_used="gemma3:27b",
        findings=[finding2],
        overall_assessment="Partial GDPR compliance with opportunities for enhancement",
        confidence_score=0.72,
        document_id="auth_spec_001",
        document_filename="authentication_requirements.pdf",
        processing_time=14.2,
        total_requirements_analyzed=12,
        iteration_number=1
    )
    
    return [report1, report2]


def demonstrate_ra_agent():
    """Demonstrate RA_Agent capabilities."""
    print("=" * 80)
    print("RA_AGENT (REPORT ASSESSOR AGENT) DEMONSTRATION")
    print("=" * 80)
    
    # Initialize RA_Agent
    print("\n1. INITIALIZING RA_AGENT")
    print("-" * 40)
    
    mock_client = create_mock_llm_client()
    ra_agent = RAAgent(llm_client=mock_client, agent_id="demo_ra_agent")
    
    status = ra_agent.get_status()
    print(f"Agent ID: {status['agent_id']}")
    print(f"Model: {status['model_name']}")
    print(f"Status: {status['status']}")
    print(f"Conflict Resolution Strategy: {status['conflict_resolution_strategy']}")
    print(f"Feedback Enabled: {status['feedback_enabled']}")
    
    # Create sample reports
    print("\n2. SAMPLE COMPLIANCE REPORTS")
    print("-" * 40)
    
    reports = create_sample_reports()
    
    for i, report in enumerate(reports, 1):
        print(f"\nReport {i} (Agent: {report.agent_id}):")
        print(f"  Model: {report.model_used}")
        print(f"  Overall Assessment: {report.overall_assessment}")
        print(f"  Confidence: {report.confidence_score:.2f}")
        print(f"  Findings: {len(report.findings)}")
        
        finding = report.findings[0]
        print(f"  Finding Status: {finding.compliance_status.value}")
        print(f"  Severity: {finding.severity.value}")
        print(f"  GDPR Articles: {', '.join(finding.gdpr_articles)}")
    
    # Demonstrate conflict identification
    print("\n3. CONFLICT IDENTIFICATION")
    print("-" * 40)
    
    conflicts = ra_agent._identify_conflicts(reports)
    print(f"Conflicts identified: {len(conflicts)}")
    
    for conflict in conflicts:
        print(f"  - {conflict['type']} for requirement {conflict['requirement_id']}")
        print(f"    Agents: {', '.join(conflict['agents'])}")
        if conflict['type'] == 'status_conflict':
            print(f"    Statuses: {', '.join(conflict['statuses'])}")
        elif conflict['type'] == 'severity_conflict':
            print(f"    Severities: {', '.join(conflict['severities'])}")
    
    # Demonstrate report assessment
    print("\n4. REPORT ASSESSMENT AND CONSOLIDATION")
    print("-" * 40)
    
    final_report = ra_agent.assess_reports(reports)
    
    print(f"Consolidated Findings: {len(final_report.consolidated_findings)}")
    print(f"Overall Status: {final_report.overall_compliance_status}")
    print(f"Final Confidence Score: {final_report.confidence_score:.2f}")
    print(f"Processing Time: {final_report.total_processing_time:.3f}s")
    print(f"Source Reports: {', '.join(final_report.source_reports)}")
    
    print(f"\nConsolidation Notes:")
    for line in final_report.consolidation_notes.split('\n'):
        print(f"  {line}")
    
    # Show consolidated findings
    print(f"\nConsolidated Findings:")
    for finding in final_report.consolidated_findings:
        print(f"  Requirement: {finding.requirement_id}")
        print(f"  Status: {finding.compliance_status.value}")
        print(f"  Severity: {finding.severity.value}")
        print(f"  Confidence: {finding.confidence_score:.2f}")
        print(f"  Model Used: {finding.model_used}")
        print(f"  GDPR Articles: {', '.join(finding.gdpr_articles)}")
        print(f"  Recommendations: {len(finding.recommendations)} items")
        print()
    
    # Demonstrate feedback generation
    print("5. FEEDBACK GENERATION")
    print("-" * 40)
    
    feedback_list = ra_agent.generate_feedback(reports)
    
    print(f"Feedback generated for {len(feedback_list)} agents:")
    
    for feedback in feedback_list:
        print(f"\nFeedback for {feedback['target_agent_id']}:")
        print(f"  Type: {feedback['feedback_type']}")
        print(f"  Iteration: {feedback['iteration_number']}")
        print(f"  Confidence: {feedback['confidence_score']:.2f}")
        print(f"  Overall Feedback: {feedback['feedback_text']}")
        
        if feedback.get('strengths'):
            print(f"  Strengths: {', '.join(feedback['strengths'])}")
        
        if feedback.get('improvement_suggestions'):
            print(f"  Improvement Suggestions:")
            for suggestion in feedback['improvement_suggestions']:
                print(f"    - {suggestion}")
        
        if feedback.get('priority_areas'):
            print(f"  Priority Areas: {', '.join(feedback['priority_areas'])}")
    
    print("\n" + "=" * 80)
    print("RA_AGENT DEMONSTRATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    try:
        demonstrate_ra_agent()
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}")
        raise