"""
generate_data.py
----------------
Creates a SYNTHETIC (made-up) dataset for a practice case study.

Scenario
--------
A beef processing plant ran a 12-week pilot of a technology that monitors
quality from live animal through to carcass (e.g. sensors/imaging at receival,
the race and the chiller). The pilot flags animals at risk of problems
(bruising, dark-cutting, poor fat cover) so the plant can intervene or sort
animals into the right market early.

Design of the pilot
-------------------
- Animals arrive in "lots" (a consignment from one farm on one day).
- Each lot is randomly assigned to CONTROL (normal practice) or TRIAL
  (technology-monitored).
- We then record what happened to each animal at the carcass stage.

The trial effect is built in (fewer downgrades, less trim loss, fewer dark
cutters, fewer customer claims) but with plenty of random noise, farm
differences and messy data, like real life.

Run it:   python generate_data.py
Output:   data/meat_trial_data.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path

# A fixed seed means you get the SAME "random" data every time you run this,
# so your results are reproducible (a key point in the job ad).
rng = np.random.default_rng(seed=42)

# ---------------------------------------------------------------------------
# 1. Build the lots (consignments)
# ---------------------------------------------------------------------------
N_LOTS = 180                      # number of consignments in the pilot
farms = [f"FARM_{i:02d}" for i in range(1, 21)]   # 20 supplying farms

# Each farm has its own "baseline quality" - some farms just supply better cattle.
farm_quality = dict(zip(farms, rng.normal(0, 1, len(farms))))

start = pd.Timestamp("2026-03-02")   # pilot starts on a Monday
lots = pd.DataFrame({
    "lot_id": [f"LOT_{i:03d}" for i in range(1, N_LOTS + 1)],
    "farm_id": rng.choice(farms, N_LOTS),
    # kill dates spread over 12 weeks, weekdays only
    "kill_date": [
        start + pd.Timedelta(days=int(d))
        for d in rng.integers(0, 84, N_LOTS)
    ],
    "lot_size": rng.integers(8, 30, N_LOTS),
    # Randomly assign each LOT to control or trial (about 50/50)
    "group": rng.choice(["control", "trial"], N_LOTS),
})
# Push weekend dates to the following Monday
lots["kill_date"] = lots["kill_date"].apply(
    lambda d: d + pd.Timedelta(days=(7 - d.weekday()) % 7) if d.weekday() >= 5 else d
)

# ---------------------------------------------------------------------------
# 2. Expand to one row per animal
# ---------------------------------------------------------------------------
df = lots.loc[lots.index.repeat(lots["lot_size"])].reset_index(drop=True)
df.insert(0, "animal_id", [f"A{i:05d}" for i in range(1, len(df) + 1)])
n = len(df)

df["farm_quality"] = df["farm_id"].map(farm_quality)
df["sex"] = rng.choice(["steer", "heifer"], n, p=[0.6, 0.4])
df["live_weight_kg"] = rng.normal(560, 55, n).round(0)

# Dressing percentage = hot carcass weight / live weight (typically ~52-58%)
dressing = rng.normal(0.545, 0.015, n) + 0.004 * df["farm_quality"]
df["hot_carcass_weight_kg"] = (df["live_weight_kg"] * dressing).round(1)

is_trial = (df["group"] == "trial").to_numpy()

# ---------------------------------------------------------------------------
# 3. Quality outcomes (this is where the technology effect is built in)
# ---------------------------------------------------------------------------

# --- Bruising / handling damage -> trim loss (kg of carcass removed) ---
bruise_prob = np.where(is_trial, 0.09, 0.14) - 0.01 * df["farm_quality"]
df["bruising"] = rng.random(n) < np.clip(bruise_prob, 0.02, 0.4)
trim = np.where(df["bruising"], rng.gamma(3.0, 0.9, n), rng.gamma(1.2, 0.25, n))
trim = trim * np.where(is_trial, 0.8, 1.0)          # tech reduces severity too
df["trim_loss_kg"] = trim.round(2)

# --- Dark cutting (high ultimate pH), a classic meat quality defect ---
dark_prob = np.where(is_trial, 0.035, 0.065) - 0.005 * df["farm_quality"]
df["dark_cutter"] = rng.random(n) < np.clip(dark_prob, 0.005, 0.3)
df["ultimate_ph"] = np.where(
    df["dark_cutter"], rng.normal(6.1, 0.12, n), rng.normal(5.55, 0.08, n)
).round(2)

# --- Grade: Premium / Standard / Downgrade ---
# Downgrade risk goes up with bruising and dark cutting, down with farm quality.
downgrade_score = (
    -2.0
    + 1.6 * df["bruising"]
    + 2.2 * df["dark_cutter"]
    - 0.25 * df["farm_quality"]
    - np.where(is_trial, 0.30, 0.0)                  # technology effect
)
p_down = 1 / (1 + np.exp(-downgrade_score))
is_down = rng.random(n) < p_down
premium_score = (
    -0.4 + 0.5 * df["farm_quality"] + np.where(is_trial, 0.12, 0.0)
)
p_prem = 1 / (1 + np.exp(-premium_score))
is_prem = (~is_down) & (rng.random(n) < p_prem)
df["grade"] = np.where(is_down, "Downgrade", np.where(is_prem, "Premium", "Standard"))

# --- Value ---
# Price per kg of carcass weight (AUD) depends on grade.
price = df["grade"].map({"Premium": 9.40, "Standard": 8.50, "Downgrade": 7.00})
df["price_per_kg"] = price
df["carcass_value"] = ((df["hot_carcass_weight_kg"] - df["trim_loss_kg"]) * price).round(2)

# --- Downstream customer claims (e.g. complaints about colour/shelf life) ---
claim_prob = np.where(is_trial, 0.012, 0.025)
claim_cost = rng.gamma(2.0, 150, n)                  # AUD, avg ~ $300 when it happens
df["claim_cost"] = np.where(rng.random(n) < claim_prob, claim_cost, 0.0).round(2)

# --- Technology risk score (only exists for trial animals) ---
risk = 0.15 + 0.35 * df["bruising"] + 0.35 * df["dark_cutter"] + rng.normal(0, 0.12, n)
df["tech_risk_score"] = np.where(is_trial, np.clip(risk, 0, 1).round(2), np.nan)

# ---------------------------------------------------------------------------
# 4. Make the data realistic and messy (so you can practise cleaning)
# ---------------------------------------------------------------------------
# a) a few missing live weights
df.loc[rng.choice(n, 40, replace=False), "live_weight_kg"] = np.nan
# b) a few missing ultimate pH readings (sensor dropout)
df.loc[rng.choice(n, 60, replace=False), "ultimate_ph"] = np.nan
# c) inconsistent text labels
df.loc[rng.choice(n, 25, replace=False), "sex"] = "Steer "
# d) a handful of impossible carcass weights (data entry errors)
bad = rng.choice(n, 5, replace=False)
df.loc[bad, "hot_carcass_weight_kg"] = df.loc[bad, "hot_carcass_weight_kg"] * 10
# e) a few duplicated rows
df = pd.concat([df, df.sample(12, random_state=1)], ignore_index=True)

# Drop helper column and tidy
df = df.drop(columns=["farm_quality", "lot_size"]).sort_values(["kill_date", "animal_id"])

out = Path("data")
out.mkdir(exist_ok=True)
df.to_csv(out / "meat_trial_data.csv", index=False)
print(f"Saved {len(df):,} rows to {out / 'meat_trial_data.csv'}")
print(df["group"].value_counts())
