.PHONY: cache-narrations cache-narrations-templated test

# Default: Anthropic Haiku 4.5 regeneration (requires ANTHROPIC_API_KEY).
# Used by .github/workflows/regenerate-narrations.yml (D-NARRATOR-09 -- key
# lives only as a GitHub Actions repository secret).
cache-narrations:
	uv run python scripts/regenerate_cache.py --scenarios all

# Bootstrap / fallback: templated narrator only (no API key required).
# Produces full-Verdict-shape JSONs structurally indistinguishable from
# Anthropic output (D-NARRATOR-03 / LLM-05).
cache-narrations-templated:
	uv run python scripts/regenerate_cache.py --scenarios all --templated

test:
	uv run pytest -x --tb=short
