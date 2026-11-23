"""Generate SYNTHETIC daily ad spend, clicks and conversions per channel.

No public dataset matches thelook_ecommerce, so this fills the ad-spend gap.
Label the data as synthetic in the README.

Usage:
    python data_gen/generate_ad_spend.py --start 2024-01-01 --end 2025-12-31 --out ad_spend.csv
"""
import argparse
import csv
import random
from datetime import date, timedelta

# channel: (avg daily spend, cost per click, click-to-conversion rate)
CHANNELS = {
    "google_search": (1500.0, 1.20, 0.040),
    "meta_ads": (1100.0, 0.80, 0.020),
    "youtube": (600.0, 0.50, 0.010),
    "email": (150.0, 0.10, 0.060),
}


def generate(start: date, end: date, seed: int):
    rng = random.Random(seed)
    rows = []
    d = start
    while d <= end:
        weekend = 1.15 if d.weekday() >= 5 else 1.0
        promo = 1.6 if (d.month == 11 and d.day >= 20) else 1.0  # Black Friday style spike
        for channel, (spend, cpc, cvr) in CHANNELS.items():
            s = spend * weekend * promo * rng.uniform(0.85, 1.15)
            clicks = max(0, int(s / cpc * rng.uniform(0.9, 1.1)))
            conversions = int(clicks * cvr * rng.uniform(0.8, 1.2))
            rows.append([d.isoformat(), channel, round(s, 2), clicks, conversions])
        d += timedelta(days=1)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="ad_spend.csv")
    a = ap.parse_args()
    rows = generate(date.fromisoformat(a.start), date.fromisoformat(a.end), a.seed)
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "channel", "spend", "clicks", "conversions"])
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {a.out}")


if __name__ == "__main__":
    main()
