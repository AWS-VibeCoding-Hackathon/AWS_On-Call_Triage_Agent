from strands import Agent
from strands_tools import get_recent_metrics
import json
from datetime import datetime


class MetricsAnalystAgent(Agent):
    """
    Metrics Analyst Agent - Monitors CloudWatch metrics for anomalies
    """

    def __init__(self):
        super().__init__(name="MetricsAnalyst")
        self.thresholds = {
            "p95_latency_ms": 1500,
            "error_rate": 0.1,
            "throttles": 0,
            "cpu_utilization": 80,
            "memory_usage_mb": 200,
        }

    def analyze_metrics(self, duration_minutes: int = 10) -> dict:
        """
        Analyze recent metrics for anomalies

        Returns:
            dict with alert_created, alert object, metric_summary, thinking_log
        """
        thinking_log = []
        thinking_log.append(
            f"Starting metrics analysis for last {duration_minutes} minutes"
        )

        # Fetch metrics
        metrics_data = get_recent_metrics(duration_minutes=duration_minutes)
        thinking_log.append(
            f"Fetched metrics data: {len(metrics_data)} metric categories"
        )

        # Analyze Lambda metrics
        lambda_metrics = metrics_data.get("lambda_metrics", {})
        custom_metrics = metrics_data.get("custom_metrics", {})

        anomalies = []

        # Check Lambda duration (p95 latency)
        duration_data = lambda_metrics.get("duration", [])
        if duration_data:
            max_duration = max([dp["Maximum"] for dp in duration_data])
            thinking_log.append(f"Max duration observed: {max_duration}ms")
            if max_duration > self.thresholds["p95_latency_ms"]:
                anomalies.append(
                    {
                        "type": "latency_spike",
                        "value": max_duration,
                        "threshold": self.thresholds["p95_latency_ms"],
                        "severity": "high" if max_duration > 3000 else "medium",
                    }
                )
                thinking_log.append(
                    f"ANOMALY: Latency spike detected - {max_duration}ms > {self.thresholds['p95_latency_ms']}ms"
                )

        # Check Lambda errors
        errors_data = lambda_metrics.get("errors", [])
        invocations_data = lambda_metrics.get("invocations", [])
        if errors_data and invocations_data:
            total_errors = sum([dp["Sum"] for dp in errors_data])
            total_invocations = sum([dp["Sum"] for dp in invocations_data])
            error_rate = (
                total_errors / total_invocations if total_invocations > 0 else 0
            )
            thinking_log.append(f"Error rate calculated: {error_rate:.3f}")
            if error_rate > self.thresholds["error_rate"]:
                anomalies.append(
                    {
                        "type": "error_rate_spike",
                        "value": error_rate,
                        "threshold": self.thresholds["error_rate"],
                        "severity": "high",
                    }
                )
                thinking_log.append(
                    f"ANOMALY: Error rate spike detected - {error_rate:.3f} > {self.thresholds['error_rate']}"
                )

        # Check custom metrics
        cpu_data = custom_metrics.get("CPUUtilization", [])
        if cpu_data:
            max_cpu = max([dp["Maximum"] for dp in cpu_data])
            thinking_log.append(f"Max CPU utilization: {max_cpu}%")
            if max_cpu > self.thresholds["cpu_utilization"]:
                anomalies.append(
                    {
                        "type": "cpu_spike",
                        "value": max_cpu,
                        "threshold": self.thresholds["cpu_utilization"],
                        "severity": "medium",
                    }
                )
                thinking_log.append(
                    f"ANOMALY: CPU spike detected - {max_cpu}% > {self.thresholds['cpu_utilization']}%"
                )

        memory_data = custom_metrics.get("MemoryUsageMB", [])
        if memory_data:
            max_memory = max([dp["Maximum"] for dp in memory_data])
            thinking_log.append(f"Max memory usage: {max_memory}MB")
            if max_memory > self.thresholds["memory_usage_mb"]:
                anomalies.append(
                    {
                        "type": "memory_spike",
                        "value": max_memory,
                        "threshold": self.thresholds["memory_usage_mb"],
                        "severity": "medium",
                    }
                )
                thinking_log.append(
                    f"ANOMALY: Memory spike detected - {max_memory}MB > {self.thresholds['memory_usage_mb']}MB"
                )

        # Determine if alert should be created
        alert_created = len(anomalies) > 0
        thinking_log.append(
            f"Analysis complete. Found {len(anomalies)} anomalies. Alert created: {alert_created}"
        )

        alert = None
        if alert_created:
            alert = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "metrics_anomaly",
                "service": "cloudwatch-log-generator",
                "anomalies": anomalies,
                "severity": max(
                    [a["severity"] for a in anomalies],
                    key=lambda x: {"low": 1, "medium": 2, "high": 3}[x],
                ),
            }

        metric_summary = {
            "lambda_metrics": {
                "duration_max": (
                    max([dp["Maximum"] for dp in duration_data]) if duration_data else 0
                ),
                "error_rate": error_rate if "error_rate" in locals() else 0,
                "invocations": (
                    sum([dp["Sum"] for dp in invocations_data])
                    if invocations_data
                    else 0
                ),
            },
            "custom_metrics": {
                "cpu_max": max([dp["Maximum"] for dp in cpu_data]) if cpu_data else 0,
                "memory_max": (
                    max([dp["Maximum"] for dp in memory_data]) if memory_data else 0
                ),
            },
        }

        return {
            "alert_created": alert_created,
            "alert": alert,
            "metric_summary": metric_summary,
            "thinking_log": thinking_log,
        }
