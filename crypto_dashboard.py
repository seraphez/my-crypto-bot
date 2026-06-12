import streamlit as st
import ccxt
from datetime import datetime
import requests

# =====================================================================
# 1. 奢華暗夜粉櫻 x 正方形卡片視覺穿透 (最安全的 CSS 注入)
# =====================================================================
st.set_page_config(page_title="CryptoHunter | 櫻之戰研艙", layout="wide")

# 初始化持久記憶體，確保點擊 AI 按鈕後的內容能存下來
if "single_coin_ai" not in st.session_state: 
    st.session_state.single_coin_ai = {}

st.markdown("""
    <style>
    /* 全局背景 */
    .stApp { background: #0B0D13; overflow-x: hidden; }
    h1, h2, h3, h4 { color: #FFB7C5 !important; font-family: 'Courier New', monospace; text-shadow: 0 0 10px rgba(255,183,197,0.4); }

    /* 將 Streamlit 原生區塊直接渲染成正方形發光卡片 */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(22, 27, 34, 0.85) !important;
        border: 2px solid rgba(255, 183, 197, 0.35) !important;
        box-shadow: 0 8px 32px 0 rgba(255, 183, 197, 0.08) !important;
        backdrop-filter: blur(6px);
        border-radius: 16px !important;
        padding: 24px !important;
        margin-bottom: 15px !important;
    }
    
    /* 🌸 動態櫻花飄落特效 */
    .sakura-bg { position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 0; overflow: hidden; }
    .petal { position: absolute; background: #FFB7C5; border-radius: 150% 0 150% 150%; opacity: 0.6; animation: fall linear infinite; }
    @keyframes fall {
        0% { transform: translateY(-20px) rotate(0deg); opacity: 0.6; }
        100% { transform: translateY(100vh) rotate(360deg); opacity: 0; }
    }
    .petal:nth-child(1) { left: 10%; width: 13px; height: 10px; animation-duration: 7s; }
    .petal:nth-child(2) { left: 30%; width: 16px; height: 12px; animation-duration: 9s; animation-delay: 1s; }
    .petal:nth-child(3) { left: 50%; width: 11px; height: 8px; animation-duration: 6s; animation-delay: 0.5s; }
    .petal:nth-child(4) { left: 70%; width: 14px; height: 11px; animation-duration: 8s; animation-delay: 2s; }
    .petal:nth-child(5) { left: 90%; width: 12px; height: 9px; animation-duration: 7.5s; animation-delay: 1.5s; }
    </style>
    <div class="sakura-bg">
        <div class="petal"></div><div class="petal"></div><div class="petal"></div>
        <div class="petal"></div><div class="petal"></div>
    </div>
""", unsafe_allow_html=True)

# =====================================================================
# 2. 交易所與交易所數據準備
# =====================================================================
@st.cache_resource
def get_exchange(): 
    return ccxt.okx()
exchange = get_exchange()

@st.cache_data(ttl=3600)
def get_all_usdt_symbols():
    try: 
        return sorted([s for s in exchange.load_markets().keys() if s.endswith('/USDT') and ':' not in s])
    except: 
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

all_cryptos = get_all_usdt_symbols()

# =====================================================================
# 3. 側邊欄控制台 (最基礎的原生元件)
# =====================================================================
st.sidebar.header("🌸 櫻之量化控制台")

# 密鑰讀取
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")

# 使用最簡單的原生元件，不跟網址列做任何多餘同步
chosen_favs = st.sidebar.multiselect("🎯 自選監控區 (可直接排序)", options=all_cryptos, default=["BTC/USDT", "ETH/USDT", "SOL/USDT"])
chosen_refresh = st.sidebar.slider("數據脈搏刷新頻率 (秒)", min_value=3, max_value=15, value=5)

# 行情定時自動刷新
st_autorefresh(interval=chosen_refresh * 1000, key="sakura_pure_heartbeat")

# =====================================================================
# 4. 毫無累贅的 Gemini AI 請求函數
# =====================================================================
def ask_gemini_ai(coin, price, change, vol_str):
    if not api_key: 
        return "⚠️ 請先配置控制台的 Gemini API Key"
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    prompt = f"代幣:{coin}/USDT | 現價:{price} | 漲跌:{change}% | 24h成交額:{vol_str}。請用繁體中文給出極精簡實戰報告：1.【主力心理學】 2.【🔥 突發下單機會提醒】(給出具體多空方向與防守點，若無提示觀望)。"
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10).json()
        if 'error' in response: 
            return f"❌ 呼叫失敗: {response['error'].get('message', '超過免費限制')}"
        return response['candidates'][0]['content']['parts'][0]['text']
    except Exception as e: 
        return f"⚠️ 網路傳輸異常 ({e})"

# =====================================================================
# 5. 實時行情獲取
# =====================================================================
try: 
    all_tickers = exchange.fetch_tickers()
except: 
    st.rerun()

fav_data_list = []
for symbol in chosen_favs:
    if symbol in all_tickers:
        t = all_tickers[symbol]
        price = t['last']
        change = t['percentage'] if t['percentage'] is not None else 0.0
        vol = t['quoteVolume'] if t['quoteVolume'] else ((t['baseVolume'] or 0) * price)
        fav_data_list.append({
            "symbol": symbol.replace('/USDT', ''), 
            "price": price, 
            "change": change, 
            "vol_str": f"{vol / 1000000:.2f}M USDT"
        })

# =====================================================================
# 6. 主畫面佈局 (正方形高級發光卡片矩陣)
# =====================================================================
st.title("🏹 CryptoHunter 智能雷達 (純自選戰研艙)")
st.write(f"⏱ 行情脈搏更新時間：`{datetime.now().strftime('%H:%M:%S')}`")
st.markdown("---")

if fav_data_list:
    cols = st.columns(3)
    
    for idx, coin in enumerate(fav_data_list):
        with cols[idx % 3]:
            # 用原生 st.container 包覆，CSS 樣式會自動把它美化成正方形發光卡片
            with st.container():
                c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                c_sign = "+" if coin['change'] >= 0 else ""
                
                # 渲染即時看板數據
                st.markdown(f"### 🪙 {coin['symbol']}/USDT")
                st.markdown(f"<h2 style='color:#00FF66; margin:0;'>${coin['price']:,}</h2>", unsafe_allow_html=True)
                st.markdown(f"漲跌: <span style='color:{c_color}; font-weight:bold;'>{c_sign}{coin['change']:.2f}%</span> | 24h量: `{coin['vol_str']}`", unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # 手動精確戰研按鈕
                if st.button(f"⚡ 執行 {coin['symbol']} AI 戰研", key=f"btn_{coin['symbol']}", use_container_width=True):
                    with st.spinner("操盤手請稍候，正在調研盤面心理..."):
                        res = ask_gemini_ai(coin['symbol'], coin['price'], coin['change'], coin['vol_str'])
                        st.session_state.single_coin_ai[coin['symbol']] = res
                    st.rerun()
                
                # --- AI 戰研結果完美渲染區 (這版絕對看的到！) ---
                if coin['symbol'] in st.session_state.single_coin_ai:
                    ai_text = st.session_state.single_coin_ai[coin['symbol']]
                    if "下單機會" in ai_text or "🔥" in ai_text:
                        st.warning(ai_text)
                    else:
                        st.info(ai_text)
                else:
                    st.caption("💡 狀態：待機中。點擊上方按鈕立即進行 AI 盤面調研。")
else:
    st.info("💡 櫻之雷達待機中。請先在左側控制台勾選你想監控的自選加密貨幣。")
