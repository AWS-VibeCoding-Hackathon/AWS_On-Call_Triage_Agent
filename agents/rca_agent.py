# agents/rca_agent.py
import os
import json
from typing import Any, Dict, List, Optional

import boto3

from incidents.incident_log import IncidentLogger


class RCAAgent:
    """
    Root Cause Analysis Agent.

    Combines metrics_result + log_summary and calls Titan to produce RCA.
    Writes its own reasoning into IncidentLogger.
    """

    def __init__(
        self, model_id: Optional[str] = None, region: Optional[str] = None
    ) -> None:
        self.agent_name = "RCAAgent"

        self.model_id = (
            model_id
            or os.getenv("BEDROCK_MODEL_ID_RCA")
            or "amazon.titan-text-express-v1"
        )
        self.region = (
            region
            or os.getenv("AWS_DEFAULT_REGION_BEDROCK")
            or os.getenv("AWS_DEFAULT_REGION")
            or "us-east-1"
        )

        self.client = boto3.client("bedrock-runtime", region_name=self.region)

    def analyze(
        self,
        metrics_result: Dict[str, Any],
        log_summary: str,
        incident_logger: IncidentLogger,
    ) -> Dict[str, Any]:
        """
        Returns structured RCA plus local thinking log.
        """

        local_trace: List[str] = []

        incident_logger.add_entry(
            agent=self.agent_name,
            stage="start",
            message="Starting RCA analysis.",
        )
        local_trace.append("Starting RCA analysis.")

        # ------------------------------------------------------------------
        # IMPORTANT CHANGE: build a compact view of metrics_result
        # so we do not blow the Titan token limit.
        # We keep only what the model really needs:
        #   - overall_severity
        #   - summary
        #   - violations
        #   - a trimmed thinking_log
        # ------------------------------------------------------------------
        compact_metrics = self._build_compact_metrics(metrics_result)
        metrics_json = json.dumps(compact_metrics, indent=2)

        # log_summary is already a short string from LogAnalysisAgent,
        # but we still guard its length just in case.
        log_summary_text = str(log_summary or "")
        if len(log_summary_text) > 4000:
            log_summary_text = (
                log_summary_text[:3800] + "\n...[truncated log summary]..."
            )

        prompt = self._build_prompt(metrics_json, log_summary_text)

        body = json.dumps(
            {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 800,
                    "temperature": 0.2,
                    "topP": 0.9,
                },
            }
        )

        incident_logger.add_entry(
            agent=self.agent_name,
            stage="call_llm",
            message=f"Calling Titan model {self.model_id} for RCA synthesis.",
        )
        local_trace.append(f"Calling Titan model {self.model_id} for RCA synthesis.")

        response = self.client.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=body,
        )

        payload = json.loads(response["body"].read())
        text = ""

        try:
            results = payload.get("results") or []
            if results and isinstance(results[0], dict):
                text = results[0].get("outputText", "") or ""
        except Exception:
            text = ""

        parsed = self._try_parse_json(text)

        if parsed:
            rca = parsed
        else:
            # fallback wrapper
            rca = {
                "incident_summary": text.strip() or "RCA summary not available.",
                "overall_severity": metrics_result.get("overall_severity", "unknown"),
                "likely_root_causes": [],
                "impacted_components": [],
                "recommended_actions": [],
                "llm_reasoning": "Model returned unstructured text, used as plain summary.",
            }

        incident_logger.add_entry(
            agent=self.agent_name,
            stage="end",
            message="Completed RCA analysis.",
            extra={"incident_summary_preview": rca.get("incident_summary", "")[:200]},
        )
        local_trace.append("Completed RCA analysis.")

        # Add link back to incident
        rca["incident_id"] = incident_logger.incident_id
        rca["thinking_log"] = local_trace

        return rca

    # ------------------------------------------------------------------
    # NEW: compact metrics builder to avoid token blowups
    # ------------------------------------------------------------------
    def _build_compact_metrics(self, metrics_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a trimmed version of metrics_result so we do not exceed
        the Titan input token limit.

        We keep:
          - overall_severity
          - summary
          - violations
          - a short thinking_log (last few lines)
        Everything else (raw metrics arrays, large payloads) is dropped.
        """
        compact: Dict[str, Any] = {}

        compact["overall_severity"] = metrics_result.get("overall_severity")
        compact["summary"] = metrics_result.get("summary")
        compact["violations"] = metrics_result.get("violations", [])

        thinking_log = metrics_result.get("thinking_log") or []
        if isinstance(thinking_log, list):
            if len(thinking_log) > 10:
                compact["thinking_log"] = [
                    "...[truncated thinking log]..."
                ] + thinking_log[-10:]
            else:
                compact["thinking_log"] = thinking_log

        return compact

    def _build_prompt(self, metrics_json: str, log_summary_text: str) -> str:
        return "\n".join(
            [
                "You are an SRE and cloud ops expert performing root cause analysis.",
                "",
                "You are given:",
                "1) Metrics analysis output (already summarized).",
                "2) Log analysis summary.",
                "",
                "Your job:",
                "- Infer the most likely root cause or small set of root causes.",
                "- Identify impacted services or components.",
                "- Propose concrete next actions for on call.",
                "",
                "Return JSON strictly in this structure:",
                "{",
                '  "incident_summary": "short paragraph",',
                '  "overall_severity": "ok | warning | critical",',
                '  "likely_root_causes": ["..."],',
                '  "impacted_components": ["..."],',
                '  "recommended_actions": ["..."],',
                '  "llm_reasoning": "brief explanation of how you arrived at this"',
                "}",
                "",
                "---------------- METRICS ANALYSIS OUTPUT (COMPACT) ----------------",
                metrics_json,
                "",
                "---------------- LOG ANALYSIS SUMMARY -------------------",
                log_summary_text,
            ]
        )

    def _try_parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        text = (text or "").strip()
        if not text:
            return None
        if text.startswith("```"):
            lines = [
                line for line in text.splitlines() if not line.strip().startswith("```")
            ]
            text = "\n".join(lines).strip()
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "incident_summary" in data:
                return data
        except Exception:
            return None
        return None
