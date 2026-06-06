import pandas as pd


def trim(group):
    n = len(group)
    if n < 10:
        return pd.Series({
            "avg_gr": group["guess rate"].mean(),
            "avg_uf": group["usefulness"].mean(),
            "count": n,
        })
    trimmed_gr = group["guess rate"].sort_values()
    trimmed_uf = group["usefulness"].sort_values()
    return pd.Series({
        "avg_gr": trimmed_gr.mean(),
        "avg_uf": trimmed_uf.mean(),
        "count": n,
    })


def get_tiers(tourType):
    tiers = {
        "Tier1": ["GuessRate"],
        "Tier2": ["erigs", "avg8"],
    }
    tier_weights = {
        "Tier1": 0.35,
        "Tier2": 0.65,
    }
    return tiers, tier_weights


def get_normalization_spec(full_stats, tourType):
    return {
        "GuessRate": {
            "min": 0,
            "max": 100,
            "direction": "max",
        },
        "avg8": {
            "min": 1,
            "max": 8,
            "direction": "min",
        },
        "erigs": {
            "min": 0,
            "max": full_stats["erigs"].max(),
            "direction": "max",
        },
    }
