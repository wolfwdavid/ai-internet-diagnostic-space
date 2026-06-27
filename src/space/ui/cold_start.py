"""Cold-start UX (UI-04). Shown above tabs while the Space is waking up.

HF free-CPU Spaces sleep after 48 hours of inactivity; the first request after
wake-up takes ~10-30s. This banner sets visitor expectations honestly and
mirrors the pattern used in the project owner's prior HF Spaces.
"""

from __future__ import annotations

COLD_START_MARKDOWN = (
    "> Space is waking up -- first request takes ~30s. Subsequent requests are sub-second."
)
