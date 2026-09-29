
import os, re, json, math, io
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="AI Trading Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- Technical engine ----------
def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()

def rsi(s, n=14):
    delta = s.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    avg_up = up.ewm(alpha=1/n, adjust=False).mean()
    avg_down = down.ewm(alpha=1/n, adjust=False).mean()
    rs = avg_up / avg_down.replace(0, np.nan)
    return 100 - (100/(1+rs))

def atr(df, n=14):
    prev = df.close.shift(1)
    tr = pd.concat([
        df.high-df.low,
        (df.high-prev).abs(),
        (df.low-prev).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()

def normalize_csv(df):
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    aliases = {
        "o":"open","h":"high","l":"low","c":"close",
        "open_price":"open","high_price":"high",
        "low_price":"low","close_price":"close"
    }
    df = df.rename(columns=aliases)
    required = ["open","high","low","close"]
    missing = [x for x in required if x not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    for c in required:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=required).reset_index(drop=True)
    if len(df) < 220:
        raise ValueError("Please provide at least 220 OHLC rows for a stable EMA-200 calculation.")
    return df

def analyze(df, min_rr=2.0, risk_pct=0.5, account=1000.0):
    df = normalize_csv(df)
    df["ema20"] = ema(df.close,20)
    df["ema50"] = ema(df.close,50)
    df["ema200"] = ema(df.close,200)
    df["rsi14"] = rsi(df.close,14)
    df["atr14"] = atr(df,14)

    x = df.iloc[-1]
    recent = df.tail(30)
    price = float(x.close)
    a = float(x.atr14)

    bull = x.ema20 > x.ema50 > x.ema200 and price > x.ema20
    bear = x.ema20 < x.ema50 < x.ema200 and price < x.ema20

    if bull:
        direction = "BUY"
        stop = min(float(df.tail(10).low.min()), price - 1.2*a)
        risk = price - stop
        target = price + min_rr*risk
        momentum_ok = 45 <= float(x.rsi14) <= 70
        allowed = risk > 0 and momentum_ok
    elif bear:
        direction = "SELL"
        stop = max(float(df.tail(10).high.max()), price + 1.2*a)
        risk = stop-price
        target = price - min_rr*risk
        momentum_ok = 30 <= float(x.rsi14) <= 55
        allowed = risk > 0 and momentum_ok
    else:
        direction = "NO TRADE"
        stop = target = risk = 0
        momentum_ok = False
        allowed = False

    risk_cash = account*risk_pct/100
    units = risk_cash/risk if risk > 0 else 0

    reasons = []
    reasons.append("EMA 20/50/200 trend alignment: PASS" if (bull or bear) else "EMA trend alignment: FAIL")
    reasons.append("Price is on the trend side of EMA 20: PASS" if ((bull and price>x.ema20) or (bear and price<x.ema20)) else "Price/EMA condition: FAIL")
    reasons.append(f"RSI(14): {float(x.rsi14):.1f}")
    reasons.append("Momentum filter: PASS" if momentum_ok else "Momentum filter: FAIL")

    return {
        "df":df, "direction":direction, "allowed":allowed,
        "price":price, "stop":stop, "target":target,
        "risk_per_unit":risk, "risk_cash":risk_cash,
        "units":units, "rsi":float(x.rsi14), "atr":a,
        "support":float(recent.low.min()),
        "resistance":float(recent.high.max()),
        "trend":"BULLISH" if bull else "BEARISH" if bear else "MIXED",
        "reasons":reasons
    }

def extract_numbers(text):
    # Useful as a transparent helper for pasted chart text.
    nums = re.findall(r'(?<!\w)(?:\d+(?:\.\d+)?)(?!\w)', text or "")
    return [float(n) for n in nums]

# ---------- Header ----------
st.title("📊 AI Trading Analyzer")
st.caption("Multi-input research and paper-trading assistant — no guaranteed profits and no live order execution.")

with st.sidebar:
    st.header("Trade settings")
    account = st.number_input("Account size", min_value=1.0, value=1000.0, step=100.0)
    risk_pct = st.number_input("Max risk per trade (%)", 0.1, 2.0, 0.5, 0.1)
    rr = st.number_input("Minimum risk/reward", 1.0, 5.0, 2.0, 0.5)
    st.divider()
    st.markdown("**Safety gate**")
    st.write("Live broker orders are disabled.")
    st.write("Every setup can be rejected as **NO TRADE**.")

# ---------- Inputs ----------
st.subheader("1. Give the system your market information")
input_tabs = st.tabs(["📷 Screenshot", "📁 OHLC / CSV", "📝 Extracted chart/chat text"])

with input_tabs[0]:
    screenshot = st.file_uploader(
        "Upload a TradingView/broker chart screenshot",
        type=["png","jpg","jpeg","webp"],
        key="screen"
    )
    if screenshot:
        st.image(screenshot, use_container_width=True)
        st.info("The screenshot is visual context. Exact numeric trade levels should come from market data whenever possible.")

with input_tabs[1]:
    csv_file = st.file_uploader(
        "Upload OHLC CSV",
        type=["csv"],
        key="ohlc"
    )
    st.caption("Recommended columns: datetime, open, high, low, close.")
    if csv_file:
        try:
            raw = pd.read_csv(csv_file)
            st.success(f"Loaded {len(raw):,} rows.")
        except Exception as e:
            st.error(f"Could not read CSV: {e}")

with input_tabs[2]:
    extracted = st.text_area(
        "Paste extracted chart information, notes, alerts, or another AI's chart description",
        height=220,
        placeholder="""Example:
EURUSD 15m
Current price: 1.10450
Trend: bullish
Resistance: 1.10600
Support: 1.10200
Price broke resistance and pulled back...
"""
    )
    if extracted:
        st.write(f"Text received: {len(extracted):,} characters.")
        st.write(f"Numbers detected for reference: {extract_numbers(extracted)[:20]}")

st.subheader("2. Analysis controls")
symbol = st.text_input("Asset / symbol", "EURUSD")
timeframe = st.selectbox("Primary timeframe", ["5m","15m","30m","1h","4h","1D"], index=1)

if st.button("🔎 ANALYZE MARKET", type="primary", use_container_width=True):
    if not csv_file:
        st.warning("For this MVP, upload OHLC CSV to calculate reliable numeric entry/SL/TP levels. Screenshot/text can be supplied as additional context.")
    else:
        try:
            raw = pd.read_csv(csv_file)
            result = analyze(raw, rr, risk_pct, account)

            st.divider()
            st.subheader(f"3. Decision — {symbol} / {timeframe}")

            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Trend", result["trend"])
            c2.metric("Decision", "TRADE CANDIDATE" if result["allowed"] else "NO TRADE")
            c3.metric("RSI", f"{result['rsi']:.1f}")
            c4.metric("R:R", f"{rr:.1f}:1")

            if result["allowed"]:
                st.success("The deterministic rules currently allow a trade candidate. This is NOT a prediction or guarantee.")
                a,b,c,d,e = st.columns(5)
                a.metric("Direction", result["direction"])
                b.metric("Entry", f"{result['price']:.5f}")
                c.metric("Stop", f"{result['stop']:.5f}")
                d.metric("Target", f"{result['target']:.5f}")
                e.metric("Max risk", f"${result['risk_cash']:.2f}")
                st.metric("Illustrative units", f"{result['units']:.4f}")
            else:
                st.error("NO TRADE — at least one required condition failed.")

            st.subheader("Decision evidence")
            for reason in result["reasons"]:
                st.write("• " + reason)

            st.subheader("Market levels")
            st.write(f"Recent support: **{result['support']:.5f}**")
            st.write(f"Recent resistance: **{result['resistance']:.5f}**")
            st.write(f"ATR(14): **{result['atr']:.5f}**")

            st.subheader("Input summary")
            st.write(f"Screenshot supplied: {'YES' if screenshot else 'NO'}")
            st.write(f"Extracted text supplied: {'YES' if extracted else 'NO'}")
            st.write("OHLC supplied: YES")

            st.subheader("Recent OHLC + indicators")
            st.dataframe(result["df"].tail(25), use_container_width=True)

        except Exception as e:
            st.error(f"Analysis failed: {e}")

# ---------- Backtest ----------
st.divider()
st.subheader("4. Simple historical test")
st.caption("This is a baseline test of the same EMA/RSI logic. It is not a guarantee of future performance.")

if csv_file:
    if st.button("Run baseline backtest", use_container_width=True):
        try:
            df = normalize_csv(pd.read_csv(csv_file))
            df["ema20"]=ema(df.close,20); df["ema50"]=ema(df.close,50); df["ema200"]=ema(df.close,200); df["rsi14"]=rsi(df.close,14)
            trades=[]
            for i in range(200,len(df)-1):
                row=df.iloc[i]
                nxt=df.iloc[i+1]
                bull=row.ema20>row.ema50>row.ema200 and row.close>row.ema20 and 45<=row.rsi14<=70
                bear=row.ema20<row.ema50<row.ema200 and row.close<row.ema20 and 30<=row.rsi14<=55
                if bull:
                    entry=row.close
                    stop=min(df.iloc[max(0,i-9):i+1].low.min(), entry-1.2*(df.high-df.low).tail(14).mean())
                    risk=entry-stop
                    target=entry+rr*risk
                    if nxt.low<=stop: outcome=-1
                    elif nxt.high>=target: outcome=rr
                    else: outcome=0
                    trades.append(outcome)
                elif bear:
                    entry=row.close
                    stop=max(df.iloc[max(0,i-9):i+1].high.max(), entry+1.2*(df.high-df.low).tail(14).mean())
                    risk=stop-entry
                    target=entry-rr*risk
                    if nxt.high>=stop: outcome=-1
                    elif nxt.low<=target: outcome=rr
                    else: outcome=0
                    trades.append(outcome)
            if trades:
                arr=np.array(trades)
                wins=(arr>0).sum(); losses=(arr<0).sum()
                st.write(f"Trades tested: **{len(arr)}**")
                st.write(f"Win observations: **{wins}** | Loss observations: **{losses}** | Unresolved next-bar observations: **{(arr==0).sum()}**")
                st.write(f"Simple net R: **{arr.sum():.2f}R**")
                st.warning("This intentionally simplified backtest does not model spread, slippage, intra-bar order sequencing, financing, or broker-specific contract sizing. Use a proper TradingView/backtesting framework before risking money.")
            else:
                st.info("No baseline trades were generated.")
        except Exception as e:
            st.error(f"Backtest failed: {e}")

st.divider()
st.subheader("5. Production roadmap")
st.markdown("""
**Current:** screenshot + text + OHLC inputs → deterministic technical/risk engine → trade/no-trade plan.

**Next:** add a vision model for screenshot interpretation, TradingView webhook alerts, a database of every signal/outcome, walk-forward testing, and paper trading.

**Later:** broker integration can be considered only after validation, with an explicit human approval switch.
""")
st.caption("Financial markets are risky. Backtested results do not guarantee future performance.")
