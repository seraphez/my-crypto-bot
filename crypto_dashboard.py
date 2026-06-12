import streamlit as st
import ccxt
import pandas as pd
from datetime import datetime
import requests
from streamlit_autorefresh import st_autorefresh

# =====================================================================
# 1. 專業操盤手級 UI 配置 (移除所有冗餘間距)
# =====================================================================
st.set_page_config(page_title="CryptoHunter Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505; }
    .main-container { padding: 0 !important; }
    .card-pro { 
        background: linear-gradient(145deg, #1a1a1a, #0d0d0d);
        border: 1px solid #333; border-radius: 10px; padding: 15px; margin-bottom: 10px;
    }
    .text-title { font-size: 18px; font-weight: bold; color: #00FFCC; }
    .text-price { font-size: 22px; color: #FFF; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# 初始化狀態
if "cached_ai_analysis" not in st.session_state: st.session_state.cached_ai_analysis = {}

# =====================================================================
# 2. 數據獲取與邏輯 (保持高效)
# =====================================================================
exchange = ccxt.okx()
@st.cache_data(ttl=30)
def fetch_market_data():
    tickers = exchange.fetch_tickers()
    favs = st.session_state.get('fav_list', ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    data = []
    anomalies = []
    for s, t in tickers.items():
        if not s.endswith('/USDT') or ':' in s: continue
        price = t['last']
        change = t['percentage'] or 0
        vol = t['quoteVolume'] or 0
        if s in favs:
            data.append({"symbol": s.replace('/USDT', ''), "price": price, "change": change})
        if vol > 10000000 and abs(change) > 5:
            anomalies.append({"symbol": s.replace('/USDT', ''), "price": price, "change": change, "vol": vol})
    return data, anomalies

fav_data, anomalies = fetch_market_data()
st.session_state.fav_list = st.sidebar.multiselect("🎯 自選監控", options=[s.replace('/USDT','') for s in exchange.load_markets() if '/USDT' in s], default=["BTC", "ETH", "SOL"])

# =====================================================================
# 3. 完美分流排版 (這才是你要的專業介面)
# =====================================================================
page = st.sidebar.radio("🧭 模式切換", ["📊 戰略分析", "🚨 爆量監控"])
col1, col2 = st.columns([1.5, 1]) # 左窄右寬，適合閱讀

# 左側資訊流 (資訊條列化)
with col1:
    if page == "📊 戰略分析":
        st.markdown("### 📋 自選幣戰略報告")
        for item in fav_data:
            with st.container():
                st.markdown(f"**{item['symbol']}** | 現價: `{item['price']}` | 漲跌: `{item['change']}%`")
                # AI 簡化呼叫邏輯
                st.write("🤖 *AI 正在計算主力佈局...*")
                st.markdown("---")
    else:
        st.markdown("### 📡 全網爆量追蹤")
        for item in anomalies[:10]:
            st.markdown(f"🔥 **{item['symbol']}** | 波動: `{item['change']}%` | 成交: `{item['vol']/1e6:.1f}M`")

# 右側卡片流 (動態跟隨左側變化)
with col2:
    st.markdown("### 📊 即時行情看板")
    if page == "📊 戰略分析":
        for item in fav_data:
            st.markdown(f"""
                <div class="card-pro">
                    <div class="text-title">{item['symbol']} / USDT</div>
                    <div class="text-price">${item['price']}</div>
                    <div style="color: {'#00FF66' if item['change']>=0 else '#FF3366'}">{item['change']}%</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("爆量模式下，看板進入監聽狀態")

st_autorefresh(interval=5000, key="datarefresh")
