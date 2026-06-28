"""Scenario catalog (SCEN-01).

8 named scenarios mapped 1:1 to DisconnectClass slugs per REQUIREMENTS.md
SCEN-01. The 2 unmapped classes (``dns_resolver_fail``, ``isp_upstream_fail``)
remain in the classifier's 10-class taxonomy but have no demo scenario at v1.

Each scenario carries a stable seed (used by plan 03-05 to regenerate cached
narrations deterministically) and a network_mode tag that drives the Phase 2
mask-then-renormalize step (D-CAL-09 -- the LAST frame's network_mode is what
``apply_mask_and_renormalize`` masks against).
"""

from __future__ import annotations

from dataclasses import dataclass

from wifi_diag_schema.enums import DisconnectClass, NetworkMode


@dataclass(frozen=True)
class Scenario:
    """A named demo scenario (SCEN-01)."""

    slug: str
    """Stable URL/cache-friendly identifier (used by 03-05 cache filenames)."""

    display_name: str
    """Plain-English card title (D-SYNTH-01)."""

    description: str
    """One-line elaboration (D-SYNTH-01 card body)."""

    class_slug: DisconnectClass
    """The DisconnectClass this scenario is engineered to surface."""

    network_mode: NetworkMode
    """Visible 'enterprise' / 'captive' / 'home' tag on the card and the value
    written into the LAST frame so D-CAL-09 mask-then-renormalize behaves the
    way the demo expects."""

    seed: int
    """Fixed seed for ``np.random.default_rng`` -- guarantees deterministic
    telemetry across runs (used by plan 03-05 cache regen)."""

    n_frames: int
    """UI hint: window length in seconds for the timeline x-axis label
    (D-TIMELINE-09). All Phase 1 state machines emit 30 frames; this field
    is informational, not used to truncate generator output."""


# Per REQUIREMENTS.md SCEN-01: 8 scenarios mapped 1:1 to 8 of 10 DisconnectClass
# slugs. The mapping below is the canonical demo lineup; do NOT reorder without
# updating .planning/phases/03-space-ui-real-inference/03-CONTEXT.md.
SCENARIOS: list[Scenario] = [
    Scenario(
        slug="school_radius_overload",
        display_name="school RADIUS overload at the bell",
        description=(
            "Class change -- many laptops re-auth simultaneously; RADIUS server saturates."
        ),
        class_slug="radius_timeout",
        network_mode="enterprise",
        seed=20260601,
        n_frames=30,
    ),
    Scenario(
        slug="walking_down_hall_roam_fails",
        display_name="walking down the hall -- roam fails",
        description="RSSI degrades smoothly; roam to next AP fails at re-key.",
        class_slug="ap_roam_rekey_fail",
        network_mode="enterprise",
        seed=20260602,
        n_frames=30,
    ),
    Scenario(
        slug="cert_expired_this_morning",
        display_name="cert expired this morning",
        description="802.1X EAP fails because the device cert expired overnight.",
        class_slug="auth_8021x_eap_fail",
        network_mode="enterprise",
        seed=20260603,
        n_frames=30,
    ),
    Scenario(
        slug="coffee_shop_captive_expired",
        display_name="coffee-shop captive portal expired",
        description="Portal session token expired; redirects begin failing.",
        class_slug="captive_portal_expiry",
        network_mode="captive",
        seed=20260604,
        n_frames=30,
    ),
    Scenario(
        slug="dhcp_pool_exhausted",
        display_name="DHCP pool exhausted at conference",
        description=("Conference floor -- DHCP pool runs out; DISCOVER goes unanswered."),
        class_slug="dhcp_lease_churn",
        network_mode="enterprise",
        seed=20260605,
        n_frames=30,
    ),
    Scenario(
        slug="apple_randomized_mac",
        display_name="Apple device on randomized MAC",
        description="Network rejects the per-network randomized MAC.",
        class_slug="mac_randomization_reject",
        network_mode="enterprise",
        seed=20260606,
        n_frames=30,
    ),
    Scenario(
        slug="laptop_just_woke_up",
        display_name="laptop just woke up -- Wi-Fi confused",
        description="Driver post-wake state; U-APSD bug; reconnect stalls.",
        class_slug="driver_power_save_wake",
        network_mode="enterprise",
        seed=20260607,
        n_frames=30,
    ),
    Scenario(
        slug="stuck_on_weak_ap",
        display_name="stuck on weak AP at the back of the room",
        description="Weak signal; client refuses to roam to a stronger AP.",
        class_slug="rf_sticky_client",
        network_mode="home",
        seed=20260608,
        n_frames=30,
    ),
]

SCENARIOS_BY_SLUG: dict[str, Scenario] = {s.slug: s for s in SCENARIOS}
