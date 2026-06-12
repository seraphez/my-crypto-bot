import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime
import google.generativeai as genai

# =====================================================================
# 1. 網頁頂級配置
# =====================================================================
st.set_page_config(
    page_title="CryptoHunter | 全幣種 AI 獵手",
    page_icon="🏹",
    layout="wide"
)

# =====================================================================
# 2. 注入黑客科技風 CSS 樣式
# =====================================================================
st.markdown("""
    <style>
    /* 全域暗色背景 */
    .stApp { background-color: #0E1117; }
    h1, h2, h3 { color: #00FFCC !important; font-family: 'Courier New', monospace; }
    
    /* 巨大正方形卡片樣式 */
    .square-card {
        background-color: #161B22;
        border: 2px solid #30363D;
        border-radius: 15px;
        padding: 25px;
        margin-bottom: 15px;
        min-height: 250px; /* 強制高度，形成大方塊 */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 8px 16px rgba(0,0,0,0.5);
    }
    .coin-title { font-size: 26px; font-weight: bold; color: #FFF; font-family: 'Courier New', monospace; }
    .coin-price { font-size: 30px; font-weight: bold; color: #00FF66; margin: 8px 0; }
    .coin-change { font-size: 18px; font-weight: bold; }
    
    /* 策略標籤樣式 */
    .trend-badge { 
        padding: 8px 12px; border-radius: 6px; font-weight: bold; font-size: 15px; text-align: center; margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏹 CryptoHunter AI 全幣種智能系統")
st.markdown("`[雷達模式: 全市場解鎖]` 現在你可以自選追蹤交易所上的任何幣種，右側維持異常暴動偵測。")

# =====================================================================
# 3. 交易所與 AI 初始化（安全防禦機制）
# =====================================================================
@st.cache_resource
def get_exchange():
    return ccxt.okx() # 使用 OKX 避開 451 錯誤

exchange = get_exchange()

# --- 【安全密鑰讀取機制】 ---
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    GEMINI_API_KEY = None

# 側邊欄控制台
st.sidebar.header("⚙️ 獵手核心配置")

# 防呆密鑰輸入框
if not GEMINI_API_KEY:
    st.sidebar.markdown("### 🔑 AI 密鑰配置")
    user_key = st.sidebar.text_input("請輸入 Gemini API Key", type="password", help="請至 Google AI Studio 申請免費 Key")
    if user_key:
        GEMINI_API_KEY = user_key

# 串接 AI 診斷引擎
has_ai = False
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        has_ai = True
    except:
        has_ai = False

# =====================================================================
# 4. 【升級核心】動態獲取全市場所有幣種名單
# =====================================================================
@st.cache_data(ttl=3600) # 每小時自動更新一次幣種清單即可，不用每次刷新都抓
def get_all_usdt_symbols():
    try:
        markets = exchange.load_markets()
        # 篩選出所有以 /USDT 結尾，且不是期權或交割合約的現貨/永續標的
        symbols = [symbol for symbol in markets.keys() if symbol.endswith('/USDT') and ':' not in symbol]
        return sorted(symbols) # 排序，方便使用者找幣
    except:
        # 萬一交易所連線失敗的備用清單
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT"]

all_available_cryptos = get_all_usdt_symbols()

# 側邊欄其他參數設定
refresh_interval = st.sidebar.slider("數據脈搏刷新 (秒)", min_value=3, max_value=15, value=5)
enable_ai = st.sidebar.toggle("🤖 啟動 AI 即時開盤推薦", value=True)

# 💡 這裡把原本死板的清單，換成剛剛動態抓到的 all_available_cryptos！
fav_cryptos = st.sidebar.multiselect(
    "🎯 設定你的自選監控區 (可輸入關鍵字搜尋)",
    options=all_available_cryptos,
    default=[s for s in ["BTC/USDT", "ETH/USDT", "SOL/USDT"] if s in all_available_cryptos]
)

# =====================================================================
# 5. 量化與 AI 分析核心邏輯
# =====================================================================
def get_strategy_signal(current, high, low):
    """根據當前價格在24h高低點的位置，計算多空開盤推薦"""
    if not high or not low:
        return "⚪ 建議觀望 (數據不足)", "#888888"
    mid = (high + low) / 2
    if current > mid * 1.015:
        return "🟢 推薦開多 (突破多頭強勢區)", "#00FF66"
    elif current < mid * 0.985:
        return "🔴 推薦開空 (跌破空頭弱勢區)", "#FF3366"
    return "⚪ 建議觀望 (區間震盪盤整)", "#888888"

def ask_gemini_analysis(coin, price, change, signal):
    """向 Gemini 索取開盤具體文字報告"""
    if not has_ai:
        return "⚠️ 請在左側邊欄輸入有效的 Gemini API Key 以啟用 AI 分析。"
    try:
        model = genai.GenerativeModel(model_name='gemini-1.5-flash')
        prompt = f"""
        你是一位加密貨幣量化操盤專家。
        標的：{coin}/USDT | 現價：{price} | 24h漲跌：{change}% | 系統量化訊號：{signal}
        請用繁體中文給出極精簡的 2 句短評：
        1. 當前市場局面型態。
        2. 具體的操作/開盤（多/空/觀望）建議與風險提示。
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 引擎連線異動中，正在嘗試重新橋接通道... ({e})"

# =====================================================================
# 6. 主程式數據循環監控區
# =====================================================================
placeholder = st.empty()

while True:
    try:
        # 一次性打包請求全市場數據
        all_tickers = exchange.fetch_tickers()
        
        fav_data_list = []
        anomaly_data_list = []
        
        # 遍歷全市場進行篩選與分流
        for symbol, ticker in all_tickers.items():
            if not symbol.endswith('/USDT') or ':' in symbol:
                continue
                
            current_price = ticker['last']
            change_pct = ticker['percentage'] if ticker['percentage'] is not None else 0.0
            high_24h = ticker['high']
            low_24h = ticker['low']
            vol_base_24h = ticker['baseVolume'] if ticker['baseVolume'] else 0
            vol_usdt_24h = ticker['quoteVolume'] if ticker['quoteVolume'] else (vol_base_24h * current_price)
            
            if vol_usdt_24h < 150000: # 過濾流動性極差的死幣
                continue
                
            # 計算是否屬於異常異動暴動幣
            is_anomaly = False
            if change_pct > 6 or change_pct < -6: # 24h 劇烈波動
                is_anomaly = True
            
            # 分流處理
            if symbol in fav_cryptos:
                signal_text, signal_color = get_strategy_signal(current_price, high_24h, low_24h)
                fav_data_list.append({
                    "symbol": symbol.replace('/USDT', ''),
                    "price": current_price,
                    "change": change_pct,
                    "signal_text": signal_text,
                    "signal_color": signal_color
                })
            elif is_anomaly:
                anomaly_data_
