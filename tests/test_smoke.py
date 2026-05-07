"""Phase 1 smoke: app.py imports cleanly with the expected Gradio + Python pins.

The full Space build sanity is run by the dedicated `space-build-sanity.yml`
workflow (RESEARCH Pattern 9). This test is a unit-level mirror that ci.yml runs.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def test_app_imports_cleanly():
    spec = importlib.util.spec_from_file_location(
        "app", Path(__file__).parent.parent / "app.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "demo"), "app.py must expose a `demo` Gradio interface"


def test_python_313():
    assert sys.version_info[:2] == (3, 13), (
        f"Expected Python 3.13, got {sys.version_info}"
    )


def test_gradio_pin():
    import gradio as gr

    assert gr.__version__.startswith("6.13"), (
        f"Expected Gradio 6.13.x, got {gr.__version__}"
    )
