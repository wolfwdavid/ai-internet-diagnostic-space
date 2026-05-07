---
title: AI Internet Diagnostic
emoji: 📡
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 6.13.0
python_version: "3.13"
app_file: app.py
pinned: false
license: apache-2.0
---

# AI Internet Diagnostic — HF Space

AI-powered diagnostic for enterprise / school / public Wi-Fi disconnects (802.1X, captive-portal, RADIUS-backed networks). Multi-class classifier + time-series anomaly detector + LLM narrator — explicitly not a "GPT wrapper".

**Phase 1 status:** Hello-world Gradio shell. Phase 3 wires the real verdict UI to the trained models from the [Model repo](https://huggingface.co/WolfDavid/ai-internet-diagnostic-model).

## Pin posture (Pitfall 7 mitigation)

The Gradio version is pinned in this README frontmatter (`sdk_version: 6.13.0`) — the SINGLE source of truth. `requirements.txt` does NOT contain a `gradio` line; double-pinning was the prior project's drift incident.

Python is pinned to 3.13 in both this frontmatter and `pyproject.toml`'s `requires-python`.

## License

Apache-2.0.
