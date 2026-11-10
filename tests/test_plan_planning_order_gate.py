# LHC:COVERS src/common/tools/lhc_plan_json.py
"""The tool enforces the planning order: no first executable leaf without critique and summary."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_plan_json as pj  # noqa: E402

FACTS = ["файл a.conf задаёт маршрут default через шлюз :: /etc/a.conf",
         "хост gw: ip rule показывает таблицу 100 для клиента :: ssh gw ip rule show",
         "сервис xray на узле слушает порт 443 и активен :: systemctl status xray"]
LEAF = {"label": "impl", "estimate_minutes": 10}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LHC_PLAN_MIRROR_CONFIG", str(tmp_path / "no-mirror.json"))


def plan(tmp_path, **fields):
    base = {"title": "T", "mode": "fullcycle", "recon": FACTS, "acceptance_scenario": "curl виден IP"}
    (tmp_path / "plan.json").write_text(json.dumps({**base, **fields}, ensure_ascii=False))


def test_refused_without_summary_and_without_critique(tmp_path):
    plan(tmp_path, critique="критика")
    with pytest.raises(pj.LeafError, match=r"summary.*update_plan.*исследование → черновик → критика → отбор по Парето"):
        pj.update_leaf(tmp_path, "L01", LEAF, create=True)
    plan(tmp_path, summary="этапы")
    with pytest.raises(pj.LeafError, match=r"critique.*update_plan"):
        pj.update_leaf(tmp_path, "L01", LEAF, create=True)


def test_accepted_with_both_fields_set_by_update_plan(tmp_path):
    plan(tmp_path)
    pj.update_plan(tmp_path, {"critique": "критика и Парето", "summary": "этапы"})
    pj.update_leaf(tmp_path, "L01", LEAF, create=True)


def test_plan_with_an_executable_leaf_is_never_blocked(tmp_path):
    plan(tmp_path, summary="s", critique="c")
    pj.update_leaf(tmp_path, "L01", LEAF, create=True)
    plan(tmp_path)  # running plan written before the gate existed
    pj.update_leaf(tmp_path, "L02", LEAF, create=True)


def test_milestone_and_research_leaves_are_always_accepted(tmp_path):
    plan(tmp_path)
    pj.update_leaf(tmp_path, "M1", {"label": "Этап", "kind": "milestone", "estimate_minutes": 45}, create=True)
    pj.update_leaf(tmp_path, "R1", {"label": "разведка", "kind": "research", "estimate_minutes": 10}, create=True)
    with pytest.raises(pj.LeafError, match="critique"):
        pj.update_leaf(tmp_path, "L01", LEAF, create=True)
