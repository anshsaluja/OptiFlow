"""Regression checks for the read-only Docker dashboard checkout.

These are static configuration checks, not a substitute for starting Docker.
"""
import unittest
from pathlib import Path

COMPOSE = Path(__file__).resolve().parents[1] / "compose.yaml"


class DockerDashboardContractTests(unittest.TestCase):
    def test_dependency_install_does_not_write_lockfile_to_read_only_checkout(self):
        config = COMPOSE.read_text(encoding="utf-8")
        self.assertIn("./:/workspace:ro", config)
        self.assertIn("--package-lock=false", config)
        self.assertIn("--no-save", config)
        self.assertIn("dashboard_node_modules:/workspace/dashboard/node_modules", config)
        self.assertIn("dashboard_sveltekit:/workspace/dashboard/.svelte-kit", config)

    def test_dashboard_only_listens_on_loopback(self):
        config = COMPOSE.read_text(encoding="utf-8")
        self.assertIn("127.0.0.1:5173:5173", config)


if __name__ == "__main__":
    unittest.main()
