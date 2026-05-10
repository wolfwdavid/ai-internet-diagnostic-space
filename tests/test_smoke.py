"""Phase 3 smoke tests -- UI-01, UI-02 layout order, UI-04 cold-start, Pitfall 7/F.

Extends the Phase 1 baseline (Python 3.13 + Gradio 6.13.x runtime check) with
the Phase 3 plan 03-01 surface: two-tab Synthetic/Live shell, cold-start
banner, and the D-SYNTH-04 'Planned flow' Live-tab preview asset.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

_REPO = Path(__file__).parent.parent
_APP = _REPO / "app.py"
_REQS = _REPO / "requirements.txt"
_README = _REPO / "README.md"


def _import_demo() -> object:
    spec = importlib.util.spec_from_file_location("app", _APP)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.demo


# --- Phase 1 regression guards (preserved) ----------------------------------


def test_app_imports_cleanly() -> None:
    demo = _import_demo()
    assert hasattr(demo, "launch"), "app.py must expose a `demo` Gradio Blocks/Interface"


def test_python_313() -> None:
    assert sys.version_info[:2] == (3, 13), (
        f"Expected Python 3.13, got {sys.version_info}"
    )


def test_gradio_pin() -> None:
    import gradio as gr

    assert gr.__version__.startswith("6.13"), (
        f"Expected Gradio 6.13.x, got {gr.__version__}"
    )


# --- Phase 3 plan 03-01 surface ---------------------------------------------


def test_two_tabs() -> None:
    demo = _import_demo()
    blob = str(demo.config) if hasattr(demo, "config") else str(demo.get_config_file())
    assert "Synthetic" in blob and "Live" in blob, (
        "Phase 3 shell must declare both Synthetic and Live tabs (UI-01)"
    )


def test_synthetic_tab_is_default() -> None:
    """D-SYNTH-03: Synthetic tab declared FIRST so Gradio renders it as default."""
    blob = _APP.read_text()
    i_syn = blob.find('"Synthetic"')
    i_live = blob.find('"Live"')
    assert i_syn != -1 and i_live != -1 and i_syn < i_live, (
        "Synthetic tab must come before Live in the source (D-SYNTH-03 default landing)"
    )


def test_cold_start_banner() -> None:
    """UI-04: cold-start banner copy visible above tabs."""
    blob = _APP.read_text()
    assert "Space is waking up" in blob, "UI-04 cold-start banner copy missing"


def test_runtime_assertions_preserved() -> None:
    """Pitfall 7 + Pitfall F: runtime version assertions MUST NOT regress."""
    blob = _APP.read_text()
    assert 'gr.__version__.startswith("6.13")' in blob, (
        "Pitfall 7 runtime assertion missing (gradio version pin guard)"
    )
    assert "sys.version_info[:2] == (3, 13)" in blob, (
        "Python version runtime assertion missing"
    )


def test_no_gradio_in_requirements() -> None:
    """Pitfall 7: README frontmatter is the SoT; requirements.txt MUST NOT pin gradio."""
    for line in _REQS.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        assert not re.match(r"^gradio\b", stripped, re.IGNORECASE), (
            f"Pitfall 7 regression: gradio pinned in requirements.txt: {stripped!r}"
        )


def test_readme_python_version_quoted() -> None:
    """Pitfall F: python_version must be QUOTED in HF Space frontmatter."""
    readme = _README.read_text()
    assert 'python_version: "3.13"' in readme, (
        "Pitfall F: python_version must be quoted (e.g. python_version: \"3.13\")"
    )


def test_readme_sdk_version_pinned() -> None:
    """Pitfall 7: sdk_version is the single source of truth for Gradio version."""
    assert "sdk_version: 6.13.0" in _README.read_text(), (
        "README frontmatter must pin sdk_version: 6.13.0 (single source of truth)"
    )


def test_live_tab_planned_flow_preview() -> None:
    """D-SYNTH-04: Live tab v1 shell must include the 'planned flow' preview asset.

    Format is Claude's discretion per CONTEXT.md -- text-only Markdown callout
    chosen as cheapest viable; future PNG/GIF/Lottie can replace this in v1.x
    without changing the surrounding shell.
    """
    blob = _APP.read_text()
    assert "Planned flow" in blob, "D-SYNTH-04 preview asset missing from Live tab"
    assert "D-SYNTH-04" in blob, "D-SYNTH-04 decision ID not referenced in Live tab"


def test_layout_order() -> None:
    """D-VERDICT-08: stacked column order verdict -> what-to-do -> timeline.

    Plan 03-02 ships anchor comments in app.py so this static-source test can
    confirm the canonical ordering without instantiating Gradio Blocks. The
    actual Gradio composition is in src/space/ui/synthetic_tab.py.
    """
    blob = _APP.read_text()
    i_v = blob.find("build_verdict_card")
    i_w = blob.find("build_what_to_do_card")
    i_t = blob.find("build_timeline")
    assert -1 < i_v < i_w < i_t, (
        f"verdict -> what-to-do -> timeline order broken in app.py: "
        f"verdict@{i_v}, what-to-do@{i_w}, timeline@{i_t}"
    )


# --- Phase 3 plan 03-06 surface (UI-05 export + UI-06 CTA) ------------------


def test_cta_present() -> None:
    """UI-06: 'Try it on a real network' CTA visible on Synthetic + Live tabs."""
    blob = _APP.read_text()
    synth = (Path(__file__).parent.parent / "src/space/ui/synthetic_tab.py").read_text()
    assert "Try it on a real network" in (blob + synth), (
        "UI-06 CTA copy missing from both Synthetic and Live tab surfaces"
    )


def test_cta_links_to_agent_repo() -> None:
    """UI-06: CTA points at the agent repo install instructions (Phase 4 owns)."""
    blob = _APP.read_text()
    synth = (Path(__file__).parent.parent / "src/space/ui/synthetic_tab.py").read_text()
    assert "github.com/wolfwdavid/ai-internet-diagnostic-agent" in (blob + synth), (
        "UI-06 CTA must link to the agent repo at github.com/wolfwdavid/ai-internet-diagnostic-agent"
    )


def test_export_buttons_in_synthetic_tab() -> None:
    """UI-05: Synthetic tab references both export builders."""
    synth = (Path(__file__).parent.parent / "src/space/ui/synthetic_tab.py").read_text()
    assert "build_markdown_export" in synth, (
        "UI-05: synthetic_tab must wire build_markdown_export"
    )
    assert "build_json_export" in synth, (
        "UI-05: synthetic_tab must wire build_json_export"
    )


def test_export_label_present() -> None:
    """UI-05: 'Export verdict' button label literal in synthetic_tab source."""
    synth = (Path(__file__).parent.parent / "src/space/ui/synthetic_tab.py").read_text()
    assert "Export verdict" in synth, (
        "UI-05: synthetic_tab must render an 'Export verdict' control"
    )
