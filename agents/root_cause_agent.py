from strands import Agent
from datetime import datetime


class RootCauseAgent(Agent):
    """
    Root Cause & Fix Agent - Combines log and metric analysis to determine root cause
    """

    def __init__(self):
        super().__init__(name="RootCauseAgent")

    def analyze_root_cause(
        self, log_summary: dict, metric_summary: dict, alert: dict = None
    ) -> dict:
        """
        Analyze root cause based on log and metric summaries

        Returns:
            dict with root_cause, possible_causes, recommended_action, incident_note, thinking_log
        """
        thinking_log = []
        thinking_log.append("Starting root cause analysis")
        thinking_log.append(
            f"Input data - Log events: {len(log_summary.get('key_errors', []))}, Metric anomalies: {len(alert.get('anomalies', []) if alert else [])}"
        )

        # Extract key indicators
        key_errors = log_summary.get("key_errors", [])
        latency_patterns = log_summary.get("latency_patterns", [])
        retry_sequences = log_summary.get("retry_sequences", [])
        unusual_events = log_summary.get("unusual_events", [])

        metric_anomalies = alert.get("anomalies", []) if alert else []

        # Analyze patterns
        possible_causes = []
        confidence_scores = {}

        # Check for timeout issues
        timeout_errors = [e for e in key_errors if e.get("type") == "timeout"]
        if timeout_errors or any(
            a.get("type") == "latency_spike" for a in metric_anomalies
        ):
            possible_causes.append("timeout_configuration")
            confidence_scores["timeout_configuration"] = len(timeout_errors) * 0.3 + (
                0.4
                if any(a.get("type") == "latency_spike" for a in metric_anomalies)
                else 0
            )
            thinking_log.append(
                f"Timeout pattern detected: {len(timeout_errors)} timeout errors, latency spike in metrics"
            )

        # Check for downstream service issues
        high_latency_count = len(
            [p for p in latency_patterns if p.get("latency_ms", 0) > 2000]
        )
        if high_latency_count > 0 or retry_sequences:
            possible_causes.append("downstream_service_degradation")
            confidence_scores["downstream_service_degradation"] = min(
                high_latency_count * 0.2 + len(retry_sequences) * 0.3, 1.0
            )
            thinking_log.append(
                f"Downstream issues detected: {high_latency_count} high latency events, {len(retry_sequences)} retry sequences"
            )

        # Check for resource issues
        memory_issues = [
            e for e in unusual_events if "memory" in e.get("message", "").lower()
        ]
        cpu_spikes = [a for a in metric_anomalies if a.get("type") == "cpu_spike"]
        memory_spikes = [a for a in metric_anomalies if a.get("type") == "memory_spike"]

        if memory_issues or cpu_spikes or memory_spikes:
            possible_causes.append("resource_exhaustion")
            confidence_scores["resource_exhaustion"] = (
                len(memory_issues) * 0.3
                + len(cpu_spikes) * 0.2
                + len(memory_spikes) * 0.2
            )
            thinking_log.append(
                f"Resource issues detected: {len(memory_issues)} memory events, {len(cpu_spikes)} CPU spikes, {len(memory_spikes)} memory spikes"
            )

        # Check for error rate spikes
        error_rate_spikes = [
            a for a in metric_anomalies if a.get("type") == "error_rate_spike"
        ]
        if error_rate_spikes:
            possible_causes.append("application_error_spike")
            confidence_scores["application_error_spike"] = min(
                len(error_rate_spikes) * 0.5, 1.0
            )
            thinking_log.append(
                f"Error rate spike detected: {len(error_rate_spikes)} error rate anomalies"
            )

        # Determine primary root cause
        if confidence_scores:
            primary_cause = max(confidence_scores.items(), key=lambda x: x[1])
            root_cause = primary_cause[0]
            confidence = primary_cause[1]
            thinking_log.append(
                f"Primary root cause determined: {root_cause} (confidence: {confidence:.2f})"
            )
        else:
            root_cause = "unknown_anomaly"
            confidence = 0.1
            thinking_log.append("No clear root cause pattern identified")

        # Generate recommendations
        recommendations = self._get_recommendations(
            root_cause, metric_anomalies, key_errors
        )
        thinking_log.append(f"Generated {len(recommendations)} recommendations")

        # Create incident note
        incident_note = self._create_incident_note(
            root_cause, log_summary, metric_summary, recommendations
        )
        thinking_log.append("Incident note created")

        return {
            "root_cause": root_cause,
            "confidence": confidence,
            "possible_causes": [
                {"cause": cause, "confidence": score}
                for cause, score in confidence_scores.items()
            ],
            "recommended_action": (
                recommendations[0]
                if recommendations
                else "Monitor system for additional signals"
            ),
            "all_recommendations": recommendations,
            "incident_note": incident_note,
            "thinking_log": thinking_log,
        }

    def _get_recommendations(
        self, root_cause: str, metric_anomalies: list, key_errors: list
    ) -> list:
        """Generate recommendations based on root cause"""
        recommendations = []

        if root_cause == "timeout_configuration":
            recommendations.extend(
                [
                    "Increase Lambda timeout configuration to 15+ seconds",
                    "Review downstream service response times",
                    "Consider implementing circuit breaker pattern",
                ]
            )

        elif root_cause == "downstream_service_degradation":
            recommendations.extend(
                [
                    "Check downstream service health and capacity",
                    "Implement retry with exponential backoff",
                    "Add circuit breaker to prevent cascade failures",
                    "Review service dependency SLAs",
                ]
            )

        elif root_cause == "resource_exhaustion":
            recommendations.extend(
                [
                    "Increase Lambda memory allocation",
                    "Optimize memory usage in application code",
                    "Review object lifecycle and garbage collection",
                    "Consider breaking down large operations",
                ]
            )

        elif root_cause == "application_error_spike":
            recommendations.extend(
                [
                    "Review recent code deployments",
                    "Check input validation and error handling",
                    "Analyze error patterns for common causes",
                    "Implement better error recovery mechanisms",
                ]
            )

        else:
            recommendations.extend(
                [
                    "Continue monitoring for pattern emergence",
                    "Review recent changes to system configuration",
                    "Check external dependencies and integrations",
                ]
            )

        return recommendations

    def _create_incident_note(
        self,
        root_cause: str,
        log_summary: dict,
        metric_summary: dict,
        recommendations: list,
    ) -> str:
        """Create a formatted incident note"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        note = f"""INCIDENT ANALYSIS - {timestamp}

ROOT CAUSE: {root_cause.replace('_', ' ').title()}

SUMMARY:
{log_summary.get('summary', 'No log summary available')}

KEY METRICS:
- Max Duration: {metric_summary.get('lambda_metrics', {}).get('duration_max', 0):.0f}ms
- Error Rate: {metric_summary.get('lambda_metrics', {}).get('error_rate', 0):.3f}
- Max CPU: {metric_summary.get('custom_metrics', {}).get('cpu_max', 0):.1f}%
- Max Memory: {metric_summary.get('custom_metrics', {}).get('memory_max', 0):.1f}MB

RECOMMENDED ACTIONS:
{chr(10).join(f"• {rec}" for rec in recommendations[:3])}

NEXT STEPS:
1. Implement immediate fixes from recommendations
2. Monitor system for 15-30 minutes post-fix
3. Review and update alerting thresholds if needed
"""

        return note
