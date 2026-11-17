#!/usr/bin/env python3
"""MP 4.2 - Rule-based IoT connectivity technology selector.

Ranks NB-IoT, LTE-M, LoRaWAN, 5G RedCap and short-range (BLE/Zigbee) for a deployment described by the six
Section 4.3 axes: data rate, coverage, battery life, mobility, infrastructure ownership, cost sensitivity.

Pipeline (every step is traceable, see SCORING / METHODOLOGY in the report):
  1. map the scenario's raw inputs onto the 0-5 scale            (map_* functions)
  2. look up each technology's 0-5 capability per axis           (CAPABILITY / SUITABILITY tables)
  3. axis score = 5 - 1.5*shortfall - 0.3*surplus  (ordinal axes) or direct suitability lookup (categorical axes)
  4. weighted sum / sum(weights), scaled to 0-100                (WEIGHTS)
  5. rule-based adjustments for cases a plain sum handles badly  (RULES)
  6. rank + generate a justification naming the axes that drove the result

Usage:  python3 iot_selector.py                 -> validate the 4 worked scenarios + 1 new scenario
        python3 iot_selector.py --interactive   -> enter your own scenario
        python3 iot_selector.py --weights data=2,coverage=1   -> override weights
"""
import argparse, csv, sys
from dataclasses import dataclass

TECHS = ["NB-IoT", "LTE-M", "LoRaWAN", "5G RedCap", "Short-range (BLE/Zigbee)"]
AXES = ["data_rate", "coverage", "battery", "mobility", "ownership", "cost"]

# ---------------------------------------------------------------- tunable constants
WEIGHTS = dict(data_rate=1.0, coverage=1.5, battery=1.0, mobility=1.0, ownership=0.75, cost=0.75)
SHORTFALL_PENALTY = 1.5      # score points lost per level the technology falls SHORT of the requirement
SURPLUS_PENALTY = 0.3        # points lost per level of over-capability (wasted cost/power)

# ------------------------------------------- ordinal axes: capability on 0-5 (higher = more of it)
CAPABILITY = {
    #                 data_rate  battery  cost_efficiency
    "NB-IoT":                   dict(data_rate=2, battery=4, cost=4),   # ~60-250 kbps | PSM, ~10 y | cheap module, small subscription
    "LTE-M":                    dict(data_rate=3, battery=3, cost=3),   # ~1 Mbps      | eDRX/PSM, 3-7 y | mid-price + subscription
    "LoRaWAN":                  dict(data_rate=1, battery=5, cost=5),   # 0.3-50 kbps  | >10 y | cheap module, no per-device fee if private
    "5G RedCap":                dict(data_rate=5, battery=2, cost=2),   # 10s of Mbps  | days-months | newest/dearest module
    "Short-range (BLE/Zigbee)": dict(data_rate=3, battery=4, cost=5),   # 0.25-2 Mbps  | months-years | cheapest silicon
}
# ---------------------------------------- categorical axes: direct 0-5 suitability per category
COVERAGE = {   # deep_indoor | wide_area_cellular | long_range_rural (no carrier assumed) | short_range_only
    "NB-IoT":    dict(deep_indoor=5, wide_area_cellular=4, long_range_rural=2, short_range_only=1),
    "LTE-M":     dict(deep_indoor=4, wide_area_cellular=5, long_range_rural=2, short_range_only=1),
    "LoRaWAN":   dict(deep_indoor=4, wide_area_cellular=3, long_range_rural=5, short_range_only=2),
    "5G RedCap": dict(deep_indoor=2, wide_area_cellular=5, long_range_rural=1, short_range_only=1),
    "Short-range (BLE/Zigbee)": dict(deep_indoor=3, wide_area_cellular=0, long_range_rural=0, short_range_only=5),
}
MOBILITY = {   # stationary | local | wide_area | global_roaming
    "NB-IoT":    dict(stationary=5, local=4, wide_area=2, global_roaming=2),
    "LTE-M":     dict(stationary=5, local=5, wide_area=4, global_roaming=4),
    "LoRaWAN":   dict(stationary=5, local=3, wide_area=1, global_roaming=1),
    "5G RedCap": dict(stationary=5, local=5, wide_area=5, global_roaming=4),
    "Short-range (BLE/Zigbee)": dict(stationary=5, local=3, wide_area=0, global_roaming=0),
}
OWNERSHIP = {  # preference: carrier (operator-managed) | either | self (own gateways/network)
    "NB-IoT":    dict(carrier=5, either=5, self=0),
    "LTE-M":     dict(carrier=5, either=5, self=0),
    "LoRaWAN":   dict(carrier=2, either=5, self=5),
    "5G RedCap": dict(carrier=5, either=5, self=1),
    "Short-range (BLE/Zigbee)": dict(carrier=1, either=5, self=5),
}
SELF_OWNED = {"LoRaWAN", "Short-range (BLE/Zigbee)"}

# ---------------------------------------------------------------- input mapping (raw -> 0..5)
def map_data_rate(bps):          # required level
    for lim, lvl in ((5e3, 1), (100e3, 2), (1e6, 3), (10e6, 4)):
        if bps <= lim: return lvl
    return 5
def map_battery(years):
    for lim, lvl in ((0.5, 1), (2, 2), (5, 3), (10, 4)):
        if years <= lim: return lvl
    return 5
def map_cost(devices, budget):   # cost sensitivity level
    base = dict(generous=1, moderate=3, tight=4)[budget]
    return min(5, base + (1 if devices >= 10_000 else 0))

@dataclass
class Scenario:
    name: str
    rate_bps: float            # or derive with rate_from_message()
    coverage: str
    battery_years: float
    mobility: str
    ownership: str
    devices: int
    budget: str

def rate_from_message(msg_bytes, interval_s): return msg_bytes * 8 / interval_s

# ------------------------------------------------------------------- scoring
def ordinal(cap, req):
    short, extra = max(0, req - cap), max(0, cap - req)
    return max(0.0, min(5.0, 5 - SHORTFALL_PENALTY * short - SURPLUS_PENALTY * extra))

def axis_scores(tech, s):
    c = CAPABILITY[tech]
    return dict(
        data_rate=ordinal(c["data_rate"], map_data_rate(s.rate_bps)),
        coverage=COVERAGE[tech][s.coverage],
        battery=ordinal(c["battery"], map_battery(s.battery_years)),
        mobility=MOBILITY[tech][s.mobility],
        ownership=OWNERSHIP[tech][s.ownership],
        cost=ordinal(c["cost"], map_cost(s.devices, s.budget)),
    )

def rules(tech, s, base):
    """Return (adjustment_in_0to5_points, [explanations]) for constraints a weighted sum handles poorly."""
    adj, why = 0.0, []
    if tech == "LoRaWAN" and s.mobility in ("wide_area", "global_roaming"):
        adj -= 1.5; why.append("R1 -1.5: LoRaWAN has no cellular-style handover/roaming for wide-area mobility")
    if (s.ownership in ("either", "self") and map_cost(s.devices, s.budget) >= 4 and s.devices >= 1000
            and s.coverage != "short_range_only" and tech in SELF_OWNED):
        adj += 0.5; why.append("R2 +0.5: severe cost pressure at scale (>=1000 devices, wide/indoor coverage) favours self-owned networks (no per-device fees)")
    if s.ownership == "self" and tech not in SELF_OWNED:
        adj -= 1.5; why.append("R3 -1.5: operator-only technology cannot satisfy a self-owned requirement")
    if s.coverage != "short_range_only" and tech.startswith("Short-range") and s.coverage != "deep_indoor":
        adj -= 1.0; why.append("R4 -1.0: short-range links need a gateway/backhaul to reach a wide-area service")
    if map_data_rate(s.rate_bps) >= 4 and CAPABILITY[tech]["data_rate"] <= 2:
        adj -= 1.0; why.append("R5 -1.0: sustained >1 Mbps is beyond this LPWAN class")
    return adj, why

def explain(tech, ax, s, w, fired):
    contrib = sorted(AXES, key=lambda a: -ax[a] * w[a])
    strong = [a for a in contrib if ax[a] >= 4.5][:3]
    weak = sorted([a for a in AXES if ax[a] <= 3.0], key=lambda a: ax[a] * w[a])[:2]
    nice = lambda a: a.replace("_", " ")
    parts = []
    if strong: parts.append("strong on " + ", ".join(f"{nice(a)} ({ax[a]:.1f})" for a in strong))
    if weak:   parts.append("held back by " + ", ".join(f"{nice(a)} ({ax[a]:.1f})" for a in weak))
    txt = "; ".join(parts) + "." if parts else "mid-range on every axis."
    if fired: txt += " " + " ".join(f.split(":")[0] for f in fired) + " applied."
    return txt[0].upper() + txt[1:]

def rank(s, w=None):
    w = w or WEIGHTS
    out = []
    for t in TECHS:
        ax = axis_scores(t, s)
        base = sum(w[a] * ax[a] for a in AXES) / sum(w.values())
        adj, fired = rules(t, s, base)
        final = max(0.0, min(5.0, base + adj))
        out.append(dict(tech=t, axes=ax, base=base, adj=adj, fired=fired, score=final * 20,
                        why=explain(t, ax, s, w, fired)))
    return sorted(out, key=lambda r: -r["score"])

# ----------------------------------------------------------------- scenarios
SCENARIOS = [
    (Scenario("Smart water meter", rate_from_message(200, 3600), "deep_indoor", 12, "stationary", "carrier", 20_000, "tight"), "NB-IoT"),
    (Scenario("Fleet-tracked shipping container", rate_from_message(100, 600), "wide_area_cellular", 4, "global_roaming", "carrier", 2_000, "moderate"), "LTE-M"),
    (Scenario("Factory-floor sensor network", rate_from_message(50, 10), "deep_indoor", 5, "stationary", "self", 500, "moderate"), "LoRaWAN"),
    (Scenario("Wearable health monitor", 30_000, "short_range_only", 0.1, "local", "either", 50_000, "tight"), "Short-range (BLE/Zigbee)"),
    (Scenario("NEW: security-guard body cameras (HD uplink)", 4_000_000, "wide_area_cellular", 0.04, "wide_area", "carrier", 200, "generous"), "5G RedCap"),
]

def show(s, ranked, expected=None, verbose=True):
    print("=" * 100)
    print(f"SCENARIO: {s.name}")
    print(f"  inputs: rate={s.rate_bps:,.1f} bps (level {map_data_rate(s.rate_bps)}), coverage={s.coverage}, battery={s.battery_years} y "
          f"(level {map_battery(s.battery_years)}), mobility={s.mobility}, ownership={s.ownership}, devices={s.devices:,}, "
          f"budget={s.budget} (cost level {map_cost(s.devices, s.budget)})")
    print(f"{'#':<3}{'Technology':<27}{'Score':>6}  " + "".join(f"{a[:5]:>7}" for a in AXES) + "  Justification")
    for i, r in enumerate(ranked, 1):
        print(f"{i:<3}{r['tech']:<27}{r['score']:>6.1f}  " + "".join(f"{r['axes'][a]:>7.1f}" for a in AXES) + "  " + r["why"])
        if verbose:
            for f in r["fired"]: print(" " * 42 + "-> " + f)
    if expected:
        print(f"  expected pick: {expected} | tool pick: {ranked[0]['tech']} | {'MATCH' if ranked[0]['tech']==expected else 'DIVERGES'}")

def interactive():
    def ask(prompt, choices=None, cast=str):
        while True:
            v = input(prompt + (f" {choices}" if choices else "") + ": ").strip()
            try:
                v = cast(v)
                if not choices or v in choices: return v
            except ValueError: pass
            print("  invalid, try again")
    name = input("Scenario name: ") or "Custom"
    s = Scenario(name, ask("Required data rate in bits/s (e.g. 200 B per hour = 0.44)", cast=float),
                 ask("Coverage", ["deep_indoor", "wide_area_cellular", "long_range_rural", "short_range_only"]),
                 ask("Battery target (years)", cast=float),
                 ask("Mobility", ["stationary", "local", "wide_area", "global_roaming"]),
                 ask("Infrastructure ownership", ["carrier", "either", "self"]),
                 ask("Device count", cast=int), ask("Budget tier", ["generous", "moderate", "tight"]))
    show(s, rank(s))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--interactive", action="store_true")
    ap.add_argument("--weights", default="", help="e.g. data_rate=2,coverage=1")
    ap.add_argument("--csv", default="", help="write ranked results of all scenarios to this CSV file")
    a = ap.parse_args()
    for kv in filter(None, a.weights.split(",")):
        k, v = kv.split("="); WEIGHTS[k] = float(v)
    if a.interactive: interactive(); sys.exit()
    rows = []
    for s, exp in SCENARIOS:
        r = rank(s); show(s, r, exp)
        rows += [[s.name, i, x["tech"], f"{x['score']:.1f}", x["why"]] for i, x in enumerate(r, 1)]
    if a.csv:
        with open(a.csv, "w", newline="") as f:
            csv.writer(f).writerows([["scenario", "rank", "technology", "score", "justification"]] + rows)
