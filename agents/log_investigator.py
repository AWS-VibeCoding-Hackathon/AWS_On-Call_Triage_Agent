from strands import Agent
from strands_tools import get_recent_logs
import json
import re
from datetime import datetime


class LogInvestigatorAgent(Agent):
    """
    Log Investigator Agent - Analyzes CloudWatch logs for patterns and anomalies
    """

    def __init__(self):
        super().__init__(name="LogInvestigator")
        self.patterns = {
            "timeout": [r"timed out", r"timeout", r"Task timed out"],
            "slow_downstream": [r"took \d+\s*ms", r"duration.*ms", r"latency"],
            "retry_storm": [r"connection reset", r"retry", r"attempt \d+"],
            "memory_error": [r"OutOfMemoryError", r"memory", r"heap space"],
            "error_general": [r"ERROR", r"Exception", r"Failed"],
        }

    def investigate_logs(
        self,
        log_group: str = "/aws/lambda/cloudwatch-log-generator",
        duration_minutes: int = 10,
    ) -> dict:
        """
        Investigate recent logs for patterns and anomalies

        Returns:
            dict with summary, key_errors, latency_patterns, retry_sequences, unusual_events, thinking_log
        """
        thinking_log = []
        thinking_log.append(
            f"Starting log investigation for {log_group} over last {duration_minutes} minutes"
        )

        # Fetch logs
        log_events = get_recent_logs(log_group, duration_minutes)
        thinking_log.append(f"Retrieved {len(log_events)} log events")

        if not log_events:
            thinking_log.append("No log events found - investigation complete")
            return {
                "summary": "No logs found in specified time window",
                "key_errors": [],
                "latency_patterns": [],
                "retry_sequences": [],
                "unusual_events": [],
                "thinking_log": thinking_log,
            }

        # Analyze patterns
        key_errors = []
        latency_patterns = []
        retry_sequences = []
        unusual_events = []

        timeout_count = 0
        error_count = 0
        warning_count = 0

        for event in log_events:
            message = event.get("message", "")
            timestamp = event.get("timestamp", 0)

            # Parse JSON logs if possible
            try:
                if message.startswith("{"):
                    log_data = json.loads(message)
                    level = log_data.get("level", "INFO")
                    event_type = log_data.get("event", "")
                    scenario = log_data.get("scenario", "unknown")

                    # Count by level
                    if level == "ERROR":
                        error_count += 1
                    elif level == "WARNING":
                        warning_count += 1

                    # Detect specific patterns
                    if "timeout" in message.lower() or "timed out" in message.lower():
                        timeout_count += 1
                        key_errors.append(
                            {
                                "timestamp": timestamp,
                                "type": "timeout",
                                "message": log_data.get("message", ""),
                                "scenario": scenario,
                            }
                        )

                    # Latency patterns
                    if "latency" in message.lower() or "duration" in message.lower():
                        latency_match = re.search(r"(\d+)\s*ms", message)
                        if latency_match:
                            latency_ms = int(latency_match.group(1))
                            latency_patterns.append(
                                {
                                    "timestamp": timestamp,
                                    "latency_ms": latency_ms,
                                    "message": log_data.get("message", ""),
                                    "scenario": scenario,
                                }
                            )

                    # Retry patterns
                    if "retry" in message.lower() or "attempt" in message.lower():
                        retry_sequences.append(
                            {
                                "timestamp": timestamp,
                                "message": log_data.get("message", ""),
                                "scenario": scenario,
                            }
                        )

                    # Memory/resource issues
                    if "memory" in message.lower() or "resource" in message.lower():
                        unusual_events.append(
                            {
                                "timestamp": timestamp,
                                "type": "resource_issue",
                                "message": log_data.get("message", ""),
                                "scenario": scenario,
                            }
                        )

            except json.JSONDecodeError:
                # Handle non-JSON logs
                if any(
                    pattern in message.lower()
                    for pattern_list in self.patterns.values()
                    for pattern in pattern_list
                ):
                    unusual_events.append(
                        {
                            "timestamp": timestamp,
                            "type": "unstructured_anomaly",
                            "message": message,
                        }
                    )

        thinking_log.append(f"Pattern analysis complete:")
        thinking_log.append(f"  - Errors: {error_count}")
        thinking_log.append(f"  - Warnings: {warning_count}")
        thinking_log.append(f"  - Timeouts: {timeout_count}")
        thinking_log.append(f"  - Latency patterns: {len(latency_patterns)}")
        thinking_log.append(f"  - Retry sequences: {len(retry_sequences)}")
        thinking_log.append(f"  - Unusual events: {len(unusual_events)}")

        # Generate summary
        total_events = len(log_events)
        error_rate = error_count / total_events if total_events > 0 else 0

        summary_parts = []
        if error_count > 0:
            summary_parts.append(f"{error_count} errors")
        if warning_count > 0:
            summary_parts.append(f"{warning_count} warnings")
        if timeout_count > 0:
            summary_parts.append(f"{timeout_count} timeouts")
        if len(latency_patterns) > 0:
            avg_latency = sum(p["latency_ms"] for p in latency_patterns) / len(
                latency_patterns
            )
            summary_parts.append(f"avg latency {avg_latency:.0f}ms")

        summary = (
            f"Analyzed {total_events} events: " + ", ".join(summary_parts)
            if summary_parts
            else f"Analyzed {total_events} events: no anomalies detected"
        )

        thinking_log.append(f"Investigation summary: {summary}")

        return {
            "summary": summary,
            "key_errors": key_errors,
            "latency_patterns": latency_patterns,
            "retry_sequences": retry_sequences,
            "unusual_events": unusual_events,
            "thinking_log": thinking_log,
        }
