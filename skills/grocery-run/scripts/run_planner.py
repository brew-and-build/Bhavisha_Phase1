#!/usr/bin/env python3
"""Grocery Run calculator (standard library only).

Subcommands:
  log      save one ride fare quote (Uber, Lyft or Waymo) for a store
  stats    usual fare and cheapest / priciest times for a store and app
  now      compare a fare quoted right now with the usual for that time
  compare  rank free shuttles, transit, rides and mixed options for one run

Priority: free shuttles first, then Valley Metro (capped at $4/day), then rides.
Fare history lives in $SKILL_DATA_DIR/fares.jsonl (falls back to ./data).
Times are Phoenix time (Arizona has no daylight saving time).
"""
import argparse
import json
import os
import statistics
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

PHX = ZoneInfo("America/Phoenix")
TRANSIT_DAILY_CAP = 4.00  # local Valley Metro cap per person per day
MIN_SAMPLES = 8
MAX_FREE_MIN = 75   # one-way minutes; beyond this a free route is not practical
MAX_TRANSIT_MIN = 90
APPS = ["uber", "lyft", "waymo"]
APP_NAME = {"uber": "Uber", "lyft": "Lyft", "waymo": "Waymo"}
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WINDOWS = [(6, 11, "morning"), (11, 14, "midday"), (14, 17, "afternoon"),
           (17, 20, "evening"), (20, 24, "night"), (0, 6, "late night")]


def data_file():
    base = os.environ.get("SKILL_DATA_DIR") or os.path.join(os.getcwd(), "data")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "fares.jsonl")


def parse_time(s):
    if not s:
        return datetime.now(PHX)
    t = datetime.fromisoformat(s)
    return t.replace(tzinfo=PHX) if t.tzinfo is None else t.astimezone(PHX)


def window_of(t):
    for start, end, name in WINDOWS:
        if start <= t.hour < end:
            return name
    return "late night"


def bucket(t):
    kind = "weekend" if t.weekday() >= 5 else "weekday"
    return f"{kind} {window_of(t)}"


def load(store, app):
    path = data_file()
    if not os.path.exists(path):
        return []
    key = store.strip().lower()
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r["store"].strip().lower() == key and r.get("app", "uber") == app:
                r["t"] = parse_time(r["at"])
                out.append(r)
    return out


def money(x):
    return f"${x:,.2f}".replace(".00", "")


# ---------- log ----------
def cmd_log(a):
    if a.fare <= 0 or a.fare > 500:
        print("ERROR: fare looks wrong; check the number.")
        return 2
    t = parse_time(a.at)
    rec = {"store": a.store, "app": a.app, "fare": round(a.fare, 2),
           "at": t.isoformat(), "source": a.source}
    with open(data_file(), "a") as f:
        f.write(json.dumps(rec) + "\n")
    n = len(load(a.store, a.app))
    print(f"Logged {APP_NAME[a.app]} {money(a.fare)} to {a.store} "
          f"({DAYS[t.weekday()]} {t:%I:%M %p}, {bucket(t)}). "
          f"{n} {APP_NAME[a.app]} fare{'s' if n != 1 else ''} logged for this store.")
    return 0


# ---------- stats ----------
def group(rows):
    g = {}
    for r in rows:
        g.setdefault(bucket(r["t"]), []).append(r["fare"])
    return {k: statistics.median(v) for k, v in g.items() if len(v) >= 2}


def stats_for(store, app):
    rows = load(store, app)
    name = APP_NAME[app]
    if not rows:
        return None
    fares = [r["fare"] for r in rows]
    med = statistics.median(fares)
    print(f"{name} to {store}: {len(rows)} fare{'s' if len(rows) != 1 else ''} logged. Usual one-way: {money(med)} "
          f"(range {money(min(fares))}–{money(max(fares))}).")
    if len(rows) < MIN_SAMPLES:
        print(f"  PATTERN_FORMING: need about {MIN_SAMPLES} fares for reliable times "
              f"({MIN_SAMPLES - len(rows)} more).")
        return med
    g = group(rows)
    if len(g) < 2:
        print("  PATTERN_FORMING: need fares from more different times of week.")
        return med
    ranked = sorted(g.items(), key=lambda kv: kv[1])
    cheap, pricey = ranked[0], ranked[-1]
    print(f"  Cheapest time: {cheap[0]} (usually {money(cheap[1])})")
    print(f"  Priciest time: {pricey[0]} (usually {money(pricey[1])})")
    if pricey[1] > cheap[1]:
        print(f"  Going at the cheapest time saves about {money(pricey[1] - cheap[1])} each way.")
    return med


def cmd_stats(a):
    apps = [a.app] if a.app else APPS
    usuals = {}
    for app in apps:
        med = stats_for(a.store, app)
        if med is not None:
            usuals[app] = med
    if not usuals:
        print(f"NO_DATA: no fares logged for {a.store} yet.")
    elif len(usuals) > 1:
        best = min(usuals, key=usuals.get)
        print(f"USUALLY_CHEAPEST_APP: {APP_NAME[best]} ({money(usuals[best])} one-way)")
    return 0


# ---------- now ----------
def cmd_now(a):
    rows = load(a.store, a.app)
    name = APP_NAME[a.app]
    t = parse_time(a.at)
    b = bucket(t)
    if len(rows) < MIN_SAMPLES:
        print(f"PATTERN_FORMING: only {len(rows)} {name} fares logged; can't judge this price yet.")
        return 0
    same = [r["fare"] for r in rows if bucket(r["t"]) == b]
    usual = statistics.median(same) if len(same) >= 2 else statistics.median(r["fare"] for r in rows)
    basis = f"usual for {b}" if len(same) >= 2 else "overall usual"
    diff = (a.fare - usual) / usual * 100
    print(f"{name} now: {money(a.fare)} vs {basis} {money(usual)} ({diff:+.0f}%).")
    verdict = "HIGH" if diff >= 20 else "GOOD_DEAL" if diff <= -10 else "NORMAL"
    print(f"VERDICT: {verdict}")
    g = group(rows)
    if verdict == "HIGH" and g:
        cheap = min(g.items(), key=lambda kv: kv[1])
        print(f"Cheaper window: {cheap[0]} (usually {money(cheap[1])}).")
    return 0


# ---------- compare ----------
def promo_value(fare, a, app):
    """Discount on one ride of `app`, if a promo applies to it."""
    if not a.promo_app or a.promo_app != app:
        return 0.0
    off = 0.0
    if a.promo_off:
        off = a.promo_off
    elif a.promo_pct:
        off = fare * a.promo_pct / 100
        if a.promo_max:
            off = min(off, a.promo_max)
    return min(off, fare)


def cmd_compare(a):
    p = max(1, a.people)
    heavy = a.load == "heavy"
    hot = a.temp_f is not None and a.temp_f >= 100

    rides = {app: getattr(a, f"{app}_oneway") for app in APPS if getattr(a, f"{app}_oneway")}
    ride_min = a.ride_min or 0

    def best_ride(n_legs):
        """Cheapest app for n one-way legs, with a promo applied to one leg."""
        best = None
        for app, fare in rides.items():
            total = n_legs * fare - promo_value(fare, a, app)
            if best is None or total < best[1]:
                best = (app, total)
        return best

    def walk_notes(walk, where=""):
        if hot and walk > 10:
            return [f"{walk} min walk in {a.temp_f:g}°F{where}"]
        return []

    opts = []
    free_ok = a.free_min is not None and a.free_min <= MAX_FREE_MIN
    transit_ok = a.transit_min is not None and a.transit_min <= MAX_TRANSIT_MIN

    if free_ok:
        notes = walk_notes(a.free_walk_min)
        if heavy:
            notes.append("carrying heavy bags back on a shuttle")
        if a.free_min > 60:
            notes.append(f"{a.free_min} min each way")
        opts.append({"name": "Free shuttles both ways", "total": 0.0,
                     "minutes": 2 * a.free_min, "notes": notes, "tier": 0})
        if rides:
            app, cost = best_ride(1)
            opts.append({"name": f"Free shuttle there, {APP_NAME[app]} back", "total": cost,
                         "minutes": a.free_min + ride_min,
                         "notes": walk_notes(a.free_walk_min, " on the way there"), "tier": 1})
    if transit_ok:
        t_total = TRANSIT_DAILY_CAP * p
        notes = walk_notes(a.walk_min)
        if heavy:
            notes.append("carrying heavy bags back on transit")
        if a.transfers >= 2:
            notes.append(f"{a.transfers} transfers each way")
        opts.append({"name": "Valley Metro both ways", "total": t_total,
                     "minutes": 2 * a.transit_min, "notes": notes, "tier": 2})
        if rides:
            app, cost = best_ride(1)
            opts.append({"name": f"Valley Metro there, {APP_NAME[app]} back",
                         "total": t_total + cost, "minutes": a.transit_min + ride_min,
                         "notes": walk_notes(a.walk_min, " on the way there"), "tier": 3})
    if rides:
        app, cost = best_ride(2)
        opts.append({"name": f"{APP_NAME[app]} both ways", "total": cost,
                     "minutes": 2 * ride_min, "notes": [], "tier": 4})

    if not opts:
        print("ERROR: give at least one ride fare, a transit route, or a free shuttle route.")
        return 2

    def penalty(o):
        heavy_both = heavy and "both ways" in o["name"] and o["tier"] in (0, 2)
        return len(o["notes"]) * 4 + (8 if heavy_both else 0)

    # Cost per person decides, with comfort penalties; ties go to the lower tier (free first).
    best = min(opts, key=lambda o: (o["total"] / p + penalty(o), o["tier"]))
    for o in sorted(opts, key=lambda o: o["tier"]):
        mins = f", ~{o['minutes']} min travel" if o["minutes"] else ""
        note = f" ({'; '.join(o['notes'])})" if o["notes"] else ""
        each = f", {money(o['total'] / p)} each" if p > 1 else ""
        cost = "FREE" if o["total"] == 0 else f"{money(o['total'])} total"
        print(f"- {o['name']}: {cost}{each}{mins}{note}")
    if a.free_min is not None and not free_ok:
        print(f"FREE: not practical (over {MAX_FREE_MIN} min each way).")
    if a.transit_min is not None and not transit_ok:
        print(f"TRANSIT: not practical (over {MAX_TRANSIT_MIN} min each way).")
    if a.promo_app and a.promo_app in rides:
        print(f"PROMO: assumed a {APP_NAME[a.promo_app]} promo on one ride; only counts if the student confirms it applied in the app.")
    if len(rides) > 1:
        cheapest = min(rides, key=rides.get)
        print(f"CHEAPEST_APP_NOW: {APP_NAME[cheapest]} ({money(rides[cheapest])} one-way before promos)")
    print(f"RECOMMEND: {best['name']}")
    if a.ride_usual and rides:
        app = min(rides, key=rides.get)
        if rides[app] >= 1.2 * a.ride_usual:
            save = 2 * (rides[app] - a.ride_usual)
            print(f"WAIT_OPTION: rides are {(rides[app] / a.ride_usual - 1) * 100:.0f}% above usual; "
                  f"a usual-price time saves about {money(save)} round trip.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    l = sub.add_parser("log")
    l.add_argument("--store", required=True)
    l.add_argument("--app", choices=APPS, default="uber")
    l.add_argument("--fare", type=float, required=True)
    l.add_argument("--at", help="ISO time; default now (Phoenix)")
    l.add_argument("--source", choices=["browser", "screenshot", "manual"], default="manual")
    l.set_defaults(fn=cmd_log)

    s = sub.add_parser("stats")
    s.add_argument("--store", required=True)
    s.add_argument("--app", choices=APPS, help="omit to show every app with data")
    s.set_defaults(fn=cmd_stats)

    n = sub.add_parser("now")
    n.add_argument("--store", required=True)
    n.add_argument("--app", choices=APPS, default="uber")
    n.add_argument("--fare", type=float, required=True)
    n.add_argument("--at")
    n.set_defaults(fn=cmd_now)

    c = sub.add_parser("compare")
    c.add_argument("--free-min", type=int, help="one-way minutes using only free shuttles + walking")
    c.add_argument("--free-walk-min", type=int, default=0)
    c.add_argument("--transit-min", type=int, help="one-way Valley Metro minutes; omit if no route")
    c.add_argument("--walk-min", type=int, default=0, help="walking minutes on the transit route")
    c.add_argument("--transfers", type=int, default=0)
    c.add_argument("--uber-oneway", type=float)
    c.add_argument("--lyft-oneway", type=float)
    c.add_argument("--waymo-oneway", type=float)
    c.add_argument("--ride-min", type=int, help="ride minutes one way")
    c.add_argument("--ride-usual", type=float, help="usual one-way fare from stats")
    c.add_argument("--promo-app", choices=APPS)
    c.add_argument("--promo-off", type=float, help="dollars off one ride")
    c.add_argument("--promo-pct", type=float, help="percent off one ride")
    c.add_argument("--promo-max", type=float, help="cap on a percent promo, in dollars")
    c.add_argument("--load", choices=["light", "heavy"], default="light")
    c.add_argument("--temp-f", type=float)
    c.add_argument("--people", type=int, default=1)
    c.set_defaults(fn=cmd_compare)

    a = ap.parse_args()
    try:
        sys.exit(a.fn(a))
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
