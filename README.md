
# AI Trading Analyzer App — v2

## What changed

This version is a multi-input application instead of a screenshot-only concept.

It accepts:

1. **Chart screenshots** — visual context.
2. **OHLC CSV data** — primary source for numerical analysis.
3. **Extracted chart/chat text** — paste text from a chart extraction, alert, notes, or another analysis.

The app combines the inputs but does not allow screenshot/text guesses to override deterministic risk rules.

## Run it

Install Python 3.10+.

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Then:

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app opens in your browser.

## Android

This package is a web-style app, not an Android APK. On Android, run it on a computer/server and open the Streamlit address from your phone, or deploy it to a supported cloud host.

A true APK requires a separate Android packaging project. The trading engine itself can be reused.

## Inputs

### Screenshot
Upload a PNG/JPG/WEBP TradingView or broker screenshot.

### OHLC
CSV should contain:
- open
- high
- low
- close

A datetime column is optional.

At least 220 rows are requested because EMA 200 is used.

### Extracted text
Paste chart descriptions, alert text, notes, or extracted chart information.

The app does not treat arbitrary text as proof of a trade. It is contextual information.

## Safety design

The system:
- does not guarantee profit
- does not promise 100% accuracy
- does not place broker orders
- has a NO TRADE state
- calculates maximum cash risk
- separates input interpretation from deterministic rules

## Next engineering phase

1. Add OpenAI vision analysis for screenshots.
2. Convert vision output to strict JSON.
3. Add TradingView webhook receiver.
4. Add a real market-data source.
5. Store signals/outcomes in SQLite/PostgreSQL.
6. Build proper walk-forward backtesting.
7. Add paper-trading mode.
8. Add performance dashboard.
9. Only after validation, consider broker integration with human approval.
