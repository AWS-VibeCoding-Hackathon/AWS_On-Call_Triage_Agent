#!/usr/bin/env python3

import load_env  # Load AWS credentials from .env
import boto3
from botocore.exceptions import NoCredentialsError, ClientError


def check_aws_credentials():
    """Check if AWS credentials are properly configured"""

    try:
        # Test basic AWS access
        sts = boto3.client("sts")
        identity = sts.get_caller_identity()
        print(f"✓ AWS credentials configured")
        print(f"  Account: {identity['Account']}")
        print(f"  User/Role: {identity['Arn']}")

        # Test CloudWatch Logs access
        logs_client = boto3.client("logs")
        log_groups = logs_client.describe_log_groups(limit=5)
        print(f"✓ CloudWatch Logs access confirmed")
        print(f"  Found {len(log_groups['logGroups'])} log groups")

        # Test CloudWatch Metrics access
        cw_client = boto3.client("cloudwatch")
        namespaces = cw_client.list_metrics(MaxRecords=5)
        print(f"✓ CloudWatch Metrics access confirmed")

        return True

    except NoCredentialsError:
        print("✗ No AWS credentials found")
        print("  Run: aws configure")
        return False

    except ClientError as e:
        print(f"✗ AWS access error: {e}")
        return False

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    check_aws_credentials()
