"""Verdict card builder (D-VERDICT-01..07).

Headline + colored confidence badge (HIGH/MED/LOW) + display name + slug
subtitle + always-visible top 3 alternatives + 'Show all 10' expander.

Per .planning/phases/03-space-ui-real-inference/03-CONTEXT.md decisions:

- D-VERDICT-01: confidence-band thresholds (green >=0.80, amber 0.60-0.80,
  red <0.60); colored badge with percentage.
- D-VERDICT-02: top-3 alternatives always-visible; remaining 7 behind a
  ``<details>`` expander labeled 'Show all 10'.
- D-VERDICT-04: large display name + small slug subtitle.
- D-VERDICT-07: HIGH/MED/LOW uppercase text label inside the colored badge
  (color-blind safe: text label reads regardless of color perception).

API surface (consumed by ``synthetic_tab.card_click_handler``):

    build_verdict_card(verdict: Verdict) -> str   # HTML string

The shape matches the inline stub in ``synthetic_tab.py`` so plan 03-03's
defensive try/except import picks this module up automatically.
"""

from __future__ import annotations

from wifi_diag_schema.enums import DISPLAY_NAMES
from wifi_diag_schema.verdict import Verdict

# D-VERDICT-01: confidence-band thresholds.
_HIGH_THRESHOLD = 0.80
_MED_THRESHOLD = 0.60


def _confidence_band(conf: float) -> str:
    """D-VERDICT-01 + D-VERDICT-07: HIGH / MED / LOW band label.

    Thresholds:
      - conf >= 0.80 -> HIGH (green)
      - 0.60 <= conf < 0.80 -> MED (amber)
      - conf < 0.60 -> LOW (red)
    """
    if conf >= _HIGH_THRESHOLD:
        return "HIGH"
    if conf >= _MED_THRESHOLD:
        return "MED"
    return "LOW"


# D-VERDICT-01 + D-VERDICT-07: badge colors per band.
# Word + hex pair lets unit tests match either form (color-name OR hex value).
_BADGE_COLORS: dict[str, tuple[str, str]] = {
    "HIGH": ("green", "#22c55e"),
    "MED": ("amber", "#f59e0b"),
    "LOW": ("red", "#ef4444"),
}


def build_verdict_card(verdict: Verdict) -> str:
    """Render the verdict card as an HTML string (Markdown-compatible block).

    Layout (top-to-bottom):
      1. Display name (large, D-VERDICT-04)
      2. Slug subtitle (small monospace, D-VERDICT-04)
      3. Colored confidence badge (HIGH/MED/LOW + pct, D-VERDICT-01/07)
      4. Headline paragraph (LLM-04 narrator output)
      5. 'Other possibilities' list with rank-2 + rank-3 always visible
         (D-VERDICT-02)
      6. ``<details>`` expander labeled 'Show all 10' with the remaining 7
         alternatives (D-VERDICT-02)
    """
    band = _confidence_band(verdict.confidence)
    color_word, color_hex = _BADGE_COLORS[band]
    display = DISPLAY_NAMES[verdict.top_class]
    pct = int(round(verdict.confidence * 100))

    # Top 3 alternatives -- always visible (D-VERDICT-02).
    top3 = verdict.top_k[1:3]
    alts_html = "\n".join(
        f"  <li><b>{int(round(p * 100))}%</b> -- {DISPLAY_NAMES[c]} <code>{c}</code></li>"
        for c, p in top3
    )

    # Remaining 7 -- 'Show all 10' expander (D-VERDICT-02).
    rest = verdict.top_k[3:]
    rest_html = "\n".join(
        f"  <li>{int(round(p * 100))}% -- {DISPLAY_NAMES[c]} <code>{c}</code></li>" for c, p in rest
    )

    return (
        '<div class="verdict-card">\n'
        f'  <h2 style="margin-bottom: 0.25em;">{display}</h2>\n'
        f'  <div style="font-size: 0.85em; color: #6b7280;">'
        f"<code>{verdict.top_class}</code></div>\n"
        '  <div style="margin: 1em 0; display: flex; align-items: center; gap: 1em;">\n'
        f'    <span style="background:{color_hex}; color:white; padding:0.4em 1em; '
        'font-weight:bold; border-radius:6px;">\n'
        f"      {pct}% &middot; {band}\n"
        "    </span>\n"
        f'    <span style="color:{color_word};">confidence</span>\n'
        "  </div>\n"
        f"  <p>{verdict.headline}</p>\n"
        "  <h4>Other possibilities</h4>\n"
        "  <ul>\n"
        f"{alts_html}\n"
        "  </ul>\n"
        "  <details>\n"
        "    <summary>Show all 10</summary>\n"
        "    <ul>\n"
        f"{rest_html}\n"
        "    </ul>\n"
        "  </details>\n"
        "</div>"
    )
