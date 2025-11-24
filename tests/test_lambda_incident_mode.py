# tests/test_lambda_incident_mode.py

import os
import json
import time
import sys

import boto3

# Assume repo root structure
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from tools.cloudwatch_logs_tool import CloudWatchLogsTool
from tools.cloudwatch_metrics_tool import CloudWatchMetricsTool


def main():
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-2")
    function_name = os.getenv("LAMBDA_FUNCTION_NAME", "cloudwatch-log-generator")

    lambda_client = boto3.client("lambda", region_name=region)

    print(f"Invoking Lambda {function_name} 5 times in DEMO_FORCE_INCIDENT mode...")
    for i in range(5):
        resp = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=b"{}",
        )
        print(f"Invocation {i+1} status code:", resp["StatusCode"])
        time.sleep(1)

    print("\nSleeping 10 seconds to allow metrics/logs to land in CloudWatch...")
    time.sleep(10)

    # Fetch logs
    log_group = os.getenv("LOG_GROUP_NAME", "/aws/lambda/cloudwatch-log-generator")
    logs_tool = CloudWatchLogsTool(log_group_name=log_group)
    logs_resp = logs_tool.get_recent_logs(minutes=60)

    print("\n===== RECENT LOGS (TRUNCATED) =====")
    if isinstance(logs_resp, dict) and "logs" in logs_resp:
        print(f"Total log entries: {logs_resp['count']}")
        print(json.dumps(logs_resp["logs"][:5], indent=2))
    else:
        print(json.dumps(logs_resp, indent=2))

    # Fetch metrics
    namespace = os.getenv("METRICS_NAMESPACE", "Custom/EcommerceOrderPipeline")
    metrics_tool = CloudWatchMetricsTool(namespace=namespace)
    metrics_resp = metrics_tool.get_recent_metrics(minutes=60)

    print("\n===== RECENT METRICS (SUMMARY) =====")
    print(json.dumps(metrics_resp, indent=2))


if __name__ == "__main__":
    main()
