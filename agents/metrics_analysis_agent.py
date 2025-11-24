import os
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import boto3

logger = logging.getLogger(__name__)

SEVERITY_ORDER = ["ok", "warning", "high", "critical"]

LOG_LEVEL_TO_SEVERITY = {
    "DEBUG": "ok",
    "INFO": "ok",
    "WARNING": "warning",
    "WARN": "warning",
    "ERROR": "high",
    "CRITICAL": "critical",
    "FATAL": "critical",
}


def _max_severity(a: str, b: str) -> str:
    """Return the higher of two severities based on SEVERITY_ORDER."""
    try:
        ia = SEVERITY_ORDER.index(a)
    except ValueError:
        ia = 0
    try:
        ib = SEVERITY_ORDER.index(b)
    except ValueError:
        ib = 0
    return a if ia >= ib else b


def _extract_structured_payload(
    raw_message: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    CloudWatch Lambda logs usually look like:

      [WARNING]\\t2025-11-24T08:51:19.426Z\\t<requestId>\\t{...json...}

    We want the JSON part + the CloudWatch prefix timestamp so you can
    cross reference what the agent saw vs the CloudWatch console.

    Returns:
      (payload_dict or None, cw_timestamp_prefix or None)
    """
    if not raw_message:
        return None, None

    # Split into at most 4 parts: [LEVEL], TS, REQID, JSON
    parts = raw_message.split("\t", 3)
    if len(parts) < 4:
        return None, None

    cw_timestamp_prefix = parts[1].strip()
    json_part = parts[3].strip()

    try:
        payload = json.loads(json_part)
        return payload, cw_timestamp_prefix
    except Exception:
        return None, cw_timestamp_prefix


class MetricAnalysisAgent:
    """
    MetricAnalysisAgent

    Hackathon-simple behavior (log-driven mode):

    - We do NOT compute or average numeric CloudWatch metrics here.
    - Instead, we look at recent CloudWatch Logs in the configured log group
      within the analysis window.
    - If we see any WARNING / ERROR / CRITICAL events, we raise severity
      accordingly based on the highest level seen.
    - If we see none, overall_severity = "ok".

    Orchestrator behavior is unchanged:
      - It calls analyze(metrics=..., incident_logger=...).
      - If overall_severity >= ALERT_SEVERITY_THRESHOLD, it triggers
        LogAnalysisAgent + RCAAgent.

    This agent also writes human readable messages into thinking_log,
    including the CloudWatch prefix timestamp and the log payload "message",
    so you can cross-reference exactly which log lines were used.
    """

    def __init__(
        self,
        cloudwatch_client: Optional[Any] = None,
        namespace: Optional[str] = None,
        window_minutes: Optional[int] = None,
    ) -> None:
        # Region for CloudWatch Logs
        aws_region = (
            os.environ.get("AWS_REGION")
            or os.environ.get("AWS_DEFAULT_REGION")
            or "us-east-1"
        )

        # CloudWatch metrics client (kept for compatibility, even if not used heavily)
        self.cloudwatch = cloudwatch_client or boto3.client(
            "cloudwatch", region_name=aws_region
        )

        # Namespace (not heavily used in this log-driven version, but kept)
        self.namespace = namespace or os.environ.get(
            "METRICS_NAMESPACE", "Custom/EcommerceOrderPipeline"
        )

        # Time window in minutes for analysis
        if window_minutes is not None:
            self.window_minutes = window_minutes
        else:
            # Default from env, then 10 if not set
            self.window_minutes = int(os.environ.get("METRICS_WINDOW_MINUTES", "10"))

        # Optional thresholds file at repo root (kept for compatibility)
        self.thresholds = self._load_thresholds()

        # CloudWatch Logs client to inspect recent log events
        self.logs_client = boto3.client("logs", region_name=aws_region)
        self.log_group_name = os.environ.get(
            "LOG_GROUP_NAME", "/aws/lambda/cloudwatch-log-generator"
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _load_thresholds(self) -> Dict[str, Any]:
        """
        Load thresholds.json from the repo root. Optional.
        """
        try:
            # agents/metrics_analysis_agent.py -> agents -> repo root
            repo_root = Path(__file__).resolve().parent.parent
            thresholds_path = repo_root / "thresholds.json"
            with thresholds_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(
                "[MetricAnalysisAgent] Failed to load thresholds.json: %s", e
            )
            return {}

    def _get_window(self) -> (datetime, datetime):
        now = datetime.now(timezone.utc)
        start = now - timedelta(minutes=self.window_minutes)
        return start, now

    def _severity_from_log_level(self, level: str) -> str:
        lvl = (level or "").upper()
        return LOG_LEVEL_TO_SEVERITY.get(lvl, "ok")

    def _fetch_recent_log_events(self) -> List[Dict[str, Any]]:
        """
        Pull recent log events from the configured log group within our window.
        Single page is enough for hackathon usage.
        """
        if not self.log_group_name:
            logger.warning(
                "MetricAnalysisAgent: LOG_GROUP_NAME is not set. "
                "Cannot drive severity from logs."
            )
            return []

        start, end = self._get_window()
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)

        try:
            response = self.logs_client.filter_log_events(
                logGroupName=self.log_group_name,
                startTime=start_ms,
                endTime=end_ms,
            )
            return response.get("events", [])
        except Exception as e:
            logger.exception(
                "MetricAnalysisAgent: failed to fetch recent log events: %s", e
            )
            return []

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def analyze(
        self,
        metrics: Dict[str, Any],
        incident_logger: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Main entry used by the orchestrator.

        Even though the orchestrator passes `metrics` from CloudWatchMetricsTool,
        this log-driven agent uses *logs* as the primary signal.

        Returns:
          {
            "incident_id": ...,
            "overall_severity": "ok" | "warning" | "high" | "critical",
            "violations": [...],
            "summary": "...",
            "thinking_log": [...]
          }
        """
        thinking_log: List[str] = []
        thinking_log.append(
            "Starting metrics analysis (log-driven incident detection)."
        )

        # Use the incident id managed by IncidentLogger so everything lines up
        incident_id = getattr(incident_logger, "incident_id", None)

        events = self._fetch_recent_log_events()
        overall_severity = "ok"
        highest_level = None
        warning_count = 0
        high_count = 0
        critical_count = 0

        for ev in events:
            raw_message = (ev.get("message") or "").strip()
            payload, cw_ts = _extract_structured_payload(raw_message)

            if not payload:
                continue

            level = str(payload.get("level", "INFO")).upper()
            severity = self._severity_from_log_level(level)

            if severity == "ok":
                continue

            overall_severity = _max_severity(overall_severity, severity)
            highest_level = level

            if severity == "warning":
                warning_count += 1
            elif severity == "high":
                high_count += 1
            elif severity == "critical":
                critical_count += 1

            # Add a human readable line so you can cross check with CloudWatch
            thinking_log.append(
                f"[Log] {cw_ts} | {payload.get('event')} | "
                f"{payload.get('message')} | severity={severity}"
            )

        if overall_severity == "ok":
            summary = "No warning, high, or critical incidents detected in recent logs."
            violations: List[Dict[str, Any]] = []
        else:
            parts = []
            if warning_count:
                parts.append(f"{warning_count} warning")
            if high_count:
                parts.append(f"{high_count} high")
            if critical_count:
                parts.append(f"{critical_count} critical")

            summary = (
                "Detected elevated incident signals from recent CloudWatch logs: "
                + ", ".join(parts)
            )

            violations = [
                {
                    "type": "log_level",
                    "metric": "log_level",
                    "value": highest_level,
                    "threshold": "WARNING",
                }
            ]

        thinking_log.append(f"Computed overall severity: {overall_severity}")

        return {
            "incident_id": incident_id,
            "overall_severity": overall_severity,
            "violations": violations,
            "summary": summary,
            "thinking_log": thinking_log,
        }
