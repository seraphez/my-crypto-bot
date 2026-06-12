import streamlit as st
import ccxt
import pandas as pd
from datetime import datetime
import requests
from streamlit_autorefresh import st_autorefresh

# =====================================================================
# 1. 網頁頂級配置與【手機/電腦雙模自適應】黑客風 CSS 注入
# =====================================================================
st.set_page_config(
    page_title="CryptoHunter | 智能量化雷達",
    layout="wide"
)

# 持久化記憶體，防止自動刷新時重複發送 HTTP 請求扣除 AI 額度
if "cached_ai_analysis" not in st.session_state:
    st.session_state.cached_ai_analysis = {}
if "previous_anomalies" not in st.session_state:
    st.session_state.previous_anomalies = set()
if "trigger_beep" not in st.session_state:
    st.session_state.trigger_beep = False

# 強制拔除 Streamlit 計時刷新時的半透明暗化遮罩（徹底消滅畫面變暗閃爍的 Bug）
st.markdown("""
    <style>
    div[data-testid="stForm"] { background-color: transparent !important; }
    .stApp div[data-testid="stVerticalBlock"] > div { opacity: 1 !important; }
    .stApp { background-color: #0E1117; }
    h1, h2, h3, h4 { color: #00FFCC !important; font-family: 'Courier New', monospace; }
    
    /* 核心數據卡片樣式 */
    .square-card {
        background-color: #161B22;
        border: 2px solid #30363D;
        border-radius: 15px;
        padding: 22px;
        margin-bottom: 15px;
        min-height: 220px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .coin-title { font-size: 24px; font-weight: bold; color: #FFF; font-family: 'Courier New', monospace; }
    .coin-price { font-size: 30px; font-weight: bold; color: #00FF66; margin: 8px 0; }
    .coin-change { font-size: 18px; font-weight: bold; }
    
    /* 異常動能警示框樣式 */
    .trend-analysis {
        background-color: #1F2937;
        padding: 10px;
        border-radius: 8px;
        font-size: 13px;
        color: #E5E7EB;
        margin-top: 10px;
        border-left: 4px solid #00FFCC;
        line-height: 1.4;
    }

    @media (max-width: 768px) {
        .square-card { padding: 15px; min-height: 180px; margin-bottom: 12px; border-radius: 10px; }
        .coin-title { font-size: 18px; }
        .coin-price { font-size: 22px; margin: 4px 0; }
        .coin-change { font-size: 15px; }
        .trend-analysis { font-size: 11px; padding: 8px; margin-top: 6px; }
        h1 { font-size: 22px !important; }
        h2 { font-size: 18px !important; }
        h3 { font-size: 16px !important; }
        div[data-testid="stVerticalBlock"] { gap: 0.5rem !important; }
    }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. 交易所初始化
# =====================================================================
@st.cache_resource
def get_exchange():
    return ccxt.okx() # 底層雷達掃描與數據維持使用 OKX

exchange = get_exchange()

# =====================================================================
# 3. 網址查詢參數記憶機制 (防止手機重新整理後設定洗掉)
# =====================================================================
query_params = st.query_parameters

saved_view = query_params.get("view", "📊 自選戰研與 AI 建議")
view_index = 1 if saved_view == "🚨 突發爆量提醒" else 0

saved_refresh = query_params.get("refresh", "5")
try: default_refresh = int(saved_refresh)
except: default_refresh = 5

saved_volume = query_params.get("volume", "0.5")
try: default_volume = float(saved_volume)
except: default_volume = 0.5

saved_favs = query_params.get_all("favs")
if not saved_favs:
    default_favs = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
else:
    default_favs = [f"{f}/USDT" if not f.endswith("/USDT") else f for f in saved_favs]

# =====================================================================
# 4. 側邊欄控制台 (設定與網址自動即時同步)
# =====================================================================
st.sidebar.header("⚙️ 獵手核心控制台")

page_view = st.sidebar.radio(
    "🧭 請選擇主畫面顯示面板",
    ["📊 自選戰研與 AI 建議", "🚨 突發爆量提醒"],
    index=view_index
)

st.sidebar.markdown("---")

api_key = None
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("🔑 已自動載入密鑰")
else:
    user_key = st.sidebar.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")
    if user_key: api_key = user_key

@st.cache_data(ttl=3600)
def get_all_usdt_symbols():
    try:
        markets = exchange.load_markets()
        return sorted([s for s in markets.keys() if s.endswith('/USDT') and ':' not in s])
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]

all_available_cryptos = get_all_usdt_symbols()

valid_defaults = [s for s in default_favs if s in all_available_cryptos]
fav_cryptos = st.sidebar.multiselect(
    "🎯 設定你的自選監控區",
    options=all_available_cryptos,
    default=valid_defaults if valid_defaults else [all_available_cryptos[0]]
)

refresh_interval = st.sidebar.slider("數據脈搏刷新頻率 (秒)", min_value=3, max_value=15, value=default_refresh)
alert_volume = st.sidebar.slider("🔊 雷達警報音量", min_value=0.0, max_value=1.0, value=default_volume, step=0.1)

# 即時把最新設定覆寫回 URL 網址列
st.query_parameters.update({
    "view": page_view,
    "refresh": str(refresh_interval),
    "volume": str(alert_volume),
    "favs": [s.replace("/USDT", "") for s in fav_cryptos]
})

# 自動刷新組件
st_autorefresh(interval=refresh_interval * 1000, key="datarefresh")

# =====================================================================
# 5. 量化與爆量動能演算法
# =====================================================================
def get_strategy_signal(current, high, low):
    if not high or not low: return "⚪ 數據不足 (暫無訊號)", "#888888"
    mid = (high + low) / 2
    if current > mid * 1.015: return "🟢 多頭強勢 (突破中軌區間)", "#00FF66"
    elif current < mid * 0.985: return "🔴 空頭弱勢 (跌破中軌區間)", "#FF3366"
    return "⚪ 區間盤整 (處於波動中軌)", "#888888"

# 🎯 突發爆量動能文字解讀
def get_anomaly_market_context(change_pct):
    if change_pct >= 10.
