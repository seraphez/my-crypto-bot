import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime
import requests

# =====================================================================
# 1. 網頁頂級配置與原創科技風 CSS 注入 (右側正方形，取消暗化)
# =====================================================================
st.set_page_config(
    page_title="CryptoHunter | 雙核完全體",
    layout="wide"
)

# 緩存鎖：儲存純文字報告，防止網頁 10 秒刷新時重新呼叫 API 導致爆掉
if "cached_ai_reports" not in st.session_state:
    st.session_state.cached_ai_reports = {}

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3, h4 { color: #00FFCC !important; font-family: 'Courier New', monospace; }
    
    /* 右側主畫面：巨大正方形卡片滿血回歸 */
    .square-card {
        background-color: #161B22;
        border: 2px solid #30363D;
        border-radius: 15px;
        padding: 25px;
        margin-bottom: 20px;
        min-height: 220px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .coin-title { font-size: 26px; font-weight: bold; color: #FFF; font-family: 'Courier New', monospace; }
    .coin-price { font-size: 32px; font-weight: bold; color: #00FF66; margin: 10px 0; }
    .coin-change { font-size: 20px; font-weight: bold; }
    
    /* 策略標籤樣式 */
    .trend-badge { 
        padding: 8px 12px; border-radius: 6px; font-weight: bold; font-size: 15px; text-align: center; margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. 交易所初始化
# =====================================================================
@st.cache_resource
def get_exchange():
    return ccxt.okx()

exchange = get_exchange()

# =====================================================================
# 3. 量化訊號與 AI 建議演算邏輯 (使用 gemini-2.5-flash 正式通道)
# =====================================================================
def get_strategy_signal(current, high, low):
    if not high or not low:
        return "⚪ 建議觀望 (數據不足)", "#888888"
    mid = (high + low) / 2
    if current > mid * 1.015:
        return "🟢 推薦開多 (突破多頭強勢區)", "#00FF66"
    elif current < mid * 0.985:
        return "🔴 推薦開空 (跌破空頭弱勢區)", "#FF3366"
    return "⚪ 建議觀望 (區間震盪盤整)", "#888888"

def ask_gemini_market_analysis(api_key, coin, price, change, signal):
    if not api_key:
        return "⚠️ 請先在側邊欄最下方配置有效的 Gemini API Key 才能看報告喔！"
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    prompt = f"""
    你現在是加密貨幣量化操盤專家與短線大單資金研究員。
    當前自選監控標的行情：{coin}/USDT | 現價：{price} | 24h漲跌幅：{change}% | 系統量化訊號：{signal}
    請用繁體中文給出極精簡且具實戰價值的 2 句短評：
    1. 分析當前市場局面背後的主力心理型態（是洗盤吸籌、拉高出貨、動能突破還是散戶踩踏）。
    2. 給出【最具體的操作方法與多空開盤建議】與精準的防守/止損風險提示。
    """
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        data = response.json()
        if 'error' in data:
            return f"❌ Google 拒絕原因: {data['error'].get('message', '頻率超限或無效金鑰')}"
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"⚠️ 網絡傳輸異常 ({e})"

# =====================================================================
# 4. 側邊欄控制台 (設定區 + 分頁切換功能)
# =====================================================================
st.sidebar.header("⚙️ 獵手核心控制台")

# 🧭 【全新設計】：左側分頁切換窗口
sidebar_tab = st.sidebar.radio(
    "🧭 請選擇左側功能面板",
    ["🚨 突發爆量提醒", "🤖 AI 獵手開盤建議"],
    index=0
)

st.sidebar.markdown("---")

# 🔑 API Key 讀取機制
api_key = None
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("🔑 已從後台 Secrets 自動載入密鑰")
else:
    user_key = st.sidebar.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")
    if user_key: api_key = user_key

# 自選監控區設定
@st.cache_data(ttl=3600)
def get_all_usdt_symbols():
    try:
        markets = exchange.load_markets()
        return sorted([s for s in markets.keys() if s.endswith('/USDT') and ':' not in s])
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]

all_available_cryptos = get_all_usdt_symbols()
fav_cryptos = st.sidebar.multiselect("🎯 設定你的自選監控區", options=all_available_cryptos, default=[s for s in ["BTC/USDT", "ETH/USDT", "SOL/USDT"] if s in all_available_cryptos])
refresh_interval = st.sidebar.slider("數據脈搏刷新頻率 (秒)", min_value=3, max_value=15, value=5)

# =====================================================================
# 5. 主畫面經典佈局 (左 4 寬度放切換視窗，右 8 寬度放你最愛的正方形卡片)
# =====================================================================
st.title("🏹 CryptoHunter 雙核雷達智能儀表板")
st.markdown("---")

col_left_panel, col_right_main = st.columns([4, 8])

# 獲取即時行情
try:
    all_tickers = exchange.fetch_tickers()
except Exception as e:
    st.error(f"📡 交易所連線中斷，自動重試中... ({e})")
    time.sleep(2)
    st.rerun()

fav_data_list = []
volume_anomalies = []

# 全市場掃描與數據分流
for symbol, ticker in all_tickers.items():
    if not symbol.endswith('/USDT') or ':' in symbol: continue
    current_price = ticker['last']
    change_pct = ticker['percentage'] if ticker['percentage'] is not None else 0.0
    high_24h = ticker['high']
    low_24h = ticker['low']
    vol_base = ticker['baseVolume'] if ticker['baseVolume'] else 0
    vol_usdt = ticker['quoteVolume'] if ticker['quoteVolume'] else (vol_base * current_price)
    coin_clean = symbol.replace('/USDT', '')
    
    if symbol in fav_cryptos:
        sig_txt, sig_col = get_strategy_signal(current_price, high_24h, low_24h)
        fav_data_list.append({"symbol": coin_clean, "price": current_price, "change": change_pct, "signal_text": sig_txt, "signal_color": sig_col})
        
    if vol_usdt >= 10000000 and (change_pct > 5 or change_pct < -5):
        volume_anomalies.append({"symbol": coin_clean, "price": current_price, "change": change_pct, "volume_str": f"{vol_usdt / 1000000:.1f}M USDT", "volume_usdt": vol_usdt})

# ---------------------------------------------------------------------
# 【左側窗口】：根據側邊欄的單選按鈕切換「提醒窗口」或「AI 開盤建議」
# ---------------------------------------------------------------------
with col_left_panel:
    if sidebar_tab == "🚨 突發爆量提醒":
        st.subheader("🚨 全網【突發爆量異常】提醒")
        st.caption("🔥 24h雷達自動鎖定：成交額 > 10M 且波動 > 5% 的黑馬標的")
        st.markdown("---")
        
        volume_anomalies = sorted(volume_anomalies, key=lambda x: x['volume_usdt'], reverse=True)
        if volume_anomalies:
            for coin in volume_anomalies[:10]:
                c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                c_sign = "+" if coin['change'] >= 0 else ""
                st.markdown(f"**🔥 爆量: {coin['symbol']}** | <span style='color:{c_color}; font-weight:bold;'>{c_sign}{coin['change']:.2f}%</span>", unsafe_allow_html=True)
                st.write(f"現價: `${coin['price']:,}` | 24h總量: `{coin['volume_str']}`")
                st.markdown("---")
        else:
            st.success("🔍 市場目前波動穩定，未偵測到爆量標的。")

    elif sidebar_tab == "🤖 AI 獵手開盤建議":
        st.subheader("🤖 AI 獵手即時開盤量化報告")
        st.caption("⚡ 針對你的自選監控標的，秒級解構主力心理與實戰策略")
        st.markdown("---")
        
        if fav_data_list:
            for coin in fav_data_list:
                st.markdown(f"#### 🪙 {coin['symbol']} 戰略報告")
                
                # 🧠 【防爆機制】：只有當緩存裡沒有，或者該幣產生了強烈波動（推薦開多/開空）時，才發送一次 API 請求
                if coin['symbol'] not in st.session_state.cached_ai_reports and "觀望" not in coin['signal_text']:
                    if api_key:
                        with st.spinner(f"AI 正在精算 {coin['symbol']} 開盤點位..."):
                            report = ask_gemini_market_analysis(api_key, coin['symbol'], coin['price'], coin['change'], coin['signal_text'])
                            st.session_state.cached_ai_reports[coin['symbol']] = report
                    else:
                        st.session_state.cached_ai_reports[coin['symbol']] = "⚠️ 請在控制台配置 API Key 以解鎖操盤報告。"
                
                # 讀取持久化報告（絕不重複發送 HTTP Requests，100% 安全）
                report_content = st.session_state.cached_ai_reports.get(coin['symbol'], "🟢 該標的目前正處於安全震盪區間內，量化訊號建議觀望，AI 保持待命防禦。")
                st.info(report_content)
                st.markdown("---")
        else:
            st.info("請在左側邊欄設定自選幣！")

# ---------------------------------------------------------------------
# 【右側主畫面】：你最愛的經典正方形卡片監控區
# ---------------------------------------------------------------------
with col_right_main:
    st.subheader("🎯 自選幣即時看板")
    st.write(f"⏱ 數據更新時間：`{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
    st.markdown("---")
    
    if fav_data_list:
        # 兩欄式並列巨大正方形卡片，高亮對比，清晰直觀
        fav_cols = st.columns(2)
        for idx, coin in enumerate(fav_data_list):
            target_col = fav_cols[idx % 2]
            with target_col:
                c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                c_sign = "+" if coin['change'] >= 0 else ""
                
                st.markdown(f"""
                    <div class="square-card">
                        <div>
                            <div class="coin-title">🪙 {coin['symbol']}/USDT</div>
                            <div class="coin-price">${coin['price']:,}</div>
                            <div class="coin-change" style="color: {c_color};">{c_sign}{coin['change']:.2f}%</div>
                        </div>
                        <div class="trend-badge" style="background-color: {coin['signal_color']}22; color: {coin['signal_color']}; border: 1px solid {coin['signal_color']};">
                            {coin['signal_text']}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("請在左側邊欄多勾選幾個自選幣，右側看板會自動排版生成大方塊！")

# =====================================================================
# 6. 非阻塞式高效自動刷新
# =====================================================================
time.sleep(refresh_interval)
st.rerun()
