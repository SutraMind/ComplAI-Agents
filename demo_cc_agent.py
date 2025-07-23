#!/usr/bin/env python3
"""
Demo script for CC_Agent (Compliance Checker Agent) functionality.

This script demonstrates how to use the CC_Agent to analyze specification documents
for GDPR compliance using chain-of-thought reasoning.
"""

import json
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import required modules
from compliance_checker.agents.cc_agent import CCAgent
from compliance_checker.models.document import SpecificationDocument, Requirement, DocumentSection
from compliance_checker.models.gdpr import GDPRArticle
from compliance_checker.llm.multi_agent_client import MultiAgentLLMClient
from compliance_checker.knowledge.gdpr_knowledge_base import GDPRKnowledgeBase


def create_sample_document() -> SpecificationDocument:
    """Create a sample specification document for testing."""
    
    requirements = [
        Requirement(
            id="req_001",
            text="The system shall collect user email addresses, full names, and phone numbers during account registration",
            section="user_management",
            category="data",
            metadata={
                "keywords": ["email", "personal data", "registration", "phone number"],
                "gdpr_relevant": True,
                "priority": "high"
            }
        ),
        Requirement(
            id="req_002", 
            text="User passwords must be encrypted using AES-256 encryption and stored securely",
            section="security",
            category="security",
            metadata={
                "keywords": ["password", "encryption", "security", "storage"],
                "gdpr_relevant": False,
                "priority": "critical"
            }
        ),
        Requirement(
            id="req_003",
            text="The application shall provide users with the ability to delete their account and all associated personal data",
            section="user_management", 
            category="functional",
            metadata={
                "keywords": ["delete account", "personal data", "user rights", "data deletion"],
                "gdpr_relevant": True,
                "priority": "medium"
            }
        ),
        Requirement(
            id="req_004",
            text="User activity logs shall be retained for 2 years for security monitoring purposes",
            section="logging",
            category="data",
            metadata={
                "keywords": ["activity logs", "retention", "monitoring", "data retention"],
                "gdpr_relevant": True,
                "priority": "medium"
            }
        ),
        Requirement(
            id="req_005",
            text="The system shall obtain explicit user consent before processing personal data for marketing purposes",
            section="marketing",
            category="data",
            metadata={
                "keywords": ["consent", "marketing", "personal data", "explicit consent"],
                "gdpr_relevant": True,
                "priority": "high"
            }
        )
    ]
    
    sections = [
        DocumentSection(
            id="user_mgmt_section",
            title="User Management",
            content="This section describes user registration, authentication, and account management requirements.",
            level=1
        ),
        DocumentSection(
            id="security_section", 
            title="Security Requirements",
            content="This section outlines security measures for data protection and system security.",
            level=1
        ),
        DocumentSection(
            id="marketing_section",
            title="Marketing and Communications",
            content="Requirements for marketing communications and user consent management.",
            level=1
        )
    ]
    
    return SpecificationDocument(
        content="""
        E-Commerce Platform Specification Document
        
        This document outlines the requirements for a new e-commerce platform
        that will handle customer data, process payments, and provide marketing
        communications to users.
        
        The system must comply with GDPR regulations for data protection
        and privacy rights.
        """,
        metadata={
            "filename": "ecommerce_platform_spec.pdf",
            "document_type": "software_specification",
            "version": "1.0",
            "created_date": "2024-01-15",
            "author": "Product Team"
        },
        requirements=requirements,
        sections=sections,
        document_id="ecommerce_spec_001",
        filename="ecommerce_platform_spec.pdf"
    )


def create_mock_gdpr_knowledge_base():
    """Create a mock GDPR knowledge base for demonstration."""
    
    class MockGDPRKnowledgeBase:
        def __init__(self):
            self.articles = {
                "6": GDPRArticle(
                    article_number="6",
                    title="Lawfulness of processing",
                    content="Processing shall be lawful only if and to the extent that at least one of the following applies: (a) the data subject has given consent...",
                    keywords=["lawful basis", "consent", "contract", "legitimate interest"]
                ),
                "7": GDPRArticle(
                    article_number="7", 
                    title="Conditions for consent",
                    content="Where processing is based on consent, the controller shall be able to demonstrate that the data subject has consented...",
                    keywords=["consent", "demonstrate", "withdraw", "freely given"]
                ),
                "13": GDPRArticle(
                    article_number="13",
                    title="Information to be provided where personal data are collected from the data subject",
                    content="Where personal data relating to a data subject are collected from the data subject, the controller shall provide...",
                    keywords=["privacy notice", "information", "transparency", "data subject"]
                ),
                "17": GDPRArticle(
                    article_number="17",
                    title="Right to erasure ('right to be forgotten')",
                    content="The data subject shall have the right to obtain from the controller the erasure of personal data...",
                    keywords=["right to erasure", "delete", "forgotten", "personal data"]
                ),
                "5": GDPRArticle(
                    article_number="5",
                    title="Principles relating to processing of personal data",
                    content="Personal data shall be processed lawfully, fairly and in a transparent manner...",
                    keywords=["data minimization", "purpose limitation", "retention", "principles"]
                )
            }
        
        def query_relevant_articles(self, query: str, top_k: int = 5):
            """Mock method to return relevant articles based on query."""
            query_lower = query.lower()
            relevant_articles = []
            
            # Simple keyword matching for demo
            for article in self.articles.values():
                if any(keyword in query_lower for keyword in article.keywords):
                    relevant_articles.append(article)
            
            return relevant_articles[:top_k]
    
    return MockGDPRKnowledgeBase()


def create_mock_llm_client():
    """Create a mock LLM client for demonstration."""
    
    class MockMultiAgentLLMClient:
        def __init__(self):
            self.available_models = {
                "deepseek-r1:8b": True,
                "gemma3:27b": True,
                "qwq:32b": True
            }
        
        def verify_model_availability(self, models=None):
            if models is None:
                return self.available_models
            return {model: self.available_models.get(model, False) for model in models}
        
        def generate(self, prompt, model, **kwargs):
            class MockResponse:
                def __init__(self):
                    self.success = True
                    self.content = "Mock LLM response"
                    self.error = None
            return MockResponse()
        
        def execute_chain_of_thought(self, prompt, agent_type, **kwargs):
            """Mock chain-of-thought analysis with realistic responses."""
            
            # Analyze the prompt to provide contextual responses
            if "email" in prompt.lower() and "registration" in prompt.lower():
                return self._create_registration_analysis()
            elif "password" in prompt.lower() and "encryption" in prompt.lower():
                return self._create_password_analysis()
            elif "delete" in prompt.lower() and "account" in prompt.lower():
                return self._create_deletion_analysis()
            elif "activity logs" in prompt.lower() and "retention" in prompt.lower():
                return self._create_retention_analysis()
            elif "consent" in prompt.lower() and "marketing" in prompt.lower():
                return self._create_consent_analysis()
            else:
                return self._create_default_analysis()
        
        def _create_registration_analysis(self):
            from compliance_checker.llm.multi_agent_client import ChainOfThoughtResponse
            
            return ChainOfThoughtResponse(
                reasoning_steps=[
                    "Identified collection of personal data: email addresses, full names, and phone numbers",
                    "Checked GDPR Article 6 for lawful basis - registration likely qualifies as contract performance (6(1)(b))",
                    "Article 13 requires privacy notice to be provided at data collection",
                    "Data minimization principle (Article 5) - need to verify all collected data is necessary",
                    "No explicit consent mechanism mentioned for data processing",
                    "Missing information about data retention periods and user rights"
                ],
                conclusion=json.dumps({
                    "compliance_status": "partially_compliant",
                    "severity": "medium",
                    "gdpr_articles_referenced": ["Article 6", "Article 13", "Article 5"],
                    "issues_identified": [
                        "No privacy notice mentioned at registration",
                        "Data retention period not specified",
                        "User rights information not provided"
                    ],
                    "recommendations": [
                        "Add privacy notice during registration process",
                        "Specify data retention periods for collected information",
                        "Implement mechanism to inform users of their rights",
                        "Consider data minimization - verify all fields are necessary"
                    ]
                }),
                confidence_score=0.82,
                raw_response="Detailed analysis of user registration requirement...",
                model="deepseek-r1:8b",
                success=True
            )
        
        def _create_password_analysis(self):
            from compliance_checker.llm.multi_agent_client import ChainOfThoughtResponse
            
            return ChainOfThoughtResponse(
                reasoning_steps=[
                    "Identified password encryption requirement using AES-256",
                    "Passwords are sensitive authentication data requiring protection",
                    "AES-256 encryption meets GDPR security requirements (Article 32)",
                    "Technical and organizational measures are being implemented",
                    "No direct personal data processing - authentication credential protection"
                ],
                conclusion=json.dumps({
                    "compliance_status": "compliant",
                    "severity": "low",
                    "gdpr_articles_referenced": ["Article 32"],
                    "issues_identified": [],
                    "recommendations": [
                        "Document encryption implementation details",
                        "Ensure secure key management practices",
                        "Consider additional security measures like salting"
                    ]
                }),
                confidence_score=0.95,
                raw_response="Analysis of password encryption requirement...",
                model="deepseek-r1:8b",
                success=True
            )
        
        def _create_deletion_analysis(self):
            from compliance_checker.llm.multi_agent_client import ChainOfThoughtResponse
            
            return ChainOfThoughtResponse(
                reasoning_steps=[
                    "Identified account deletion functionality with personal data removal",
                    "This directly implements GDPR Article 17 - Right to erasure",
                    "Requirement covers both account and 'all associated personal data'",
                    "Comprehensive data deletion is a key GDPR compliance requirement",
                    "Implementation appears to meet right to be forgotten obligations"
                ],
                conclusion=json.dumps({
                    "compliance_status": "compliant",
                    "severity": "low",
                    "gdpr_articles_referenced": ["Article 17", "Article 12"],
                    "issues_identified": [],
                    "recommendations": [
                        "Ensure deletion covers all data stores and backups",
                        "Implement confirmation mechanism for deletion requests",
                        "Document data deletion procedures",
                        "Consider retention of minimal data for legal compliance"
                    ]
                }),
                confidence_score=0.88,
                raw_response="Analysis of account deletion requirement...",
                model="deepseek-r1:8b",
                success=True
            )
        
        def _create_retention_analysis(self):
            from compliance_checker.llm.multi_agent_client import ChainOfThoughtResponse
            
            return ChainOfThoughtResponse(
                reasoning_steps=[
                    "Identified 2-year retention period for user activity logs",
                    "Security monitoring is a legitimate interest under Article 6(1)(f)",
                    "Retention period must be justified and proportionate (Article 5)",
                    "2 years may be excessive for activity logs depending on purpose",
                    "Need to balance security needs with data minimization principle",
                    "Users should be informed about log retention in privacy notice"
                ],
                conclusion=json.dumps({
                    "compliance_status": "partially_compliant",
                    "severity": "medium",
                    "gdpr_articles_referenced": ["Article 5", "Article 6", "Article 13"],
                    "issues_identified": [
                        "2-year retention period may be excessive",
                        "Legitimate interest assessment not documented",
                        "User notification about log retention unclear"
                    ],
                    "recommendations": [
                        "Conduct legitimate interest assessment for log retention",
                        "Consider shorter retention period if adequate for security",
                        "Include log retention information in privacy notice",
                        "Implement automated deletion after retention period"
                    ]
                }),
                confidence_score=0.75,
                raw_response="Analysis of activity log retention requirement...",
                model="deepseek-r1:8b",
                success=True
            )
        
        def _create_consent_analysis(self):
            from compliance_checker.llm.multi_agent_client import ChainOfThoughtResponse
            
            return ChainOfThoughtResponse(
                reasoning_steps=[
                    "Identified explicit consent requirement for marketing data processing",
                    "Marketing processing requires consent as lawful basis (Article 6(1)(a))",
                    "Consent must be freely given, specific, informed, and unambiguous (Article 7)",
                    "Explicit consent is correctly identified for marketing purposes",
                    "Users must be able to withdraw consent easily (Article 7(3))",
                    "Requirement demonstrates good GDPR compliance understanding"
                ],
                conclusion=json.dumps({
                    "compliance_status": "compliant",
                    "severity": "low",
                    "gdpr_articles_referenced": ["Article 6", "Article 7", "Article 21"],
                    "issues_identified": [],
                    "recommendations": [
                        "Implement clear consent collection mechanism",
                        "Provide easy consent withdrawal option",
                        "Document consent records for compliance",
                        "Consider granular consent for different marketing types"
                    ]
                }),
                confidence_score=0.92,
                raw_response="Analysis of marketing consent requirement...",
                model="deepseek-r1:8b",
                success=True
            )
        
        def _create_default_analysis(self):
            from compliance_checker.llm.multi_agent_client import ChainOfThoughtResponse
            
            return ChainOfThoughtResponse(
                reasoning_steps=[
                    "Analyzed requirement for GDPR compliance",
                    "Checked relevant GDPR articles",
                    "Assessed compliance status"
                ],
                conclusion=json.dumps({
                    "compliance_status": "unclear",
                    "severity": "medium",
                    "gdpr_articles_referenced": ["Article 6"],
                    "issues_identified": ["Requires manual review"],
                    "recommendations": ["Conduct detailed compliance assessment"]
                }),
                confidence_score=0.60,
                raw_response="General analysis response...",
                model="deepseek-r1:8b",
                success=True
            )
    
    return MockMultiAgentLLMClient()


def demonstrate_cc_agent():
    """Demonstrate CC_Agent functionality with sample data."""
    
    print("=" * 80)
    print("CC_Agent (Compliance Checker Agent) Demonstration")
    print("=" * 80)
    print()
    
    # Create mock dependencies
    print("1. Setting up mock dependencies...")
    llm_client = create_mock_llm_client()
    gdpr_kb = create_mock_gdpr_knowledge_base()
    
    # Create CC_Agent instances
    print("2. Creating CC_Agent instances...")
    cc_agent_1 = CCAgent(
        agent_id="cc_agent_1",
        model_name="deepseek-r1:8b",
        llm_client=llm_client,
        gdpr_knowledge_base=gdpr_kb
    )
    
    cc_agent_2 = CCAgent(
        agent_id="cc_agent_2", 
        model_name="gemma3:27b",
        llm_client=llm_client,
        gdpr_knowledge_base=gdpr_kb
    )
    
    print(f"   - CC_Agent_1 status: {cc_agent_1.get_status()['status']}")
    print(f"   - CC_Agent_2 status: {cc_agent_2.get_status()['status']}")
    print()
    
    # Create sample document
    print("3. Creating sample specification document...")
    document = create_sample_document()
    print(f"   - Document: {document.filename}")
    print(f"   - Requirements: {len(document.requirements)}")
    print(f"   - Sections: {len(document.sections)}")
    print()
    
    # Analyze with CC_Agent_1
    print("4. Analyzing with CC_Agent_1 (deepseek-r1:8b)...")
    report_1 = cc_agent_1.analyze_compliance(document)
    
    print(f"   - Agent ID: {report_1.agent_id}")
    print(f"   - Model: {report_1.model_used}")
    print(f"   - Requirements analyzed: {report_1.total_requirements_analyzed}")
    print(f"   - Findings: {len(report_1.findings)}")
    print(f"   - Confidence: {report_1.confidence_score:.2f}")
    print(f"   - Processing time: {report_1.processing_time:.2f}s")
    print()
    
    # Display findings summary
    print("   Findings Summary:")
    for finding in report_1.findings:
        status_emoji = {
            "compliant": "✅",
            "non_compliant": "❌", 
            "partially_compliant": "⚠️",
            "unclear": "❓"
        }.get(finding.compliance_status.value, "❓")
        
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢"
        }.get(finding.severity.value, "🟡")
        
        print(f"     {status_emoji} {severity_emoji} {finding.requirement_id}: {finding.compliance_status.value}")
        if finding.recommendations:
            print(f"        Recommendations: {len(finding.recommendations)} items")
    print()
    
    # Analyze with CC_Agent_2
    print("5. Analyzing with CC_Agent_2 (gemma3:27b)...")
    report_2 = cc_agent_2.analyze_compliance(document)
    
    print(f"   - Agent ID: {report_2.agent_id}")
    print(f"   - Model: {report_2.model_used}")
    print(f"   - Requirements analyzed: {report_2.total_requirements_analyzed}")
    print(f"   - Findings: {len(report_2.findings)}")
    print(f"   - Confidence: {report_2.confidence_score:.2f}")
    print(f"   - Processing time: {report_2.processing_time:.2f}s")
    print()
    
    # Compare reports
    print("6. Comparing agent reports...")
    
    # Get compliance statistics
    stats_1 = report_1.get_summary_stats()
    stats_2 = report_2.get_summary_stats()
    
    print("   CC_Agent_1 Statistics:")
    for status, count in stats_1.items():
        if count > 0:
            print(f"     - {status.replace('_', ' ').title()}: {count}")
    
    print("   CC_Agent_2 Statistics:")
    for status, count in stats_2.items():
        if count > 0:
            print(f"     - {status.replace('_', ' ').title()}: {count}")
    print()
    
    # Demonstrate feedback processing
    print("7. Demonstrating feedback processing...")
    feedback = """
    Focus more on data retention requirements and consider Article 17 (right to erasure).
    Also pay attention to consent withdrawal mechanisms for marketing communications.
    """
    
    cc_agent_1.process_feedback(feedback.strip())
    print(f"   - Feedback processed by {cc_agent_1.agent_id}")
    print(f"   - Feedback history length: {len(cc_agent_1.feedback_history)}")
    
    # Re-analyze with feedback
    print("   - Re-analyzing with feedback...")
    report_1_v2 = cc_agent_1.analyze_compliance(document)
    print(f"   - Iteration number: {report_1_v2.iteration_number}")
    print(f"   - New confidence score: {report_1_v2.confidence_score:.2f}")
    print()
    
    # Display detailed finding example
    print("8. Detailed finding example:")
    if report_1.findings:
        example_finding = report_1.findings[0]
        print(f"   Requirement: {example_finding.requirement_id}")
        print(f"   Status: {example_finding.compliance_status.value}")
        print(f"   Severity: {example_finding.severity.value}")
        print(f"   GDPR Articles: {', '.join(example_finding.gdpr_articles)}")
        print(f"   Confidence: {example_finding.confidence_score:.2f}")
        print()
        print("   Reasoning:")
        for line in example_finding.reasoning.split('\n')[:3]:  # Show first 3 lines
            print(f"     {line}")
        if len(example_finding.reasoning.split('\n')) > 3:
            print("     ...")
        print()
        
        if example_finding.recommendations:
            print("   Recommendations:")
            for rec in example_finding.recommendations[:2]:  # Show first 2
                print(f"     - {rec}")
            if len(example_finding.recommendations) > 2:
                print(f"     ... and {len(example_finding.recommendations) - 2} more")
    
    print()
    print("=" * 80)
    print("Demonstration completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        demonstrate_cc_agent()
    except Exception as e:
        logger.error(f"Demonstration failed: {str(e)}")
        raise