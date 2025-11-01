"""Utility to verify Step Functions state machine accessibility in CI.

This script now performs an end-to-end smoke test by executing the state machine
against the locally running SAM Lambda endpoints. By waiting for a successful
execution and validating the output structure, we can confirm that
Step Functions Local is actually invoking the functions served by
``sam local start-lambda``.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict

import boto3
from botocore.exceptions import BotoCoreError, ClientError


def _create_client(endpoint: str, region: str, access_key: str, secret_key: str):
    """Create a Step Functions client that targets the local endpoint."""

    return boto3.client(
        "stepfunctions",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


def _wait_for_execution(client, execution_arn: str, timeout: int = 120, poll: int = 2) -> Dict[str, Any]:
    """Poll the execution until a terminal state is reached or timeout occurs."""

    deadline = time.time() + timeout

    while time.time() < deadline:
        response = client.describe_execution(executionArn=execution_arn)
        status = response["status"]

        if status in {"SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"}:
            return response

        time.sleep(poll)

    raise TimeoutError(f"Execution {execution_arn} did not finish within {timeout} seconds")


def _run_smoke_test(client, state_machine_arn: str) -> Dict[str, Any]:
    """Start a workflow execution and validate the final output."""

    sample_input = {
        "requestId": "healthcheck-request",
        "inputData": {
            "value": "healthcheck",
            "metadata": {
                "source": "ci-healthcheck",
                "timestamp": "2024-01-01T00:00:00Z",
            },
        },
    }

    execution_response = client.start_execution(
        stateMachineArn=state_machine_arn,
        name=f"healthcheck-{int(time.time())}",
        input=json.dumps(sample_input),
    )

    execution_arn = execution_response["executionArn"]
    final_status = _wait_for_execution(client, execution_arn)

    if final_status["status"] != "SUCCEEDED":
        raise RuntimeError(
            f"State machine execution ended in non-success status: {final_status['status']}"
        )

    output_payload = json.loads(final_status.get("output", "{}"))

    final_result = output_payload.get("finalResult", {})
    if not final_result or not final_result.get("success"):
        raise RuntimeError("State machine output is missing a successful finalResult block")

    return {
        "executionArn": execution_arn,
        "output": output_payload,
        "history": client.get_execution_history(executionArn=execution_arn).get("events", []),
    }


def main() -> int:
    endpoint = os.environ.get("STEPFUNCTIONS_ENDPOINT") or "http://localhost:8083"
    state_machine_arn = os.environ.get("STATE_MACHINE_ARN")
    region = os.environ.get("AWS_REGION", "us-east-1")
    access_key = os.environ.get("AWS_ACCESS_KEY_ID", "dummy")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "dummy")

    if not state_machine_arn:
        print("❌ STATE_MACHINE_ARN environment variable is not set")
        return 1

    try:
        client = _create_client(endpoint, region, access_key, secret_key)
        state_machine = client.describe_state_machine(stateMachineArn=state_machine_arn)
        print("✓ State machine is accessible and responding")
        print(f"  Name: {state_machine['name']}")
        print(f"  Status: {state_machine['status']}")

        smoke_test_result = _run_smoke_test(client, state_machine_arn)
        print("✓ Smoke test execution succeeded against SAM Local-backed Lambda functions")
        print(f"  Execution ARN: {smoke_test_result['executionArn']}")
        print(
            "  Final result key:",
            smoke_test_result["output"].get("finalResult", {}).get("finalValue", "<missing>"),
        )
        print(f"  Observed {len(smoke_test_result['history'])} execution history events")

        return 0
    except (ClientError, BotoCoreError, TimeoutError, RuntimeError) as exc:
        print(f"❌ State machine accessibility test failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
