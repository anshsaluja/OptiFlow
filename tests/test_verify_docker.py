"""Black-box regression tests for isolated Docker verification without Docker."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify-docker.sh"


class DockerVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for directory in ("scripts", "output/scenarios", "bin"):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        (self.root / "scripts/verify-docker.sh").write_text(SCRIPT.read_text())
        (self.root / "scripts/isolate_compose.py").write_text("import sys\nsys.stdout.write(sys.stdin.read())\n")
        (self.root / "scripts/smoke_dashboard.py").write_text('import os,sys\nsys.exit(int(os.getenv("FAIL_SMOKE", "0")))\n')
        (self.root / "compose.yaml").write_text("services: {}\n")
        for path in ("output/allocation.json", "output/scenarios/manifest.json", "output/scenarios/baseline.json"):
            (self.root / path).write_text("{}")
        docker = self.root / "bin/docker"
        docker.write_text('''#!/usr/bin/env python3
import os,sys
from pathlib import Path
args = sys.argv[1:]
with Path(os.environ['DOCKER_LOG']).open('a') as log:
    log.write(' '.join(args) + '\\n')
if 'config' in args and '--format' in args:
    print('{"services":{"dashboard":{}}}')
if 'up' in args and os.getenv('FAIL_UP') == '1':
    sys.exit(9)
''')
        docker.chmod(0o755)
        self.log = self.root / "docker.log"

    def run_script(self, **env):
        variables = dict(os.environ, PATH=f"{self.root / 'bin'}:{os.environ['PATH']}", DOCKER_LOG=str(self.log))
        variables.update(env)
        return subprocess.run(["bash", str(self.root / "scripts/verify-docker.sh")], cwd=self.root, env=variables, capture_output=True, text=True, timeout=15)

    def test_success_starts_and_cleans_up(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS: isolated Docker", result.stdout)
        log = self.log.read_text()
        self.assertIn("up --detach --no-build", log)
        self.assertIn("down --volumes --remove-orphans", log)

    def test_custom_port(self):
        result = self.run_script(OPTIFLOW_DOCKER_PORT="15432")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_invalid_port_without_starting(self):
        result = self.run_script(OPTIFLOW_DOCKER_PORT="80")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.log.exists())

    def test_missing_report_fails_before_docker(self):
        (self.root / "output/scenarios/manifest.json").unlink()
        result = self.run_script()
        self.assertEqual(result.returncode, 2)
        self.assertIn("Missing generated report", result.stderr)
        self.assertFalse(self.log.exists())

    def test_startup_failure_collects_logs_and_cleans_up(self):
        result = self.run_script(FAIL_UP="1")
        self.assertNotEqual(result.returncode, 0)
        log = self.log.read_text()
        self.assertIn("logs --no-color --tail=150", log)
        self.assertIn("down --volumes --remove-orphans", log)

    def test_http_failure_collects_logs_and_cleans_up(self):
        result = self.run_script(FAIL_SMOKE="1")
        self.assertNotEqual(result.returncode, 0)
        log = self.log.read_text()
        self.assertIn("logs --no-color --tail=150", log)
        self.assertIn("down --volumes --remove-orphans", log)


if __name__ == "__main__":
    unittest.main()
