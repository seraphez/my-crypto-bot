import streamlit as st
import ccxt
import pandas as pd
from datetime import datetime
import requests
import time
from streamlit_autorefresh import st_autorefresh

# =====================================================================
# 1. 網頁頂級配置與【櫻花飛舞 x 奢華正方形卡片】CSS 動態注入
# =====================================================================
st.set_page_config(
    page_title="CryptoHunter | 櫻之自選戰研艙",
    layout="wide"
)

# 🧠 【防跑針核心】利用 Session State 進行零元件干擾初始化
if "sb_favs" not in st.session_state:
    st.session_state.sb_favs = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
if "sb_refresh" not in st.session_state:
    st.session_state.sb_refresh = 5
if "single_coin_ai" not in st.session_state:
    st.session_state.single_coin_ai = {}

# 🌸 注入純 CSS 櫻花飄落特效與精緻正方形卡片樣式
st.markdown("""
    <style>
    /* 全局背景 */
    .stApp { 
        background: #0B0D13; 
        overflow-x: hidden;
    }
    
    /* 移除表單暗化遮罩與不必要元素 */
    div[data-testid="stForm"] { background-color: transparent !important; }
    .stApp div[data-testid="stVerticalBlock"] > div { opacity: 1 !important; }
    h1, h2, h3, h4 { color: #FFB7C5 !important; font-family: 'Courier New', monospace; text-shadow: 0 0 10px rgba(255,183,197,0.3); }

    /* 🎯 專屬正方形奢華卡片樣式 */
    .square-coin-card {
        background: rgba(22, 27, 34, 0.85);
        border: 2px solid rgba(255, 183, 197, 0.4);
        box-shadow: 0 8px 32px 0 rgba(255, 183, 197, 0.1);
        backdrop-filter: blur(4px);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        min-height: 320px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: all 0.3s ease;
    }
    .square-coin-card:hover {
        border-color: #FFB7C5;
        box-shadow: 0 8px 32px 0 rgba(255, 183, 197, 0.25);
        transform: translateY(-2px);
    }
    
    .coin-title { font-size: 26px; font-weight: bold; color: #FFFFFF; font-family: 'Courier New', monospace; }
    .coin-price { font-size: 32px; font-weight: bold; color: #00FF66; margin: 6px 0; font-family: 'Courier New', monospace; }
    .coin-change { font-size: 18px; font-weight: bold; }
    
    /* 🌸 櫻花飄落背景動畫特效 */
    .sakura-bg {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        pointer-events: none; z-index: 0; overflow: hidden;
    }
    .petal {
        position: absolute; background: #FFB7C5; border-radius: 150% 0 150% 150%;
        opacity: 0.7; animation: fall linear infinite;
    }
    @keyframes fall {
        0% { transform: translateY(-20px) rotate(0deg); opacity: 0.7; }
        100% { transform: translateY(100vh) rotate(360deg); opacity: 0; }
    }
    /* 產生不同落點與速度的櫻花 */
    .petal:nth-child(1) { left: 10%; width: 12px; height: 9px; animation-duration: 7s; animation-delay: 0s; }
    .petal:nth-child(2) { left: 25%; width: 15px; height: 11px; animation-duration: 9s; animation-delay: 1.5s; }
    .petal:nth-child(3) { left: 40%; width: 10px; height: 8px; animation-duration: 6s; animation-delay: 0.5s; }
    .petal:nth-child(4) { left: 55%; width: 14px; height: 10px; animation-duration: 8s; animation-delay: 2s; }
    .petal:nth-child(5) { left: 70%; width: 11px; height: 9px; animation-duration: 7.5s; animation-delay: 1s; }
    .petal:nth-child(6) { left: 85%; width: 16px; height: 12px; animation-duration: 10s; animation-delay: 2.5s; }
    .petal:nth-child(7) { left: 95%; width: 13px; height: 10px; animation-duration: 8.5s; animation-delay: 0.2s; }
    </style>
    
    <div class="sakura-bg">
        <div class="petal"></div><div class="petal"></div><div class="petal"></div>
        <div class="petal"></div><div class="petal"></div><div class="petal"></div>
        <div class="petal"></div>
    </div>
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
# 3. 側邊欄控制台 (移除所有 default/value 傳參，達成鋼鐵死鎖不跑針)
# =====================================================================
st.sidebar.header("🌸 櫻之量化控制台")

api_key = None
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("🔑 已自動載入密鑰")
else:
    user_key = st.sidebar.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")
    if user_key: api_key = user_key

# 🎯 【防跑針關鍵】多選框改用 key 自主委任，絕對不寫 default 參數
st.sidebar.multiselect(
    "🎯 自選監控區 (按勾選先後順序進行自訂排序)",
    options=all_available_cryptos,
    key="sb_favs"
)

# 🎯 【防跑針關鍵】刷新滑桿同樣用 key 自主委任，絕對不寫 value 參數
st.sidebar.slider(
    "數據脈搏刷新頻率 (秒)", 
    min_value=3, 
    max_value=15, 
    key="sb_refresh"
)

# 自動刷新器安全啟動 (完美綁定持久化數值)
st_autorefresh(interval=st.session_state.sb_refresh * 1000, key="sakura_heartbeat_fixed")

# =====================================================================
# 4. Gemini 單幣精準下單機會調研函數
# =====================================================================
def ask_gemini_single_coin(coin, price, change, vol_str):
    if not api_key: return "⚠️ 請先配置控制台的 Gemini API Key"
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    prompt = f"""
    你現在是精通加密貨幣主力大單資金流向與短線量化結構的頂級操盤專家。
    正在對指定自選幣進行調研：
    - 標的幣種：{coin}/USDT | 當前現價：{price} | 24h漲跌幅：{change}% | 24h總成交額：{vol_str}
    
    請用繁體中文給出極度精簡、一針見血的實戰報告：
    1. 【主力心理學】：拆解目前盤面背後最真實的「主力心理狀態」（洗盤吸籌、拉高出貨、動能突破、散戶踩踏）。
    2. 【下單機會精確提醒】：如果有明確的下單機會，請用【🔥 突發下單機會提醒】開頭給出具體多空方向與防守點！如果沒有，請提示觀望。
    """
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        data = response.json()
        if 'error' in data: 
            err_msg = data['error'].get('message', '')
            if "quota" in err_msg.lower():
                return "❌ 調研失敗: 觸發免費層每分鐘次數限制，請靜待 30 秒後重新點擊。"
            return f"❌ 調研失敗: {err_msg}"
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e: return f"⚠️ 網路傳輸異常 ({e})"

# =====================================================================
# 5. 數據掃描中心 (100% 遵守自選、零雜訊)
# =====================================================================
try:
    all_tickers = exchange.fetch_tickers()
except:
    st.rerun()

fav_data_list = []

# 嚴格遵從交易員在控制台排定勾選的優先順序建立數據流
for symbol in st.session_state.sb_favs:
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
# 6. 主畫面佈局 (正方形發光矩陣卡片艙)
# =====================================================================
st.title("🏹 CryptoHunter 智能雷達 (櫻之自選研究艙)")
st.write(f"⏱ 數據脈搏更新時間：`{datetime.now().strftime('%H:%M:%S')}`")
st.markdown("---")

if fav_data_list:
    # 使用 3 欄響應式佈局，將自選幣塑造成完美對齊的正方形卡片
    cols = st.columns(3)
    
    for idx, coin in enumerate(fav_data_list):
        with cols[idx % 3]:
            c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
            c_sign = "+" if coin['change'] >= 0 else ""
            
            # 使用 HTML 渲染正方形卡片上半部的基本即時數據
            card_top_html = f"""
            <div class="square-coin-card">
                <div>
                    <div class="coin-title">🪙 {coin['symbol']}/USDT</div>
                    <div class="coin-price">${coin['price']:,}</div>
                    <div class="coin-change" style="color: {c_color};">{c_sign}{coin['change']:.2f}%</div>
                    <div style="color: #8B949E; font-size: 13px; margin-top: 4px;">24h成交額: {coin['volume_str']}</div>
                </div>
            """
            st.markdown(card_top_html, unsafe_allow_html=True)
            
            # 🎯 【精確控管】單幣獨立戰研按鈕，點擊後觸發執行並寫入持久化快取
            if st.button(f"⚡ 執行 {coin['symbol']} AI 戰研", key=f"btn_sakura_{coin['symbol']}", use_container_width=True):
                with st.spinner(f"正在深度解析 {coin['symbol']} 資金流向..."):
                    res = ask_gemini_single_coin(coin['symbol'], coin['price'], coin['change'], coin['volume_str'])
                    st.session_state.single_coin_ai[coin['symbol']] = res
                st.rerun() # 立即重研渲染，擺脫自動重整的白屏卡死
            
            # 顯示對應幣種的 AI 戰研成果，即使定時刷新到了也絕對不會消失！
            if coin['symbol'] in st.session_state.single_coin_ai:
                ai_text = st.session_state.single_coin_ai[coin['symbol']]
                if "下單機會" in ai_text or "🔥" in ai_text:
                    st.warning(ai_text)
                else:
                    st.info(ai_text)
            else:
                st.caption("💡 點擊上方按鈕，即刻調研主力做局方針。")
                
            # 閉合卡片 div 標籤
            st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("💡 櫻之雷達待機中。請先在左側控制台勾選你想排列、監控的自選加密貨幣。")
