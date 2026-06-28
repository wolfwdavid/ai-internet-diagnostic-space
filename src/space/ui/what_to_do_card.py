"""'What to do' suggested-fix card (D-VERDICT-03).

Renders directly below the verdict card per D-VERDICT-08 stacked column
layout. The card contains the narrator's ``suggested_fix`` text verbatim --
the LLM and templated narrators both populate this field with the
recommended remediation step (LLM-04).
"""

from __future__ import annotations

from wifi_diag_schema.verdict import Verdict


def build_what_to_do_card(verdict: Verdict) -> str:
    """Render the recommended-action card as an HTML string.

    Renders the verdict's ``suggested_fix`` verbatim (D-VERDICT-03). The
    blue-tinted left border matches the IT-ticket reading order signal:
    'here is the action item'.
    """
    return (
        '<div class="what-to-do-card" '
        'style="border-left:4px solid #3b82f6; padding:1em; background:#eff6ff;">\n'
        "  <h3>Recommended action</h3>\n"
        f"  <p>{verdict.suggested_fix}</p>\n"
        "</div>"
    )
