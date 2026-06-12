import streamlit as st
import ccxt
import pandas as pd
from datetime import datetime
import requests
import time
from streamlit_autorefresh import st_autorefresh

# =====================================================================
# 1. 網頁頂級配置與黑客風 CSS 注入
# =====================================================================
st.set_page_config(
    page_title="CryptoHunter | 量化聯動研究艙",
    layout="wide"
)

# 🧠 初始化持久化記憶體（核心：防止刷新時設定與 AI 快取洗掉）
if "user_favs" not in st.session_state:
    st.session_state.user_favs = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
if "cached_portfolio_analysis" not in st.session_state:
    st.session_state.cached_portfolio_analysis = "💡 等待 AI 進行多幣連通調研..."
if "last_ai_update" not in st.session_state:
    st.session_state.last_ai_update = 0.0
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
        min-height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .coin-title { font-size: 24px; font-weight: bold; color: #FFF; font-family: 'Courier New', monospace; }
    .coin-price { font-size: 30px; font-weight: bold; color: #00FF66; margin: 8px 0; }
    .coin-change { font-size: 18px; font-weight: bold; }
    
    /* 突發雷達精簡方向提示樣式 */
    .radar-direction {
        background-color: #1F2937;
        padding: 10px;
        border-radius: 8px;
        font-size: 13px;
        color: #FF3366;
        margin-top: 8px;
        border-left: 4px solid #FF3366;
        font-weight: bold;
    }
    .radar-direction.bull {
        color: #00FF66;
        border-left: 4px solid #00FF66;
    }

    @media (max-width: 768px) {
        .square-card { padding: 15px; min-height: 180px; margin-bottom: 12px; border-radius: 10px; }
        .coin-title { font-size: 18px; }
        .coin-price { font-size: 22px; margin: 4px 0; }
        .coin-change { font-size: 15px; }
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
# 3. 【修復】網址查詢參數記憶機制 (改為與 session_state 綁定防洗掉)
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

# 載入 URL 的自選，若無則使用 session_state 的
if "favs" in query_dict:
    if hasattr(query_dict, "get_all"): raw_favs = query_dict.get_all("favs")
    else: raw_favs = query_dict["favs"]
    if isinstance(raw_favs, str): raw_favs = [raw_favs]
    url_favs = [f"{f}/USDT" if not f.endswith("/USDT") else f for f in raw_favs]
    if url_favs:
        st.session_state.user_favs = url_favs

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

# 【修復】過濾掉不合法的標的，並保持 session 裡的自訂排序
valid_defaults = [s for s in st.session_state.user_favs if s in all_available_cryptos]

# 核心：使用 multiselect 捕捉自選順序，當使用者改選時直接更新記憶體
chosen_favs = st.sidebar.multiselect(
    "🎯 自選監控區 (按勾選先後順序進行自訂排序)",
    options=all_available_cryptos,
    default=valid_defaults if valid_defaults else [all_available_cryptos[0]]
)

# 當使用者手動調整自選，才去改寫 session_state 的順序並清空 AI 分析快取
if chosen_favs != st.session_state.user_favs:
    st.session_state.user_favs = chosen_favs
    st.session_state.cached_portfolio_analysis = "💡 自選變更，等待下一次 AI 聯通調研計時..."
    st.session_state.last_ai_update = 0.0  # 強制下次重刷時可以點擊或自動觸發

refresh_interval = st.sidebar.slider("數據脈搏刷新頻率 (秒)", min_value=3, max_value=15, value=default_refresh)
alert_volume = st.sidebar.slider("🔊 雷達警報音量", min_value=0.0, max_value=1.0, value=default_volume, step=0.1)

# 安全將設定寫回 URL，確保頁面不跑掉
try:
    new_params = {
        "view": page_view,
        "refresh": str(refresh_interval),
        "volume": str(alert_volume),
        "favs": [s.replace("/USDT", "") for s in st.session_state.user_favs]
    }
    if hasattr(st, "query_parameters"): st.query_parameters.update(new_params)
    else: st.experimental_set_query_params(**new_params)
except:
    pass

st_autorefresh(interval=refresh_interval * 1000, key="datarefresh")

# =====================================================================
# 5. 雷達精簡大概方向演算法
# =====================================================================
def get_rough_direction(change_pct):
    if change_pct >= 10.0: return "⚠️ ［主力瘋狂強拉］ 短線嚴重超買，留意高位暴跌風險", "bull"
    elif 5.0 <= change_pct < 10.0: return "🟢 ［多頭強勢突破］ 成交量放大，上攻動能充足", "bull"
    elif change_pct <= -10.0: return "⚠️ ［全網恐慌砸盤］ 多頭踩踏砸盤，切勿盲目左側接刀", "bear"
    elif -10.0 < change_pct <= -5.0: return "🔴 ［空頭大單壓制］ 資金淨流出，下行趨勢明顯", "bear"
    return "⚪ ［常態籌碼沉澱］ 無明顯方向，維持區間洗盤", "neutral"

def ask_gemini_portfolio_analysis(fav_data_list):
    if not api_key: return "⚠️ 請先配置 Gemini API Key"
    if not fav_data_list: return "暫無自選標的"
    
    portfolio_summary = "\n".join([
        f"- {c['symbol']}: 現價 {c['price']}, 24h漲跌 {c['change']}%, 成交量 {c['volume_str']}" 
        for c in fav_data_list
    ])
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    prompt = f"""
    你現在是精通加密貨幣主力大單資金流向與多幣聯動矩陣的頂級操盤專家。
    目前交易員自選了以下幣種，並按照他高度重視的優先順序排列：
    {portfolio_summary}
    
    請將這些自選幣視為一個【完整的連通器戰略組合】，用繁體中文給出極度精簡、直擊痛點的連通調研：
    1. 【資金流向拆解】：這幾個自選幣之間是否存在聯動關係？資金目前正從哪個幣流出、並集中流入哪個幣？（例如：資金從大盤BTC溢出至板塊輪動，還是全線失血）。
    2. 【主力心理學】：看穿主力對這幾個自選幣當下的整體做局意圖。
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

# A. 【嚴格自訂排序】強制完全依照使用者在控制台排列的順序輸出
for symbol in st.session_state.user_favs:
    if symbol in all_tickers:
        ticker = all_tickers[symbol]
        current_price = ticker['last']
        change_pct = ticker['percentage'] if ticker['percentage'] is not None else 0.0
        vol_base = ticker['baseVolume'] if ticker['baseVolume'] else 0
        vol_usdt = ticker['quoteVolume'] if ticker['quoteVolume'] else (vol_base * current_price)
        coin_clean = symbol.replace('/USDT', '')
        
        fav_data_list.append({
            "symbol": coin_clean, "price": current_price, "change": change_pct, 
            "volume_str": f"{vol_usdt / 1000000:.2f}M USDT", "volume_usdt": vol_usdt
        })

# B. 全網異常大單掃描
for symbol, ticker in all_tickers.items():
    if not symbol.endswith('/USDT') or ':' in symbol: continue
    current_price = ticker['last']
    change_pct = ticker['percentage'] if ticker['percentage'] is not None else 0.0
    vol_base = ticker['baseVolume'] if ticker['baseVolume'] else 0
    vol_usdt = ticker['quoteVolume'] if ticker['quoteVolume'] else (vol_base * current_price)
    coin_clean = symbol.replace('/USDT', '')
    
    # 爆量標準：24h成交量大於 10M 且 波動大於 5%
    if vol_usdt >= 10000000 and (change_pct > 5 or change_pct < -5):
        current_anomaly_symbols.add(coin_clean)
        volume_anomalies.append({
            "symbol": coin_clean, "price": current_price, "change": change_pct, 
            "volume_str": f"{vol_usdt / 1000000:.1f}M USDT", "volume_usdt": vol_usdt
        })

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
# 7. 主畫面雙欄自適應佈局 (徹底隔離版面，拒絕重疊與死鎖)
# =====================================================================
st.title("🏹 CryptoHunter 智能雷達")
st.markdown("---")

# ---------------------------------------------------------------------
# 模式 A：📊 自選戰研與 AI 建議 (左自選狀態、右爆量極簡方向)
# ---------------------------------------------------------------------
if page_view == "📊 自選戰研與 AI 建議":
    col_left, col_right = st.columns([6, 6])
    
    with col_left:
        st.subheader("📊 自選標的核心監控艙")
        st.write(f"⏱ 數據更新：`{datetime.now().strftime('%H:%M:%S')}`")
        st.markdown("---")
        
        if fav_data_list:
            for coin in fav_data_list:
                c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                c_sign = "+" if coin['change'] >= 0 else ""
                st.markdown(f"### 🪙 {coin['symbol']} 實時狀態")
                st.markdown(f"現價: `${coin['price']:,}` | 24h漲跌: <span style='color:{c_color}; font-weight:bold;'>{c_sign}{coin['change']:.2f}%</span> | 24h成交額: `{coin['volume_str']}`", unsafe_allow_html=True)
                st.markdown("---")
            
            # 【修復】限制 AI 請求頻率（每 60 秒才允許發送一次），徹底解決額度爆炸問題
            st.subheader("🧠 Gemini 自選組合多幣聯動調研")
            time_now = time.time()
            
            # 只有當快取為空，或是距離上一次成功請求大於 60 秒時，才會調用 API
            if "💡 Waiting" in st.session_state.cached_portfolio_analysis or (time_now - st.session_state.last_ai_update > 60.0):
                with st.spinner("正在進行跨市場自選幣資金連通性調研..."):
                    res = ask_gemini_portfolio_analysis(fav_data_list)
                    if "❌ 調研失敗" not in res:
                        st.session_state.cached_portfolio_analysis = res
                        st.session_state.last_ai_update = time_now
                    else:
                        # 噴錯時顯示警告，但保留上一次的成功快取，不讓畫面崩潰
                        st.error(res)
            
            # 輸出快取的 AI 分析報告
            st.info(st.session_state.cached_portfolio_analysis)
            
            # 顯示下一次可重新調研的倒數計時提示
            seconds_left = int(60 - (time_now - st.session_state.last_ai_update))
            if seconds_left > 0:
                st.caption(f"⏱ 為了防止 AI 額度爆載，智能快取護盾生效中。 `{seconds_left}秒` 後自動解鎖下次調研。")
        else:
            st.info("💡 請先在左側控制台勾選你想排列監控的自選幣。")

    with col_right:
        # 【修復】右側欄嚴格與「全網突發爆量即時快訊」綁定，資料不交叉感染
        st.subheader("🚨 全網突發爆量即時快訊")
        st.markdown("---")
        if volume_anomalies:
            volume_anomalies = sorted(volume_anomalies, key=lambda x: x['volume_usdt'], reverse=True)
            for anomaly in volume_anomalies:
                dir_text, dir_type = get_rough_direction(anomaly['change'])
                class_type = "bull" if dir_type == "bull" else ("neutral" if dir_type == "neutral" else "")
                
                st.markdown(f"**⚡ 爆量警告：{anomaly['symbol']}/USDT**")
                st.write(f"現價: {anomaly['price']} | 漲跌幅: {anomaly['change']:.2f}% | 成交量: {anomaly['volume_str']}")
                st.markdown(f"<div class='radar-direction {class_type}'>{dir_text}</div>", unsafe_allow_html=True)
                st.markdown("---")
        else:
            st.info("目前市場暫無符合突發動能（成交額 > 10M 且 波動 > 5%）的異常標的。")

# ---------------------------------------------------------------------
# 模式 B：🚨 突發爆量提醒 (全螢幕獨立 3 欄大方格卡片面板，絕不與模式 A 疊加)
# ---------------------------------------------------------------------
else:
    st.subheader("🚨 全網突發爆量大方格監控面板 (成交額 > 10M 且 波動 > 5%)")
    if volume_anomalies:
        volume_anomalies = sorted(volume_anomalies, key=lambda x: x['volume_usdt'], reverse=True)
        
        cols = st.columns(3)
        for idx, anomaly in enumerate(volume_anomalies):
            with cols[idx % 3]:
                c_color = "#00FF66" if anomaly['change'] >= 0 else "#FF3366"
                c_sign = "+" if anomaly['change'] >= 0 else ""
                dir_text, dir_type = get_rough_direction(anomaly['change'])
                class_type = "bull" if dir_type == "bull" else ("neutral" if dir_type == "neutral" else "")
                
                card_html = f"""
                <div class="square-card">
                    <div>
                        <div class="coin-title">🔥 {anomaly['symbol']}/USDT</div>
                        <div class="coin-price">${anomaly['price']:,}</div>
                        <div class="coin-change" style="color: {c_color};">{c_sign}{anomaly['change']:.2f}%</div>
                        <div style="color: #8B949E; font-size: 13px; margin-top: 4px;">24h成交額: {anomaly['volume_str']}</div>
                        <div class="radar-direction {class_type}">{dir_text}</div>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
    else:
        st.info("⚡ 雷達靜悄悄... 目前全網暫無觸發『爆量且劇烈波動』的異常標的。")
