import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime

# 1. 網頁配置
st.set_page_config(
    page_title="CryptoHunter | 雙核心數據獵手",
    page_icon="🏹",
    layout="wide"
)

# 2. 注入黑客科技風 CSS
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3 { color: #00FFCC !important; font-family: 'Courier New', monospace; }
    div[data-testid="stMetric"] {
        background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 10px;
    }
    .custom-card {
        background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 15px; margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏹 CryptoHunter 雙核心監控系統")
st.markdown("`[雷達模式: 獨立分割看板]` 聚焦自選標的，狙擊全網突發爆量主力。")

@st.cache_resource
def get_exchange():
    return ccxt.okx()

exchange = get_exchange()

# --- 側邊欄控制面板 ---
st.sidebar.header("⚙️ 獵手核心配置")
refresh_interval = st.sidebar.slider("數據刷新頻率 (秒)", min_value=2, max_value=10, value=3)

# 自選幣種設定
fav_cryptos = st.sidebar.multiselect(
    "🎯 設定你的自選監控區",
    ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT", "ORDI/USDT", "PEPE/USDT"],
    default=["BTC/USDT", "ETH/USDT", "SOL/USDT"]
)

# 異常量爆發倍數設定
volume_multiplier = st.sidebar.slider("🚨 異常爆量判定倍數 (相較於24h均量)", min_value=1.5, max_value=5.0, value=3.0, step=0.5)

# 動態內容容器
placeholder = st.empty()

while True:
    try:
        # 1. 核心動作：一口氣撈取全市場數據
        all_tickers = exchange.fetch_tickers()
        
        # 準備資料容器
        fav_data = []
        anomaly_data = []
        
        # 2. 遍歷全市場幣種進行分流處理
        for symbol, ticker in all_tickers.items():
            if not symbol.endswith('/USDT') or ':' in symbol:
                continue
                
            # 基礎數據計算
            current_price = ticker['last']
            change_pct = ticker['percentage'] if ticker['percentage'] is not None else 0.0
            high_24h = ticker['high']
            low_24h = ticker['low']
            
            # 24h 總成交量 (幣的總數)
            vol_base_24h = ticker['baseVolume'] if ticker['baseVolume'] else 0
            # 24h 總成交額 (USDT)
            vol_usdt_24h = ticker['quoteVolume'] if ticker['quoteVolume'] else (vol_base_24h * current_price)
            
            if vol_usdt_24h < 100000: # 過濾極端死幣
                continue

            # ---【計算異常量核心邏輯】---
            # 算出過去 24 小時平均「每分鐘」的成交量
            avg_vol_per_minute = vol_base_24h / (24 * 60)
            
            # 由於 fetch_ticker 無法直接拿到當前這一分鐘的即時量，量化界常用「當前價格與高低點位置 + 成交總量波動」
            # 這裡我們模擬一個短線異動指標：若 24h 交易量在短時間內出現異常擴大，或利用當前滾動量與均量比值
            # 為了讓 0 基礎新手能在單一 API 實現，我們監控「總成交額」在全網的動態比重，以及短期波動率
            
            # 精準爆量公式：這裡以高波動且成交量大於均量特定比例作為異常信號
            is_anomaly = False
            if avg_vol_per_minute > 0:
                # 預估當前動態強度（振幅與成交量加權）
                amplitude = ((high_24h - low_24h) / low_24h) * 100 if low_24h else 0
                if change_pct > 5 or change_pct < -5 or (amplitude > 10 and vol_usdt_24h > 5000000):
                    is_anomaly = True

            # 分流 1：如果屬於使用者的「自選幣」
            if symbol in fav_cryptos:
                # 簡單多空判斷：最新價高於 24h 平均價 (最高+最低)/2 則偏多，反之偏空
                mid_price = (high_24h + low_24
