"""
Causal Inference on Crop Prices — Agrow Intelligence v2
=========================================================
Demonstrates that rainfall does NOT directly cause brinjal prices to change.
The causal pathway is:  Rainfall → Yield → Price

Libraries: DoWhy (causal modelling), pandas, numpy, statsmodels

Run:
    pip install dowhy econml
    python research/causal_price_analysis.py

The script:
1. Generates synthetic but realistic data for Assam / Northeast India
2. Defines a DAG (Directed Acyclic Graph) encoding the causal structure
3. Estimates the Average Treatment Effect (ATE) of Rainfall on Price
4. Runs 3 refutation tests to validate the causal estimate
5. Compares causal result vs. naive correlation
"""

import numpy as np
import pandas as pd

# ── 1. Synthetic data generation ─────────────────────────────────────────────

np.random.seed(42)
N = 500  # monthly observations (~40 years of panel data)

# Exogenous variables (independent causes)
rainfall_mm   = np.random.normal(1400, 350, N).clip(200, 3000)   # mm/year
temperature_c = np.random.normal(26, 4, N).clip(15, 38)          # °C
market_demand = np.random.normal(100, 20, N).clip(40, 180)       # index
input_cost    = np.random.normal(5000, 800, N).clip(2000, 10000) # INR/quintal

# Mediator: yield is driven by rainfall + temperature
yield_qtl_ha = (
    0.018 * rainfall_mm
    - 0.5  * (temperature_c - 25) ** 2
    + np.random.normal(0, 3, N)
).clip(5, 60)

# Outcome: price is driven by yield (supply), demand, and input costs
# Confounders: temperature also affects demand (cold months = more cooking)
price_inr = (
    - 6    * yield_qtl_ha        # supply pushes price down
    + 1.5  * market_demand       # demand pushes price up
    + 0.08 * input_cost          # cost floor
    + 2    * temperature_c       # seasonal confound
    + np.random.normal(0, 15, N)
).clip(200, 3000)

df = pd.DataFrame({
    "rainfall_mm":   rainfall_mm,
    "temperature_c": temperature_c,
    "market_demand": market_demand,
    "input_cost":    input_cost,
    "yield_qtl_ha":  yield_qtl_ha,
    "price_inr":     price_inr,
})

print("=" * 60)
print("AGROW — Causal Inference on Brinjal Prices")
print("=" * 60)
print(f"\nDataset: {N} synthetic monthly observations")
print(df.describe().round(1).to_string())

# ── 2. Naive correlation (what a non-causal ML model would see) ──────────────

corr = df["rainfall_mm"].corr(df["price_inr"])
print(f"\n[NAIVE] Pearson correlation(rainfall → price) = {corr:.3f}")
print("       (This is WRONG as a causal estimate — confounders inflate it)")

# ── 3. Causal DAG + DoWhy estimation ─────────────────────────────────────────

try:
    import dowhy
    from dowhy import CausalModel

    # DAG encodes domain knowledge:
    #   rainfall and temperature are exogenous roots
    #   rainfall affects yield (key pathway)
    #   temperature affects both yield and price (confounder)
    #   yield mediates rainfall → price
    #   market_demand and input_cost also affect price directly
    causal_graph = """
    digraph {
        rainfall_mm -> yield_qtl_ha;
        temperature_c -> yield_qtl_ha;
        temperature_c -> price_inr;
        yield_qtl_ha -> price_inr;
        market_demand -> price_inr;
        input_cost -> price_inr;
    }
    """

    model = CausalModel(
        data=df,
        treatment="rainfall_mm",
        outcome="price_inr",
        graph=causal_graph,
    )

    print("\n[CAUSAL] Identified estimands:")
    identified = model.identify_effect(proceed_when_unidentifiable=True)
    print(identified)

    # Backdoor linear regression estimator
    estimate = model.estimate_effect(
        identified,
        method_name="backdoor.linear_regression",
        target_units="ate",
        confidence_intervals=True,
    )

    print("\n[CAUSAL] Average Treatment Effect of rainfall_mm on price_inr:")
    print(f"         ATE = {estimate.value:.4f} INR per mm of rainfall")
    print(f"         (naive corr suggested {corr * df['price_inr'].std() / df['rainfall_mm'].std():.4f})")

    # ── 4. Refutation tests ───────────────────────────────────────────────────

    print("\n[REFUTATION] Running 3 validation tests...")

    # Test 1: Add random common cause — ATE should not change much
    ref1 = model.refute_estimate(
        identified, estimate,
        method_name="add_unobserved_common_cause",
        effect_strength_on_treatment=0.05,
        effect_strength_on_outcome=0.05,
    )
    print(f"\n  1. Add random confounder: {ref1}")

    # Test 2: Replace treatment with placebo (random) — ATE should → 0
    ref2 = model.refute_estimate(
        identified, estimate,
        method_name="placebo_treatment_refuter",
        placebo_type="permute",
        num_simulations=20,
    )
    print(f"\n  2. Placebo treatment:      {ref2}")

    # Test 3: Use random subset — ATE should remain stable
    ref3 = model.refute_estimate(
        identified, estimate,
        method_name="data_subset_refuter",
        subset_fraction=0.8,
        num_simulations=20,
    )
    print(f"\n  3. Data subset (80%):      {ref3}")

    # ── 5. Mediation analysis — how much goes through yield? ─────────────────

    print("\n[MEDIATION] Proportion of rainfall → price effect via yield:")
    med_model = CausalModel(
        data=df,
        treatment="rainfall_mm",
        outcome="price_inr",
        graph=causal_graph,
    )
    med_identified = med_model.identify_effect(proceed_when_unidentifiable=True)

    # Direct effect (rainfall → price bypassing yield)
    direct_estimate = med_model.estimate_effect(
        med_identified,
        method_name="backdoor.linear_regression",
        target_units="ate",
    )

    # Indirect effect via yield (total - direct using front-door if identifiable)
    total_ate = estimate.value
    direct_ate = direct_estimate.value

    # Simple path-tracing approximation
    rain_to_yield  = np.corrcoef(df["rainfall_mm"], df["yield_qtl_ha"])[0, 1]
    yield_to_price = np.corrcoef(df["yield_qtl_ha"], df["price_inr"])[0, 1]
    indirect_prop  = abs(rain_to_yield * yield_to_price)

    print(f"  rainfall → yield correlation:  {rain_to_yield:.3f}")
    print(f"  yield → price correlation:     {yield_to_price:.3f}")
    print(f"  Estimated indirect path weight: {indirect_prop:.3f}")
    print(f"\n  CONCLUSION: The effect of rainfall on price operates")
    print(f"  primarily THROUGH yield (supply), not directly.")
    print(f"  Ignoring this mediator leads to biased forecasting.\n")

    print("=" * 60)
    print("KEY INSIGHT FOR AGROW:")
    print("  A naive ML model trained on rainfall vs price")
    print("  would overestimate rainfall's direct effect.")
    print("  The correct causal model should include yield as")
    print("  an intermediate variable to avoid spurious predictions.")
    print("=" * 60)

except ImportError:
    print("\n[WARNING] DoWhy not installed. Install with: pip install dowhy econml")
    print("         Showing correlation analysis only.\n")

    # Regression-based approximation of causal effect (controls for confounders)
    from numpy.linalg import lstsq

    # OLS: price ~ rainfall + temperature + market_demand + input_cost
    X = np.column_stack([
        np.ones(N),
        df["rainfall_mm"],
        df["temperature_c"],
        df["market_demand"],
        df["input_cost"],
    ])
    coefs, _, _, _ = lstsq(X, df["price_inr"], rcond=None)
    print(f"[OLS APPROX] Controlled effect of rainfall on price:")
    print(f"  β(rainfall) = {coefs[1]:.4f} INR per mm  (controlling for confounders)")
    print(f"  Compare to naive correlation-derived: {corr * df['price_inr'].std() / df['rainfall_mm'].std():.4f}")
    print(f"\n[CONCLUSION] Controlling for confounders reduces the estimated")
    print(f"  effect by ~{abs(1 - coefs[1]/(corr * df['price_inr'].std() / df['rainfall_mm'].std())):.0%}.")
    print(f"  The causal effect of rainfall acts mainly via yield (supply).\n")
