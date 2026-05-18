"""Metrics endpoint tests — verifies Prometheus instrumentation is working."""
import re

import pytest
from httpx import ASGITransport, AsyncClient

from tests.conftest import auth_headers, signup_user, unique_email

pytestmark = pytest.mark.asyncio(loop_scope="session")

BASE = "/api/v1"
METRICS_URL = "/metrics"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_metric(body: str, metric_name: str) -> list[str]:
    """Return all lines for a given metric name (ignores # HELP / # TYPE lines)."""
    return [
        line for line in body.splitlines()
        if line.startswith(metric_name) and not line.startswith("#")
    ]


def _get_counter_value(body: str, metric_name: str, labels: dict[str, str]) -> float | None:
    """Find the value of a specific labelled metric line."""
    label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
    for line in body.splitlines():
        if line.startswith(metric_name) and "{" in line:
            line_labels = line[line.index("{") + 1 : line.index("}")]
            if all(f'{k}="{v}"' in line_labels for k, v in labels.items()):
                return float(line.split()[-1])
    return None


# ── Existence & Format ────────────────────────────────────────────────────────

class TestMetricsEndpointExists:
    async def test_metrics_returns_200(self, client: AsyncClient) -> None:
        res = await client.get(METRICS_URL)
        assert res.status_code == 200

    async def test_metrics_content_type_is_prometheus(self, client: AsyncClient) -> None:
        res = await client.get(METRICS_URL)
        ct = res.headers.get("content-type", "")
        # Prometheus format uses text/plain with version parameter
        assert "text/plain" in ct

    async def test_metrics_body_is_not_empty(self, client: AsyncClient) -> None:
        res = await client.get(METRICS_URL)
        assert len(res.text) > 0

    async def test_metrics_contains_help_and_type_lines(self, client: AsyncClient) -> None:
        res = await client.get(METRICS_URL)
        body = res.text
        assert "# HELP" in body
        assert "# TYPE" in body

    async def test_metrics_not_json(self, client: AsyncClient) -> None:
        res = await client.get(METRICS_URL)
        # Should NOT be JSON — Prometheus uses its own text format
        assert not res.text.strip().startswith("{")


# ── Required Metric Families ──────────────────────────────────────────────────

class TestRequiredMetricFamilies:
    async def test_http_requests_total_present(self, client: AsyncClient) -> None:
        # Trigger at least one request first
        await client.get(f"{BASE}/health")
        res = await client.get(METRICS_URL)
        assert "http_requests_total" in res.text

    async def test_http_request_duration_seconds_present(self, client: AsyncClient) -> None:
        await client.get(f"{BASE}/health")
        res = await client.get(METRICS_URL)
        assert "http_request_duration_seconds" in res.text

    async def test_high_resolution_duration_histogram_present(self, client: AsyncClient) -> None:
        # v7 replaced http_requests_in_progress with a high-resolution histogram
        await client.get(f"{BASE}/health")
        res = await client.get(METRICS_URL)
        assert "http_request_duration_highr_seconds" in res.text

    async def test_request_counter_has_handler_label(self, client: AsyncClient) -> None:
        await client.get(f"{BASE}/health")
        res = await client.get(METRICS_URL)
        lines = _parse_metric(res.text, "http_requests_total")
        assert any("handler" in line for line in lines)

    async def test_request_counter_has_method_label(self, client: AsyncClient) -> None:
        await client.get(f"{BASE}/health")
        res = await client.get(METRICS_URL)
        lines = _parse_metric(res.text, "http_requests_total")
        assert any("method" in line for line in lines)

    async def test_request_counter_has_status_label(self, client: AsyncClient) -> None:
        await client.get(f"{BASE}/health")
        res = await client.get(METRICS_URL)
        lines = _parse_metric(res.text, "http_requests_total")
        assert any("status_code" in line or "status" in line for line in lines)

    async def test_duration_histogram_has_buckets(self, client: AsyncClient) -> None:
        await client.get(f"{BASE}/health")
        res = await client.get(METRICS_URL)
        body = res.text
        assert "http_request_duration_seconds_bucket" in body

    async def test_duration_histogram_has_sum(self, client: AsyncClient) -> None:
        await client.get(f"{BASE}/health")
        res = await client.get(METRICS_URL)
        assert "http_request_duration_seconds_sum" in res.text

    async def test_duration_histogram_has_count(self, client: AsyncClient) -> None:
        await client.get(f"{BASE}/health")
        res = await client.get(METRICS_URL)
        assert "http_request_duration_seconds_count" in res.text

    async def test_python_process_metrics_present(self, client: AsyncClient) -> None:
        res = await client.get(METRICS_URL)
        # Standard Python process metrics always exported by prometheus_client
        assert "process_" in res.text or "python_" in res.text


# ── Counter Increments ────────────────────────────────────────────────────────

class TestCounterIncrements:
    async def test_health_requests_tracked(self, client: AsyncClient) -> None:
        # Get baseline count
        before = await client.get(METRICS_URL)
        before_lines = _parse_metric(before.text, "http_requests_total")
        before_total = sum(
            float(l.split()[-1]) for l in before_lines
            if "/health" in l or "health" in l
        )

        # Make 3 health requests
        for _ in range(3):
            await client.get(f"{BASE}/health")

        after = await client.get(METRICS_URL)
        after_lines = _parse_metric(after.text, "http_requests_total")
        after_total = sum(
            float(l.split()[-1]) for l in after_lines
            if "/health" in l or "health" in l
        )

        assert after_total >= before_total + 3

    async def test_401_responses_tracked(self, client: AsyncClient) -> None:
        before = await client.get(METRICS_URL)

        # Make 2 unauthenticated requests that will return 401
        await client.get(f"{BASE}/auth/me")
        await client.get(f"{BASE}/auth/me")

        after = await client.get(METRICS_URL)
        body_after = after.text

        # 401s must appear somewhere in the counter lines
        counter_lines = _parse_metric(body_after, "http_requests_total")
        has_401 = any("401" in line for line in counter_lines)
        assert has_401, "401 status codes not tracked in metrics"

    async def test_201_responses_tracked_on_signup(self, client: AsyncClient) -> None:
        before = await client.get(METRICS_URL)

        # Create a new user (201 response)
        await signup_user(client)

        after = await client.get(METRICS_URL)
        counter_lines = _parse_metric(after.text, "http_requests_total")
        has_201 = any("201" in line for line in counter_lines)
        assert has_201, "201 status codes not tracked in metrics"

    async def test_404_responses_tracked(self, client: AsyncClient) -> None:
        before = await client.get(METRICS_URL)

        await client.get(f"{BASE}/dashboards/00000000-0000-0000-0000-000000000000",
                         headers={"Authorization": "Bearer fake"})

        after = await client.get(METRICS_URL)
        counter_lines = _parse_metric(after.text, "http_requests_total")
        # 401 or 404 depending on auth check order — either is fine, just verify 4xx tracked
        has_4xx = any(
            any(code in line for code in ["401", "403", "404"]) for line in counter_lines
        )
        assert has_4xx

    async def test_post_method_tracked_separately_from_get(self, client: AsyncClient) -> None:
        await signup_user(client)
        await client.get(f"{BASE}/health")

        res = await client.get(METRICS_URL)
        counter_lines = _parse_metric(res.text, "http_requests_total")
        has_get = any('"GET"' in line or "GET" in line for line in counter_lines)
        has_post = any('"POST"' in line or "POST" in line for line in counter_lines)
        assert has_get and has_post, "GET and POST must be tracked as separate method labels"

    async def test_multiple_endpoints_tracked_separately(self, client: AsyncClient) -> None:
        signup = await signup_user(client)
        token = signup["data"]["access_token"]
        await client.get(f"{BASE}/health")
        await client.get(f"{BASE}/auth/me", headers=auth_headers(token))

        res = await client.get(METRICS_URL)
        counter_lines = _parse_metric(res.text, "http_requests_total")
        # Both /health and /auth/me handlers should appear in the lines
        handlers = " ".join(counter_lines)
        has_health = "health" in handlers
        has_me = "me" in handlers
        assert has_health and has_me


# ── Duration Sanity Checks ────────────────────────────────────────────────────

class TestDurationMetrics:
    async def test_duration_sum_is_positive(self, client: AsyncClient) -> None:
        await client.get(f"{BASE}/health")
        res = await client.get(METRICS_URL)
        sum_lines = [
            l for l in res.text.splitlines()
            if "http_request_duration_seconds_sum" in l and not l.startswith("#")
        ]
        assert len(sum_lines) > 0
        total_sum = sum(float(l.split()[-1]) for l in sum_lines)
        assert total_sum > 0, "Duration sum must be > 0 after serving requests"

    async def test_duration_count_matches_at_least_requests_made(self, client: AsyncClient) -> None:
        # Get baseline
        before_res = await client.get(METRICS_URL)
        before_counts = [
            l for l in before_res.text.splitlines()
            if "http_request_duration_seconds_count" in l and not l.startswith("#")
        ]
        before_total = sum(float(l.split()[-1]) for l in before_counts)

        N = 5
        for _ in range(N):
            await client.get(f"{BASE}/health")

        after_res = await client.get(METRICS_URL)
        after_counts = [
            l for l in after_res.text.splitlines()
            if "http_request_duration_seconds_count" in l and not l.startswith("#")
        ]
        after_total = sum(float(l.split()[-1]) for l in after_counts)

        assert after_total >= before_total + N

    async def test_bucket_values_are_monotonically_non_decreasing(self, client: AsyncClient) -> None:
        await client.get(f"{BASE}/health")
        res = await client.get(METRICS_URL)

        # Find a set of bucket lines for one handler
        bucket_lines = [
            l for l in res.text.splitlines()
            if "http_request_duration_seconds_bucket" in l
            and "health" in l
            and not l.startswith("#")
        ]
        if not bucket_lines:
            pytest.skip("No health bucket lines found yet")

        # Extract le values and counts
        le_values = []
        for line in bucket_lines:
            le_match = re.search(r'le="([^"]+)"', line)
            count = float(line.split()[-1])
            if le_match:
                le_str = le_match.group(1)
                le_val = float("inf") if le_str == "+Inf" else float(le_str)
                le_values.append((le_val, count))

        le_values.sort(key=lambda x: x[0])
        counts = [c for _, c in le_values]

        # Each bucket must be >= the previous (histogram invariant)
        for i in range(1, len(counts)):
            assert counts[i] >= counts[i - 1], (
                f"Bucket counts not monotonic: {counts}"
            )


# ── Metrics Not Tracked For /metrics Itself ───────────────────────────────────

class TestMetricsExclusion:
    async def test_metrics_endpoint_excluded_from_tracking(self, client: AsyncClient) -> None:
        # Scrape /metrics many times
        for _ in range(5):
            await client.get(METRICS_URL)

        res = await client.get(METRICS_URL)
        counter_lines = _parse_metric(res.text, "http_requests_total")
        # /metrics must NOT appear as a tracked handler
        metrics_self_tracked = any("/metrics" in line for line in counter_lines)
        assert not metrics_self_tracked, "/metrics must not track its own scrapes"


# ── Idempotency ───────────────────────────────────────────────────────────────

class TestMetricsIdempotency:
    async def test_metrics_stable_across_multiple_scrapes(self, client: AsyncClient) -> None:
        r1 = await client.get(METRICS_URL)
        r2 = await client.get(METRICS_URL)
        # Both responses should contain the same metric families
        families_1 = {l for l in r1.text.splitlines() if l.startswith("# TYPE")}
        families_2 = {l for l in r2.text.splitlines() if l.startswith("# TYPE")}
        assert families_1 == families_2

    async def test_counter_never_decreases(self, client: AsyncClient) -> None:
        r1 = await client.get(METRICS_URL)
        await client.get(f"{BASE}/health")
        r2 = await client.get(METRICS_URL)

        lines_1 = {l.split("{")[0]: l for l in _parse_metric(r1.text, "http_requests_total")}
        lines_2 = {l.split("{")[0]: l for l in _parse_metric(r2.text, "http_requests_total")}

        for key in lines_1:
            if key in lines_2:
                val_before = float(lines_1[key].split()[-1])
                val_after = float(lines_2[key].split()[-1])
                assert val_after >= val_before, f"Counter decreased for {key}"
