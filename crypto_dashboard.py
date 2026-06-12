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
    page_title="CryptoHunter | 純自選戰研艙",
    layout="wide"
)

# 🧠 全面綁定記憶體鎖，防止自動刷新時重置設定或反覆扣除 AI 額度
if "refresh_val" not in st.session_state:
    st.session_state.refresh_val = 5
if "user_favs" not in st.session_state:
    st.session_state.user_favs = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
if "cached_portfolio_analysis" not in st.session_state:
    st.session_state.cached_portfolio_analysis = "💡 等待 AI 進行自選組合連通調研..."
if "last_ai_update" not in st.session_state:
    st.session_state.last_ai_update = 0.0

st.markdown("""
    <style>
    div[data-testid="stForm"] { background-color: transparent !important; }
    .stApp div[data-testid="stVerticalBlock"] > div { opacity: 1 !important; }
    .stApp { background-color: #0E1117; }
    h1, h2, h3, h4 { color: #00FFCC !important; font-family: 'Courier New', monospace; }
    
    @media (max-width: 768px) {
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
# 3. 側邊欄控制台 (設定永久鎖定，絕不跳針)
# =====================================================================
st.sidebar.header("⚙️ 獵手核心控制台")

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
valid_defaults = [s for s in st.session_state.user_favs if s in all_available_cryptos]

# 🎯 多選框與記憶體對齊，完美保留你的自訂排序順序
chosen_favs = st.sidebar.multiselect(
    "🎯 自選監控區 (按勾選先後順序進行自訂排序)",
    options=all_available_cryptos,
    default=valid_defaults if valid_defaults else [all_available_cryptos[0]]
)

if chosen_favs != st.session_state.user_favs:
    st.session_state.user_favs = chosen_favs
    st.session_state.cached_portfolio_analysis = "💡 自選變更，等待下一次 AI 聯通調研計時..."
    st.session_state.last_ai_update = 0.0

# 🎯 刷新頻率綁定 key，徹底解決滑桿自動跳回 5 秒的 Bug
st.sidebar.slider("數據脈搏刷新頻率 (秒)", min_value=3, max_value=15, key="refresh_val")

# 自動刷新器安全啟動
st_autorefresh(interval=st.session_state.refresh_val * 1000, key="datarefresh")

# =====================================================================
# 4. Gemini 自選組合多幣連通與下單機會調研函數
# =====================================================================
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
# 5. 數據掃描中心 (100% 純自選化)
# =====================================================================
try:
    all_tickers = exchange.fetch_tickers()
except:
    st.rerun()

fav_data_list = []

# 精準按照使用者在多選欄點擊的順序建立數據，不夾帶任何外部雜訊
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

# =====================================================================
# 6. 主畫面雙欄自適應佈局 (自選極簡完全體)
# =====================================================================
st.title("🏹 CryptoHunter 智能雷達 (純自選戰研艙)")
st.markdown("---")

col_left, col_right = st.columns([6, 6])

with col_left:
    st.subheader("📊 自選標的核心監控區")
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
        
        # 手動重研按鈕，冷卻防禦設為 300 秒保護免費層額度
        force_refresh_ai = st.button("⚡ 手動刷新 AI 戰研報告", use_container_width=True)
        
        if force_refresh_ai or "💡 等待" in st.session_state.cached_portfolio_analysis or (time_diff > 300.0):
            with st.spinner("正在進行自選幣組合跨市場資金連通性與下單機會調研..."):
                res = ask_gemini_portfolio_analysis(fav_data_list)
                if "❌ 調研失敗" not in res:
                    st.session_state.cached_portfolio_analysis = res
                    st.session_state.last_ai_update = time_now
                else:
                    st.error(res)
        
        # 偵測下單機會高亮
        if "下單機會" in st.session_state.cached_portfolio_analysis or "🔥" in st.session_state.cached_portfolio_analysis:
            st.warning(st.session_state.cached_portfolio_analysis)
        else:
            st.info(st.session_state.cached_portfolio_analysis)
        
        seconds_left = int(300 - (time_now - st.session_state.last_ai_update))
        if seconds_left > 0:
            st.caption(f"⏱ 智能快取安全護盾生效中。 `{seconds_left}秒` 後自動解鎖下次 AI 調研，或點擊上方按鈕手動更新。")
    else:
        st.info("暫無自選幣數據可供 AI 進行連通分析。")
