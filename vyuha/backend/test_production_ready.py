#!/usr/bin/env python3
"""
Production readiness smoke checks for VYUHA backend.

Default behavior is non-destructive:
- Validates /health
- Validates /health/detailed
- Optionally validates auth/login when credentials are provided
"""

import argparse
import os
import sys
from typing import Any, Dict

import requests


def log(message: str) -> None:
    print(f"[SMOKE] {message}")


def assert_ok(response: requests.Response, endpoint: str) -> Dict[str, Any]:
    if response.status_code != 200:
        raise RuntimeError(f"{endpoint} returned {response.status_code}: {response.text[:300]}")
    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(f"{endpoint} did not return valid JSON") from exc


def run_health_checks(base_url: str, timeout: int, expect_db: bool) -> None:
    log(f"Checking liveness endpoint at {base_url}/health")
    health = assert_ok(requests.get(f"{base_url}/health", timeout=timeout), "/health")
    if health.get("status") != "healthy":
        raise RuntimeError(f"/health status is not healthy: {health}")

    log(f"Checking detailed readiness endpoint at {base_url}/health/detailed")
    detailed = assert_ok(requests.get(f"{base_url}/health/detailed", timeout=timeout), "/health/detailed")
    if detailed.get("status") != "healthy":
        raise RuntimeError(f"/health/detailed status is not healthy: {detailed}")

    checks = detailed.get("checks", {})
    if expect_db:
        db_check = checks.get("database")
        if not db_check:
            raise RuntimeError("database check missing from /health/detailed response")
        if db_check.get("status") != "pass":
            raise RuntimeError(f"database check did not pass: {db_check}")
    log("Health checks passed.")


def run_optional_login_check(
    base_url: str,
    timeout: int,
    email: str | None,
    password: str | None,
) -> None:
    if not email or not password:
        log("Skipping auth check (no BACKEND_SMOKE_EMAIL/BACKEND_SMOKE_PASSWORD provided).")
        return

    log(f"Checking auth/login for {email}")
    response = requests.post(
        f"{base_url}/auth/login",
        json={"email": email, "password": password},
        timeout=timeout,
    )
    payload = assert_ok(response, "/auth/login")
    if not payload.get("token"):
        raise RuntimeError("/auth/login response missing token")
    if not payload.get("user"):
        raise RuntimeError("/auth/login response missing user payload")
    log("Auth login check passed.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run non-destructive backend production smoke checks.")
    parser.add_argument(
        "--api-url",
        default=os.getenv("API_URL", "http://localhost:8000"),
        help="Backend base URL (default: API_URL env or http://localhost:8000)",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=int(os.getenv("SMOKE_TIMEOUT_SECONDS", "12")),
        help="Request timeout in seconds",
    )
    parser.add_argument(
        "--expect-db",
        action="store_true",
        help="Fail if database check is missing or failing in /health/detailed",
    )
    args = parser.parse_args()

    base_url = args.api_url.rstrip("/")
    email = os.getenv("BACKEND_SMOKE_EMAIL")
    password = os.getenv("BACKEND_SMOKE_PASSWORD")

    try:
        run_health_checks(base_url, args.timeout_seconds, args.expect_db)
        run_optional_login_check(base_url, args.timeout_seconds, email, password)
        log("All smoke checks passed.")
        return 0
    except Exception as exc:
        log(f"FAILED: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
