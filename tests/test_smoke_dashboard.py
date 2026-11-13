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

    def read(self, size=-1):
        return self.body if size < 0 else self.body[:size]


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

    def test_redirect_response_fails(self):
        class RedirectResponse(Response):
            status = 302
        with self.assertRaisesRegex(RuntimeError, "status=302"):
            smoke.check_route("http://localhost", "/", ("Ready",), attempts=1,
                              opener=lambda *a, **kw: RedirectResponse(b"Ready"))

    def test_oversized_response_fails(self):
        with self.assertRaisesRegex(RuntimeError, "response exceeds"):
            smoke.check_route("http://localhost", "/", ("Ready",), attempts=1,
                              opener=lambda *a, **kw: Response(b"Ready" + b"x" * smoke.MAX_HTML_BYTES))

    def test_response_read_is_bounded(self):
        sizes = []

        class BoundedResponse(Response):
            def read(self, size=-1):
                sizes.append(size)
                return super().read(size)

        with patch("sys.stdout", new_callable=io.StringIO):
            smoke.check_route("http://localhost", "/", ("Ready",), attempts=1,
                              opener=lambda *a, **kw: BoundedResponse(b"Ready"))
        self.assertEqual(sizes, [smoke.MAX_HTML_BYTES + 1])

    def test_redirect_handler_does_not_follow(self):
        self.assertIsNone(smoke.NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://example.com"))

    def test_bad_status_fails(self):
        class BadResponse(Response):
            status = 503
        with self.assertRaisesRegex(RuntimeError, "status=503"):
            smoke.check_route("http://localhost", "/", ("Ready",), attempts=1,
                              opener=lambda *a, **kw: BadResponse(b"Ready"))


if __name__ == "__main__":
    unittest.main()
