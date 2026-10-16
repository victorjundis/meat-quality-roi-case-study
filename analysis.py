import sys
print(sys.executable)

"""
analysis.py
-----------
Case study: Should a meat processor invest in technology that monitors quality
from live animal to carcass?

HOW TO USE THIS FILE IN VS CODE
-------------------------------
The lines that start with  # %%  split this file into "cells".
Above each cell VS Code shows "Run Cell". Click it to run just that cell and
see the results in a side panel (needs the Python + Jupyter extensions).
Run the cells top to bottom the first time. You can also run the whole file
from the terminal:   python analysis.py

The story we are telling (this is what an interviewer wants to hear):
  1. What did the pilot show?          (data cleaning + comparison)
  2. Is the result real or just luck?  (statistics)
  3. What is it worth to the business? (ROI model)
  4. How confident are we?             (scenarios + sensitivity)
"""

# %% 0. SETUP -----------------------------------------------------------------
# Import the libraries we need. Think of them as toolboxes:
#   pandas      -> tables of data (like Excel, but programmable)
#   numpy       -> fast maths on lists/arrays of numbers
#   scipy.stats -> statistical tests
#   matplotlib  -> charts
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from pathlib import Path

# Folder for charts and result tables. exist_ok=True means "don't complain if
# it already exists".
OUT = Path("outputs")
OUT.mkdir(exist_ok=True)

# A fixed random seed so the bootstrap results are the same every run.
rng = np.random.default_rng(42)

# Make charts a bit cleaner
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True,
                     "grid.alpha": 0.25})
COLOURS = {"control": "#8a8a8a", "trial": "#1f77b4"}


# %% 1. LOAD AND INSPECT ------------------------------------------------------
# Read the CSV into a DataFrame (a table). parse_dates turns the text in
# kill_date into real dates so we can do date maths later.
raw = pd.read_csv("data/meat_trial_data.csv", parse_dates=["kill_date"])

print("Shape (rows, columns):", raw.shape)
print()
print(raw.head())              # first 5 rows - always look at the data first!
print()
raw.info()                     # column types and non-null counts
print()
print("Missing values per column:")
print(raw.isna().sum())        # counts blanks in each column
print()
print(raw.describe().round(1)) # min / max / mean - spot weird values here


# %% 2. CLEAN THE DATA -------------------------------------------------------
# Real data is messy. We document every cleaning decision so someone else
# can reproduce and challenge it (the job ad says "transparent, reproducible").
df = raw.copy()          # work on a copy so the raw data is never changed
log = []                 # a simple list where we record what we did

# 2a. Remove exact duplicate rows
before = len(df)
df = df.drop_duplicates()
log.append(f"Removed {before - len(df)} duplicate rows")

# 2b. Fix inconsistent labels: "Steer " (capital + trailing space) -> "steer"
df["sex"] = df["sex"].str.strip().str.lower()
log.append("Standardised sex labels (trimmed spaces, lower case)")

# 2c. Remove impossible carcass weights. A beef carcass is roughly 150-450 kg.
# Anything outside that range is a data entry error (e.g. an extra zero).
bad_weight = ~df["hot_carcass_weight_kg"].between(150, 450)
log.append(f"Removed {bad_weight.sum()} rows with impossible carcass weight")
df = df[~bad_weight]

# test
print(raw["hot_carcass_weight_kg"].between(150, 450).value_counts())
print((~raw["hot_carcass_weight_kg"].between(150, 450)).value_counts())
# end test

# 2d. Missing live weight / pH: we do NOT drop these rows. Our main analysis
# uses carcass value, which doesn't need them. We just keep the blanks.
log.append(f"Left {df['live_weight_kg'].isna().sum()} missing live weights "
           f"and {df['ultimate_ph'].isna().sum()} missing pH values as blank "
           "(not needed for the value analysis)")

# 2e. Create the key business metric: NET VALUE PER ANIMAL.
# = what the carcass sold for, minus downstream customer claims.
df["net_value"] = df["carcass_value"] - df["claim_cost"]

# 2f. A yes/no column for downgrades, handy for counting rates
df["is_downgrade"] = df["grade"] == "Downgrade"

print("\n".join(log))
print("\nRows after cleaning:", len(df))


# %% 3. EXPLORE: IS THE PILOT FAIR? -------------------------------------------
# Before comparing outcomes, check the two groups look similar at the start.
# If the trial group got heavier or better-bred animals, any improvement could
# be down to that and NOT the technology.
print("Animals per group:")
print(df["group"].value_counts(), "\n")

# groupby + agg: calculate several summaries per group in one go.
# Syntax: new_name=("column", "function")
balance = df.groupby("group").agg(
    animals=("animal_id", "count"),
    avg_live_weight=("live_weight_kg", "mean"),
    avg_carcass_weight=("hot_carcass_weight_kg", "mean"),
    pct_steers=("sex", lambda s: (s == "steer").mean() * 100),
).round(1)
print(balance)
# Take-away: if these numbers are close, randomising by lot worked.


# %% 4. PILOT RESULTS: WHAT DID THE TECHNOLOGY CHANGE? -------------------------
# Compare average outcomes between control and trial.
results = df.groupby("group").agg(
    animals=("animal_id", "count"),
    downgrade_rate=("is_downgrade", "mean"),
    bruising_rate=("bruising", "mean"),
    dark_cutter_rate=("dark_cutter", "mean"),
    avg_trim_loss_kg=("trim_loss_kg", "mean"),
    avg_claim_cost=("claim_cost", "mean"),
    avg_net_value=("net_value", "mean"),
).T          # .T flips the table so groups are columns (easier to read)
results["difference"] = results["trial"] - results["control"]
print(results.round(3))

# Grade mix as percentages: how did the split between
# Premium / Standard / Downgrade change?
grade_mix = (pd.crosstab(df["group"], df["grade"], normalize="index") * 100)
grade_mix = grade_mix[["Premium", "Standard", "Downgrade"]].round(1)
print("\nGrade mix (% of animals):")
print(grade_mix)

# Chart: grade mix by group
ax = grade_mix.plot(kind="bar", stacked=True, figsize=(6, 4),
                    color=["#2ca02c", "#bdbdbd", "#d62728"])
ax.set_ylabel("% of animals")
ax.set_xlabel("")
ax.set_title("Grade mix: trial shifts animals out of 'Downgrade'")
ax.legend(title="Grade", bbox_to_anchor=(1.02, 1), loc="upper left")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(OUT / "grade_mix.png")
plt.show()


# %% 5. STATISTICS: IS THE DIFFERENCE REAL OR LUCK? ----------------------------
# Even with no technology effect, two groups of animals would differ a little
# by chance. Tests tell us how likely it is that we'd see this big a gap
# by luck alone (the p-value).

control = df.loc[df["group"] == "control", "net_value"]
trial = df.loc[df["group"] == "trial", "net_value"]
uplift = trial.mean() - control.mean()
print(f"Observed uplift in net value: ${uplift:,.2f} per animal")

# 5a. Welch's t-test: compares two averages without assuming equal spread.
t_stat, p_value = stats.ttest_ind(trial, control, equal_var=False)
print(f"Welch t-test: t = {t_stat:.2f}, p = {p_value:.4f}")

# 5b. Mann-Whitney U: a backup test that doesn't assume bell-shaped data.
u_stat, p_mw = stats.mannwhitneyu(trial, control, alternative="two-sided")
print(f"Mann-Whitney: p = {p_mw:.4f}")

# 5c. Chi-square test for downgrade RATES (yes/no outcome, so we compare
# proportions, not averages).
table = pd.crosstab(df["group"], df["is_downgrade"])
chi2, p_chi, _, _ = stats.chi2_contingency(table)
print(f"Chi-square on downgrade rate: p = {p_chi:.4f}")

# 5d. BOOTSTRAP confidence interval. Idea: re-draw the data with replacement
# 5,000 times, recalculate the uplift each time, and look at the spread.
# The middle 95% gives a plausible range for the true uplift.
boot = np.empty(5000)
for i in range(5000):
    t_sample = rng.choice(trial.to_numpy(), size=len(trial), replace=True)
    c_sample = rng.choice(control.to_numpy(), size=len(control), replace=True)
    boot[i] = t_sample.mean() - c_sample.mean()
ci_low, ci_high = np.percentile(boot, [2.5, 97.5])
print(f"95% bootstrap CI for uplift: ${ci_low:,.2f} to ${ci_high:,.2f} per animal")

# 5e. ROBUSTNESS CHECK. We randomised by LOT (consignment), and animals in the
# same lot are similar to each other, so animals aren't fully independent.
# A safer check: average within each lot first, then compare lots.
lot_means = df.groupby(["lot_id", "group"])["net_value"].mean().reset_index()
t_lot, p_lot = stats.ttest_ind(
    lot_means.loc[lot_means["group"] == "trial", "net_value"],
    lot_means.loc[lot_means["group"] == "control", "net_value"],
    equal_var=False,
)
print(f"Lot-level t-test (more conservative): p = {p_lot:.4f}")

# Chart: distribution of the bootstrap uplift
fig, ax = plt.subplots(figsize=(6, 4))
ax.hist(boot, bins=50, color="#1f77b4", alpha=0.8)
ax.axvline(ci_low, color="k", ls="--", lw=1)
ax.axvline(ci_high, color="k", ls="--", lw=1)
ax.axvline(0, color="#d62728", lw=1.5)
ax.set_title("Uplift per animal: 95% confidence interval (dashed)")
ax.set_xlabel("Uplift in net value ($ per animal)  |  red line = no effect")
ax.set_ylabel("Frequency")
plt.tight_layout()
plt.savefig(OUT / "uplift_bootstrap.png")
plt.show()
# How to say it in an interview: "The trial group earned about $X more per
# animal; the 95% interval excludes zero, and the result holds at lot level."


# %% 6. ROI MODEL -------------------------------------------------------------
# Now convert the pilot result into a business case. We build a FUNCTION that
# takes assumptions as inputs, so we can easily re-run it for different cases.

# All assumptions in ONE place, clearly labelled. These are illustrative
# numbers you would normally confirm with the client / vendor.
BASE = {
    "uplift_per_head": uplift,      # from the pilot ($ per animal)
    "annual_head": 60_000,          # animals processed per year at the plant
    "realisation": 0.60,            # haircut: we only bank 60% of pilot gain
                                    # (pilots are usually better-run than rollout)
    "capex": 1_500_000,             # upfront cost: hardware + install ($)
    "annual_opex": 400_000,         # yearly running cost: licences, support, staff
    "ramp": [0.5, 0.8, 1.0, 1.0, 1.0],  # share of benefit achieved each year
    "years": 5,
    "discount_rate": 0.08,          # 8%: money later is worth less than today
}


def roi_model(a: dict) -> dict:
    """Return NPV, payback and ROI for a set of assumptions `a`."""
    years = a["years"]
    ramp = np.array(a["ramp"][:years])

    # Benefit each year = gain per animal x animals x realisation x ramp-up
    benefits = a["uplift_per_head"] * a["annual_head"] * a["realisation"] * ramp
    net_yearly = benefits - a["annual_opex"]

    # Cash flows: year 0 is the upfront cost (negative), then yearly net benefit
    cashflows = np.concatenate([[-a["capex"]], net_yearly])

    # Discounting: divide each year's cash by (1 + rate) ^ year
    discount_factors = 1 / (1 + a["discount_rate"]) ** np.arange(years + 1)
    npv = float((cashflows * discount_factors).sum())

    # Payback: first year where cumulative cash turns positive
    # (linear interpolation within that year)
    cumulative = np.cumsum(cashflows)
    payback = np.nan
    for yr in range(1, years + 1):
        if cumulative[yr] >= 0:
            payback = (yr - 1) + (-cumulative[yr - 1]) / cashflows[yr]
            break

    roi_pct = float((net_yearly.sum() - a["capex"]) / a["capex"] * 100)
    return {"npv": npv, "payback_years": payback, "roi_pct": roi_pct,
            "cumulative": cumulative, "benefits": benefits}


base_result = roi_model(BASE)
print(f"BASE CASE  NPV: ${base_result['npv']:,.0f} | "
      f"Payback: {base_result['payback_years']:.1f} years | "
      f"5-yr ROI: {base_result['roi_pct']:.0f}%")


# %% 7. SCENARIOS: BEST / BASE / WORST -----------------------------------------
# Clients don't trust a single number. Show a range.
# We use the CONFIDENCE INTERVAL from the statistics for the uplift:
#   conservative = low end of CI, optimistic = high end of CI.
scenarios = {
    "Conservative": {**BASE, "uplift_per_head": ci_low, "realisation": 0.5,
                     "capex": BASE["capex"] * 1.2},
    "Base":         BASE,
    "Optimistic":   {**BASE, "uplift_per_head": ci_high, "realisation": 0.75},
}
# {**BASE, "key": value} means "copy BASE but override these keys".

rows = []
for name, assumptions in scenarios.items():
    r = roi_model(assumptions)
    rows.append({"scenario": name,
                 "uplift_per_head": assumptions["uplift_per_head"],
                 "npv": r["npv"], "payback_years": r["payback_years"],
                 "roi_pct": r["roi_pct"]})
scen_table = pd.DataFrame(rows).set_index("scenario").round(1)
print(scen_table)
scen_table.to_csv(OUT / "scenario_table.csv")

# Chart: cumulative cash position per scenario (the "payback" picture)
fig, ax = plt.subplots(figsize=(7, 4))
for name, assumptions in scenarios.items():
    cum = roi_model(assumptions)["cumulative"] / 1e6
    ax.plot(range(len(cum)), cum, marker="o", label=name)
ax.axhline(0, color="k", lw=1)
ax.set_xlabel("Year")
ax.set_ylabel("Cumulative cash ($ million)")
ax.set_title("Cumulative cash flow: where each scenario breaks even")
ax.legend()
plt.tight_layout()
plt.savefig(OUT / "cumulative_cash.png")
plt.show()


# %% 8. SENSITIVITY: WHAT DRIVES THE ANSWER? -----------------------------------
# Change ONE assumption at a time by -20% / +20% and see how NPV moves.
# The assumption that moves NPV the most is the one to challenge first.
drivers = ["uplift_per_head", "annual_head", "realisation", "capex", "annual_opex"]
sens = []
for d in drivers:
    low = roi_model({**BASE, d: BASE[d] * 0.8})["npv"]
    high = roi_model({**BASE, d: BASE[d] * 1.2})["npv"]
    sens.append((d, low, high))
sens_df = pd.DataFrame(sens, columns=["driver", "npv_at_-20%", "npv_at_+20%"])
sens_df["swing"] = (sens_df["npv_at_+20%"] - sens_df["npv_at_-20%"]).abs()
sens_df = sens_df.sort_values("swing", ascending=True)
print(sens_df.round(0))

# Tornado chart
fig, ax = plt.subplots(figsize=(7, 4))
ypos = np.arange(len(sens_df))
base_npv = base_result["npv"]
ax.barh(ypos, (sens_df["npv_at_-20%"] - base_npv) / 1e6, color="#d62728",
        label="-20%")
ax.barh(ypos, (sens_df["npv_at_+20%"] - base_npv) / 1e6, color="#2ca02c",
        label="+20%")
ax.set_yticks(ypos)
ax.set_yticklabels(sens_df["driver"])
ax.axvline(0, color="k", lw=1)
ax.set_xlabel("Change in NPV vs base case ($ million)")
ax.set_title("Sensitivity: which assumption matters most?")
ax.legend()
plt.tight_layout()
plt.savefig(OUT / "sensitivity_tornado.png")
plt.show()


# %% 9. BREAK-EVEN: HOW LOW CAN THE BENEFIT GO? --------------------------------
# What is the smallest uplift per animal for which NPV is still >= 0?
# We search for it by repeatedly halving the range (bisection).
lo, hi = 0.0, BASE["uplift_per_head"] * 2
for _ in range(60):
    mid = (lo + hi) / 2
    if roi_model({**BASE, "uplift_per_head": mid})["npv"] > 0:
        hi = mid
    else:
        lo = mid
breakeven = hi
print(f"Break-even uplift: ${breakeven:,.2f} per animal "
      f"(pilot measured ${uplift:,.2f}, i.e. a safety margin of "
      f"{(1 - breakeven / uplift) * 100:.0f}%)")


# %% 10. SAVE KEY NUMBERS FOR YOUR WRITE-UP ------------------------------------
# Write the headline results to a text file you can paste into your summary.
summary = f"""
HEADLINE RESULTS
Pilot animals analysed:       {len(df):,} (trial {len(trial):,} / control {len(control):,})
Uplift in net value:          ${uplift:,.2f} per animal
95% confidence interval:      ${ci_low:,.2f} to ${ci_high:,.2f}
Welch t-test p-value:         {p_value:.4f}
Lot-level t-test p-value:     {p_lot:.4f}
Downgrade rate:               {results.loc['downgrade_rate','control']:.1%} -> {results.loc['downgrade_rate','trial']:.1%}

BASE CASE (5 years, {BASE['discount_rate']:.0%} discount rate)
NPV:                          ${base_result['npv']:,.0f}
Payback:                      {base_result['payback_years']:.1f} years
5-year ROI:                   {base_result['roi_pct']:.0f}%
Break-even uplift:            ${breakeven:,.2f} per animal
"""
(OUT / "headline_results.txt").write_text(summary)
print(summary)
