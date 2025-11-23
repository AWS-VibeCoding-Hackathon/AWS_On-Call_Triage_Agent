import load_env
import os

print("Environment variables:")
print(f"AWS_ACCESS_KEY_ID: {os.environ.get('AWS_ACCESS_KEY_ID', 'Not set')}")
print(f"AWS_SECRET_ACCESS_KEY: {'***' if os.environ.get('AWS_SECRET_ACCESS_KEY') else 'Not set'}")
print(f"AWS_DEFAULT_REGION: {os.environ.get('AWS_DEFAULT_REGION', 'Not set')}")

# Quick boto3 test
try:
    import boto3
    client = boto3.client('sts')
    identity = client.get_caller_identity()
    print(f"✓ AWS connection successful - Account: {identity['Account']}")
except Exception as e:
    print(f"✗ AWS connection failed: {e}")