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
    if change_pct >= 10.0:
        return "⚠️ 市場動能狂熱：主力極速強拉，現價短線嚴重超買，留意回踩均線風險。"
    elif 5.0 <= change_pct < 10.0:
        return "🟢 多頭強勢突破：成交量能同步放大，短線多頭趨勢結構完整。"
    elif change_pct <= -10.0:
        return "⚠️ 恐慌砸盤警告：市場出現不計成本的多頭踩踏，留意大單止跌訊號。"
    elif -10.0 < change_pct <= -5.0:
        return "🔴 空頭動能噴發：空方大單強力壓制，短線下行慣性強烈。"
    return "⚪ 波動正常：動能洗盤盤整中。"

def ask_gemini_market_analysis(coin, price, change, signal, vol_24h):
    if not api_key: return "⚠️ 請先配置 Gemini API Key"
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    prompt = f"""
    你現在是精通加密貨幣『突發爆量/主力大單資金』的頂級短線量化操盤專家與黑客交易員。
    正在對目前自選幣進行【即時盤面量化結構調研】：
    - 標的幣種：{coin}/USDT | 當前現價：{price} | 24h漲跌幅：{change}% | 24h總成交額：{vol_24h} | 系統目前量化訊號：{signal}
    請用繁體中文給出極度精簡、一針見血且極具實戰攻擊性的短評報告：
    1. 拆解該幣目前盘面背後最真實的「主力心理狀態」（例如：主力正在洗盤吸籌、惡意拉高出貨、動能強勢突破，還是散戶恐慌踩踏）。
    2. 給出【下一個階段最精確的盤面動向觀察點與風險防守提示】。
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
        st.subheader("📊 自選幣核心數據監控")
        st.write(f"⏱ 更新：`{datetime.now().strftime('%H:%M:%S')}`")
        st.markdown("---")
        
        if fav_data_list:
            for coin in fav_data_list:
                c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                c_sign = "+" if coin['change'] >= 0 else ""
                st.markdown(f"### 🪙 {coin['symbol']} 調研狀態")
                st.markdown(f"現價: `${coin['price']:,}` | 24h漲跌: <span style='color:{c_color}; font-weight:bold;'>{c_sign}{coin['change']:.2f}%</span>", unsafe_allow_html=True)
                st.write(f"量化結構訊號: {coin['signal_text']}")
                
                # 自動觸發 AI 數據分析
                if "盤整" not in coin['signal_text'] and coin['symbol'] not in st.session_state.cached_ai_analysis:
                    with st.spinner(f"正在調研 {coin['symbol']} 主力鏈上動向..."):
                        analysis = ask_gemini_market_analysis(coin['symbol'], coin['price'], coin['change'], coin['signal_text'], coin['volume_str'])
                        st.session_state.cached_ai_analysis[coin['symbol']] = analysis
                
                if coin['symbol'] in st.session_state.cached_ai_analysis:
                    st.info(st.session_state.cached_ai_analysis[coin['symbol']])
                st.markdown("---")

    with col_right:
        st.subheader("🚨 突發爆量即時快訊")
        st.markdown("---")
        if volume_anomalies:
            for anomaly in volume_anomalies:
                st.markdown(f"**⚡ 動能警告：{anomaly['symbol']}**")
                st.write(f"現價: {anomaly['price']} | 漲跌幅: {anomaly['change']}% | 成交量: {anomaly['volume_str']}")
                st.markdown("---")
        else:
            st.info("目前市場暫無符合突發動能（成交額 > 10M 且 波動 > 5%）的標的。")

# ---------------------------------------------------------------------
# 模式 B：🚨 突發爆量提醒
# ---------------------------------------------------------------------
else:
    st.subheader("🚨 全網突發爆量監控面板")
    if volume_anomalies:
        # 依成交量大小排序
        volume_anomalies = sorted(volume_anomalies, key=lambda x: x['volume_usdt'], reverse=True)
        
        # 使用響應式方格卡片布局
        cols = st.columns(3)
        for idx, anomaly in enumerate(volume_anomalies):
            with cols[idx % 3]:
                c_color = "#00FF66" if anomaly['change'] >= 0 else "#FF3366"
                c_sign = "+" if anomaly['change'] >= 0 else ""
                context_text = get_anomaly_market_context(anomaly['change'])
                
                card_html = f"""
                <div class="square-card">
                    <div>
                        <div class="coin-title">🔥 {anomaly['symbol']}/USDT</div>
                        <div class="coin-price">${anomaly['price']:,}</div>
                        <div class="coin-change" style="color: {c_color};">{c_sign}{anomaly['change']:.2f}%</div>
                        <div style="color: #8B949E; font-size: 13px; margin-top: 4px;">24h成交額: {anomaly['volume_str']}</div>
                        <div class="trend-analysis">{context_text}</div>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
    else:
        st.info("⚡ 雷達靜悄悄... 目前全網暫無觸發『爆量且劇烈波動』的異常標的。")
