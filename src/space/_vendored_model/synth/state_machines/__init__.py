"""Per-class state-machine generators (D-06).

Insertion order MATTERS for byte-identicality (RESEARCH Pattern 4 Critical note):
the order below is the order classes are iterated in `generate.py`, which
determines the order rows are appended to the Parquet table.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from numpy.random import Generator

from .ap_roam_rekey_fail import generate as gen_ap_roam
from .auth_8021x_eap_fail import generate as gen_auth
from .captive_portal_expiry import generate as gen_captive
from .dhcp_lease_churn import generate as gen_dhcp
from .dns_resolver_fail import generate as gen_dns
from .driver_power_save_wake import generate as gen_driver
from .isp_upstream_fail import generate as gen_isp
from .mac_randomization_reject import generate as gen_mac_rand
from .radius_timeout import generate as gen_radius
from .rf_sticky_client import generate as gen_sticky

GeneratorFn = Callable[[Generator], list[dict[str, Any]]]

# CANONICAL ORDER — do NOT reorder without bumping schema/data version.
GENERATORS: dict[str, GeneratorFn] = {
    "auth_8021x_eap_fail": gen_auth,
    "ap_roam_rekey_fail": gen_ap_roam,
    "radius_timeout": gen_radius,
    "captive_portal_expiry": gen_captive,
    "mac_randomization_reject": gen_mac_rand,
    "dhcp_lease_churn": gen_dhcp,
    "dns_resolver_fail": gen_dns,
    "driver_power_save_wake": gen_driver,
    "rf_sticky_client": gen_sticky,
    "isp_upstream_fail": gen_isp,
}
