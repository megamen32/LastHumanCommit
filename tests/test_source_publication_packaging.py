"""The native CLI must ship its source-publication helper at both tool roots."""
from pathlib import Path


def test_source_publication_helper_ships_in_all_tool_projections():
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/common/tools/lhc_source_publication.py").read_bytes()
    package = root / "plugins/last-human-commit"
    for prefix in ("common/tools", "tools", "native/codex/common/tools", "native/codex/tools"):
        assert (package / prefix / "lhc_source_publication.py").read_bytes() == source
