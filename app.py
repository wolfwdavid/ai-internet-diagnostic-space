"""AI Internet Diagnostic — Hugging Face Space.

Phase 1 Space deliverable: hello-world shell. The Phase 1 goal is to lock the
Python 3.13 + Gradio 6.13.x pin combo via the `space-build-sanity.yml` CI gate
BEFORE any application code (Phase 3) adds complexity. Per CONTEXT D-18 and
PITFALLS.md Pitfall 7 (the prior project's pin-drift incident).
"""
from __future__ import annotations

import sys

import gradio as gr

# Runtime version assertions (RESEARCH Pitfall 7 mitigation #2): catch silent
# SDK-metadata drift on first launch.
assert gr.__version__.startswith("6.13"), (
    f"Expected Gradio 6.13.x, got {gr.__version__}"
)
assert sys.version_info[:2] == (3, 13), (
    f"Expected Python 3.13, got {sys.version_info}"
)


demo = gr.Interface(
    fn=lambda x: f"Phase 1 hello-world. You typed: {x}",
    inputs="text",
    outputs="text",
    title="AI Internet Diagnostic (Phase 1 hello-world)",
    description="Phase 3 will replace this with the real diagnostic UI.",
)


if __name__ == "__main__":
    demo.launch()
