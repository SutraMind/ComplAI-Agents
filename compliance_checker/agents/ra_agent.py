"""
RA_Agent (Report Assessor Agent) implementation for consolidating compliance reports.
"""

import json
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .base import ReportAssessorAgent
from ..models.report import (
    ComplianceReport, FinalComplianceReport, ComplianceFinding, 
    ComplianceStatus, SeverityLevel
)
from ..llm.multi_agent_client import MultiAgentLLMClient, AgentType, ChainOfThoughtResponse
from ..exceptions import ModelUnavailableError


logger = logging.getLogger(__name__)


class RAAgent(ReportAssessorAgent):
    """
    Report Assessor Agent that consolidates and assesses compliance reports from CC_Agents.
    
    This agent uses the qwq:32b model to compare reports, resolve conflicts, generate
    consolidated findings, and provide feedback to CC_Agents for iterative improvement.
    """
    
    def __init__(self, 
                 llm_client: MultiAgentLLMClient,
                 agent_id: str = "ra_agent",
                 model_name: str = "qwq:32b"):
        """
        Initialize RA_Agent.
        
        Args:
            llm_client: Multi-agent LLM client for model communication
            agent_id: Unique identifier for this agent
            model_name: LLM model to use (default: qwq:32b)
        """
        super().__init__(model_name, agent_id)
        self.llm_client = llm_client
        self.agent_type = AgentType.RA_AGENT
        
        # Assessment parameters
        self.temperature = 0.2  # Slightly higher for creative consolidation
        self.confidence_threshold = 0.7  # Minimum confidence for findings
        self.conflict_resolution_strategy = "conservative"  # conservative, liberal, or balanced
        
        # Feedback generation settings
        self.feedback_enabled = True
        self.max_feedback_iterations = 3
        self.feedback_history: List[Dict[str, Any]] = []
        
        # Initialize the agent
        self.initialize()
    
    def initialize(self) -> bool:
        """Initialize the agent and verify model availability."""
        try:
            logger.info(f"Initializing RA_Agent {self.agent_id} with model {self.model_name}")
            
            # Verify model availability
            availability = self.llm_client.verify_model_availability([self.model_name])
            if not availability.get(self.model_name, False):
                raise ModelUnavailableError(f"Model {self.model_name} is not available")
            
            # Test basic functionality
            test_response = self.llm_client.generate(
                prompt="Test prompt for RA_Agent initialization",
                model=self.model_name,
                temperature=self.temperature
            )
            
            if not test_response.success:
                raise ModelUnavailableError(f"Model {self.model_name} failed test: {test_response.error}")
            
            self.status = "ready"
            logger.info(f"RA_Agent {self.agent_id} initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize RA_Agent {self.agent_id}: {str(e)}")
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
            "feedback_enabled": self.feedback_enabled,
            "feedback_history_count": len(self.feedback_history),
            "conflict_resolution_strategy": self.conflict_resolution_strategy,
            "last_assessment": getattr(self, 'last_assessment_time', None)
        }    
def assess_reports(self, reports: List[ComplianceReport]) -> FinalComplianceReport:
        """
        Assess and consolidate multiple compliance reports into a final report.
        
        Args:
            reports: List of compliance reports from CC_Agents
            
        Returns:
            FinalComplianceReport with consolidated findings and assessment
        """
        start_time = time.time()
        self.last_assessment_time = datetime.now()
        
        logger.info(f"Starting report assessment with {len(reports)} reports")
        
        try:
            if not reports:
                return self._create_empty_final_report("No reports provided for assessment")
            
            if len(reports) < 2:
                logger.warning("Only one report provided, performing single-report assessment")
                return self._assess_single_report(reports[0])
            
            # Step 1: Compare reports and identify conflicts
            conflicts = self._identify_conflicts(reports)
            logger.info(f"Identified {len(conflicts)} conflicts between reports")
            
            # Step 2: Resolve conflicts using chain-of-thought reasoning
            resolved_findings = self._resolve_conflicts(reports, conflicts)
            
            # Step 3: Consolidate unique findings from all reports
            consolidated_findings = self._consolidate_findings(reports, resolved_findings)
            logger.info(f"Consolidated {len(consolidated_findings)} findings")
            
            # Step 4: Generate overall compliance assessment
            overall_status = self._generate_overall_status(consolidated_findings)
            
            # Step 5: Calculate confidence score for final report
            confidence_score = self._calculate_final_confidence(reports, consolidated_findings)
            
            # Step 6: Generate consolidation notes
            consolidation_notes = self._generate_consolidation_notes(reports, conflicts, resolved_findings)
            
            # Create final report
            final_report = FinalComplianceReport(
                consolidated_findings=consolidated_findings,
                overall_compliance_status=overall_status,
                confidence_score=confidence_score,
                source_reports=[report.agent_id for report in reports],
                consolidation_notes=consolidation_notes,
                document_id=reports[0].document_id if reports else None,
                document_filename=reports[0].document_filename if reports else None,
                total_processing_time=time.time() - start_time,
                feedback_iterations=len(self.feedback_history)
            )
            
            logger.info(f"Report assessment complete: {len(consolidated_findings)} consolidated findings")
            return final_report
            
        except Exception as e:
            logger.error(f"Report assessment failed: {str(e)}")
            return self._create_error_final_report(str(e))
    
    def _identify_conflicts(self, reports: List[ComplianceReport]) -> List[Dict[str, Any]]:
        """
        Identify conflicts between compliance reports.
        
        Args:
            reports: List of compliance reports to compare
            
        Returns:
            List of conflict descriptions
        """
        conflicts = []
        
        # Group findings by requirement ID
        findings_by_req = {}
        for report in reports:
            for finding in report.findings:
                req_id = finding.requirement_id
                if req_id not in findings_by_req:
                    findings_by_req[req_id] = []
                findings_by_req[req_id].append((report.agent_id, finding))
        
        # Check for conflicts in each requirement
        for req_id, agent_findings in findings_by_req.items():
            if len(agent_findings) < 2:
                continue  # No conflict possible with single finding
            
            # Check for status conflicts
            statuses = [finding.compliance_status for _, finding in agent_findings]
            if len(set(statuses)) > 1:
                conflicts.append({
                    "type": "status_conflict",
                    "requirement_id": req_id,
                    "agents": [agent_id for agent_id, _ in agent_findings],
                    "statuses": [status.value for status in statuses],
                    "findings": [finding for _, finding in agent_findings]
                })
            
            # Check for severity conflicts
            severities = [finding.severity for _, finding in agent_findings]
            if len(set(severities)) > 1:
                conflicts.append({
                    "type": "severity_conflict",
                    "requirement_id": req_id,
                    "agents": [agent_id for agent_id, _ in agent_findings],
                    "severities": [severity.value for severity in severities],
                    "findings": [finding for _, finding in agent_findings]
                })
            
            # Check for reasoning conflicts (significant differences)
            reasonings = [finding.reasoning for _, finding in agent_findings]
            if self._has_reasoning_conflict(reasonings):
                conflicts.append({
                    "type": "reasoning_conflict",
                    "requirement_id": req_id,
                    "agents": [agent_id for agent_id, _ in agent_findings],
                    "reasonings": reasonings,
                    "findings": [finding for _, finding in agent_findings]
                })
        
        return conflicts
    
    def _has_reasoning_conflict(self, reasonings: List[str]) -> bool:
        """
        Determine if there's a significant conflict in reasoning approaches.
        
        Args:
            reasonings: List of reasoning texts to compare
            
        Returns:
            True if significant conflict exists
        """
        if len(reasonings) < 2:
            return False
        
        # Simple heuristic: check for contradictory keywords
        contradictory_pairs = [
            ("compliant", "non-compliant"),
            ("secure", "insecure"),
            ("adequate", "inadequate"),
            ("sufficient", "insufficient"),
            ("meets", "fails"),
            ("satisfies", "violates")
        ]
        
        for reasoning1 in reasonings:
            for reasoning2 in reasonings:
                if reasoning1 == reasoning2:
                    continue
                
                reasoning1_lower = reasoning1.lower()
                reasoning2_lower = reasoning2.lower()
                
                for word1, word2 in contradictory_pairs:
                    if word1 in reasoning1_lower and word2 in reasoning2_lower:
                        return True
                    if word2 in reasoning1_lower and word1 in reasoning2_lower:
                        return True
        
        return False    d
ef _resolve_conflicts(self, 
                          reports: List[ComplianceReport], 
                          conflicts: List[Dict[str, Any]]) -> List[ComplianceFinding]:
        """
        Resolve conflicts between reports using chain-of-thought reasoning.
        
        Args:
            reports: Original compliance reports
            conflicts: List of identified conflicts
            
        Returns:
            List of resolved compliance findings
        """
        resolved_findings = []
        
        for conflict in conflicts:
            try:
                resolved_finding = self._resolve_single_conflict(conflict)
                if resolved_finding:
                    resolved_findings.append(resolved_finding)
            except Exception as e:
                logger.error(f"Failed to resolve conflict for requirement {conflict.get('requirement_id')}: {str(e)}")
                # Use fallback resolution
                fallback_finding = self._fallback_conflict_resolution(conflict)
                if fallback_finding:
                    resolved_findings.append(fallback_finding)
        
        return resolved_findings
    
    def _resolve_single_conflict(self, conflict: Dict[str, Any]) -> Optional[ComplianceFinding]:
        """
        Resolve a single conflict using chain-of-thought reasoning.
        
        Args:
            conflict: Conflict information
            
        Returns:
            Resolved ComplianceFinding or None if resolution fails
        """
        conflict_type = conflict["type"]
        requirement_id = conflict["requirement_id"]
        findings = conflict["findings"]
        
        # Prepare conflict analysis prompt
        conflict_prompt = self._create_conflict_resolution_prompt(conflict)
        
        # Execute chain-of-thought analysis
        cot_response = self.llm_client.execute_chain_of_thought(
            prompt=conflict_prompt,
            agent_type=self.agent_type,
            system_prompt=self._get_conflict_resolution_system_prompt(),
            temperature=self.temperature
        )
        
        if not cot_response.success:
            logger.warning(f"Conflict resolution failed for {requirement_id}: {cot_response.error}")
            return None
        
        # Parse resolution results
        return self._parse_conflict_resolution(conflict, cot_response)
    
    def _create_conflict_resolution_prompt(self, conflict: Dict[str, Any]) -> str:
        """Create a prompt for resolving a specific conflict."""
        conflict_type = conflict["type"]
        requirement_id = conflict["requirement_id"]
        findings = conflict["findings"]
        
        # Format findings for comparison
        findings_text = ""
        for i, finding in enumerate(findings, 1):
            findings_text += f"\nFinding {i} (Agent: {conflict['agents'][i-1]}):\n"
            findings_text += f"  Status: {finding.compliance_status.value}\n"
            findings_text += f"  Severity: {finding.severity.value}\n"
            findings_text += f"  Reasoning: {finding.reasoning[:300]}...\n"
            findings_text += f"  GDPR Articles: {', '.join(finding.gdpr_articles)}\n"
            findings_text += f"  Recommendations: {'; '.join(finding.recommendations[:2])}\n"
        
        prompt = f"""
CONFLICT RESOLUTION TASK

Conflict Type: {conflict_type}
Requirement ID: {requirement_id}

CONFLICTING FINDINGS:
{findings_text}

RESOLUTION INSTRUCTIONS:
1. Analyze each finding carefully and identify the source of disagreement
2. Evaluate the quality and accuracy of reasoning in each finding
3. Consider the GDPR articles referenced and their relevance
4. Apply the {self.conflict_resolution_strategy} resolution strategy
5. Determine the most accurate compliance status and severity
6. Provide consolidated reasoning that addresses the conflict
7. Generate comprehensive recommendations

Resolution Strategy Guidelines:
- Conservative: When in doubt, choose the more restrictive/non-compliant assessment
- Liberal: Give benefit of doubt and choose more permissive assessment
- Balanced: Weigh evidence equally and choose most supported conclusion

Please provide your resolution in the following JSON format:
{{
    "resolution_reasoning": [
        "Step 1: Analysis of conflict source...",
        "Step 2: Evaluation of finding quality...",
        "Step 3: GDPR article relevance assessment...",
        "Step 4: Application of resolution strategy...",
        "Step 5: Final determination..."
    ],
    "resolved_finding": {{
        "compliance_status": "compliant|non_compliant|partially_compliant|unclear",
        "severity": "critical|high|medium|low",
        "gdpr_articles": ["Article X", "Article Y"],
        "consolidated_reasoning": "Detailed reasoning for the resolution...",
        "recommendations": ["Recommendation 1", "Recommendation 2"],
        "confidence_score": 0.85,
        "resolution_notes": "Notes about how the conflict was resolved"
    }}
}}
"""
        return prompt
    
    def _get_conflict_resolution_system_prompt(self) -> str:
        """Get system prompt for conflict resolution."""
        return f"""You are an expert GDPR compliance assessor working as the Report Assessor Agent (RA_Agent).

Your role is to resolve conflicts between compliance findings from different CC_Agents by:
1. Carefully analyzing conflicting assessments
2. Applying systematic reasoning to determine the most accurate conclusion
3. Using the {self.conflict_resolution_strategy} resolution strategy
4. Providing clear, well-reasoned consolidated findings

Key principles:
- Prioritize accuracy and thoroughness over speed
- Consider all evidence and reasoning provided
- Reference specific GDPR articles in your analysis
- Provide actionable recommendations
- Maintain high confidence in your resolutions
- Always respond with valid JSON format

Your goal is to produce the most accurate and reliable compliance assessment possible.""" 
   def _parse_conflict_resolution(self, 
                                  conflict: Dict[str, Any], 
                                  cot_response: ChainOfThoughtResponse) -> Optional[ComplianceFinding]:
        """
        Parse conflict resolution results into a ComplianceFinding.
        
        Args:
            conflict: Original conflict information
            cot_response: Chain-of-thought response with resolution
            
        Returns:
            Resolved ComplianceFinding or None if parsing fails
        """
        try:
            # Extract resolution from response
            resolution_data = self._extract_resolution_from_response(cot_response)
            resolved_finding_data = resolution_data.get("resolved_finding", {})
            
            # Get the original finding for reference
            original_finding = conflict["findings"][0]  # Use first finding as template
            
            # Map compliance status
            status_mapping = {
                "compliant": ComplianceStatus.COMPLIANT,
                "non_compliant": ComplianceStatus.NON_COMPLIANT,
                "partially_compliant": ComplianceStatus.PARTIALLY_COMPLIANT,
                "unclear": ComplianceStatus.UNCLEAR
            }
            
            compliance_status = status_mapping.get(
                resolved_finding_data.get("compliance_status", "unclear").lower(),
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
                resolved_finding_data.get("severity", "medium").lower(),
                SeverityLevel.MEDIUM
            )
            
            # Create resolved finding
            resolved_finding = ComplianceFinding(
                requirement_id=original_finding.requirement_id,
                requirement_text=original_finding.requirement_text,
                compliance_status=compliance_status,
                gdpr_articles=resolved_finding_data.get("gdpr_articles", original_finding.gdpr_articles),
                reasoning=resolved_finding_data.get("consolidated_reasoning", "Conflict resolved by RA_Agent"),
                severity=severity,
                recommendations=resolved_finding_data.get("recommendations", []),
                confidence_score=resolved_finding_data.get("confidence_score", 0.8),
                model_used=self.model_name
            )
            
            return resolved_finding
            
        except Exception as e:
            logger.error(f"Failed to parse conflict resolution: {str(e)}")
            return None
    
    def _extract_resolution_from_response(self, cot_response: ChainOfThoughtResponse) -> Dict[str, Any]:
        """Extract resolution data from chain-of-thought response."""
        try:
            # Try to parse JSON from conclusion
            if cot_response.conclusion:
                resolution_data = json.loads(cot_response.conclusion)
                if isinstance(resolution_data, dict):
                    return resolution_data
            
            # Fallback: parse from raw response
            raw_response = cot_response.raw_response
            if "resolved_finding" in raw_response.lower():
                import re
                json_match = re.search(r'\{.*"resolved_finding".*\}', raw_response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            
            # Default fallback
            return {
                "resolved_finding": {
                    "compliance_status": "unclear",
                    "severity": "medium",
                    "gdpr_articles": [],
                    "consolidated_reasoning": "Resolution parsing failed",
                    "recommendations": [],
                    "confidence_score": 0.5
                }
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract resolution: {str(e)}")
            return {
                "resolved_finding": {
                    "compliance_status": "unclear",
                    "severity": "medium",
                    "gdpr_articles": [],
                    "consolidated_reasoning": "Resolution parsing failed",
                    "recommendations": [],
                    "confidence_score": 0.5
                }
            }
    
    def _fallback_conflict_resolution(self, conflict: Dict[str, Any]) -> Optional[ComplianceFinding]:
        """
        Provide fallback conflict resolution when chain-of-thought fails.
        
        Args:
            conflict: Conflict information
            
        Returns:
            Fallback resolved finding
        """
        findings = conflict["findings"]
        if not findings:
            return None
        
        # Apply resolution strategy
        if self.conflict_resolution_strategy == "conservative":
            # Choose the most restrictive assessment
            resolved_finding = self._choose_most_restrictive_finding(findings)
        elif self.conflict_resolution_strategy == "liberal":
            # Choose the most permissive assessment
            resolved_finding = self._choose_most_permissive_finding(findings)
        else:  # balanced
            # Choose the finding with highest confidence
            resolved_finding = max(findings, key=lambda f: f.confidence_score or 0.5)
        
        # Update reasoning to indicate fallback resolution
        resolved_finding.reasoning = f"Conflict resolved using {self.conflict_resolution_strategy} strategy (fallback). Original reasoning: {resolved_finding.reasoning[:200]}..."
        resolved_finding.confidence_score = (resolved_finding.confidence_score or 0.5) * 0.8  # Reduce confidence
        
        return resolved_finding
    
    def _choose_most_restrictive_finding(self, findings: List[ComplianceFinding]) -> ComplianceFinding:
        """Choose the most restrictive (non-compliant) finding."""
        # Priority: NON_COMPLIANT > PARTIALLY_COMPLIANT > UNCLEAR > COMPLIANT
        status_priority = {
            ComplianceStatus.NON_COMPLIANT: 0,
            ComplianceStatus.PARTIALLY_COMPLIANT: 1,
            ComplianceStatus.UNCLEAR: 2,
            ComplianceStatus.COMPLIANT: 3
        }
        
        return min(findings, key=lambda f: status_priority.get(f.compliance_status, 2))
    
    def _choose_most_permissive_finding(self, findings: List[ComplianceFinding]) -> ComplianceFinding:
        """Choose the most permissive (compliant) finding."""
        # Priority: COMPLIANT > UNCLEAR > PARTIALLY_COMPLIANT > NON_COMPLIANT
        status_priority = {
            ComplianceStatus.COMPLIANT: 0,
            ComplianceStatus.UNCLEAR: 1,
            ComplianceStatus.PARTIALLY_COMPLIANT: 2,
            ComplianceStatus.NON_COMPLIANT: 3
        }
        
        return min(findings, key=lambda f: status_priority.get(f.compliance_status, 1)) 
   def _consolidate_findings(self, 
                             reports: List[ComplianceReport], 
                             resolved_findings: List[ComplianceFinding]) -> List[ComplianceFinding]:
        """
        Consolidate all findings from reports, including resolved conflicts.
        
        Args:
            reports: Original compliance reports
            resolved_findings: Findings from conflict resolution
            
        Returns:
            List of consolidated findings
        """
        consolidated = []
        resolved_req_ids = {finding.requirement_id for finding in resolved_findings}
        
        # Add resolved findings first
        consolidated.extend(resolved_findings)
        
        # Add non-conflicting findings from reports
        for report in reports:
            for finding in report.findings:
                if finding.requirement_id not in resolved_req_ids:
                    # Check if this requirement already exists from another agent
                    existing_finding = next(
                        (f for f in consolidated if f.requirement_id == finding.requirement_id),
                        None
                    )
                    
                    if existing_finding is None:
                        # Add unique finding
                        consolidated.append(finding)
                    else:
                        # Merge findings for the same requirement
                        merged_finding = self._merge_compatible_findings(existing_finding, finding)
                        # Replace existing with merged
                        consolidated = [f if f.requirement_id != finding.requirement_id else merged_finding 
                                      for f in consolidated]
        
        # Sort by severity and requirement ID
        consolidated.sort(key=lambda f: (
            self._severity_sort_key(f.severity),
            f.requirement_id
        ))
        
        return consolidated
    
    def _merge_compatible_findings(self, 
                                  finding1: ComplianceFinding, 
                                  finding2: ComplianceFinding) -> ComplianceFinding:
        """
        Merge two compatible findings for the same requirement.
        
        Args:
            finding1: First finding
            finding2: Second finding
            
        Returns:
            Merged finding
        """
        # Use the finding with higher confidence as base
        base_finding = finding1 if (finding1.confidence_score or 0) >= (finding2.confidence_score or 0) else finding2
        other_finding = finding2 if base_finding == finding1 else finding1
        
        # Merge GDPR articles
        merged_articles = list(set(base_finding.gdpr_articles + other_finding.gdpr_articles))
        
        # Merge recommendations
        merged_recommendations = list(set(base_finding.recommendations + other_finding.recommendations))
        
        # Combine reasoning
        merged_reasoning = f"{base_finding.reasoning}\n\nAdditional analysis: {other_finding.reasoning[:200]}..."
        
        # Average confidence scores
        merged_confidence = ((base_finding.confidence_score or 0.5) + (other_finding.confidence_score or 0.5)) / 2
        
        return ComplianceFinding(
            requirement_id=base_finding.requirement_id,
            requirement_text=base_finding.requirement_text,
            compliance_status=base_finding.compliance_status,
            gdpr_articles=merged_articles,
            reasoning=merged_reasoning,
            severity=base_finding.severity,
            recommendations=merged_recommendations,
            confidence_score=merged_confidence,
            model_used=f"{base_finding.model_used}, {other_finding.model_used}"
        )
    
    def _severity_sort_key(self, severity: SeverityLevel) -> int:
        """Get sort key for severity level (lower number = higher priority)."""
        severity_order = {
            SeverityLevel.CRITICAL: 0,
            SeverityLevel.HIGH: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.LOW: 3
        }
        return severity_order.get(severity, 2)
    
    def _generate_overall_status(self, consolidated_findings: List[ComplianceFinding]) -> str:
        """
        Generate overall compliance status from consolidated findings.
        
        Args:
            consolidated_findings: List of consolidated findings
            
        Returns:
            Overall compliance status description
        """
        if not consolidated_findings:
            return "No compliance findings available for assessment."
        
        # Count findings by status
        status_counts = {
            ComplianceStatus.COMPLIANT: 0,
            ComplianceStatus.NON_COMPLIANT: 0,
            ComplianceStatus.PARTIALLY_COMPLIANT: 0,
            ComplianceStatus.UNCLEAR: 0
        }
        
        for finding in consolidated_findings:
            status_counts[finding.compliance_status] += 1
        
        total = len(consolidated_findings)
        non_compliant = status_counts[ComplianceStatus.NON_COMPLIANT]
        partially_compliant = status_counts[ComplianceStatus.PARTIALLY_COMPLIANT]
        unclear = status_counts[ComplianceStatus.UNCLEAR]
        compliant = status_counts[ComplianceStatus.COMPLIANT]
        
        # Count critical and high severity issues
        critical_count = len([f for f in consolidated_findings if f.severity == SeverityLevel.CRITICAL])
        high_count = len([f for f in consolidated_findings if f.severity == SeverityLevel.HIGH])
        
        # Generate status description
        if critical_count > 0:
            status = f"CRITICAL GDPR COMPLIANCE ISSUES IDENTIFIED: {critical_count} critical findings require immediate attention. "
        elif non_compliant > 0:
            status = f"GDPR COMPLIANCE VIOLATIONS FOUND: {non_compliant} non-compliant requirements identified. "
        elif high_count > 0:
            status = f"HIGH-PRIORITY GDPR ISSUES: {high_count} high-severity findings require attention. "
        elif partially_compliant > 0:
            status = f"PARTIAL GDPR COMPLIANCE: {partially_compliant} requirements need improvement. "
        elif unclear > 0:
            status = f"GDPR COMPLIANCE UNCLEAR: {unclear} requirements require manual review. "
        else:
            status = f"GDPR COMPLIANT: All {total} analyzed requirements appear compliant. "
        
        # Add summary statistics
        compliance_rate = (compliant / total * 100) if total > 0 else 0
        status += f"Overall compliance rate: {compliance_rate:.1f}% ({compliant}/{total} requirements compliant)."
        
        return status 
   def _calculate_final_confidence(self, 
                                   reports: List[ComplianceReport], 
                                   consolidated_findings: List[ComplianceFinding]) -> float:
        """
        Calculate confidence score for the final consolidated report.
        
        Args:
            reports: Original compliance reports
            consolidated_findings: Consolidated findings
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not consolidated_findings:
            return 0.0
        
        # Base confidence from individual findings
        finding_confidences = [f.confidence_score or 0.5 for f in consolidated_findings]
        base_confidence = sum(finding_confidences) / len(finding_confidences)
        
        # Agreement bonus: higher confidence when agents agree
        agreement_bonus = self._calculate_agreement_bonus(reports)
        
        # Model diversity bonus: higher confidence with different models
        model_diversity_bonus = 0.05 if len(set(r.model_used for r in reports)) > 1 else 0.0
        
        # Consolidation quality bonus
        consolidation_bonus = 0.1 if len(consolidated_findings) > 0 else 0.0
        
        # Combine factors
        final_confidence = min(
            base_confidence + agreement_bonus + model_diversity_bonus + consolidation_bonus,
            1.0
        )
        
        return round(final_confidence, 2)
    
    def _calculate_agreement_bonus(self, reports: List[ComplianceReport]) -> float:
        """Calculate bonus based on agreement between reports."""
        if len(reports) < 2:
            return 0.0
        
        # Compare overall assessments and confidence scores
        confidences = [r.confidence_score for r in reports]
        confidence_variance = max(confidences) - min(confidences)
        
        # Lower variance = higher agreement = higher bonus
        agreement_bonus = max(0.0, 0.15 - confidence_variance)
        
        return agreement_bonus
    
    def _generate_consolidation_notes(self, 
                                     reports: List[ComplianceReport],
                                     conflicts: List[Dict[str, Any]],
                                     resolved_findings: List[ComplianceFinding]) -> str:
        """
        Generate notes about the consolidation process.
        
        Args:
            reports: Original compliance reports
            conflicts: Identified conflicts
            resolved_findings: Resolved findings
            
        Returns:
            Consolidation notes text
        """
        notes = []
        
        # Report summary
        notes.append(f"Consolidated {len(reports)} compliance reports from agents: {', '.join(r.agent_id for r in reports)}")
        
        # Conflict resolution summary
        if conflicts:
            notes.append(f"Resolved {len(conflicts)} conflicts using {self.conflict_resolution_strategy} strategy:")
            for conflict in conflicts[:3]:  # Show first 3 conflicts
                notes.append(f"  - {conflict['type']} for requirement {conflict['requirement_id']}")
            if len(conflicts) > 3:
                notes.append(f"  - ... and {len(conflicts) - 3} more conflicts")
        else:
            notes.append("No conflicts detected between reports")
        
        # Model information
        models_used = list(set(r.model_used for r in reports))
        notes.append(f"Models used: {', '.join(models_used)}")
        
        # Processing statistics
        total_findings = sum(len(r.findings) for r in reports)
        consolidated_count = len(resolved_findings)
        notes.append(f"Processed {total_findings} total findings, consolidated to {consolidated_count} unique findings")
        
        return "\n".join(notes)  
  def generate_feedback(self, reports: List[ComplianceReport]) -> List[Dict[str, Any]]:
        """
        Generate feedback for CC_Agents based on their reports.
        
        Args:
            reports: List of compliance reports to analyze
            
        Returns:
            List of feedback dictionaries for each agent
        """
        if not self.feedback_enabled:
            logger.info("Feedback generation is disabled")
            return []
        
        logger.info(f"Generating feedback for {len(reports)} reports")
        
        feedback_list = []
        
        for report in reports:
            try:
                feedback = self._generate_agent_feedback(report, reports)
                if feedback:
                    feedback_list.append(feedback)
            except Exception as e:
                logger.error(f"Failed to generate feedback for {report.agent_id}: {str(e)}")
                # Add error feedback
                feedback_list.append({
                    "target_agent_id": report.agent_id,
                    "feedback_text": f"Feedback generation failed: {str(e)}",
                    "specific_findings": [],
                    "improvement_suggestions": ["Manual review recommended due to feedback generation failure"],
                    "iteration_number": len(self.feedback_history) + 1,
                    "feedback_type": "error",
                    "confidence_score": 0.0
                })
        
        # Store feedback history
        self.feedback_history.extend(feedback_list)
        
        return feedback_list
    
    def _generate_agent_feedback(self, 
                                target_report: ComplianceReport, 
                                all_reports: List[ComplianceReport]) -> Optional[Dict[str, Any]]:
        """
        Generate feedback for a specific CC_Agent.
        
        Args:
            target_report: Report from the target agent
            all_reports: All reports for comparison
            
        Returns:
            Feedback dictionary or None if generation fails
        """
        # Compare with other reports
        other_reports = [r for r in all_reports if r.agent_id != target_report.agent_id]
        
        # Create feedback generation prompt
        feedback_prompt = self._create_feedback_prompt(target_report, other_reports)
        
        # Execute chain-of-thought feedback generation
        cot_response = self.llm_client.execute_chain_of_thought(
            prompt=feedback_prompt,
            agent_type=self.agent_type,
            system_prompt=self._get_feedback_generation_system_prompt(),
            temperature=self.temperature
        )
        
        if not cot_response.success:
            logger.warning(f"Feedback generation failed for {target_report.agent_id}: {cot_response.error}")
            return None
        
        # Parse feedback results
        return self._parse_feedback_response(target_report, cot_response)
    
    def _create_feedback_prompt(self, 
                               target_report: ComplianceReport, 
                               other_reports: List[ComplianceReport]) -> str:
        """Create a prompt for generating agent feedback."""
        
        # Format target report
        target_summary = f"""
TARGET REPORT (Agent: {target_report.agent_id}, Model: {target_report.model_used}):
- Total findings: {len(target_report.findings)}
- Overall assessment: {target_report.overall_assessment}
- Confidence score: {target_report.confidence_score}
- Processing time: {target_report.processing_time:.2f}s

Key findings:
"""
        
        for finding in target_report.findings[:5]:  # Show first 5 findings
            target_summary += f"  - {finding.requirement_id}: {finding.compliance_status.value} ({finding.severity.value})\n"
        
        # Format comparison reports
        comparison_summary = ""
        for report in other_reports:
            comparison_summary += f"""
COMPARISON REPORT (Agent: {report.agent_id}, Model: {report.model_used}):
- Total findings: {len(report.findings)}
- Confidence score: {report.confidence_score}
- Key differences: [To be analyzed]
"""
        
        prompt = f"""
FEEDBACK GENERATION TASK

Analyze the target agent's compliance report and provide constructive feedback for improvement.

{target_summary}

{comparison_summary}

FEEDBACK ANALYSIS INSTRUCTIONS:
1. Evaluate the quality and thoroughness of the target report
2. Compare findings with other reports to identify gaps or inconsistencies
3. Assess the reasoning quality and GDPR article references
4. Identify areas where analysis could be improved
5. Suggest specific improvements for better compliance assessment
6. Consider the agent's confidence levels and processing approach

Please provide feedback in the following JSON format:
{{
    "analysis_quality": {{
        "thoroughness": "high|medium|low",
        "reasoning_quality": "excellent|good|fair|poor",
        "gdpr_coverage": "comprehensive|adequate|limited",
        "confidence_appropriateness": "well_calibrated|overconfident|underconfident"
    }},
    "specific_findings_feedback": [
        {{
            "requirement_id": "REQ_001",
            "feedback": "Specific feedback about this finding...",
            "suggested_improvement": "Specific suggestion..."
        }}
    ],
    "improvement_suggestions": [
        "Consider more thorough analysis of data processing activities",
        "Include more specific GDPR article references",
        "Improve reasoning clarity and structure"
    ],
    "strengths": [
        "Good identification of critical issues",
        "Clear reasoning structure"
    ],
    "overall_feedback": "Overall assessment and recommendations...",
    "priority_areas": ["area1", "area2", "area3"]
}}
"""
        return prompt
    
    def _get_feedback_generation_system_prompt(self) -> str:
        """Get system prompt for feedback generation."""
        return """You are an expert GDPR compliance mentor working as the Report Assessor Agent (RA_Agent).

Your role is to provide constructive, actionable feedback to CC_Agents to help them improve their compliance analysis quality.

Key principles for feedback:
- Be specific and actionable in your suggestions
- Focus on improving analysis quality and accuracy
- Highlight both strengths and areas for improvement
- Consider the agent's model capabilities and limitations
- Provide examples when possible
- Maintain a supportive and educational tone
- Always respond with valid JSON format

Your goal is to help CC_Agents become more effective at GDPR compliance analysis through targeted feedback."""    def 
_parse_feedback_response(self, 
                                target_report: ComplianceReport, 
                                cot_response: ChainOfThoughtResponse) -> Dict[str, Any]:
        """
        Parse feedback generation response into structured feedback.
        
        Args:
            target_report: Original target report
            cot_response: Chain-of-thought response with feedback
            
        Returns:
            Structured feedback dictionary
        """
        try:
            # Extract feedback from response
            feedback_data = self._extract_feedback_from_response(cot_response)
            
            # Create structured feedback
            feedback = {
                "target_agent_id": target_report.agent_id,
                "feedback_text": feedback_data.get("overall_feedback", "General feedback for improvement"),
                "specific_findings": [
                    f"Requirement {sf.get('requirement_id', 'N/A')}: {sf.get('feedback', 'No specific feedback')}"
                    for sf in feedback_data.get("specific_findings_feedback", [])
                ],
                "improvement_suggestions": feedback_data.get("improvement_suggestions", []),
                "iteration_number": len(self.feedback_history) + 1,
                "feedback_type": "improvement",
                "confidence_score": cot_response.confidence_score,
                "strengths": feedback_data.get("strengths", []),
                "priority_areas": feedback_data.get("priority_areas", []),
                "analysis_quality": feedback_data.get("analysis_quality", {})
            }
            
            return feedback
            
        except Exception as e:
            logger.error(f"Failed to parse feedback response: {str(e)}")
            # Return basic feedback
            return {
                "target_agent_id": target_report.agent_id,
                "feedback_text": "Feedback parsing failed, manual review recommended",
                "specific_findings": [],
                "improvement_suggestions": ["Manual review of analysis quality recommended"],
                "iteration_number": len(self.feedback_history) + 1,
                "feedback_type": "error",
                "confidence_score": 0.3
            }
    
    def _extract_feedback_from_response(self, cot_response: ChainOfThoughtResponse) -> Dict[str, Any]:
        """Extract feedback data from chain-of-thought response."""
        try:
            # Try to parse JSON from conclusion
            if cot_response.conclusion:
                feedback_data = json.loads(cot_response.conclusion)
                if isinstance(feedback_data, dict):
                    return feedback_data
            
            # Fallback: parse from raw response
            raw_response = cot_response.raw_response
            if "improvement_suggestions" in raw_response.lower():
                import re
                json_match = re.search(r'\{.*"improvement_suggestions".*\}', raw_response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            
            # Default fallback
            return {
                "overall_feedback": "Feedback extraction failed, manual review recommended",
                "improvement_suggestions": ["Manual review of analysis quality recommended"],
                "strengths": [],
                "priority_areas": []
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract feedback: {str(e)}")
            return {
                "overall_feedback": "Feedback extraction failed",
                "improvement_suggestions": ["Manual review recommended"],
                "strengths": [],
                "priority_areas": []
            }
    
    def _assess_single_report(self, report: ComplianceReport) -> FinalComplianceReport:
        """
        Assess a single report when only one CC_Agent report is available.
        
        Args:
            report: Single compliance report
            
        Returns:
            FinalComplianceReport based on single report
        """
        logger.info(f"Assessing single report from {report.agent_id}")
        
        # Use findings as-is but add RA_Agent assessment
        consolidated_findings = report.findings.copy()
        
        # Generate overall status
        overall_status = f"Single-agent assessment: {report.overall_assessment}"
        
        # Reduce confidence slightly for single-agent analysis
        confidence_score = max(0.1, report.confidence_score * 0.9)
        
        # Generate consolidation notes
        consolidation_notes = f"Single report assessment from {report.agent_id} using {report.model_used}. Multi-agent validation not available."
        
        return FinalComplianceReport(
            consolidated_findings=consolidated_findings,
            overall_compliance_status=overall_status,
            confidence_score=confidence_score,
            source_reports=[report.agent_id],
            consolidation_notes=consolidation_notes,
            document_id=report.document_id,
            document_filename=report.document_filename,
            total_processing_time=0.1,  # Minimal processing time
            feedback_iterations=0
        )
    
    def _create_empty_final_report(self, reason: str) -> FinalComplianceReport:
        """Create an empty final report when no assessment can be performed."""
        return FinalComplianceReport(
            consolidated_findings=[],
            overall_compliance_status=f"Assessment could not be completed: {reason}",
            confidence_score=0.0,
            source_reports=[],
            consolidation_notes=reason,
            total_processing_time=0.0,
            feedback_iterations=0
        )
    
    def _create_error_final_report(self, error: str) -> FinalComplianceReport:
        """Create an error final report when assessment fails."""
        return FinalComplianceReport(
            consolidated_findings=[],
            overall_compliance_status=f"Assessment failed due to error: {error}",
            confidence_score=0.0,
            source_reports=[],
            consolidation_notes=f"Error during assessment: {error}",
            total_processing_time=0.0,
            feedback_iterations=0
        )