#!/usr/bin/env python3
"""MP 4.1 Part B - LPWAN link-budget and battery-life comparison.

Scenario (lab manual step 11): 200 soil-moisture/temperature sensors on a 25 km^2 farm, one 12-byte
reading every 30 min, max sensor-to-gateway distance 8 km, 5-year target on a 3.6 V / 19,000 mAh
primary lithium cell, no cellular coverage nearby, avoid per-device fees at 200-unit scale.

Run:   python3 link_budget_compare.py            (everything: scenario + Lab Tasks 4,5,6)
       python3 link_budget_compare.py --no-tasks (just the assigned scenario, 3 technologies + RedCap)
All numbers marked ASSUMED are representative engineering values, not measurements; change them in
the TECH table below and re-run.
"""
import argparse
import math
import numpy as np

# ------------------------------------------------------------------ scenario
DISTANCE_KM = 8.0
INTERVAL_S = 30 * 60
PAYLOAD_B = 12
BATTERY_MAH = 19_000
TARGET_YEARS = 5.0
N_DEVICES = 200
PL_D0_DB, D0_KM = 91.5, 1.0          # free-space loss at 1 km, ~900 MHz (given)
N_EXP = 3.5                          # open rural exponent (given)
REQUIRED_FADE_MARGIN_DB = 10.0       # ASSUMED design margin used in the pass/fail column
CYCLES_PER_YEAR = 365 * 24 * 3600 / INTERVAL_S

# --------------------------------------------------------- LoRa time-on-air
def lora_airtime_s(payload_bytes, sf=12, bw=125e3, cr=1, preamble=8, header=True, crc=True):
    """Semtech SX127x time-on-air formula (CR 1 => 4/5). Low-data-rate optimisation on for SF11/12 @125k."""
    de = 1 if (sf >= 11 and bw <= 125e3) else 0
    tsym = 2 ** sf / bw
    n_pay = 8 + max(math.ceil((8 * payload_bytes - 4 * sf + 28 + 16 * crc - 20 * (not header))
                              / (4 * (sf - 2 * de))) * (cr + 4), 0)
    return (preamble + 4.25) * tsym + n_pay * tsym

LORA_PHY_BYTES = PAYLOAD_B + 13                    # + LoRaWAN MHDR/FHDR/FPort/MIC overhead
LORA_TOA = lora_airtime_s(LORA_PHY_BYTES)

# ---------------------------------------------------------------- technology table
# phases = list of (current_mA, duration_s) per reporting cycle; sleep_uA = current for the remainder
TECH = {
    "NB-IoT":          dict(tx_dbm=23, sens_dbm=-129, sleep_uA=3.0,
                            phases=[(220, 2.5), (46, 4.0)],          # TX with repetitions; connected-mode RX tail
                            note="repetition-based coverage enhancement, PSM sleep"),
    "LTE-M (CE-B)":    dict(tx_dbm=23, sens_dbm=-125, sleep_uA=8.0,
                            phases=[(250, 3.0), (60, 6.0)],          # more TX current, longer connected tail, eDRX/PSM
                            note="CE Mode B repetitions, higher TX current"),
    "LoRaWAN (SF12)":  dict(tx_dbm=14, sens_dbm=-137, sleep_uA=1.5,
                            phases=[(44, LORA_TOA), (12, 0.5)],      # one SF12 uplink + Class-A RX1/RX2 windows
                            note=f"SF12/125 kHz, {LORA_PHY_BYTES} B PHY payload, airtime {LORA_TOA:.3f} s"),
    "5G RedCap":       dict(tx_dbm=23, sens_dbm=-110, sleep_uA=25.0,
                            phases=[(250, 2.0), (80, 4.0)],          # Lab Task 5 - ASSUMED representative values
                            note="ASSUMED: 20 MHz-class NR, reduced-capability UE, no deep-coverage repetitions"),
}

def path_loss_db(d_km, n=N_EXP, pl0=PL_D0_DB, d0=D0_KM):
    return pl0 + 10 * n * np.log10(np.asarray(d_km, dtype=float) / d0)

def mcl_db(t):
    return t["tx_dbm"] - t["sens_dbm"]

def battery_years(t):
    active_mAh = sum(i * s for i, s in t["phases"]) / 3600.0
    active_s = sum(s for _, s in t["phases"])
    sleep_mAh = (t["sleep_uA"] / 1000.0) * (INTERVAL_S - active_s) / 3600.0
    per_cycle = active_mAh + sleep_mAh
    per_year = per_cycle * CYCLES_PER_YEAR
    return per_cycle, per_year, BATTERY_MAH / per_year

def max_range_km(t, n=N_EXP):
    return D0_KM * 10 ** ((mcl_db(t) - PL_D0_DB) / (10 * n))

def table(rows, header):
    w = [max(len(str(x)) for x in col) for col in zip(header, *rows)]
    line = lambda r: "  ".join(str(x).ljust(w[i]) if i == 0 else str(x).rjust(w[i]) for i, x in enumerate(r))
    print(line(header)); print("  ".join("-" * x for x in w))
    for r in rows: print(line(r))

# ------------------------------------------------------------------- reports
def scenario_report():
    pl = float(path_loss_db(DISTANCE_KM))
    print("=" * 78)
    print("MP 4.1 PART B - assigned scenario: 200-sensor farm, 8 km, 5-year battery")
    print("=" * 78)
    print(f"Path loss  PL(8 km) = {PL_D0_DB} + 10*{N_EXP}*log10({DISTANCE_KM}/{D0_KM}) = {pl:.2f} dB")
    print(f"Cycles per year = {CYCLES_PER_YEAR:,.0f} (one every {INTERVAL_S//60} min); battery = {BATTERY_MAH:,} mAh\n")
    rows = []
    for name, t in TECH.items():
        mcl = mcl_db(t); margin = mcl - pl
        per_cycle, per_year, yrs = battery_years(t)
        ok_cov = margin >= REQUIRED_FADE_MARGIN_DB
        ok_bat = yrs >= TARGET_YEARS
        rows.append([name, f"{t['tx_dbm']}", f"{t['sens_dbm']}", f"{mcl:.0f}", f"{margin:+.1f}",
                     f"{per_cycle:.4f}", f"{per_year:,.0f}", f"{yrs:.1f}",
                     "PASS" if ok_cov else "FAIL", "PASS" if ok_bat else "FAIL"])
    table(rows, ["Technology", "Tx dBm", "Sens dBm", "MCL dB", "Margin dB", "mAh/cycle", "mAh/year",
                 "Life (yr)", f"Cov>={REQUIRED_FADE_MARGIN_DB:.0f}dB", f"Life>={TARGET_YEARS:.0f}y"])
    print("\nNotes: LoRaWAN life exceeds the cell's realistic shelf life (~10-15 y); treat >15 y as 'battery-limited by chemistry'.")
    for name, t in TECH.items():
        print(f"  {name:<16} {t['note']}")
    # capacity sanity check for the unlicensed option
    G = N_DEVICES * LORA_TOA / INTERVAL_S
    print(f"\nLoRaWAN capacity check: offered load G = {N_DEVICES} x {LORA_TOA:.3f} s / {INTERVAL_S} s = {G:.3f} Erlang "
          f"(duty cycle {100*LORA_TOA/INTERVAL_S:.3f} % per node, limit 1 %)")
    print(f"  pure-ALOHA success per uplink on ONE channel/SF: exp(-2G) = {math.exp(-2*G):.2f}; "
          f"with 8 channels: exp(-2G/8) = {math.exp(-2*G/8):.3f}")
    print(f"Geometry: 25 km^2 circular footprint has radius {math.sqrt(25/math.pi):.2f} km; one central gateway covers it, "
          f"8 km is the worst-case (corner/off-centre) distance.")

def task4_container():
    print("\n" + "=" * 78)
    print("LAB TASK 4 - fleet-tracked shipping container, ocean crossing (no terrestrial coverage)")
    print("=" * 78)
    ds = [1, 5, 8, 20, 50, 100, 300, 1000]
    print("Margin (dB) = MCL - PL(d), n = 3.5, as a function of distance to the nearest base station/gateway:")
    rows = []
    for name, t in TECH.items():
        rows.append([name] + [f"{mcl_db(t) - float(path_loss_db(d)):+.0f}" for d in ds] + [f"{max_range_km(t):.0f} km"])
    table(rows, ["Technology"] + [f"{d} km" for d in ds] + ["max range"])
    print("\nEvery technology goes negative beyond ~40-55 km: mid-ocean there is NO gateway/base station within range,")
    print("so the margin at a single distance is not the deciding variable. The decision depends on availability")
    print("(coverage along the whole route: ports + satellite/NTN), roaming/handover, and time-varying visibility.")

def task6_sweep():
    print("\n" + "=" * 78)
    print("LAB TASK 6 - sensitivity to path-loss exponent n (8 km)")
    print("=" * 78)
    ns = [2.5, 3.0, 3.5, 4.0, 4.5]
    rows = []
    for name, t in TECH.items():
        rows.append([name] + [f"{mcl_db(t) - float(path_loss_db(DISTANCE_KM, n)):+.1f}" for n in ns]
                    + [f"{(mcl_db(t) - PL_D0_DB) / (10*math.log10(DISTANCE_KM)):.2f}",
                       f"{(mcl_db(t) - REQUIRED_FADE_MARGIN_DB - PL_D0_DB) / (10*math.log10(DISTANCE_KM)):.2f}"])
    table(rows, ["Technology"] + [f"n={n}" for n in ns] + ["n_crit(0 dB)", f"n_crit({REQUIRED_FADE_MARGIN_DB:.0f} dB)"])
    print("\nPath loss at 8 km:", ", ".join(f"n={n}: {float(path_loss_db(DISTANCE_KM, n)):.1f} dB" for n in ns))
    print("Battery life does not depend on n in this simple model (no power control / extra repetitions modelled),")
    print("so the ranking by battery life is unchanged for all n; only the coverage column moves.")

def recommendation():
    print("\n" + "=" * 78)
    print("RECOMMENDATION")
    print("=" * 78)
    print("LoRaWAN (SF12) with one privately owned gateway.")
    print("  * Link: MCL 151 dB (1 dB below NB-IoT), +27.9 dB margin at 8 km, still +18.9 dB at n = 4.5.")
    print("  * Battery: ~0.02 mAh/cycle -> decades on 19 Ah, versus ~5 y (NB-IoT, marginal) and ~3.5 y (LTE-M, fails).")
    print("  * Section 4.3 axes: no cellular coverage nearby rules out carrier-based NB-IoT/LTE-M/RedCap regardless of")
    print("    margin; own gateway = no per-device subscription at 200 units; low data rate and stationary nodes suit LoRa.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--no-tasks", action="store_true"); a = ap.parse_args()
    scenario_report()
    if not a.no_tasks:
        task4_container(); task6_sweep()
    recommendation()
