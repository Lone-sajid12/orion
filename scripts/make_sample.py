"""Generate deterministic sample dataset for onboarding/testing."""
import numpy as np, pandas as pd
rng = np.random.default_rng(42)
n = 600
dates = pd.date_range("2023-01-01", periods=n, freq="D")
regions = rng.choice(["North","South","East","West"], size=n, p=[0.3,0.25,0.25,0.2])
channels = rng.choice(["Online","Retail","Partner"], size=n, p=[0.5,0.35,0.15])
base = {"North":520,"South":430,"East":470,"West":390}
rev = np.array([base[r] for r in regions], dtype=float)
rev *= 1 + 0.004*np.arange(n)  # upward trend
rev += rng.normal(0, 70, n)
units = np.maximum(1, (rev/48 + rng.normal(0,3,n)).astype(int))
discount = np.clip(rng.normal(8, 4, n), 0, 30).round(1)
rating = np.clip(rng.normal(4.1, 0.6, n), 1, 5).round(1)
churn = ((rating < 3.4) & (rng.random(n) < 0.6)) | (rng.random(n) < 0.06)
churn = churn.astype(int)
# inject missing + whitespace + outliers
rev[rng.choice(n, 30, replace=False)] = np.nan
rating[rng.choice(n, 20, replace=False)] = np.nan
regions = regions.astype(object); regions[rng.choice(n, 12, replace=False)] = " north "
rev[5] = 4000; rev[99] = 3900  # outliers
df = pd.DataFrame({"date": dates, "region": regions, "channel": channels,
                   "revenue": rev.round(2), "units": units, "discount_pct": discount,
                   "rating": rating, "churned": churn})
df.to_csv("/home/user/orion/sample_data/orion_sample_sales.csv", index=False)
print(df.shape); print(df.head(3).to_string())
