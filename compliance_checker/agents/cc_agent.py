"""
CC_Agent (Compliance Checker Agent) implementation for GDPR compliance analysis.
"""

import json
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base import ComplianceCheckerAgent
from ..models.document import SpecificationDocument, Requirement
from ..models.report import ComplianceReport, ComplianceFinding, ComplianceStatus, SeverityLevel
from ..models.gdpr import GDPRArticle
from ..llm.multi_agent_client import MultiAgentLLMClient, AgentType, ChainOfThoughtResponse
from ..knowledge.gdpr_knowledge_base import GDPRKnowledgeBase
from ..exceptions import ModelUnavailableError, DocumentProcessingError


logger = logging.getLogger(__name__)


class CCAgent(ComplianceCheckerAgent):
    """
    Compliance Checker Agent that analyzes specification documents for GDPR compliance.
    
    This agent uses chain-of-thought reasoning to analyze requirements against GDPR regulations
    and generates detailed compliance reports with findings, severity levels, and recommendations.
    """
    
    def __init__(self, 
                 agent_id: str,
                 model_name: str,
                 llm_client: MultiAgentLLMClient,
                 gdpr_knowledge_base: GDPRKnowledgeBase):
        """
        Initialize CC_Agent.
        
        Args:
            agent_id: Unique identifier for this agent (e.g., "cc_agent_1", "cc_agent_2")
            model_name: LLM model to use (deepseek-r1:8b or gemma3:27b)
            llm_client: Multi-agent LLM client for model communication
            gdpr_knowledge_base: GDPR knowledge base for regulation lookup
        """
        super().__init__(model_name, agent_id)
        self.llm_client = llm_client
        self.gdpr_knowledge_base = gdpr_knowledge_base
        
        # Agent-specific configuration
        self.agent_type = AgentType.CC_AGENT_1 if "1" in agent_id else AgentType.CC_AGENT_2
        self.feedback_history: List[str] = []
        self.iteration_count = 0
        
        # Analysis parameters
        self.temperature = 0.1  # Low temperature for consistent analysis
        self.max_gdpr_articles = 10  # Maximum GDPR articles to consider per requirement
        
        # Initialize the agent
        self.initialize()
    
    def initialize(self) -> bool:
        """Initialize the agent and verify model availability."""
        try:
            logger.info(f"Initializing CC_Agent {self.agent_id} with model {self.model_name}")
            
            # Verify model availability
            availability = self.llm_client.verify_model_availability([self.model_name])
            if not availability.get(self.model_name, False):
                raise ModelUnavailableError(f"Model {self.model_name} is not available")
            
            # Test basic functionality
            test_response = self.llm_client.generate(
                prompt="Test prompt for initialization",
                model=self.model_name,
                temperature=self.temperature
            )
            
            if not test_response.success:
                raise ModelUnavailableError(f"Model {self.model_name} failed test: {test_response.error}")
            
            self.status = "ready"
            logger.info(f"CC_Agent {self.agent_id} initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize CC_Agent {self.agent_id}: {str(e)}")
            self.status = "error"
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status and health information."""
        return {
            "agent_id": self.agent_id,
            "model_name": self.model_name,
            "agent_type": self.agent_type.value,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "iteration_count": self.iteration_count,
            "feedback_count": len(self.feedback_history),
            "last_analysis": getattr(self, 'last_analysis_time', None)
        }
    
    def analyze_compliance(self, 
                          document: SpecificationDocument, 
                          gdpr_context: Optional[List[GDPRArticle]] = None) -> ComplianceReport:
        """
        Analyze document for GDPR compliance and generate detailed report.
        
        Args:
            document: Specification document to analyze
            gdpr_context: Optional pre-selected GDPR articles for context
            
        Returns:
            ComplianceReport with detailed findings and recommendations
        """
        start_time = time.time()
        self.last_analysis_time = datetime.now()
        self.iteration_count += 1
        
        logger.info(f"Starting compliance analysis with {self.agent_id} (iteration {self.iteration_count})")
        
        try:
            # Extract requirements from document
            requirements = document.requirements
            if not requirements:
                logger.warning("No requirements found in document")
                return self._create_empty_report(document, "No requirements found in document")
            
            logger.info(f"Analyzing {len(requirements)} requirements")
            
            # Analyze each requirement for GDPR compliance
            findings = []
            for requirement in requirements:
                finding = self._analyze_requirement_compliance(requirement, gdpr_context)
                if finding:
                    findings.append(finding)
            
            # Generate overall assessment
            overall_assessment = self._generate_overall_assessment(findings)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(findings)
            
            # Create compliance report
            report = ComplianceReport(
                agent_id=self.agent_id,
                model_used=self.model_name,
                findings=findings,
                overall_assessment=overall_assessment,
                confidence_score=confidence_score,
                document_id=document.document_id,
                document_filename=document.filename,
                processing_time=time.time() - start_time,
                total_requirements_analyzed=len(requirements),
                iteration_number=self.iteration_count
            )
            
            logger.info(f"Analysis complete: {len(findings)} findings generated")
            return report
            
        except Exception as e:
            logger.error(f"Compliance analysis failed: {str(e)}")
            return self._create_error_report(document, str(e))
    
    def _analyze_requirement_compliance(self, 
                                       requirement: Requirement,
                                       gdpr_context: Optional[List[GDPRArticle]] = None) -> Optional[ComplianceFinding]:
        """
        Analyze a single requirement for GDPR compliance using chain-of-thought reasoning.
        
        Args:
            requirement: Requirement to analyze
            gdpr_context: Optional GDPR articles for context
            
        Returns:
            ComplianceFinding or None if analysis fails
        """
        try:
            # Get relevant GDPR articles if not provided
            if gdpr_context is None:
                gdpr_articles = self._get_relevant_gdpr_articles(requirement)
            else:
                gdpr_articles = gdpr_context[:self.max_gdpr_articles]
            
            if not gdpr_articles:
                logger.debug(f"No relevant GDPR articles found for requirement {requirement.id}")
                return None
            
            # Perform chain-of-thought analysis
            cot_response = self._perform_chain_of_thought_analysis(requirement, gdpr_articles)
            
            if not cot_response.success:
                logger.warning(f"Chain-of-thought analysis failed for {requirement.id}: {cot_response.error}")
                return None
            
            # Parse analysis results
            finding = self._parse_analysis_results(requirement, gdpr_articles, cot_response)
            
            return finding
            
        except Exception as e:
            logger.error(f"Failed to analyze requirement {requirement.id}: {str(e)}")
            return None
    
    def _get_relevant_gdpr_articles(self, requirement: Requirement) -> List[GDPRArticle]:
        """
        Get relevant GDPR articles for a requirement using similarity search.
        
        Args:
            requirement: Requirement to find articles for
            
        Returns:
            List of relevant GDPR articles
        """
        try:
            # Create search query from requirement text and keywords
            search_query = requirement.text
            if requirement.metadata.get('keywords'):
                keywords = ' '.join(requirement.metadata['keywords'])
                search_query = f"{requirement.text} {keywords}"
            
            # Query GDPR knowledge base
            articles = self.gdpr_knowledge_base.query_relevant_articles(
                query=search_query,
                top_k=self.max_gdpr_articles
            )
            
            logger.debug(f"Found {len(articles)} relevant GDPR articles for requirement {requirement.id}")
            return articles
            
        except Exception as e:
            logger.error(f"Failed to get GDPR articles for requirement {requirement.id}: {str(e)}")
            return []
    
    def _perform_chain_of_thought_analysis(self, 
                                          requirement: Requirement,
                                          gdpr_articles: List[GDPRArticle]) -> ChainOfThoughtResponse:
        """
        Perform chain-of-thought analysis of requirement against GDPR articles.
        
        Args:
            requirement: Requirement to analyze
            gdpr_articles: Relevant GDPR articles
            
        Returns:
            ChainOfThoughtResponse with reasoning and conclusion
        """
        # Prepare GDPR context
        gdpr_context = self._format_gdpr_context(gdpr_articles)
        
        # Include feedback from previous iterations
        feedback_context = ""
        if self.feedback_history:
            recent_feedback = self.feedback_history[-2:]  # Use last 2 feedback items
            feedback_context = f"\n\nPrevious feedback to consider:\n{chr(10).join(recent_feedback)}"
        
        # Create analysis prompt
        analysis_prompt = f"""
Analyze the following software requirement for GDPR compliance using systematic reasoning.

REQUIREMENT TO ANALYZE:
ID: {requirement.id}
Category: {requirement.category}
Text: {requirement.text}

RELEVANT GDPR ARTICLES:
{gdpr_context}

ANALYSIS INSTRUCTIONS:
1. Examine the requirement carefully and identify any data processing activities
2. Determine what types of personal data might be involved
3. Check each relevant GDPR article to see if the requirement complies
4. Consider the lawful basis for processing if personal data is involved
5. Identify any potential compliance issues or risks
6. Determine the overall compliance status
7. Suggest specific recommendations for improvement if needed

Please provide your analysis in the following JSON format:
{{
    "reasoning_steps": [
        "Step 1: Analysis of data processing activities...",
        "Step 2: Identification of personal data types...",
        "Step 3: GDPR article compliance check...",
        "Step 4: Lawful basis assessment...",
        "Step 5: Risk identification...",
        "Step 6: Overall compliance determination..."
    ],
    "conclusion": {{
        "compliance_status": "compliant|non_compliant|partially_compliant|unclear",
        "severity": "critical|high|medium|low",
        "gdpr_articles_referenced": ["Article 6", "Article 7", ...],
        "issues_identified": ["Issue 1", "Issue 2", ...],
        "recommendations": ["Recommendation 1", "Recommendation 2", ...]
    }},
    "confidence_score": 0.85
}}{feedback_context}
"""
        
        # Create system prompt
        system_prompt = f"""You are an expert GDPR compliance analyst working as {self.agent_id}. 
Your role is to analyze software requirements for GDPR compliance using systematic chain-of-thought reasoning.

Key principles:
- Be thorough and systematic in your analysis
- Consider all aspects of data processing and privacy rights
- Reference specific GDPR articles in your reasoning
- Provide actionable recommendations
- Be conservative in compliance assessments - when in doubt, flag as non-compliant
- Always respond with valid JSON format

Focus areas:
- Personal data identification and categorization
- Lawful basis for processing
- Data subject rights implementation
- Data protection by design and by default
- Security and breach notification requirements
- International data transfers
- Consent mechanisms and withdrawal"""
        
        # Execute chain-of-thought analysis
        return self.llm_client.execute_chain_of_thought(
            prompt=analysis_prompt,
            agent_type=self.agent_type,
            system_prompt=system_prompt,
            temperature=self.temperature
        )
    
    def _format_gdpr_context(self, gdpr_articles: List[GDPRArticle]) -> str:
        """Format GDPR articles for inclusion in analysis prompt."""
        context_parts = []
        
        for article in gdpr_articles:
            context_part = f"Article {article.article_number}: {article.title}\n"
            context_part += f"Content: {article.content[:500]}..."  # Truncate for prompt length
            if article.keywords:
                context_part += f"\nKeywords: {', '.join(article.keywords)}"
            context_parts.append(context_part)
        
        return "\n\n".join(context_parts)
    
    def _parse_analysis_results(self, 
                               requirement: Requirement,
                               gdpr_articles: List[GDPRArticle],
                               cot_response: ChainOfThoughtResponse) -> ComplianceFinding:
        """
        Parse chain-of-thought analysis results into a ComplianceFinding.
        
        Args:
            requirement: Original requirement
            gdpr_articles: GDPR articles used in analysis
            cot_response: Chain-of-thought response
            
        Returns:
            ComplianceFinding object
        """
        try:
            # Try to parse structured conclusion from response
            conclusion = self._extract_conclusion_from_response(cot_response)
            
            # Map compliance status
            status_mapping = {
                "compliant": ComplianceStatus.COMPLIANT,
                "non_compliant": ComplianceStatus.NON_COMPLIANT,
                "partially_compliant": ComplianceStatus.PARTIALLY_COMPLIANT,
                "unclear": ComplianceStatus.UNCLEAR
            }
            
            compliance_status = status_mapping.get(
                conclusion.get("compliance_status", "unclear").lower(),
                ComplianceStatus.UNCLEAR
            )
            
            # Map severity level
            severity_mapping = {
                "critical": SeverityLevel.CRITICAL,
                "high": SeverityLevel.HIGH,
                "medium": SeverityLevel.MEDIUM,
                "low": SeverityLevel.LOW
            }
            
            severity = severity_mapping.get(
                conclusion.get("severity", "medium").lower(),
                SeverityLevel.MEDIUM
            )
            
            # Create reasoning text from steps
            reasoning = self._format_reasoning_steps(cot_response.reasoning_steps)
            
            # Extract GDPR article references
            gdpr_article_refs = conclusion.get("gdpr_articles_referenced", [])
            if not gdpr_article_refs:
                gdpr_article_refs = [f"Article {article.article_number}" for article in gdpr_articles[:3]]
            
            # Create compliance finding
            finding = ComplianceFinding(
                requirement_id=requirement.id,
                requirement_text=requirement.text,
                compliance_status=compliance_status,
                gdpr_articles=gdpr_article_refs,
                reasoning=reasoning,
                severity=severity,
                recommendations=conclusion.get("recommendations", []),
                confidence_score=cot_response.confidence_score,
                model_used=self.model_name
            )
            
            return finding
            
        except Exception as e:
            logger.error(f"Failed to parse analysis results: {str(e)}")
            # Create fallback finding
            return self._create_fallback_finding(requirement, gdpr_articles, cot_response)
    
    def _extract_conclusion_from_response(self, cot_response: ChainOfThoughtResponse) -> Dict[str, Any]:
        """Extract structured conclusion from chain-of-thought response."""
        try:
            # Try to parse JSON from conclusion
            if cot_response.conclusion:
                conclusion_data = json.loads(cot_response.conclusion)
                if isinstance(conclusion_data, dict) and "conclusion" in conclusion_data:
                    return conclusion_data["conclusion"]
                elif isinstance(conclusion_data, dict):
                    return conclusion_data
            
            # Fallback: parse from raw response
            raw_response = cot_response.raw_response
            if "conclusion" in raw_response.lower():
                # Try to extract JSON block
                import re
                json_match = re.search(r'\{.*"conclusion".*\}', raw_response, re.DOTALL)
                if json_match:
                    json_data = json.loads(json_match.group())
                    return json_data.get("conclusion", {})
            
            # Default fallback
            return {
                "compliance_status": "unclear",
                "severity": "medium",
                "gdpr_articles_referenced": [],
                "issues_identified": [],
                "recommendations": []
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract conclusion: {str(e)}")
            return {
                "compliance_status": "unclear",
                "severity": "medium",
                "gdpr_articles_referenced": [],
                "issues_identified": [],
                "recommendations": []
            }
    
    def _format_reasoning_steps(self, reasoning_steps: List[str]) -> str:
        """Format reasoning steps into readable text."""
        if not reasoning_steps:
            return "No detailed reasoning available."
        
        formatted_steps = []
        for i, step in enumerate(reasoning_steps, 1):
            formatted_steps.append(f"{i}. {step}")
        
        return "\n".join(formatted_steps)
    
    def _create_fallback_finding(self, 
                                requirement: Requirement,
                                gdpr_articles: List[GDPRArticle],
                                cot_response: ChainOfThoughtResponse) -> ComplianceFinding:
        """Create a fallback finding when parsing fails."""
        return ComplianceFinding(
            requirement_id=requirement.id,
            requirement_text=requirement.text,
            compliance_status=ComplianceStatus.UNCLEAR,
            gdpr_articles=[f"Article {article.article_number}" for article in gdpr_articles[:3]],
            reasoning=f"Analysis completed but parsing failed. Raw response: {cot_response.raw_response[:200]}...",
            severity=SeverityLevel.MEDIUM,
            recommendations=["Manual review required due to analysis parsing failure"],
            confidence_score=0.3,
            model_used=self.model_name
        )
    
    def _generate_overall_assessment(self, findings: List[ComplianceFinding]) -> str:
        """Generate overall compliance assessment from findings."""
        if not findings:
            return "No compliance findings generated. Manual review required."
        
        # Count findings by status
        status_counts = {
            ComplianceStatus.COMPLIANT: 0,
            ComplianceStatus.NON_COMPLIANT: 0,
            ComplianceStatus.PARTIALLY_COMPLIANT: 0,
            ComplianceStatus.UNCLEAR: 0
        }
        
        for finding in findings:
            status_counts[finding.compliance_status] += 1
        
        total = len(findings)
        non_compliant = status_counts[ComplianceStatus.NON_COMPLIANT]
        partially_compliant = status_counts[ComplianceStatus.PARTIALLY_COMPLIANT]
        unclear = status_counts[ComplianceStatus.UNCLEAR]
        compliant = status_counts[ComplianceStatus.COMPLIANT]
        
        # Generate assessment
        if non_compliant > 0:
            assessment = f"GDPR compliance issues identified. {non_compliant} non-compliant requirements found out of {total} analyzed."
        elif partially_compliant > 0:
            assessment = f"Partial GDPR compliance. {partially_compliant} requirements need attention out of {total} analyzed."
        elif unclear > 0:
            assessment = f"GDPR compliance unclear for {unclear} requirements out of {total} analyzed. Manual review recommended."
        else:
            assessment = f"All {total} analyzed requirements appear GDPR compliant."
        
        # Add severity information
        critical_findings = [f for f in findings if f.severity == SeverityLevel.CRITICAL]
        high_findings = [f for f in findings if f.severity == SeverityLevel.HIGH]
        
        if critical_findings:
            assessment += f" {len(critical_findings)} critical issues require immediate attention."
        elif high_findings:
            assessment += f" {len(high_findings)} high-priority issues identified."
        
        return assessment
    
    def _calculate_confidence_score(self, findings: List[ComplianceFinding]) -> float:
        """Calculate overall confidence score for the analysis."""
        if not findings:
            return 0.0
        
        # Average confidence scores from individual findings
        total_confidence = sum(finding.confidence_score or 0.5 for finding in findings)
        base_confidence = total_confidence / len(findings)
        
        # Adjust based on feedback iterations (more iterations = higher confidence)
        iteration_bonus = min(0.1 * self.iteration_count, 0.2)
        
        # Adjust based on model reliability (could be model-specific)
        model_reliability = 0.85 if "deepseek" in self.model_name.lower() else 0.80
        
        final_confidence = min(base_confidence * model_reliability + iteration_bonus, 1.0)
        return round(final_confidence, 2)
    
    def process_feedback(self, feedback: str) -> None:
        """
        Process feedback from RA_Agent and adjust analysis approach.
        
        Args:
            feedback: Feedback text from RA_Agent
        """
        logger.info(f"Processing feedback for {self.agent_id}")
        
        # Store feedback for future analysis
        self.feedback_history.append(feedback)
        
        # Keep only recent feedback to avoid prompt bloat
        if len(self.feedback_history) > 5:
            self.feedback_history = self.feedback_history[-5:]
        
        # Log feedback for debugging
        logger.debug(f"Feedback received: {feedback[:100]}...")
        
        # Update status
        self.status = "feedback_processed"
    
    def _create_empty_report(self, document: SpecificationDocument, reason: str) -> ComplianceReport:
        """Create an empty report when no analysis can be performed."""
        return ComplianceReport(
            agent_id=self.agent_id,
            model_used=self.model_name,
            findings=[],
            overall_assessment=f"Analysis could not be completed: {reason}",
            confidence_score=0.0,
            document_id=document.document_id,
            document_filename=document.filename,
            processing_time=0.0,
            total_requirements_analyzed=0,
            iteration_number=self.iteration_count
        )
    
    def _create_error_report(self, document: SpecificationDocument, error: str) -> ComplianceReport:
        """Create an error report when analysis fails."""
        return ComplianceReport(
            agent_id=self.agent_id,
            model_used=self.model_name,
            findings=[],
            overall_assessment=f"Analysis failed due to error: {error}",
            confidence_score=0.0,
            document_id=document.document_id,
            document_filename=document.filename,
            processing_time=0.0,
            total_requirements_analyzed=0,
            iteration_number=self.iteration_count
        )