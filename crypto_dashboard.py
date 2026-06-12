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
    page_title="CryptoHunter | 幣安下單完全體",
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
    
    /* 你的巨大正方形卡片樣式 */
    .square-card {
        background-color: #161B22;
        border: 2px solid #30363D;
        border-radius: 15px;
        padding: 22px;
        margin-bottom: 15px;
        min-height: 290px; /* 加高以容納下單建議與下單按鈕 */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .coin-title { font-size: 24px; font-weight: bold; color: #FFF; font-family: 'Courier New', monospace; }
    .coin-price { font-size: 30px; font-weight: bold; color: #00FF66; margin: 8px 0; }
    .coin-change { font-size: 18px; font-weight: bold; }
    .trend-badge { padding: 8px 12px; border-radius: 6px; font-weight: bold; font-size: 14px; text-align: center; margin-top: 5px; }
    
    /* 下單建議文字樣式 */
    .trade-advice {
        background-color: #1F2937;
        padding: 10px;
        border-radius: 8px;
        font-size: 13px;
        color: #E5E7EB;
        margin-top: 10px;
        border-left: 4px solid #F3BA2F; /* 改為幣安經典黃色左邊條 */
        line-height: 1.4;
    }

    /* ⚡ 前往幣安下單按鈕樣式 */
    .btn-trade {
        display: block;
        text-align: center;
        background-color: #F3BA2F; /* 滿血還原幣安黃色按鈕 */
        color: #000 !important;
        padding: 10px;
        border-radius: 8px;
        text-decoration: none !important;
        font-weight: bold;
        margin-top: 12px;
        font-size: 14px;
        transition: background-color 0.2s ease;
    }
    .btn-trade:hover {
        background-color: #E2AD26;
    }

    @media (max-width: 768px) {
        .square-card { padding: 15px; min-height: 240px; margin-bottom: 12px; border-radius: 10px; }
        .coin-title { font-size: 18px; }
        .coin-price { font-size: 22px; margin: 4px 0; }
        .coin-change { font-size: 15px; }
        .trend-badge { padding: 6px 10px; font-size: 12px; margin-top: 4px; }
        .trade-advice { font-size: 11px; padding: 8px; margin-top: 6px; }
        .btn-trade { padding: 8px; font-size: 12px; margin-top: 8px; }
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

# 即時把最新設定覆寫回 URL 網址列，實現重開免重新調整
st.query_parameters.update({
    "view": page_view,
    "refresh": str(refresh_interval),
    "volume": str(alert_volume),
    "favs": [s.replace("/USDT", "") for s in fav_cryptos]
})

# =====================================================================
# 5. 量化與爆量下單建議演算法
# =====================================================================
def get_strategy_signal(current, high, low):
    if not high or not low: return "⚪ 建議觀望 (數據不足)", "#888888"
    mid = (high + low) / 2
    if current > mid * 1.015: return "🟢 推薦開多 (突破多頭強勢區)", "#00FF66"
    elif current < mid * 0.985: return "🔴 推薦開空 (跌破空頭弱勢區)", "#FF3366"
    return "⚪ 建議觀望 (區間震盪盤整)", "#888888"

# 🎯 全自動爆量方格下單狙擊指引
def get_anomaly_trade_advice(change_pct):
    if change_pct >= 10.0:
        return "⚠️ 主力瘋狂強拉！現價拉開極度超買，直接追多極易被埋，建議等待 5 分鐘 K 線回踩均線不破再行切入。"
    elif 5.0 <= change_pct < 10.0:
        return "🟢 多頭量能強勢突破！短線具備下單開多條件，防守點精準鎖定在前一根 1 分鐘爆量 K 線的低點。"
    elif change_pct <= -10.0:
        return "⚠️ 全網恐慌踩踏砸盤！左側接刀極度危險，下單抄底前必須盯緊 1 分鐘 K 線出現大單爆量止跌訊號。"
    elif -10.0 < change_pct <= -5.0:
        return "🔴 空頭大單強力砸盤！短線順勢開空動能充足，下單防守點建立在上方最近的整數關卡或壓力線。"
    return "⚪ 動能洗盤盤整中，暫不符合狙擊開盤標準。"

# ⚡ 【全新重構】：生成 Binance (幣安) 精準現貨交易對跳轉按鈕連結
def get_binance_trade_button_html(symbol):
    # 將代號轉換為幣安現貨網址格式，例如 SOL/USDT -> SOL_USDT
    formatted_symbol = symbol.replace("/", "_").upper()
    url = f"https://www.binance.com/zh-TC/trade/{formatted_symbol}?type=spot"
    return f'<a href="{url}" target="_blank" class="btn-trade">⚡ 前往幣安下單</a>'

def ask_gemini_market_analysis(coin, price, change, signal, vol_24h):
    if not api_key: return "⚠️ 請先配置 Gemini API Key"
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    prompt = f"""
    你現在是精通加密貨幣『突發爆量/主力大單資金』的頂級短線量化操盤專家與黑客交易員。
    正在對目前自選幣進行【即時盤面量化結構調研】：
    - 標的幣種：{coin}/USDT | 當前現價：{price} | 24h漲跌幅：{change}% | 24h總成交額：{vol_24h} | 系統目前量化訊號：{signal}
    請用繁體中文給出極度精簡、一針見血且極具實戰攻擊性的短評報告：
    1. 拆解該幣目前盘面背後最真實的「主力心理狀態」（例如：主力正在洗盤吸籌、惡意拉高出貨、動能強勢突破，還是散戶恐慌踩踏）。
    2. 給出【下一個階段最具體的操作開盤方針與潛在埋伏點】，並附帶精準的止損/防守風險提示。
    """
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        data = response.json()
        if 'error' in data: return f"❌ 調研失敗: {data['error'].get('message', '頻率超限')}"
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e: return f"⚠️ 網路傳輸異常 ({e})"

# =====================================================================
# 6. 數據掃描中心
# =====================================================================
try:
    all_tickers = exchange.fetch_tickers()
except:
    st.rerun()

fav_data_list = []
volume_anomalies = []
current_anomaly_symbols = set()

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
        fav_data_list.append({
            "symbol": coin_clean, "price": current_price, "change": change_pct, 
            "signal_text": sig_txt, "signal_color": sig_col, "volume_str": f"{vol_usdt / 1000000:.2f}M USDT"
        })
        
    if vol_usdt >= 10000000 and (change_pct > 5 or change_pct < -5):
        current_anomaly_symbols.add(coin_clean)
        volume_anomalies.append({"symbol": coin_clean, "price": current_price, "change": change_pct, "volume_str": f"{vol_usdt / 1000000:.1f}M USDT", "volume_usdt": vol_usdt})

# 🎛️ 提示音引擎
new_anomalies = current_anomaly_symbols - st.session_state.previous_anomalies
if new_anomalies and alert_volume > 0: st.session_state.trigger_beep = True
st.session_state.previous_anomalies = current_anomaly_symbols

if st.session_state.trigger_beep:
    st.session_state.trigger_beep = False
    st.markdown(f"""
        <audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2568/2568-84.wav" type="audio/wav"></audio>
        <script>document.querySelector('audio').volume = {alert_volume};</script>
    """, unsafe_allow_html=True)

# =====================================================================
# 7. 主畫面雙欄自適應佈局 (不鎖死、不重疊)
# =====================================================================
st.title("🏹 CryptoHunter 智能雷達")
st.markdown("---")

col_left, col_right = st.columns([6, 6])

# ---------------------------------------------------------------------
# 模式 A：📊 自選戰研與 AI 建議
# ---------------------------------------------------------------------
if page_view == "📊 自選戰研與 AI 建議":
    
    with col_left:
        st.subheader("📊 自選幣核心戰研建議 (左區：下單決策)")
        st.write(f"⏱ 更新：`{datetime.now().strftime('%H:%M:%S')}`")
        st.markdown("---")
        
        if fav_data_list:
            for coin in fav_data_list:
                c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                c_sign = "+" if coin['change'] >= 0 else ""
                st.markdown(f"### 🪙 {coin['symbol']} 戰研調研")
                st.markdown(f"現價: `${coin['price']:,}` | 24h漲跌: <span style='color:{c_color}; font-weight:bold;'>{c_sign}{coin['change']:.2f}%</span>", unsafe_allow_html=True)
                st.write(f"系統量化訊號: {coin['signal_text']}")
                
                if "觀望" not in coin['signal_text'] and coin['symbol'] not in st.session_state.cached_ai_analysis
