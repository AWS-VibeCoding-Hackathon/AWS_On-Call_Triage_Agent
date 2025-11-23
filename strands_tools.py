import boto3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any


class CloudWatchTools:
    def __init__(self):
        self.logs_client = boto3.client("logs")
        self.cloudwatch_client = boto3.client("cloudwatch")

    def get_recent_logs(
        self, log_group: str, duration_minutes: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent logs from CloudWatch Logs

        Args:
            log_group: CloudWatch log group name
            duration_minutes: How many minutes back to fetch logs

        Returns:
            List of log events
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=duration_minutes)

        start_timestamp = int(start_time.timestamp() * 1000)
        end_timestamp = int(end_time.timestamp() * 1000)

        try:
            response = self.logs_client.filter_log_events(
                logGroupName=log_group,
                startTime=start_timestamp,
                endTime=end_timestamp,
                limit=1000,
            )

            return response.get("events", [])

        except Exception as e:
            print(f"Error fetching logs: {e}")
            return []

    def get_recent_metrics(
        self, namespace: str, metric_queries: List[Dict], duration_minutes: int = 10
    ) -> Dict[str, Any]:
        """
        Fetch recent metrics from CloudWatch

        Args:
            namespace: CloudWatch namespace
            metric_queries: List of metric query configurations
            duration_minutes: How many minutes back to fetch metrics

        Returns:
            Dictionary with metric data
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=duration_minutes)

        try:
            # Get Lambda metrics
            lambda_metrics = self._get_lambda_metrics(start_time, end_time)

            # Get custom metrics if namespace provided
            custom_metrics = {}
            if namespace and metric_queries:
                custom_metrics = self._get_custom_metrics(
                    namespace, metric_queries, start_time, end_time
                )

            return {
                "lambda_metrics": lambda_metrics,
                "custom_metrics": custom_metrics,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                },
            }

        except Exception as e:
            print(f"Error fetching metrics: {e}")
            return {}

    def _get_lambda_metrics(
        self, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Get standard Lambda metrics"""
        function_name = "cloudwatch-log-generator"

        metrics = {}

        # Duration
        try:
            duration_response = self.cloudwatch_client.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Duration",
                Dimensions=[{"Name": "FunctionName", "Value": function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=["Average", "Maximum"],
            )
            metrics["duration"] = duration_response.get("Datapoints", [])
        except:
            metrics["duration"] = []

        # Errors
        try:
            errors_response = self.cloudwatch_client.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Errors",
                Dimensions=[{"Name": "FunctionName", "Value": function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=["Sum"],
            )
            metrics["errors"] = errors_response.get("Datapoints", [])
        except:
            metrics["errors"] = []

        # Invocations
        try:
            invocations_response = self.cloudwatch_client.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Invocations",
                Dimensions=[{"Name": "FunctionName", "Value": function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=["Sum"],
            )
            metrics["invocations"] = invocations_response.get("Datapoints", [])
        except:
            metrics["invocations"] = []

        return metrics

    def _get_custom_metrics(
        self,
        namespace: str,
        metric_queries: List[Dict],
        start_time: datetime,
        end_time: datetime,
    ) -> Dict[str, Any]:
        """Get custom metrics from specified namespace"""
        custom_metrics = {}

        for query in metric_queries:
            metric_name = query.get("metric_name")
            if not metric_name:
                continue

            try:
                response = self.cloudwatch_client.get_metric_statistics(
                    Namespace=namespace,
                    MetricName=metric_name,
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=["Average", "Maximum", "Sum"],
                )
                custom_metrics[metric_name] = response.get("Datapoints", [])
            except Exception as e:
                print(f"Error fetching {metric_name}: {e}")
                custom_metrics[metric_name] = []

        return custom_metrics


# Convenience functions for Strands Agents
def get_recent_logs(
    log_group: str = "/aws/lambda/cloudwatch-log-generator", duration_minutes: int = 10
) -> List[Dict[str, Any]]:
    """Wrapper function for getting recent logs"""
    tools = CloudWatchTools()
    return tools.get_recent_logs(log_group, duration_minutes)


def get_recent_metrics(
    namespace: str = "Custom/EcommerceOrderPipeline", duration_minutes: int = 10
) -> Dict[str, Any]:
    """Wrapper function for getting recent metrics"""
    tools = CloudWatchTools()

    # Default metric queries for the ecommerce pipeline
    metric_queries = [
        {"metric_name": "CPUUtilization"},
        {"metric_name": "MemoryUsageMB"},
        {"metric_name": "OrderLatencyMS"},
        {"metric_name": "ErrorRate"},
        {"metric_name": "RetryCount"},
    ]

    return tools.get_recent_metrics(namespace, metric_queries, duration_minutes)
