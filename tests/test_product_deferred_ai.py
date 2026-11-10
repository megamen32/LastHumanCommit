# LHC:COVERS src/common/tools/lhc_product.py
"""A leaf the agent deferred looks deferred on the delivery side, not queued."""
from pathlib import Path

from _inprocess import load_module

ROOT = Path(__file__).resolve().parents[1]


def test_a_leaf_deferred_by_the_agent_is_shown_as_deferred():
    product = load_module(ROOT / "src/common/tools/lhc_product.py", name="lhc_product_deferred_ai")
    leaves = product.product_leaves({"tasks": [
        {"id": "L1", "label": "отложено ИИ", "status": "deferred_ai"},
        {"id": "L2", "label": "отложено владельцем", "status": "deferred"},
    ]})
    assert [leaf["status"] for leaf in leaves] == ["deferred", "deferred"]
