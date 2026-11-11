"""Offline regression tests for the HTTP dashboard smoke test."""
import importlib.util
import io
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "smoke_dashboard.py"
spec = importlib.util.spec_from_file_location("smoke_dashboard", SCRIPT)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class Response:
    status = 200

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


class DashboardSmokeTests(unittest.TestCase):
    def test_success_requires_all_rendered_markers(self):
        with patch("sys.stdout", new_callable=io.StringIO):
            smoke.check_route("http://localhost:5173/", "/", ("Overview", "Loaded"),
                              opener=lambda *a, **kw: Response(b"Overview Loaded"), sleeper=lambda _: None)

    def test_retries_transient_startup_errors(self):
        calls = []

        def opener(*args, **kwargs):
            calls.append(1)
            if len(calls) < 3:
                raise ConnectionRefusedError("not ready")
            return Response(b"Ready")

        with patch("sys.stdout", new_callable=io.StringIO):
            smoke.check_route("http://localhost:5173", "/", ("Ready",), attempts=3,
                              opener=opener, sleeper=lambda _: None)
        self.assertEqual(len(calls), 3)

    def test_missing_marker_fails(self):
        with self.assertRaisesRegex(RuntimeError, "missing rendered data markers"):
            smoke.check_route("http://localhost", "/", ("Not present",), attempts=1,
                              opener=lambda *a, **kw: Response(b"Other content"))

    def test_bad_status_fails(self):
        class BadResponse(Response):
            status = 503
        with self.assertRaisesRegex(RuntimeError, "status=503"):
            smoke.check_route("http://localhost", "/", ("Ready",), attempts=1,
                              opener=lambda *a, **kw: BadResponse(b"Ready"))


if __name__ == "__main__":
    unittest.main()
