# agents/log_analysis_agent.py

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


def _extract_structured_payload(raw_message: str) -> Optional[Dict[str, Any]]:
    """
    CloudWatch Lambda logs usually look like either:

      1) message == '{...json...}'  (most common for Lambda structured logs)
      2) message == '[WARNING]\\t2025-11-24T07:52:14.335Z\\tREQID\\t{...json...}'

    We want the JSON part. This helper finds the first '{' and parses from there.
    """
    if not raw_message:
        return None

    idx = raw_message.find("{")
    if idx == -1:
        return None

    candidate = raw_message[idx:]
    try:
        return json.loads(candidate)
    except Exception:
        return None


class LogAnalysisAgent:
    """
    LogAnalysisAgent

    Hackathon behavior:

    - Look at recent log events in the configured CloudWatch log group,
      within the same window as metrics (METRICS_WINDOW_MINUTES).
    - Parse the structured JSON part of each Lambda log line.
    - Only keep WARNING / ERROR / CRITICAL level events.
    - Compute highest severity across those events and return them,
      including the original 'message' field so the orchestrator output
      is human readable.

    This agent is invoked by the orchestrator once metrics severity
    crosses ALERT_SEVERITY_THRESHOLD.
    """

    def __init__(
        self,
        logs_client: Optional[Any] = None,
        log_group_name: Optional[str] = None,
        window_minutes: Optional[int] = None,
    ) -> None:
        aws_region = (
            os.environ.get("AWS_REGION")
            or os.environ.get("AWS_DEFAULT_REGION")
            or "us-east-1"
        )

        self.logs_client = logs_client or boto3.client("logs", region_name=aws_region)

        # Log group name comes from env by default
        self.log_group_name = log_group_name or os.environ.get("LOG_GROUP_NAME", "")

        # Use same window as metrics for simplicity
        if window_minutes is not None:
            self.window_minutes = window_minutes
        else:
            self.window_minutes = int(os.environ.get("METRICS_WINDOW_MINUTES", "10"))

        # Optional thresholds.json at repo root (not strictly required here,
        # but kept for consistency and potential future use).
        self.thresholds = self._load_thresholds()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _load_thresholds(self) -> Dict[str, Any]:
        """
        Load thresholds.json from the repo root. Optional.
        """
        try:
            repo_root = Path(__file__).resolve().parent.parent
            thresholds_path = repo_root / "thresholds.json"
            with thresholds_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("[LogAnalysisAgent] Failed to load thresholds.json: %s", e)
            return {}

    def _get_window(self) -> Tuple[datetime, datetime]:
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
                "LogAnalysisAgent: LOG_GROUP_NAME is not set. "
                "Cannot analyze incidents from logs."
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
                "LogAnalysisAgent: failed to fetch recent log events: %s", e
            )
            return []

    # ------------------------------------------------------------------ #
    # Public API used by orchestrator (wrapper)
    # ------------------------------------------------------------------ #

    def analyze(
        self,
        logs: Dict[str, Any],
        incident_logger: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Wrapper to match the orchestrator interface:

            logs_result = self.log_agent.analyze(
                logs=logs,
                incident_logger=logger,
            )

        We ignore the `logs` dict (since this agent fetches directly from
        CloudWatch), pull the incident_id from the logger, and call
        analyze_logs(...) to do the actual work.
        """
        incident_id = getattr(incident_logger, "incident_id", None)

        incident_logger.add_entry(
            agent="LogAnalysisAgent",
            stage="start",
            message="Starting log analysis from orchestrator escalation.",
        )

        result = self.analyze_logs(
            incident_id=incident_id,
            metrics_context=None,
        )

        incident_logger.add_entry(
            agent="LogAnalysisAgent",
            stage="end",
            message=f"Completed log analysis. Computed severity={result.get('severity')}.",
        )

        return result

    # ------------------------------------------------------------------ #
    # Core log analysis
    # ------------------------------------------------------------------ #

    def analyze_logs(
        self,
        incident_id: str,
        metrics_context: Optional[Dict[str, Any]] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Main log analysis logic.

        Returns:
          {
            "incident_id": ...,
            "severity": "ok" | "warning" | "high" | "critical",
            "summary": "...",
            "events": [...],
            "thinking_log": [...]
          }
        """
        thinking_log: List[str] = []
        thinking_log.append("Starting log analysis for recent high-severity events.")

        events = self._fetch_recent_log_events()
        incident_events: List[Dict[str, Any]] = []

        overall_severity = "ok"
        warning_count = 0
        high_count = 0
        critical_count = 0

        for ev in events:
            raw_message = (ev.get("message") or "").strip()
            payload = _extract_structured_payload(raw_message)

            if not payload:
                continue

            level = str(payload.get("level", "INFO")).upper()
            severity = self._severity_from_log_level(level)

            # We only care about warning or worse here
            if severity == "ok":
                continue

            overall_severity = _max_severity(overall_severity, severity)

            if severity == "warning":
                warning_count += 1
            elif severity == "high":
                high_count += 1
            elif severity == "critical":
                critical_count += 1

            # CloudWatch event timestamp (epoch ms)
            cw_ts_ms = ev.get("timestamp")
            cw_ts_iso = None
            if isinstance(cw_ts_ms, int):
                cw_ts_iso = datetime.fromtimestamp(
                    cw_ts_ms / 1000.0, tz=timezone.utc
                ).isoformat()

            # capture key fields including original message so you can read it
            incident_events.append(
                {
                    "cloudwatch_timestamp": cw_ts_ms,
                    "cloudwatch_timestamp_iso": cw_ts_iso,
                    "log_stream": ev.get("logStreamName"),
                    "level": level,
                    "severity": severity,
                    "event": payload.get("event"),
                    "message": payload.get("message"),
                    "service": payload.get("service"),
                    "component": payload.get("component"),
                    "scenario": payload.get("scenario"),
                    "payload_timestamp": payload.get("timestamp"),
                    "details": payload.get("details", {}),
                    "raw": raw_message,
                }
            )

        if overall_severity == "ok":
            summary = "No warning, high, or critical log events detected in the analysis window."
        else:
            parts: List[str] = []
            if warning_count:
                parts.append(f"{warning_count} warning")
            if high_count:
                parts.append(f"{high_count} high")
            if critical_count:
                parts.append(f"{critical_count} critical")

            summary = (
                "Detected elevated incident signals from CloudWatch logs in the analysis window: "
                + ", ".join(parts)
            )

        thinking_log.append(
            f"Completed log analysis. Computed overall log severity: {overall_severity}."
        )

        return {
            "incident_id": incident_id,
            "severity": overall_severity,
            "summary": summary,
            "events": incident_events,
            "thinking_log": thinking_log,
        }
