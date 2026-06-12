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
    page_title="CryptoHunter | 純自選戰研艙",
    layout="wide"
)

# 🧠 全面綁定記憶體鎖，防止自動刷新時重置設定或反覆扣除 AI 額度
if "refresh_val" not in st.session_state:
    st.session_state.refresh_val = 5
if "user_favs" not in st.session_state:
    st.session_state.user_favs = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
if "single_coin_ai" not in st.session_state:
    st.session_state.single_coin_ai = {} # 用來存放每一個幣獨立的 AI 分析結果

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
# 3. 側邊欄控制台 (設定與狀態完全鎖定，徹底解決跳針 Bug)
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

# 核心修正：利用 Widget Session State 雙向綁定，不給 default 參數二次複寫的機會
def on_favs_change():
    st.session_state.user_favs = st.session_state.select_favs

if "select_favs" not in st.session_state:
    st.session_state.select_favs = [s for s in st.session_state.user_favs if s in all_available_cryptos]

# 🎯 這邊勾選的順序，就是你的自選幣排序
st.sidebar.multiselect(
    "🎯 自選監控區 (按勾選先後順序進行自訂排序)",
    options=all_available_cryptos,
    key="select_favs",
    on_change=on_favs_change
)

# 🎯 刷新頻率綁定 key，自動刷新時絕對死鎖，不還原
st.sidebar.slider("數據脈搏刷新頻率 (秒)", min_value=3, max_value=15, key="refresh_val")

# 自動刷新器安全啟動 (完全使用記憶體鎖定的數值)
st_autorefresh(interval=st.session_state.refresh_val * 1000, key="datarefresh")

# =====================================================================
# 4. Gemini 單幣精準戰研調研函數 (只有你手動點擊時才會觸發)
# =====================================================================
def ask_gemini_single_coin(coin, price, change, vol_str):
    if not api_key: return "⚠️ 請先配置 Gemini API Key"
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    prompt = f"""
    你現在是精通加密貨幣主力大單資金流向與短線量化結構的頂級操盤專家。
    正在對指定幣種進行個別調研：
    - 標的幣種：{coin}/USDT | 當前現價：{price} | 24h漲跌幅：{change}% | 24h總成交額：{vol_str}
    
    請用繁體中文給出極度精簡、直擊痛點的短評報告：
    1. 【主力心理學】：拆解背後最真實的「主力心理狀態」（例如：主力正在洗盤吸籌、拉高出貨、動能突破，還是散戶恐慌踩踏）。
    2. 【下單機會精確提醒】：如果有明確的下單機會，請用【🔥 突發下單機會提醒】開頭給出具體多空方向與防守點！如果沒有，請提示觀望。
    """
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        data = response.json()
        if 'error' in data: return f"❌ 調研失敗: {data['error'].get('message', '頻率超限')}"
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e: return f"⚠️ 網路傳輸異常 ({e})"

# =====================================================================
# 5. 數據掃描中心 (100% 純自選排序化)
# =====================================================================
try:
    all_tickers = exchange.fetch_tickers()
except:
    st.rerun()

fav_data_list = []

# 嚴格按照使用者在多選欄勾選排列的順序建立數據
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
            "volume_str": f"{vol_usdt / 1000000:.2f}M USDT"
        })

# =====================================================================
# 6. 主畫面單一網頁佈局 (由你掌控的 AI 戰研舱)
# =====================================================================
st.title("🏹 CryptoHunter 智能雷達 (純自選戰研艙)")
st.write(f"⏱ 數據脈搏更新時間：`{datetime.now().strftime('%H:%M:%S')}`")
st.markdown("---")

if fav_data_list:
    # 採用優雅的排版呈現你自訂排序的自選幣
    for coin in fav_data_list:
        c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
        c_sign = "+" if coin['change'] >= 0 else ""
        
        # 建立一個幣種區塊
        st.markdown(f"## 🪙 {coin['symbol']} 實時狀態")
        
        # 橫向並排基本數據與按鈕
        col_meta, col_btn = st.columns([8, 4])
        with col_meta:
            st.markdown(f"#### 現價: `${coin['price']:,}` | 24h漲跌: <span style='color:{c_color}; font-weight:bold;'>{c_sign}{coin['change']:.2f}%</span> | 24h成交額: `{coin['volume_str']}`", unsafe_allow_html=True)
        
        with col_btn:
            # 🎯 核心功能：讓使用者自己點選要哪一個自選幣進行 AI 分析
            if st.button(f"⚡ 進行 {coin['symbol']} 深度 AI 戰研", key=f"btn_{coin['symbol']}", use_container_width=True):
                with st.spinner(f"正在調研 {coin['symbol']} 主力鏈上心理學..."):
                    res = ask_gemini_single_coin(coin['symbol'], coin['price'], coin['change'], coin['volume_str'])
                    st.session_state.single_coin_ai[coin['symbol']] = res
        
        # 渲染該幣專屬的 AI 分析結果 (存在記憶體中，自動刷新時不會消失，除非你點別台或改自選)
        if coin['symbol'] in st.session_state.single_coin_ai:
            analysis_result = st.session_state.single_coin_ai[coin['symbol']]
            
            # 如果 AI 回覆包含下單機會，自動用醒目的特別色塊高亮呈現
            if "下單機會" in analysis_result or "🔥" in analysis_result:
                st.warning(analysis_result)
            else:
                st.info(analysis_result)
                
        st.markdown("<br>", unsafe_allow_html=True)
else:
    st.info("💡 控制台內空空如也，請先在左側多選欄中勾選並排序你想監控的自選標的。")
