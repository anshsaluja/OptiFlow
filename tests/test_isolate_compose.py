"""Regression tests for isolated Docker dashboard port configuration."""
import copy
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from isolate_compose import isolate


def sample():
    return {
        "name": "optiflow",
        "services": {
            "dashboard": {
                "ports": [{"target": 5173, "published": "5173", "host_ip": "127.0.0.1", "protocol": "tcp"}],
                "volumes": [{"type": "bind", "source": "/tmp/optiflow", "target": "/workspace"}],
            }
        },
        "volumes": {"dashboard_node_modules": {}},
    }


class IsolateComposeTests(unittest.TestCase):
    def test_replaces_original_publication(self):
        config = sample()
        result = isolate(config, 15173)
        self.assertEqual(result["services"]["dashboard"]["ports"][0]["published"], "15173")
        self.assertEqual(len(result["services"]["dashboard"]["ports"]), 1)
        self.assertEqual(result["services"]["dashboard"]["ports"][0]["host_ip"], "127.0.0.1")

    def test_preserves_other_configuration(self):
        original = sample()
        result = isolate(copy.deepcopy(original), 16000)
        self.assertEqual(result["services"]["dashboard"]["volumes"], original["services"]["dashboard"]["volumes"])
        self.assertEqual(result["volumes"], original["volumes"])

    def test_invalid_ports(self):
        for port in (0, 1023, 65536, True, "15173"):
            with self.subTest(port=port), self.assertRaises(ValueError):
                isolate(sample(), port)

    def test_rejects_extra_mappings(self):
        config = sample()
        config["services"]["dashboard"]["ports"].append(dict(config["services"]["dashboard"]["ports"][0]))
        with self.assertRaises(ValueError):
            isolate(config, 15173)

    def test_rejects_public_bind(self):
        config = sample()
        config["services"]["dashboard"]["ports"][0]["host_ip"] = "0.0.0.0"
        with self.assertRaises(ValueError):
            isolate(config, 15173)

    def test_rejects_wrong_target(self):
        config = sample()
        config["services"]["dashboard"]["ports"][0]["target"] = 8080
        with self.assertRaises(ValueError):
            isolate(config, 15173)

    def test_rejects_missing_service(self):
        with self.assertRaises(ValueError):
            isolate({"services": {}}, 15173)


if __name__ == "__main__":
    unittest.main()
