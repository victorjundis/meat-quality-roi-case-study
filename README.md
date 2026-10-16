# Meat Quality Monitoring: Pilot Analysis and ROI Case Study

A practice case study for a commercial data analyst role. The data is **synthetic** (made up), so don't quote the numbers as real industry figures.

**Question:** A beef processor ran a 12-week pilot of technology that monitors quality from live animal to carcass. Did it work, and is it worth investing in at full scale?

## What's in this folder

| File | Purpose |
|---|---|
| `generate_data.py` | Creates the dataset (`data/meat_trial_data.csv`). Run once. |
| `analysis.py` | The case study: clean, compare, test, ROI model, scenarios. Run in cells. |
| `requirements.txt` | Python libraries needed |
| `data/` | The CSV the scripts read and write |
| `outputs/` | Charts and result tables the analysis creates |

## The dataset

One row per animal, about 3,300 animals from 180 consignments (lots). Each **lot** was randomly assigned to `control` (normal practice) or `trial` (technology-monitored).

| Column | Meaning |
|---|---|
| `animal_id`, `lot_id`, `farm_id`, `kill_date` | Identifiers and date |
| `group` | `control` or `trial` |
| `sex`, `live_weight_kg`, `hot_carcass_weight_kg` | Animal characteristics |
| `bruising`, `trim_loss_kg` | Handling damage and kg trimmed off |
| `dark_cutter`, `ultimate_ph` | Dark-cutting defect and the pH reading |
| `grade`, `price_per_kg`, `carcass_value` | Premium / Standard / Downgrade and the resulting value (AUD) |
| `claim_cost` | Downstream customer claim cost |
| `tech_risk_score` | Technology risk score (trial animals only) |

The data has deliberate mess for you to clean: duplicates, missing values, inconsistent labels and impossible weights.

## One-time setup (about 15 minutes)

### 1. Install the tools
- **Python 3.10+**: from python.org. On Windows, tick "Add Python to PATH" in the installer.
- **Git**: from git-scm.com (accept the defaults).
- In **VS Code**, install the extensions **Python** and **Jupyter** (Extensions icon in the left bar, search by name).

### 2. Open the project in VS Code
1. Unzip this folder somewhere sensible (e.g. `Documents/meat-quality-roi-case-study`).
2. VS Code: **File > Open Folder** and choose it.
3. Open the terminal inside VS Code: **Terminal > New Terminal**. Every command below goes there.

### 3. Create a virtual environment
A virtual environment is a private box of libraries for this project, so it doesn't clash with anything else on your laptop.

```bash
python -m venv .venv
```
Activate it:
- Windows: `.venv\Scripts\activate`
- Mac/Linux: `source .venv/bin/activate`

You should see `(.venv)` at the start of the terminal line. If Windows blocks the activation script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.

Then install the libraries:
```bash
pip install -r requirements.txt
```
VS Code may ask which Python to use: pick the one inside `.venv`. (Or press `Ctrl+Shift+P`, type "Python: Select Interpreter".)

### 4. Create the dataset
```bash
python generate_data.py
```
You should see "Saved 3,352 rows" and a new file at `data/meat_trial_data.csv`.

## Running the analysis

Open `analysis.py`. You'll see **Run Cell** above each `# %%` line. Click it to run one section at a time and see the output in a panel on the right. Work top to bottom.

Don't just run it. For each cell: read the comments, predict what the output will look like, run it, then change something (a number, a column) and see what breaks. That's how rusty skills come back.

Or run everything at once: `python analysis.py`. Charts and tables land in `outputs/`.

## The story the analysis tells

1. **Was the pilot fair?** Control and trial animals have similar weights and sex mix.
2. **What changed?** The trial group had fewer downgrades, less bruising and trim, and fewer claims, worth roughly $38 more per animal.
3. **Is it real?** Welch t-test, Mann-Whitney, chi-square and a bootstrap confidence interval. A lot-level check confirms it, since animals in a lot aren't independent.
4. **What is it worth?** An ROI model scales the pilot gain up to a full plant, with a 40% haircut because pilots usually outperform rollouts.
5. **How sure are we?** Conservative / base / optimistic scenarios, a sensitivity chart and a break-even uplift.

### What the results tell you
- **Base case is positive** (NPV about $1.5M, payback about 2.5 years).
- **The conservative case is negative.** The low end of the confidence interval ($14 per animal), plus a lower realisation rate and higher capex, doesn't pay back. This is not a bug. It's a realistic and useful finding: the decision is only safe if the true uplift is above the **break-even of about $26 per animal**. A good analyst says this out loud, and recommends a bigger or longer pilot to narrow the interval before committing capital.
- In the tornado chart, `uplift_per_head`, `annual_head` and `realisation` have identical bars because they all multiply together. Say that in the interview rather than being caught out by it.

## Putting it on GitHub

### First time
1. On github.com, click **New repository**, name it `meat-quality-roi-case-study`, keep it **Public** (so employers can see it) and don't add a README (you already have one). Click Create.
2. In the VS Code terminal, from the project folder:

```bash
git init
git add .
git commit -m "Initial commit: meat quality pilot ROI case study"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/meat-quality-roi-case-study.git
git push -u origin main
```
Replace `YOUR-USERNAME`. A browser window may pop up to sign in to GitHub the first time.

If git says it doesn't know who you are, run these once:
```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

### Every time after
```bash
git add .
git commit -m "Describe what you changed"
git push
```
Small, regular commits with clear messages look professional. For example: "Add lot-level robustness check", "Add sensitivity chart".

## Make it your own (this is what impresses interviewers)

Once it runs, extend it. These all map to the job ad.
1. **Write a one-page client summary** (Word or markdown) for a non-technical plant manager: the headline, one chart, the recommendation and the risks. No jargon.
2. **Add SQL.** Load the CSV into SQLite and rewrite two of the group comparisons as SQL queries with `GROUP BY` and a window function.
3. **Add a regression** with `statsmodels` (`net_value ~ group + farm_id + hot_carcass_weight_kg`) to adjust for farm differences.
4. **Build a small interactive dashboard** with Plotly or Streamlit.
5. **Challenge the assumptions.** Which one in the ROI model is weakest? What evidence would you ask the client for?
6. **Use an AI coding tool** to help with any of the above, and write down how you checked its output was right. The job ad asks for this explicitly.

## Interview talking points
- "I randomised by lot, so I checked the result at lot level too, not just per animal."
- "I haircut the pilot benefit by 40%, because pilots are usually run more carefully than rollouts."
- "The break-even uplift is about $26 per animal against a measured $38, so there's a margin, but the confidence interval includes values below break-even, so I'd recommend extending the pilot."
- "All assumptions sit in one dictionary, so a client can change them and see the effect immediately."

## Common errors
| Error | Fix |
|---|---|
| `python` not found | Try `python3`, or reinstall Python and tick "Add to PATH" |
| `ModuleNotFoundError: pandas` | The virtual environment isn't active or libraries aren't installed. Activate `.venv`, then `pip install -r requirements.txt` |
| `FileNotFoundError: data/meat_trial_data.csv` | Run `python generate_data.py` first, from the project folder |
| Charts don't appear | Run cells in VS Code (Run Cell), or open the PNG files in `outputs/` |
| Git asks for a password | Use the browser sign-in prompt, or a personal access token (GitHub > Settings > Developer settings) |
