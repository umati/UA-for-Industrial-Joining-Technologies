from __future__ import annotations

import importlib
import io


def test_job_durations_uses_github_token_and_api_url_fallbacks(monkeypatch) -> None:
    module = importlib.import_module("reporting.system_tests_run_summary")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GH_API_URL", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "fallback-token")
    monkeypatch.setenv("GITHUB_API_URL", "https://api.github.invalid")
    monkeypatch.setenv("REPORT_JOB_NAME", "Report")

    seen_urls = []

    class FakeResponse(io.BytesIO):
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout):
        seen_urls.append(request.full_url)
        assert request.get_header("Authorization") == "Bearer fallback-token"
        assert timeout == 20
        payload = (
            b'{"jobs": ['
            b'{"name": "Report", "started_at": "2026-05-14T10:00:00Z", '
            b'"completed_at": "2026-05-14T10:01:00Z", "conclusion": "success"},'
            b'{"name": "Build", "started_at": "2026-05-14T10:00:00Z", '
            b'"completed_at": "2026-05-14T10:01:30Z", "conclusion": "success"}'
            b"]}"
        )
        return FakeResponse(payload)

    monkeypatch.setattr(module, "_urlopen", fake_urlopen)

    rows = module.job_durations("repos/example/project/actions/runs/84/jobs")

    assert seen_urls == ["https://api.github.invalid/repos/example/project/actions/runs/84/jobs"]
    assert rows == [("Build", 90.0, "success")]
