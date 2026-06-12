import streamlit as st
import ccxt
import pandas as pd
from datetime import datetime
import requests
from streamlit_autorefresh import st_autorefresh

# =====================================================================
# 1. 網頁頂級配置與黑客風 CSS 注入
# =====================================================================
st.set_page_config(
    page_title="CryptoHunter | 量化策略研究艙",
    layout="wide"
)

# 持久化記憶體，防止自動刷新時重複發送 HTTP 請求扣除 AI 額度
if "cached_ai_analysis" not in st.session_state:
    st.session_state.cached_ai_analysis = {}
if "previous_anomalies" not in st.session_state:
    st.session_state.previous_anomalies = set()
if "trigger_beep" not in st.session_state:
    st.session_state.trigger_beep = False

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
        min-height: 310px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .coin-title { font-size: 24px; font-weight: bold; color: #FFF; font-family: 'Courier New', monospace; }
    .coin-price { font-size: 30px; font-weight: bold; color: #00FF66; margin: 8px 0; }
    .coin-change { font-size: 18px; font-weight: bold; }
    
    /* 量化分析區塊樣式 - 藍青色條 */
    .trend-analysis {
        background-color: #1F2937;
        padding: 12px;
        border-radius: 8px;
        font-size: 13px;
        color: #E5E7EB;
        margin-top: 10px;
        border-left: 4px solid #00FFCC;
        line-height: 1.5;
    }
    
    /* 計劃下單方針專用樣式 - 翠綠色條 */
    .trade-plan {
        background-color: #1A2E26;
        padding: 12px;
        border-radius: 8px;
        font-size: 13px;
        color: #A3F7BF;
        margin-top: 10px;
        border-left: 4px solid #00FF66;
        line-height: 1.5;
    }

    @media (max-width: 768px) {
        .square-card { padding: 15px; min-height: 260px; margin-bottom: 12px; border-radius: 10px; }
        .coin-title { font-size: 18px; }
        .coin-price { font-size: 22px; margin: 4px 0; }
        .coin-change { font-size: 15px; }
        .trend-analysis, .trade-plan { font-size: 11px; padding: 8px; margin-top: 6px; }
        h1 { font-size: 22px !important; }
        h2 { font-size: 18px !important; }
        h3 { font-size: 16px !important; }
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
# 3. 【新舊版環境完美相容】網址查詢參數記憶機制
# =====================================================================
try:
    if hasattr(st, "query_parameters") and not callable(st.query_parameters):
        query_dict = st.query_parameters
    elif hasattr(st, "query_parameters") and callable(st.query_parameters):
        query_dict = st.query_parameters()
    else:
        query_dict = st.experimental_get_query_params()
except:
    query_dict = {}

saved_view = query_dict.get("view", "📊 自選戰研與 AI 建議")
if isinstance(saved_view, list): saved_view = saved_view[0]
view_index = 1 if saved_view == "🚨 突發爆量提醒" else 0

saved_refresh = query_dict.get("refresh", "5")
if isinstance(saved_refresh, list): saved_refresh = saved_refresh[0]
try: default_refresh = int(saved_refresh)
except: default_refresh = 5

saved_volume = query_dict.get("volume", "0.5")
if isinstance(saved_volume, list): saved_volume = saved_volume[0]
try: default_volume = float(saved_volume)
except: default_volume = 0.5

if "favs" in query_dict:
    if hasattr(query_dict, "get_all"): raw_favs = query_dict.get_all("favs")
    else: raw_favs = query_dict["favs"]
    if isinstance(raw_favs, str): raw_favs = [raw_favs]
    default_favs = [f"{f}/USDT" if not f.endswith("/USDT") else f for f in raw_favs]
else:
    default_favs = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

# =====================================================================
# 4. 側邊欄控制台
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
    "🎯 設定你的自選監控區 (依勾選順序排定優先權)",
    options=all_available_cryptos,
    default=valid_defaults if valid_defaults else [all_available_cryptos[0]]
)

refresh_interval = st.sidebar.slider("數據脈搏刷新頻率 (秒)", min_value=3, max_value=15, value=default_refresh)
alert_volume = st.sidebar.slider("🔊 雷達警報音量", min_value=0.0, max_value=1.0, value=default_volume, step=0.1)

try:
    new_params = {
        "view": page_view,
        "refresh": str(refresh_interval),
        "volume": str(alert_volume),
        "favs": [s.replace("/USDT", "") for s in fav_cryptos]
    }
    if hasattr(st, "query_parameters"): st.query_parameters.update(new_params)
    else: st.experimental_set_query_params(**new_params)
except:
    pass

st_autorefresh(interval=refresh_interval * 1000, key="datarefresh")

# =====================================================================
# 5. 【多維解耦】量化矩陣與高辨識度下單方針演算法
# =====================================================================
def get_strategy_signal(current, high, low):
    if not high or not low: return "⚪ 區間盤整", "#888888"
    mid = (high + low) / 2
    if current > mid * 1.015: return "🟢 多頭強勢", "#00FF66"
    elif current < mid * 0.985: return "🔴 空頭弱勢", "#FF3366"
    return "⚪ 區間盤整", "#888888"

# 🎯 雙指標交叉比對引擎：大幅提高各個幣種之間的辨識度，拒絕複製品
def get_matrix_analysis_and_plan(change_pct, signal_text):
    # 狀態 1：極端暴漲 (強拉型)
    if change_pct >= 15.0:
        analysis = "📊 <b>量化結構：</b>突發性垂直噴發！多頭量能出現極端乖離，主力進行不計成本的暴力拉抬，市場投機情緒已達頂峰。"
        plan = "🎯 <b>計劃下單方針：</b>風控權重高於一切，此處極易遭遇『天地針』洗盤。禁止開多，計劃在 15 分鐘 K 線跌破 5MA 均線時輕倉建立右側防守性空單，止損精確設在高點。"
    
    # 狀態 2：多頭強勢突破
    elif "🟢 多頭強勢" in signal_text:
        if change_pct >= 5.0:
            analysis = "📊 <b>量化結構：</b>健康的帶量多頭突破。量價配合良好，價格已成功站穩 24h 箱體中軌上方，且底部成交量逐步墊高，主力護盤意願強烈。"
            plan = "🎯 <b>計劃下單方針：</b>策略採『順勢踩點進多』。可於現價分批試倉，理想二次埋伏點為回踩 5 分鐘線 30EMA 縮量不破之時；防守防線鎖定在今日早盤起漲點。"
        else:
            analysis = "📊 <b>量化結構：</b>低位微幅蓄勢。雖然 24h 漲幅不明顯，但價格結構已悄悄爬升至量價分佈密集區上方，屬於典型的潛在主力暗中吸籌結構。"
            plan = "🎯 <b>計劃下單方針：</b>適合左側潛伏。可在現價微幅左側建倉多單，防守點直接設在昨日最低點，用極小虧損空間博取後續的爆量主升浪。"

    # 狀態 3：空頭砸盤弱勢
    elif "🔴 空頭弱勢" in signal_text:
        if change_pct <= -5.0:
            analysis = "📊 <b>量化結構：</b>空方大單傾巢而出，多頭防線出現鏈式潰敗。盤面暫無任何主力的左側承接大單，市場呈現多頭踩踏的恐慌性失血。"
            plan = "🎯 <b>計劃下單方針：</b>嚴禁盲目抄底接刀！方針採『反彈遇阻順勢開空』。計劃在價格反彈至上方整數壓力位且 1 分鐘線出現長上影線時開空，防守設在壓力位上方 0.5%。"
        else:
            analysis = "📊 <b>量化結構：</b>陰跌磨損結構。多頭動能耗盡後引發的陰跌盤整，市場缺乏流動性支持，價格重心震盪下移。"
            plan = "🎯 <b>計劃下單方針：</b>維持觀望或反彈微空。不宜重倉，若持有現貨應適度減倉，防守防線鎖定在今日高點。"

    # 狀態 4：標準箱體盤整
    else:
        if abs(change_pct) < 3.0:
            analysis = "📊 <b>量化結構：</b>標準高頻窄幅震盪。多空資金在此處達成微妙平衡，成交量萎縮至均值以下，屬於標準的籌碼沉澱箱體。"
            plan = "🎯 <b>計劃下單方針：</b>無方向市場，不進行任何狙擊開盤，避免被高頻的上下歸零針磨損手續費。靜待 5 分鐘 K 線爆量突破箱體邊界後再行右側跟進。"
        else:
            analysis = f"📊 <b>量化結構：</b>寬幅震盪洗盤。24h 變動幅達 {change_pct}%，但未能形成單邊趨勢，主力正在通過上下洗盤清除高槓桿合約。"
            plan = "🎯 <b>計劃下單方針：</b>採高拋低吸高勝率策略。計劃在價格觸及 24h 最高價附近佈局空單，或在 24h 最低價附近測試多單，嚴格執行區間內的小止損防守。"

    return analysis, plan

def ask_gemini_market_analysis(coin, price, change, signal, vol_24h):
    if not api_key: return "⚠️ 請先配置 Gemini API Key"
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    prompt = f"""
    你現在是精通加密貨幣『突發爆量/主力大單資金』的頂級短線量化操盤專家與黑客交易員。
    正在對目前自選幣進行【即時盤面量化結構調研】：
    - 標的幣種：{coin}/USDT | 當前現價：{price} | 24h漲跌幅：{change}% | 24h總成交額：{vol_24h} | 系統目前量化訊號：{signal}
    請用繁體中文給出極度精簡、一針見血且極具實戰攻擊性的短評報告：
    1. 拆解該幣目前盘面背後最真實的「主力心理狀態」（洗盤吸籌、拉高出貨、動能突破、散戶踩踏）。
    2. 給出【下一個階段最具體的操作開盤方針、精確的潛在埋伏點，與止損/防守風險提示】。
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

# 為了實現【自選幣自由排序】，這裡改以使用者勾選的順序作為基準去抓取資料
fav_data_list = []
volume_anomalies = []
current_anomaly_symbols = set()

# A. 優先處理自選幣排序邏輯
for symbol in fav_cryptos:
    if symbol in all_tickers:
        ticker = all_tickers[symbol]
        current_price = ticker['last']
        change_pct = ticker['percentage'] if ticker['percentage'] is not None else 0.0
        high_24h = ticker['high']
        low_24h = ticker['low']
        vol_base = ticker['baseVolume'] if ticker['baseVolume'] else 0
        vol_usdt = ticker['quoteVolume'] if ticker['quoteVolume'] else (vol_base * current_price)
        coin_clean = symbol.replace('/USDT', '')
        
        sig_txt, sig_col = get_strategy_signal(current_price, high_24h, low_24h)
        fav_data_list.append({
            "symbol": coin_clean, "price": current_price, "change": change_pct, 
            "signal_text": sig_txt, "signal_color": sig_col, "volume_str": f"{vol_usdt / 1000000:.2f}M USDT",
            "volume_usdt": vol_usdt
        })

# B. 全市場全自動爆量幣掃描
for symbol, ticker in all_tickers.items():
    if not symbol.endswith('/USDT') or ':' in symbol: continue
    current_price = ticker['last']
    change_pct = ticker['percentage'] if ticker['percentage'] is not None else 0.0
    vol_base = ticker['baseVolume'] if ticker['baseVolume'] else 0
    vol_usdt = ticker['quoteVolume'] if ticker['quoteVolume'] else (vol_base * current_price)
    coin_clean = symbol.replace('/USDT', '')
    
    if vol_usdt >= 10000000 and (change_pct > 5 or change_pct < -5):
        current_anomaly_symbols.add(coin_clean)
        high_24h = ticker['high']
        low_24h = ticker['low']
        sig_txt, _ = get_strategy_signal(current_price, high_24h, low_24h)
        volume_anomalies.append({
            "symbol": coin_clean, "price": current_price, "change": change_pct, 
            "volume_str": f"{vol_usdt / 1000000:.1f}M USDT", "volume_usdt": vol_usdt,
            "signal_text": sig_txt
        })

# 🎛️ 雷達警報音效
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
# 7. 主畫面雙欄自適應佈局 (自選排序、解耦防重疊)
# =====================================================================
st.title("🏹 CryptoHunter 智能雷達")
st.markdown("---")

# ---------------------------------------------------------------------
# 模式 A：📊 自選戰研與 AI 建議 (精準辨識、完美自訂排序)
# ---------------------------------------------------------------------
if page_view == "📊 自選戰研與 AI 建議":
    col_left, col_right = st.columns([6, 6])
    
    with col_left:
        st.subheader("📊 自選監控核心 (已依自訂順序排列)")
        st.write(f"⏱ 數據脈搏更新：`{datetime.now().strftime('%H:%M:%S')}`")
        st.markdown("---")
        
        if fav_data_list:
            for coin in fav_data_list:
                c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                c_sign = "+" if coin['change'] >= 0 else ""
                st.markdown(f"### 🪙 {coin['symbol']} 實時狀態")
                st.markdown(f"當前現價: `${coin['price']:,}` | 24h漲跌: <span style='color:{c_color}; font-weight:bold;'>{c_sign}{coin['change']:.2f}%</span>", unsafe_allow_html=True)
                st.markdown(f"系統量化狀態: <span style='color:{coin['signal_color']}; font-weight:bold;'>{coin['signal_text']}</span>", unsafe_allow_html=True)
                
                # 自動觸發 Gemini 深度戰研報告
                if "盤整" not in coin['signal_text'] and coin['symbol'] not in st.session_state.cached_ai_analysis:
                    with st.spinner(f"正在深度解析 {coin['symbol']} 主力鏈上心理學..."):
                        analysis = ask_gemini_market_analysis(coin['symbol'], coin['price'], coin['change'], coin['signal_text'], coin['volume_str'])
                        st.session_state.cached_ai_analysis[coin['symbol']] = analysis
                
                if coin['symbol'] in st.session_state.cached_ai_analysis:
                    st.info(st.session_state.cached_ai_analysis[coin['symbol']])
                st.markdown("---")
        else:
            st.info("💡 控制台內空空如也，請先在左側多選欄中勾選自選監控標的。")

    with col_right:
        st.subheader("📈 自選專屬量化結構與計劃下單方針")
        st.markdown("---")
        if fav_data_list:
            for coin in fav_data_list:
                # 傳入「漲跌幅」與「量化狀態」雙重指標，完全移除了功能重疊與複製的問題
                matrix_analysis, trade_plan = get_matrix_analysis_and_plan(coin['change'], coin['signal_text'])
                st.markdown(f"### 🪙 {coin['symbol']} 矩陣戰術方針")
                st.write(f"24h 總成交量： `{coin['volume_str']}`")
                st.markdown(f"<div class='trend-analysis'>{matrix_analysis}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='trade-plan'>{trade_plan}</div>", unsafe_allow_html=True)
                st.markdown("---")

# ---------------------------------------------------------------------
# 模式 B：🚨 突發爆量提醒 (全市場大單黑馬卡片面板)
# ---------------------------------------------------------------------
else:
    st.subheader("🚨 全網突發爆量監控面板 (成交額 > 10M 且 波動 > 5%)")
    if volume_anomalies:
        # 依 24h 成交額大小降序排列
        volume_anomalies = sorted(volume_anomalies, key=lambda x: x['volume_usdt'], reverse=True)
        
        cols = st.columns(3)
        for idx, anomaly in enumerate(volume_anomalies):
            with cols[idx % 3]:
                c_color = "#00FF66" if anomaly['change'] >= 0 else "#FF3366"
                c_sign = "+" if anomaly['change'] >= 0 else ""
                
                # 爆量提醒面板同樣享有高辨識度的交叉比對矩陣
                matrix_analysis, trade_plan = get_matrix_analysis_and_plan(anomaly['change'], anomaly['signal_text'])
                
                card_html = f"""
                <div class="square-card">
                    <div>
                        <div class="coin-title">🔥 {anomaly['symbol']}/USDT</div>
                        <div class="coin-price">${anomaly['price']:,}</div>
                        <div class="coin-change" style="color: {c_color};">{c_sign}{anomaly['change']:.2f}%</div>
                        <div style="color: #8B949E; font-size: 13px; margin-top: 4px;">24h成交額: {anomaly['volume_str']}</div>
                        <div class="trend-analysis">{matrix_analysis}</div>
                        <div class="trade-plan">{trade_plan}</div>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
    else:
        st.info("⚡ 雷達靜悄悄... 目前全網暫無觸發大單異常流入或多頭恐慌踩踏的黑馬幣。")
