"""Utility to verify Step Functions state machine accessibility in CI."""

import os
import sys

import boto3


def main() -> int:
    endpoint = os.environ.get("STEPFUNCTIONS_ENDPOINT") or "http://localhost:8083"
    state_machine_arn = os.environ.get("STATE_MACHINE_ARN")
    region = os.environ.get("AWS_REGION", "us-east-1")
    access_key = os.environ.get("AWS_ACCESS_KEY_ID", "dummy")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "dummy")

    if not state_machine_arn:
        print("❌ STATE_MACHINE_ARN environment variable is not set")
        return 1

    client = boto3.client(
        "stepfunctions",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    try:
        response = client.describe_state_machine(stateMachineArn=state_machine_arn)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"❌ State machine accessibility test failed: {exc}")
        return 1

    print("✓ State machine is accessible and ready for testing")
    print(f"State machine name: {response['name']}")
    print(f"State machine status: {response['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
