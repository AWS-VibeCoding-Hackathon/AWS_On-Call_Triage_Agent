import os


def load_aws_env():
    """Load AWS credentials from .env.ts file"""
    try:
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("export "):
                    key_value = line.replace("export ", "").strip()
                    if "=" in key_value:
                        key, value = key_value.split("=", 1)
                        os.environ[key] = value
        print("✓ AWS credentials loaded from .env")
    except FileNotFoundError:
        print("✗ .env file not found")
    except Exception as e:
        print(f"✗ Error loading .env: {e}")


# Load credentials when this module is imported
load_aws_env()
