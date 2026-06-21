def pct_text(value):
    return "N/A" if value is None or pd.isna(value) else f"{value:.2%}"

def pct_text_with_fraction(value, fraction_string):
    return f"@ {pct_text(value)} ({fraction_string})"

def number_text(value, _ignore=None):
    decimals = 2
    text = "N/A" if value is None or pd.isna(value) else f"{value:.{decimals}f}"
    return f"({text})"
