#!/usr/bin/env python3
"""
Simple benchmark script for the recommendation API.

Usage:
    python scripts/benchmark.py
"""

import time
import requests
import statistics

API_BASE = "http://localhost:8000"

TEST_QUERIES = [
    "something spicy",
    "mild comfort food",
    "like mapo tofu",
    "crispy texture",
    "vegetarian dinner",
]


def benchmark_endpoint(endpoint: str, payloads: list[dict] = None, n: int = 10):
    """Run benchmark on an endpoint."""
    latencies = []

    for i in range(n):
        payload = payloads[i % len(payloads)] if payloads else {}

        start = time.perf_counter()
        if payload:
            resp = requests.post(f"{API_BASE}{endpoint}", json=payload, timeout=30)
        else:
            resp = requests.get(f"{API_BASE}{endpoint}", timeout=30)
        elapsed = (time.perf_counter() - start) * 1000

        if resp.status_code == 200:
            latencies.append(elapsed)
        else:
            print(f"  Request {i+1} failed: {resp.status_code}")

    if latencies:
        return {
            "count": len(latencies),
            "p50": statistics.median(latencies),
            "p95": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0],
            "p99": sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 1 else latencies[0],
        }
    return None


def main():
    print("=" * 50)
    print("Asian Food Intelligence - Benchmark")
    print("=" * 50)

    # Check API is running
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        if resp.status_code != 200:
            print(f"API not healthy: {resp.status_code}")
            return
        print(f"API healthy: {resp.json()}")
    except requests.ConnectionError:
        print("API not running. Start with: python run_server.py")
        return

    print()

    # Benchmark GET endpoints
    endpoints = [
        ("/api/v1/dishes", None),
        ("/api/v1/cuisines", None),
        ("/api/v1/taste-map", None),
    ]

    for endpoint, _ in endpoints:
        result = benchmark_endpoint(endpoint, n=20)
        if result:
            print(f"{endpoint}: p50={result['p50']:.1f}ms, p95={result['p95']:.1f}ms")

    # Benchmark recommendations
    payloads = [{"query": q, "max_results": 10} for q in TEST_QUERIES]
    result = benchmark_endpoint("/api/v1/recommend", payloads, n=30)
    if result:
        print(f"/api/v1/recommend: p50={result['p50']:.1f}ms, p95={result['p95']:.1f}ms")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
