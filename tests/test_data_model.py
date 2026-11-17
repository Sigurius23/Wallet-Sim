"""The YAML example in docs/DATA_MODEL.md and the template must parse and agree on their top-level keys."""
import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")
ROOT = Path(__file__).resolve().parents[1]


def _example():
    text = (ROOT / "docs" / "DATA_MODEL.md").read_text()
    return yaml.safe_load(re.search(r"```yaml\n(.*?)```", text, re.S).group(1))


def test_example_parses_and_has_expected_sections():
    doc = _example()
    for key in ("archive", "leather", "components", "process_steps", "panels", "folds"):
        assert key in doc
    mat = doc["leather"][0]["material"]
    assert mat["poisson"]["source"] == "assumed"          # regression: used to be swallowed by a comment


def test_template_parses_and_matches_example_keys():
    template = yaml.safe_load((ROOT / "wallets" / "_template" / "wallet.yaml").read_text())
    assert set(_example()) <= set(template)


def test_process_steps_use_known_windows():
    from walletsim.materials import WINDOWS

    for step in _example()["process_steps"]:
        assert step["window"] in WINDOWS
