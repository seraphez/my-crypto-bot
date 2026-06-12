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
    page_title="CryptoHunter | 跨平台完全體",
    layout="wide"
)

# 持久化記憶體
if "cached_ai_analysis" not in st.session_state:
    st.session_state.cached_ai_analysis = {}
if "previous_anomalies" not in st.session_state:
    st.session_state.previous_anomalies = set()
if "trigger_beep" not in st.session_state:
    st.session_state.trigger_beep = False

# ⚡ 核心：注入頂級 RWD 自適應 RWD 樣式，消滅所有閃爍暗化，優化手機方格
st.markdown("""
    <style>
    div[data-testid="stForm"] { background-color: transparent !important; }
    .stApp div[data-testid="stVerticalBlock"] > div { opacity: 1 !important; }
    .stApp { background-color: #0E1117; }
    h1, h2, h3, h4 { color: #00FFCC !important; font-family: 'Courier New', monospace; }
    
    /* ---------------- 預設：電腦端大方格排版 ---------------- */
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
    .trend-badge { padding: 8px 12px; border-radius: 6px; font-weight: bold; font-size: 14px; text-align: center; margin-top: 10px; }

    /* ---------------- 手機行動端自適應覆蓋 (螢幕寬度小於 768px) ---------------- */
    @media (max-width: 768px) {
        .square-card {
            padding: 15px;
            min-height: 160px;
            margin-bottom: 12px;
            border-radius: 10px;
        }
        .coin-title { font-size: 18px; }
        .coin-price { font-size: 22px; margin: 4px 0; }
        .coin-change { font-size: 15px; }
        .trend-badge { padding: 6px 10px; font-size: 12px; margin-top: 6px; }
        h1 { font-size: 22px !important; }
        h2 { font-size: 18px !important; }
        h3 { font-size: 16px !important; }
        /* 壓縮手機端的元件上下極致間距，防止一頁裝不下 */
        div[data-testid="stVerticalBlock"] { gap: 0.5rem !important; }
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
# 3. 側邊欄控制台 (手機版會收納在左上角 > 裡面，完美不佔空間)
# =====================================================================
st.sidebar.header("⚙️ 獵手核心控制台")

page_view = st.sidebar.radio(
    "🧭 請選擇主畫面顯示面板",
    ["📊 自選戰研與 AI 建議", "🚨 突發爆量提醒"],
    index=0
)

st.sidebar.markdown("---")

# 🔒 自動讀取 Secrets API 密鑰
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

fav_cryptos = st.sidebar.multiselect(
    "🎯 設定你的自選監控區",
    options=all_available_cryptos,
    default=[s for s in ["BTC/USDT", "ETH/USDT", "SOL/USDT"] if s in all_available_cryptos]
)

refresh_interval = st.sidebar.slider("數據脈搏刷新頻率 (秒)", min_value=3, max_value=15, value=5)
alert_volume = st.sidebar.slider("🔊 雷達警報音量", min_value=0.0, max_value=1.0, value=0.5, step=0.1)

# =====================================================================
# 4. 量化訊號與 Gemini 原始請求引擎
# =====================================================================
def get_strategy_signal(current, high, low):
    if not high or not low: return "⚪ 建議觀望 (數據不足)", "#888888"
    mid = (high + low) / 2
    if current > mid * 1.015: return "🟢 推薦開多 (突破多頭強勢區)", "#00FF66"
    elif current < mid * 0.985: return "🔴 推薦開空 (跌破空頭弱勢區)", "#FF3366"
    return "⚪ 建議觀望 (區間震盪盤整)", "#888888"

def ask_gemini_market_analysis(coin, price, change, signal, vol_24h):
    if not api_key: return "⚠️ 請先配置 Gemini API Key"
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    prompt = f"""
    你現在是精通加密貨幣『突發爆量/主力大單資金』的頂級短線量化操盤專家與黑客交易員。
    正在對目前自選幣進行【即時盤面量化結構調研】：
    - 標的幣種：{coin}/USDT | 當前現價：{price} | 24h漲跌幅：{change}% | 24h總成交額：{vol_24h} | 系統目前量化訊號：{signal}
    請用繁體中文給出極度精簡、一針見血且極具實戰攻擊性的短評報告：
    1. 拆解該幣目前盤面背後最真實的「主力心理狀態」（例如：主力正在洗盤吸籌、惡意拉高出貨、動能強勢突破，還是散戶恐慌踩踏）。
    2. 給出【下一個階段最具體的操作開盤方針與潛在埋伏點】，並附帶精準的止損/防守風險提示。
    """
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        data = response.json()
        if 'error' in data: return f"❌ 調研失敗: {data['error'].get('message', '頻率超限')}"
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e: return f"⚠️ 網路傳輸異常 ({e})"

# =====================================================================
# 5. 數據掃描中心
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

# 🎛️ 手機/電腦通用網頁提示音引擎
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
# 6. 主畫面自適應排版 (電腦端自動切成 [6,6]，手機端自動垂直降維)
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
                
                if "觀望" not in coin['signal_text'] and coin['symbol'] not in st.session_state.cached_ai_analysis:
                    with st.spinner(f"正在調研 {coin['symbol']}..."):
                        ai_res = ask_gemini_market_analysis(coin['symbol'], coin['price'], coin['change'], coin['signal_text'], coin['volume_str'])
                        st.session_state.cached_ai_analysis[coin['symbol']] = ai_res
                
                report_output = st.session_state.cached_ai_analysis.get(coin['symbol'], "⚪ 該標的目前正處於安全震盪區間內，量化訊號建議觀望，暫無下單指引。")
                if "🟢" in coin['signal_text']: st.success(report_output)
                elif "🔴" in coin['signal_text']: st.error(report_output)
                else: st.info(report_output)
                st.markdown("---")
        else:
            st.info("請在側邊欄勾選監控幣種！")

    with col_right:
        st.subheader("📊 行情卡片看板 (右區：行情監控)")
        st.markdown("---")
        if fav_data_list:
            fav_cols = st.columns(2)
            for idx, coin in enumerate(fav_data_list):
                with fav_cols[idx % 2]:
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

# ---------------------------------------------------------------------
# 模式 B：🚨 突發爆量提醒 (大方塊徹底不見，完美分流為下單方格與觀察清單)
# ---------------------------------------------------------------------
elif page_view == "🚨 突發爆量提醒":
    
    volume_anomalies = sorted(volume_anomalies, key=lambda x: x['volume_usdt'], reverse=True)
    half_len = (len(volume_anomalies) + 1) // 2
    
    with col_left:
        st.subheader("🚨 突發爆量 (左區：方格下單備選)")
        st.markdown("---")
        
        if volume_anomalies:
            left_cols = st.columns(2)
            for idx, coin in enumerate(volume_anomalies[:half_len]): 
                with left_cols[idx % 2]:
                    c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                    c_sign = "+" if coin['change'] >= 0 else ""
                    st.markdown(f"""
                        <div class="square-card">
                            <div>
                                <div class="coin-title">🔥 {coin['symbol']}/USDT</div>
                                <div class="coin-price">${coin['price']:,}</div>
                                <div class="coin-change" style="color: {c_color};">{c_sign}{coin['change']:.2f}%</div>
                            </div>
                            <div class="trend-badge" style="background-color: #00FFCC22; color: #00FFCC; border: 1px solid #00FFCC;">
                                成交額: {coin['volume_str']}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
        else:
            st.success("🔍 全網目前大盤平穩。")

    with col_right:
        st.subheader("🚨 突發爆量 (右區：重點觀察名單)")
        st.markdown("---")
        
        if volume_anomalies and len(volume_anomalies) > half_len:
            for coin in volume_anomalies[half_len:12]:
                c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                c_sign = "+" if coin['change'] >= 0 else ""
                st.markdown(f"**👀 觀察: {coin['symbol']}** | <span style='color:{c_color}; font-weight:bold;'>{c_sign}{coin['change']:.2f}%</span>", unsafe_allow_html=True)
                st.write(f"現價: `${coin['price']:,}` | 總量: `{coin['volume_str']}`")
                st.markdown("---")

# =====================================================================
# 7. 原生無阻斷計時刷新器 (消滅任何手機端、網頁端的暗化閃爍)
# =====================================================================
st_autorefresh(interval=refresh_interval * 1000, key="crypto_hunter_heartbeat")
