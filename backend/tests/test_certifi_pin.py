import re
import unittest
from pathlib import Path

REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"
MINIMUM_FIXED_CERTIFI = (2026, 10, 18)


def _pinned_version(package):
    pattern = re.compile(
        rf"^{re.escape(package)}\s*==\s*([0-9][0-9A-Za-z.\-]*)$", re.MULTILINE
    )
    match = pattern.search(REQUIREMENTS.read_text(encoding="utf-8"))
    if match is None:
        raise AssertionError(f"{package} is not pinned in {REQUIREMENTS}")
    return tuple(int(part) for part in match.group(1).split("."))


class CertifiPinTest(unittest.TestCase):
    def test_certifi_pin_includes_fixed_ca_bundle(self):
        self.assertGreaterEqual(
            _pinned_version("certifi"),
            MINIMUM_FIXED_CERTIFI,
            "certifi must be pinned at or above the CA bundle fix release",
        )


if __name__ == "__main__":
    unittest.main()
