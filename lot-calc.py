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
    "gold": SymbolRules(100.0, 0.01, 0.01, 100.0, 2, 20),  # XAUUSD
    "btc":  SymbolRules(1.0,   0.01, 0.01, 100.0, 2, 0),   # BTCUSD
}

def point_size(digits: int) -> float:
    return 10 ** (-digits)

def min_stop_distance(r: SymbolRules) -> float:
    return r.stops_level_points * point_size(r.digits)

def round_price(x: float, digits: int) -> float:
    return round(x, digits)

def round_down(x: float, step: float) -> float:
    return math.floor(x / step) * step

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def get_float_retry(prompt: str, *, min_value: float | None = None) -> float:
    while True:
        raw = input(prompt).strip()
        try:
            v = float(raw)
            if min_value is not None and v <= min_value:
                raise ValueError
            return v
        except ValueError:
            print("  ❌ Invalid number, try again.")

def get_float_default(prompt: str, default: float) -> float:
    raw = input(prompt).strip()
    if raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        print("  ❌ Invalid number, using default.")
        return default

def get_symbol_default_gold() -> tuple[str, SymbolRules]:
    raw = input("Symbol [gold/btc] (default gold): ").strip().lower()
    sym = raw if raw in RULES else "gold"
    return sym, RULES[sym]

def get_side_default_buy() -> str:
    raw = input("Side [buy/sell] (default buy): ").strip().lower()
    if raw == "":
        return "buy"
    if raw in ("buy", "sell"):
        return raw
    print("  ❌ Invalid side, defaulting to BUY.")
    return "buy"

def get_valid_entry_stop(side: str, rules: SymbolRules) -> tuple[float, float]:
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
            print(f"  ❌ Stop too close. Min distance is {msd:g} (Stops level {rules.stops_level_points} points).")
            continue

        return entry, stop

def main():
    print("\n=== Fast Risk Calculator (PU Prime) ===\n")

    symbol, rules = get_symbol_default_gold()
    side = get_side_default_buy()

    equity = get_float_retry("Equity ($): ", min_value=0)

    # Defaults
    risk_pct = get_float_default("Risk % [1]: ", 1.0)
    rr       = get_float_default("Risk:Reward [2]: ", 2.0)

    # Entry/Stop with guaranteed validation
    entry, stop = get_valid_entry_stop(side, rules)

    # Core math
    stop_distance = abs(entry - stop)
    risk_dollars = equity * (risk_pct / 100.0)

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

    if raw_lot < rules.min_lot:
        min_risk_pct = (risk_used / equity) * 100.0
        print(f"\n⚠ Min lot forces risk ≈ {min_risk_pct:.2f}%")

if __name__ == "__main__":
    main()
