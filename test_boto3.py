import load_env
import time

print("Testing boto3 import speed...")

start = time.time()
import boto3
print(f"boto3 import took {time.time() - start:.2f}s")

start = time.time()
client = boto3.client('logs')
print(f"logs client creation took {time.time() - start:.2f}s")

start = time.time()
response = client.describe_log_groups(limit=1)
print(f"API call took {time.time() - start:.2f}s")
print("Success!")