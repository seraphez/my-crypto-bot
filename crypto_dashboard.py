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

# 🧠 【防跑針與 AI 鎖定核心】初始化絕對持久化記憶體
if "real_favs" not in st.session_state:
    st.session_state.real_favs = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
if "real_refresh" not in st.session_state:
    st.session_state.real_refresh = 5
if "single_coin_ai" not in st.session_state:
    st.session_state.single_coin_ai = {}

st.markdown("""
    <style>
    div[data-testid="stForm"] { background-color: transparent !important; }
    .stApp div[data-testid="stVerticalBlock"] > div { opacity: 1 !important; }
    .stApp { background-color: #0E1117; }
    h1, h2, h3, h4 { color: #00FFCC !important; font-family: 'Courier New', monospace; }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. 交易所初始化
# =====================================================================
@st.cache_resource
def get_exchange():
    return ccxt.okx()

exchange = get_exchange()

@st.cache_data(ttl=3600)
def get_all_usdt_symbols():
    try:
        markets = exchange.load_markets()
        return sorted([s for s in markets.keys() if s.endswith('/USDT') and ':' not in s])
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]

all_available_cryptos = get_all_usdt_symbols()

# =====================================================================
# 3. 側邊欄控制台 (手動存檔死鎖機制，100% 根除自動刷新跑針的 Bug)
# =====================================================================
st.sidebar.header("⚙️ 獵手核心控制台")

api_key = None
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("🔑 已自動載入密鑰")
else:
    user_key = st.sidebar.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")
    if user_key: api_key = user_key

st.sidebar.markdown("### 🛠️ 盤面參數設定")

# 安全過濾器
valid_defaults = [s for s in st.session_state.real_favs if s in all_available_cryptos]
if not valid_defaults:
    valid_defaults = [all_available_cryptos[0]]

# 多選框與滑桿只作為「UI 輸入端」，絕不讓它們自動複寫記憶體
ui_favs = st.sidebar.multiselect(
    "🎯 自選監控區 (按勾選先後順序排序)",
    options=all_available_cryptos,
    default=valid_defaults
)

ui_refresh = st.sidebar.slider(
    "數據脈搏刷新頻率 (秒)", 
    min_value=3, 
    max_value=15, 
    value=st.session_state.real_refresh
)

# 🎯 【殺手鐧】只有按下這個按鈕，設定才會寫入記憶體！自動刷新時這段完全凍結，設定絕對不可能再跑掉
if st.sidebar.button("💾 鎖定自選與刷新頻率", use_container_width=True):
    if ui_favs:
        st.session_state.real_favs = ui_favs
    st.session_state.real_refresh = ui_refresh
    st.sidebar.success("儲存成功！記憶體已死鎖")
    st.rerun()

# 自動刷新器安全啟動 (死死鎖定實時記憶體的值，不受 UI 元件重製影響)
st_autorefresh(interval=st.session_state.real_refresh * 1000, key="hunter_heartbeat_fixed_v2")

# =====================================================================
# 4. Gemini 單幣精準戰研調研函數 (物理防卡死、防超限)
# =====================================================================
def ask_gemini_single_coin(coin, price, change, vol_str):
    if not api_key: return "⚠️ 請先配置 Gemini API Key"
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    prompt = f"""
    你現在是精通加密貨幣主力大單資金流向與短線量化結構的頂級操盤專家。
    正在對指定幣種進行個別調研：
    - 標的幣種：{coin}/USDT | 當前現價：{price} | 24h漲跌幅：{change}% | 24h總成交額：{vol_str}
    
    請用繁體中文給出極度精簡、一針見血的實戰報告：
    1. 【主力心理學】：拆解目前盤面背後最真實的「主力心理狀態」（洗盤吸籌、拉高出貨、動能突破、散戶踩踏）。
    2. 【下單機會精確提醒】：如果有明確的下單機會，請用【🔥 突發下單機會提醒】開頭給出具體多空方向與防守點！如果沒有，請提示觀望。
    """
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        data = response.json()
        if 'error' in data: return f"❌ 調研失敗: {data['error'].get('message', '頻率超限')}"
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e: return f"⚠️ 網路傳輸異常 ({e})"

# =====================================================================
# 5. 數據掃描中心 (100% 遵從真實自訂排序)
# =====================================================================
try:
    all_tickers = exchange.fetch_tickers()
except:
    st.rerun()

fav_data_list = []

# 嚴格遵從記憶體鎖定的優先順序建立數據流
for symbol in st.session_state.real_favs:
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
# 6. 主畫面佈局 (操作主權完全在你手上的 AI 戰研舱)
# =====================================================================
st.title("🏹 CryptoHunter 智能雷達 (純自選戰研艙)")
st.write(f"⏱ 數據脈搏更新時間：`{datetime.now().strftime('%H:%M:%S')}`")
st.caption("💡 提示：若修改了左側自選幣或刷新頻率，請記得點擊側邊欄的『💾 鎖定自選』按鈕以寫入記憶體。")
st.markdown("---")

if fav_data_list:
    for coin in fav_data_list:
        c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
        c_sign = "+" if coin['change'] >= 0 else ""
        
        st.markdown(f"## 🪙 {coin['symbol']} 實時狀態")
        
        col_meta, col_btn = st.columns([8, 4])
        with col_meta:
            st.markdown(f"#### 現價: `${coin['price']:,}` | 24h漲跌: <span style='color:{c_color}; font-weight:bold;'>{c_sign}{coin['change']:.2f}%</span> | 24h成交額: `{coin['volume_str']}`", unsafe_allow_html=True)
        
        with col_btn:
            # 🎯 【修復 AI 動不了的關鍵】使用獨立 key，並且點擊後立即執行，結果直接鎖死在單獨的 session 欄位中
            if st.button(f"⚡ 進行 {coin['symbol']} 深度 AI 戰研", key=f"btn_lock_{coin['symbol']}", use_container_width=True):
                with st.spinner(f"正在調研 {coin['symbol']} 主力鏈上心理學..."):
                    res = ask_gemini_single_coin(coin['symbol'], coin['price'], coin['change'], coin['volume_str'])
                    st.session_state.single_coin_ai[coin['symbol']] = res
                st.rerun() # 強制刷新畫面，確保 AI 結果不受計時器干擾、立刻渲染
        
        # 渲染該幣專屬的 AI 分析結果 (存在記憶體中，自動刷新時絕對不會消失)
        if coin['symbol'] in st.session_state.single_coin_ai:
            analysis_result = st.session_state.single_coin_ai[coin['symbol']]
            
            if "下單機會" in analysis_result or "🔥" in analysis_result:
                st.warning(analysis_result)
            else:
                st.info(analysis_result)
                
        st.markdown("---")
else:
    st.info("💡 控制台內空空如也，請先在左側多選欄中勾選並點擊『儲存鎖定』。")
