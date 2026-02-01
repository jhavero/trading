#!/usr/bin/env python3
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class SymbolRules:
    contract_size: float
    lot_step: float
    min_lot: float
    max_lot: float
    digits: int
    stops_level_points: int

RULES = {
    "gold": SymbolRules(100.0, 0.01, 0.01, 100.0, 2, 20),
    "btc":  SymbolRules(1.0,   0.01, 0.01, 100.0, 2, 0),
    "nas100": SymbolRules(1.0, 0.01, 0.01, 500, 2, 50), # NAS100
    "dj30": SymbolRules(1.0, 0.01, 0.01, 500, 2, 0), #DJ30 or US30
}

def point_size(d):
    return 10 ** (-d)

def min_stop_distance(r):
    return r.stops_level_points * point_size(r.digits)

def round_price(x, d):
    return round(x, d)

def round_down(x, step):
    return math.floor(x / step) * step

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def get_float_retry(prompt, *, min_value=None):
    while True:
        raw = input(prompt).strip()
        try:
            v = float(raw)
            if min_value is not None and v <= min_value:
                raise ValueError
            return v
        except ValueError:
            print("  ❌ Invalid number, try again.")

def get_float_default(prompt, default):
    raw = input(prompt).strip()
    if raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        print("  ❌ Invalid number, using default.")
        return default

# 🔒 SAFE symbol input
def get_symbol():
    while True:
        raw = input("Symbol [gold/btc] (default gold): ").strip().lower()
        if raw == "":
            return "gold", RULES["gold"]
        if raw in RULES:
            return raw, RULES[raw]
        print("  ❌ Invalid symbol. Enter 'gold' or 'btc'.")

def get_side_default_buy():
    raw = input("Side [buy/sell] (default buy): ").strip().lower()
    if raw in ("", "buy"):
        return "buy"
    if raw == "sell":
        return "sell"
    print("  ❌ Invalid side, defaulting to BUY.")
    return "buy"

def get_risk_input():
    mode = input("Risk mode [%/$] (default %): ").strip().lower()
    return mode if mode in ("$", "d") else "%"

def get_valid_entry_stop(side, rules):
    entry = round_price(get_float_retry("Entry price: ", min_value=0), rules.digits)

    while True:
        stop = round_price(get_float_retry("Stop-loss price: ", min_value=0), rules.digits)

        if stop == entry:
            print("  ❌ Stop cannot equal entry.")
            continue
        if side == "buy" and stop >= entry:
            print("  ❌ BUY stop must be BELOW entry.")
            continue
        if side == "sell" and stop <= entry:
            print("  ❌ SELL stop must be ABOVE entry.")
            continue

        dist = abs(entry - stop)
        msd = min_stop_distance(rules)
        if msd > 0 and dist < msd:
            print(f"  ❌ Stop too close. Min distance is {msd:g}.")
            continue

        return entry, stop

def main():
    print("\n=== Fast Risk Calculator (PU Prime) ===\n")

    symbol, rules = get_symbol()
    side = get_side_default_buy()

    # --- Risk selection ---
    risk_mode = get_risk_input()

    if risk_mode == "%":
        equity = get_float_retry("Equity ($): ", min_value=0)
        risk_pct = get_float_default("Risk % [1]: ", 1.0)
        risk_dollars = equity * (risk_pct / 100.0)
    else:
        equity = None
        risk_dollars = get_float_retry("Risk amount ($): ", min_value=0)

    rr = get_float_default("Risk:Reward [2]: ", 2.0)

    entry, stop = get_valid_entry_stop(side, rules)

    # --- Core math ---
    stop_distance = abs(entry - stop)
    loss_per_1_lot = stop_distance * rules.contract_size
    raw_lot = risk_dollars / loss_per_1_lot

    lot = round_down(raw_lot, rules.lot_step)
    lot = clamp(lot, rules.min_lot, rules.max_lot)

    risk_used = stop_distance * rules.contract_size * lot

    tp_dist = stop_distance * rr
    tp = entry + tp_dist if side == "buy" else entry - tp_dist
    tp = round_price(tp, rules.digits)

    print("\n--- RESULT ---")
    print(f"Symbol: {symbol.upper()}")
    print(f"Side: {side.upper()}")
    print(f"Entry: {entry}")
    print(f"Stop:  {stop}")
    print(f"TP:    {tp}")
    print(f"Lot:   {lot:.2f}")
    print(f"Risk used: ${risk_used:.2f}")

    if risk_mode == "%" and risk_used > risk_dollars * 1.01:
        actual_pct = (risk_used / equity) * 100
        print(f"\n⚠ Actual risk ≈ {actual_pct:.2f}% (min volume constraint)")

if __name__ == "__main__":
    main()
