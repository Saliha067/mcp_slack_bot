"""
Response formatter for structured incident troubleshooting responses.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class IncidentResponse:
    """Structured incident troubleshooting response."""
    problem_summary: str
    affected_services: List[str]
    time_range: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    analysis: Optional[str] = None
    root_cause: Optional[str] = None
    related_docs: List[str] = None
    severity: Optional[str] = None
    
    def format_slack(self) -> str:
        """Format response for Slack with proper structure."""
        sections = []
        
        # Header with severity
        if self.severity:
            severity_emoji = {
                "critical": "🔴",
                "high": "🟠", 
                "medium": "🟡",
                "low": "🟢"
            }.get(self.severity.lower(), "ℹ️")
            sections.append(f"{severity_emoji} **{self.severity.upper()} SEVERITY**\n")
        
        # Problem Summary
        sections.append(f"**🔍 Problem Summary**\n{self.problem_summary}\n")
        
        # Affected Services
        if self.affected_services:
            services = "\n".join([f"  • {svc}" for svc in self.affected_services])
            sections.append(f"**🎯 Affected Services**\n{services}\n")
        
        # Time Range
        if self.time_range:
            sections.append(f"**⏰ Time Range**\n{self.time_range}\n")
        
        # Metrics Summary
        if self.metrics:
            metrics_str = "\n".join([f"  • `{k}`: {v}" for k, v in self.metrics.items()])
            sections.append(f"📊 **Metrics Summary**\n{metrics_str}\n")
        
        # Analysis
        if self.analysis:
            sections.append(f"� **Analysis**\n{self.analysis}\n")
        
        # Root Cause / Findings
        if self.root_cause:
            sections.append(f"⚠️ **Findings**\n{self.root_cause}\n")
        
        # Related Documentation
        if self.related_docs:
            docs = "\n".join([f"  • {doc}" for doc in self.related_docs])
            sections.append(f"📚 **Related Documentation**\n{docs}\n")
        
        return "\n".join(sections)


class ResponseFormatter:
    """Format bot responses with proper structure."""
    
    @staticmethod
    def format_incident_response(
        problem: str,
        services: List[str],
        time_range: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        analysis: Optional[str] = None,
        root_cause: Optional[str] = None,
        related_docs: Optional[List[str]] = None,
        severity: Optional[str] = None
    ) -> str:
        """Create a structured incident response."""
        response = IncidentResponse(
            problem_summary=problem,
            affected_services=services,
            time_range=time_range,
            metrics=metrics,
            analysis=analysis,
            root_cause=root_cause,
            related_docs=related_docs or [],
            severity=severity
        )
        return response.format_slack()
    
    @staticmethod
    def format_clarification_needed(questions: List[str]) -> str:
        """Format response when clarification is needed."""
        questions_str = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
        return f"**❓ I need some clarification to help you better:**\n\n{questions_str}"
    
    @staticmethod
    def format_runbook_guidance(runbook_name: str, steps: List[str]) -> str:
        """Format runbook-guided troubleshooting steps."""
        steps_str = "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)])
        return f"**📖 Following runbook: {runbook_name}**\n\n{steps_str}"
    
    @staticmethod
    def format_escalation(reason: str, contact: str) -> str:
        """Format escalation recommendation."""
        return f"**⬆️ ESCALATION RECOMMENDED**\n\n**Reason:** {reason}\n**Contact:** {contact}\n\nRefer to incident response checklist for escalation procedures."


# Example usage
if __name__ == "__main__":
    # Example incident response
    response = ResponseFormatter.format_incident_response(
        problem="High latency in OpenSearch prod-logs cluster",
        services=["OpenSearch prod-logs", "Log aggregation pipeline"],
        time_range="2024-11-08 14:00:00 to 2024-11-08 15:00:00 (1 hour)",
        metrics={
            "Query latency (p95)": "1,234ms (threshold: 500ms)",
            "JVM heap usage": "87% (threshold: 85%)",
            "CPU usage": "92%"
        },
        analysis="JVM heap pressure combined with high query volume. Old generation GC occurring every 2 minutes.",
        root_cause="Memory pressure from large aggregation queries during peak hours.",
        related_docs=[
            "docs/runbooks/opensearch-high-latency.md",
            "docs/architecture/cluster-topology.md"
        ],
        severity="high"
    )
    
    print(response)
