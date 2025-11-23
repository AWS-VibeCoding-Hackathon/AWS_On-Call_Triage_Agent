#!/usr/bin/env python3

import load_env  # Load AWS credentials
from strands_tools import get_recent_logs, get_recent_metrics
import json

def test_cloudwatch_tools():
    """Test the CloudWatch tools with your log group"""
    
    print("Testing CloudWatch Tools...")
    print("=" * 50)
    
    # Test logs
    print("\n1. Fetching recent logs...")
    logs = get_recent_logs("/aws/lambda/cloudwatch-log-generator", duration_minutes=30)
    print(f"Found {len(logs)} log events")
    
    if logs:
        print("\nSample log event:")
        print(json.dumps(logs[0], indent=2, default=str))
    
    # Test metrics
    print("\n2. Fetching recent metrics...")
    metrics = get_recent_metrics("Custom/EcommerceOrderPipeline", duration_minutes=30)
    print(f"Metrics data structure:")
    print(json.dumps({k: f"{len(v)} datapoints" if isinstance(v, list) else str(v) 
                     for k, v in metrics.items()}, indent=2))
    
    # Show Lambda metrics
    if 'lambda_metrics' in metrics:
        lambda_metrics = metrics['lambda_metrics']
        print(f"\nLambda metrics found:")
        for metric_name, datapoints in lambda_metrics.items():
            print(f"  {metric_name}: {len(datapoints)} datapoints")
    
    # Show custom metrics
    if 'custom_metrics' in metrics:
        custom_metrics = metrics['custom_metrics']
        print(f"\nCustom metrics found:")
        for metric_name, datapoints in custom_metrics.items():
            print(f"  {metric_name}: {len(datapoints)} datapoints")

if __name__ == "__main__":
    test_cloudwatch_tools()