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

# 🧠 全面綁定記憶體鎖，防止自動刷新時重置設定或反覆扣除 AI 額度
if "refresh_val" not in st.session_state:
    st.session_state.refresh_val = 5
if "user_favs" not in st.session_state:
    st.session_state.user_favs = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
if "cached_portfolio_analysis" not in st.session_state:
    st.session_state.cached_portfolio_analysis = "💡 等待 AI 進行多幣連通調研..."
if "last_ai_update" not in st.session_state:
    st.session_state.last_ai_update = 0.0

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
# 3. 側邊欄控制台 (設定與狀態完全鎖定)
# =====================================================================
st.sidebar.header("⚙️ 獵手核心控制台")

page_view = st.sidebar.radio(
    "🧭 請選擇主畫面顯示面板",
    ["📊 自選戰研與 AI 建議", "🚨 突發爆量提醒"],
    index=0 if st.session_state.get("last_page_view") == "📊 自選戰研與 AI 建議" else (1 if st.session_state.get("last_page_view") == "🚨 突發爆量提醒" else 0)
)
st.session_state.last_page_view = page_view

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

# 確保預設值合法
valid_defaults = [s for s in st.session_state.user_favs if s in all_available_cryptos]

# 🎯 利用 key 屬性直接持久化自選順序，使用者調整才會觸發 session_state 變更
chosen_favs = st.sidebar.multiselect(
    "🎯 自選監控區 (按勾選先後順序進行自訂排序)",
    options=all_available_cryptos,
    default=valid_defaults if valid_defaults else [all_available_cryptos[0]]
)

if chosen_favs != st.session_state.user_favs:
    st.session_state.user_favs = chosen_favs
    st.session_state.cached_portfolio_analysis = "💡 自選變更，等待下一次 AI 聯通調研計時..."
    st.session_state.last_ai_update = 0.0

# 🎯 刷新頻率同樣綁定 key，徹底解決滑桿自動跳針回 5 秒的 Bug
st.sidebar.slider("數據脈搏刷新頻率 (秒)", min_value=3, max_value=15, key="refresh_val")

# 根據持久化記憶體中的時間計時刷新
st_autorefresh(interval=st.session_state.refresh_val * 1000, key="datarefresh")

# =====================================================================
# 4. 雷達精簡大概方向演算法 (只有在出現下單機會時特別備註)
# =====================================================================
def get_rough_direction(change_pct):
    if change_pct >= 10.0: return "⚠️ ［主力瘋狂強拉］ 短線嚴重超買，留意高位歸零針", "bull"
    elif 5.0 <= change_pct < 10.0: return "🟢 ［多頭強勢突破］ 具備短線右側下單機會，防守鎖定爆量K低點", "bull"
    elif change_pct <= -10.0: return "⚠️ ［全網恐慌砸盤］ 鏈式爆倉觸發，右側出現止跌量前嚴禁下單抄底", "bear"
    elif -10.0 < change_pct <= -5.0: return "🔴 ［空頭大單壓制］ 順勢做空動能充足，反彈阻力位即下單機會", "bear"
    return "⚪ ［常態籌碼沉澱］ 無明顯下單機會，維持窄幅洗盤", "neutral"

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
    1. 【資金流向拆解】：這幾個自選幣之間是否存在聯動關係？資金目前正從哪個幣流出、並集中流入哪個幣？
    2. 【下單機會精確提醒】：如果有明確的多空失衡、主力急迫吸籌、或資金瘋狂灌入的具體下單機會，請在開頭用【🔥 突發下單機會提醒】噴出具體策略！如果沒有，請直接提示觀望，保持專業。
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

# A. 【自選幣排序】精準按照使用者在多選欄點擊的順序迭代
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

# B. 【全網突發爆量隔離區】
for symbol, ticker in all_tickers.items():
    if not symbol.endswith('/USDT') or ':' in symbol: continue
    current_price = ticker['last']
    change_pct = ticker['percentage'] if ticker['percentage'] is not None else 0.0
    vol_base = ticker['baseVolume'] if ticker['baseVolume'] else 0
    vol_usdt = ticker['quoteVolume'] if ticker['quoteVolume'] else (vol_base * current_price)
    coin_clean = symbol.replace('/USDT', '')
    
    if vol_usdt >= 10000000 and (change_pct > 5 or change_pct < -5):
        current_anomaly_symbols.add(coin_clean)
        volume_anomalies.append({
            "symbol": coin_clean, "price": current_price, "change": change_pct, 
            "volume_str": f"{vol_usdt / 1000000:.1f}M USDT", "volume_usdt": vol_usdt
        })

# =====================================================================
# 6. 主畫面雙欄自適應佈局 (版面乾淨解耦，各回各家)
# =====================================================================
st.title("🏹 CryptoHunter 智能雷達")
st.markdown("---")

# ---------------------------------------------------------------------
# 模式 A：📊 自選戰研與 AI 建議 (左自選、右邊純淨 AI 調研與下單提醒)
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
        else:
            st.info("💡 請先在左側控制台勾選你想排列監控的自選幣。")

    with col_right:
        st.subheader("🧠 Gemini 自選組合多幣聯動與下單機會調研")
        st.markdown("---")
        
        if fav_data_list:
            time_now = time.time()
            time_diff = time_now - st.session_state.last_ai_update
            
            # 提供手動點擊刷新的機制，並且當超過 300 秒(5分鐘)才會在頁面重整時自動請求
            force_refresh_ai = st.button("⚡ 手動刷新 AI 戰研報告", use_container_width=True)
            
            if force_refresh_ai or "💡 Waiting" in st.session_state.cached_portfolio_analysis or (time_diff > 300.0):
                with st.spinner("正在進行跨市場自選幣資金連通性與下單機會調研..."):
                    res = ask_gemini_portfolio_analysis(fav_data_list)
                    if "❌ 調研失敗" not in res:
                        st.session_state.cached_portfolio_analysis = res
                        st.session_state.last_ai_update = time_now
                    else:
                        st.error(res)
            
            # 如果 AI 分析中帶有下單機會提示，自動用醒目的特別區塊高亮呈現
            if "下單機會" in st.session_state.cached_portfolio_analysis or "🔥" in st.session_state.cached_portfolio_analysis:
                st.warning(st.session_state.cached_portfolio_analysis)
            else:
                st.info(st.session_state.cached_portfolio_analysis)
            
            # 精確的冷卻狀態提示，保護你的免費 API 額度
            seconds_left = int(300 - (time_now - st.session_state.last_ai_update))
            if seconds_left > 0:
                st.caption(f"⏱ 智能快取安全護盾生效中。距離下一次自動調研還有 `{seconds_left}秒`，你也可以點擊上方按鈕隨時手動強制更新。")
        else:
            st.info("暫無自選幣數據可供 AI 進行連通分析。")

# ---------------------------------------------------------------------
# 模式 B：🚨 突發爆量提醒 (全網爆量路人幣的專屬停機坪，附帶大概方向提醒)
# ---------------------------------------------------------------------
else:
    st.subheader("🚨 全網突發爆量監控面板 (成交額 > 10M 且 波動 > 5%)")
    if volume_anomalies:
        # 按成交量從大到小排序
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
