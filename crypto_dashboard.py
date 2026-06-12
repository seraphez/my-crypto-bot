import streamlit as pd  # 保留你習慣的 import 結構
import streamlit as st
import ccxt
import time
from datetime import datetime
import requests

# =====================================================================
# 1. 全局網頁配置與【奢華粉櫻 x 正方形卡片】高級 CSS 注入
# =====================================================================
st.set_page_config(page_title="CryptoHunter | 櫻之戰研艙", layout="wide")

st.markdown("""
    <style>
    /* 全局奢華暗夜櫻花背景 */
    .stApp { background: #0B0D13; overflow-x: hidden; }
    h1, h2, h3, h4 { color: #FFB7C5 !important; font-family: 'Courier New', monospace; text-shadow: 0 0 10px rgba(255,183,197,0.4); }

    /* 🎯 透過樣式穿透，直接將容器美化為發光正方形卡片 */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(22, 27, 34, 0.85) !important;
        border: 2px solid rgba(255, 183, 197, 0.35) !important;
        box-shadow: 0 8px 32px 0 rgba(255, 183, 197, 0.08) !important;
        backdrop-filter: blur(6px);
        border-radius: 16px !important;
        padding: 24px !important;
        margin-bottom: 15px !important;
    }
    
    /* 🌸 櫻花隨風飄落動畫特效 */
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
# 2. 交易所與數據源準備
# =====================================================================
@st.cache_resource
def get_exchange(): return ccxt.okx()
exchange = get_exchange()

@st.cache_data(ttl=3600)
def get_all_usdt_symbols():
    try: return sorted([s for s in exchange.load_markets().keys() if s.endswith('/USDT') and ':' not in s])
    except: return ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

all_cryptos = get_all_usdt_symbols()

# =====================================================================
# 3. 側邊欄控制台
# =====================================================================
st.sidebar.header("🌸 櫻之量化控制台")

# API Key 讀取
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")

chosen_favs = st.sidebar.multiselect("🎯 自選監控區", options=all_cryptos, default=["BTC/USDT", "ETH/USDT", "SOL/USDT"])
chosen_refresh = st.sidebar.slider("數據脈搏刷新頻率 (秒)", min_value=3, max_value=15, value=5)

# =====================================================================
# 4. Gemini AI 請求函數 (整合雙重計數滑動窗口，防禦 429 頻率超限)
# =====================================================================
def ask_gemini_market_analysis(coin, price, change, vol_str):
    if not api_key: 
        return "⚠️ 請先配置控制台的 Gemini API Key"
    
    current_time = time.time()
    
    # 🕒 🛡️ 防線 1：全局頻率檢查（過去 60 秒內，所有幣種點擊總數限制在 10 次內）
    if "global_request_timestamps" not in st.session_state:
        st.session_state["global_request_timestamps"] = []
    
    st.session_state["global_request_timestamps"] = [
        t for t in st.session_state["global_request_timestamps"] if current_time - t < 60
    ]
    
    if len(st.session_state["global_request_timestamps"]) >= 10:
        oldest_request = st.session_state["global_request_timestamps"][0]
        wait_time = int(60 - (current_time - oldest_request))
        return f"⏳ 櫻之雷達超載！全系統一分鐘內點擊過於頻繁。請等待 {wait_time} 秒後再試，以防被 Google 封鎖。"

    # 🕒 🛡️ 防線 2：單一幣種冷卻檢查（防止同一個按鈕連續狂點）
    last_call_key = f"last_call_{coin}"
    if last_call_key in st.session_state:
        time_passed = current_time - st.session_state[last_call_key]
        if time_passed < 20:
            remaining = int(20 - time_passed)
            return f"⏳ {coin} 戰研冷卻中...請等待 {remaining} 秒。"
            
    # 更新計時與計數紀錄
    st.session_state[last_call_key] = current_time
    st.session_state["global_request_timestamps"].append(current_time)

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    prompt = f"""
    你現在是精通加密貨幣『突發爆量/主力大單資金』的頂級短線量化操盤專家。
    正在對目前自選幣進行【即時盤面量化結構調研】：
    - 標的幣種：{coin}/USDT | 當前現價：{price} | 24h漲跌幅：{change}% | 24h總成交額：{vol_str}
    請用繁體中文給出極度精簡、一針見血且極具實戰攻擊性的短評報告：
    1. 【主力心理學】：拆解該幣目前盤面背後最真實的資金動態。
    2. 【🔥 突發下單機會提醒】：給出具體多空方向與防守點，若無提示觀望。
    """
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        
        if response.status_code == 429:
            return "❌ 觸發 Gemini 官方 429 限制（可能此 Key 被多處網頁開啟分頁共用）。請靜置 1 分鐘後再試。"
            
        res_json = response.json()
        if 'error' in res_json:
            err_msg = res_json['error'].get('message', '未知錯誤')
            return f"❌ API 限制: {err_msg}"
            
        return res_json['candidates'][0]['content']['parts'][0]['text']
    except Exception as e: 
        return f"⚠️ 網路傳輸異常 ({e})"

# =====================================================================
# 5. 核心：局部重新整理片段 (Fragment)
# =====================================================================
@st.fragment(run_every=chosen_refresh)
def render_monitor_dashboard(fav_coins):
    try: all_tickers = exchange.fetch_tickers()
    except: return
    
    st.write(f"⏱ 行情脈搏更新時間：`{datetime.now().strftime('%H:%M:%S')}` (僅局部刷新行情，其餘元件完全死鎖)")
    st.markdown("---")
    
    # 建立 3 欄響應式粉櫻發光正方形矩陣
    cols = st.columns(3)
    
    for idx, symbol in enumerate(fav_coins):
        if symbol not in all_tickers: continue
        
        t = all_tickers[symbol]
        price = t['last']
        change = t['percentage'] if t['percentage'] is not None else 0.0
        vol = t['quoteVolume'] if t['quoteVolume'] else ((t['baseVolume'] or 0) * price)
        coin_name = symbol.replace('/USDT', '')
        vol_str = f"{vol / 1000000:.2f}M USDT"
        
        with cols[idx % 3]:
            with st.container():
                c_color = "#00FF66" if change >= 0 else "#FF3366"
                c_sign = "+" if change >= 0 else ""
                
                # 數據美化渲染
                st.markdown(f"### 🪙 {coin_name}/USDT")
                st.markdown(f"<h2 style='color:#00FF66; margin:0;'>${price}</h2>", unsafe_allow_html=True)
                st.markdown(f"漲跌: <span style='color:{c_color}; font-weight:bold;'>{c_sign}{change:.2f}%</span> | 24h量: `{vol_str}`", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                
                # 手動精確戰研按鈕 (防止 Fragment 計時器打斷，點擊時拉取最新的盤面資訊)
                button_key = f"btn_{coin_name}"
                if st.button(f"⚡ 執行 {coin_name} AI 戰研", key=button_key, use_container_width=True):
                    with st.spinner("深度調研主力籌碼流向中..."):
                        res = ask_gemini_market_analysis(coin_name, price, change, vol_str)
                        st.session_state[f"ai_res_{coin_name}"] = res
                        # 當前片段（Fragment）主動 rerun 鎖定報告，不會被 5 秒定時刷新洗掉
                        st.rerun(scope="fragment")
                
                # --- AI 戰研結果完美渲染區 ---
                cache_key = f"ai_res_{coin_name}"
                if cache_key in st.session_state:
                    ai_text = st.session_state[cache_key]
                    if "⏳" in ai_text:
                        st.warning(ai_text)
                    elif "❌" in ai_text or "⚠️" in ai_text:
                        st.error(ai_text)
                    elif "下單機會" in ai_text or "🔥" in ai_text:
                        st.warning(ai_text)
                    else:
                        st.info(ai_text)
                else:
                    st.caption("💡 狀態：待機中。點擊按鈕即刻調研。")

# =====================================================================
# 6. 主畫面入口
# =====================================================================
st.title("🏹 CryptoHunter 智能雷達 (櫻之局部刷新艙)")
if chosen_favs:
    render_monitor_dashboard(chosen_favs)
else:
    st.info("💡 櫻之雷達待機中。請先在左側控制台勾選你想監控的自選加密貨幣。")
