"""Reproducible synthetic-data generator (FOUND-04, D-06, D-08).

`make synth` regenerates train + eval Parquet from fixed master seeds.
PCG64 + SeedSequence.spawn() guarantees byte-identical regeneration
(RESEARCH Pattern 4, Pitfall 2 mitigation).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from numpy.random import PCG64, Generator, SeedSequence

from .state_machines import GENERATORS

# Master seeds (D-08; documented in DATASHEET.md per plan 01-04).
MASTER_TRAIN_SEED = 20260501
MASTER_EVAL_SEED = 20260502

# Per-class sample counts (D-07 uniform-at-train; D-08 sizes).
N_TRAIN = 10_000
N_EVAL = 2_000

# Canonical class list (mirrors GENERATORS insertion order — Pattern 4 Critical note).
CLASSES: list[str] = list(GENERATORS.keys())  # 10 entries, fixed order


def make_per_class_rngs(master_seed: int) -> dict[str, Generator]:
    """Spawn one independent PCG64 sub-stream per class from a master SeedSequence.

    Identical master_seed -> identical sub-streams -> identical samples ->
    byte-identical Parquet (RESEARCH Pattern 4, Pitfall 2 mitigation).
    """
    ss = SeedSequence(master_seed)
    sub_seeds = ss.spawn(len(CLASSES))
    return {cls: Generator(PCG64(s)) for cls, s in zip(CLASSES, sub_seeds, strict=True)}


def _flatten_ping_continuity(frame: dict[str, Any]) -> dict[str, Any]:
    """Flatten the nested PingContinuity sub-dict for Parquet column-friendliness."""
    pc = frame.pop("ping_continuity")
    return {
        **frame,
        "ping_continuity_window_ms": pc["window_ms"],
        "ping_continuity_avg_rtt_ms": pc["avg_rtt_ms"],
        "ping_continuity_packet_loss_pct": pc["packet_loss_pct"],
        "ping_continuity_jitter_ms": pc["jitter_ms"],
    }


_COLUMNS: tuple[str, ...] = (
    "timestamp",
    "os",
    "network_mode",
    "rssi_dbm",
    "bssid",
    "bssid_mode",
    "channel",
    "ping_continuity_window_ms",
    "ping_continuity_avg_rtt_ms",
    "ping_continuity_packet_loss_pct",
    "ping_continuity_jitter_ms",
    "latency_jitter_ms",
    "dns_resolution_ms",
    "dhcp_event_class",
    "auth_event_class",
    "captive_portal_detected",
    "mac_randomization_state",
    "driver_state",
    "per_packet_retry_count",
    "rts_cts_rate",
    "beacon_rssi_dbm",
    "neighbor_ap_count_5ghz",
    "window_ms",
    "class",
)


def generate_split(master_seed: int, n_per_class: int) -> pa.Table:
    """Generate one split (train or eval) deterministically from a master seed.

    Returns a PyArrow Table ready for `pq.write_table()`. Byte-identical given
    the same (master_seed, n_per_class) inputs.

    Implementation note (Pitfall 4 — speed): we build columnar Python lists and
    hand them to `pa.Table.from_pydict`, which is several times faster than
    `pa.Table.from_pylist` on millions of rows.
    """
    rngs = make_per_class_rngs(master_seed)
    columns: dict[str, list[Any]] = {col: [] for col in _COLUMNS}

    for cls in CLASSES:
        # Iterate the canonical CLASSES list (NOT rngs.items()) — list iteration is
        # the byte-identicality anchor (RESEARCH Pattern 4 Critical note).
        rng = rngs[cls]
        for _ in range(n_per_class):
            window = GENERATORS[cls](rng)  # list[dict] (raw — Pitfall 4 speed)
            for frame in window:
                pc = frame["ping_continuity"]
                columns["timestamp"].append(frame["timestamp"])
                columns["os"].append(frame["os"])
                columns["network_mode"].append(frame["network_mode"])
                columns["rssi_dbm"].append(frame["rssi_dbm"])
                columns["bssid"].append(frame["bssid"])
                columns["bssid_mode"].append(frame["bssid_mode"])
                columns["channel"].append(frame["channel"])
                columns["ping_continuity_window_ms"].append(pc["window_ms"])
                columns["ping_continuity_avg_rtt_ms"].append(pc["avg_rtt_ms"])
                columns["ping_continuity_packet_loss_pct"].append(pc["packet_loss_pct"])
                columns["ping_continuity_jitter_ms"].append(pc["jitter_ms"])
                columns["latency_jitter_ms"].append(frame["latency_jitter_ms"])
                columns["dns_resolution_ms"].append(frame["dns_resolution_ms"])
                columns["dhcp_event_class"].append(frame["dhcp_event_class"])
                columns["auth_event_class"].append(frame["auth_event_class"])
                columns["captive_portal_detected"].append(frame["captive_portal_detected"])
                columns["mac_randomization_state"].append(frame["mac_randomization_state"])
                columns["driver_state"].append(frame["driver_state"])
                columns["per_packet_retry_count"].append(frame["per_packet_retry_count"])
                columns["rts_cts_rate"].append(frame["rts_cts_rate"])
                columns["beacon_rssi_dbm"].append(frame["beacon_rssi_dbm"])
                columns["neighbor_ap_count_5ghz"].append(frame["neighbor_ap_count_5ghz"])
                columns["window_ms"].append(frame["window_ms"])
                columns["class"].append(cls)

    return pa.Table.from_pydict(columns)


def main() -> None:
    out_dir = Path("data")
    out_dir.mkdir(exist_ok=True)
    train_tbl = generate_split(MASTER_TRAIN_SEED, N_TRAIN)
    eval_tbl = generate_split(MASTER_EVAL_SEED, N_EVAL)
    pq.write_table(train_tbl, out_dir / "train.parquet")
    pq.write_table(eval_tbl, out_dir / "eval.parquet")
    print(f"Wrote train={train_tbl.num_rows} rows, eval={eval_tbl.num_rows} rows")


if __name__ == "__main__":
    main()
