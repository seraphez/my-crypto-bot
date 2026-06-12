import streamlit as st
import ccxt
import pandas as pd
from datetime import datetime
import requests
import time
from streamlit_autorefresh import st_autorefresh

# =====================================================================
# 1. 網頁頂級配置與【櫻花飛舞 x 奢華正方形矩陣】CSS 動態注入
# =====================================================================
st.set_page_config(
    page_title="CryptoHunter | 櫻之自選純淨艙",
    layout="wide"
)

# 🌸 注入純 CSS 櫻花飄落背景動畫與精緻正方形發光卡片樣式
st.markdown("""
    <style>
    /* 全局奢華暗夜櫻花背景 */
    .stApp { 
        background: #0B0D13; 
        overflow-x: hidden;
    }
    
    /* 徹底拔除表單暗化遮罩與不必要元素 */
    div[data-testid="stForm"] { background-color: transparent !important; }
    .stApp div[data-testid="stVerticalBlock"] > div { opacity: 1 !important; }
    h1, h2, h3, h4 { color: #FFB7C5 !important; font-family: 'Courier New', monospace; text-shadow: 0 0 10px rgba(255,183,197,0.4); }

    /* 🎯 精緻正方形發光卡片外殼 */
    .square-coin-card {
        background: rgba(22, 27, 34, 0.85);
        border: 2px solid rgba(255, 183, 197, 0.35);
        box-shadow: 0 8px 32px 0 rgba(255, 183, 197, 0.08);
        backdrop-filter: blur(6px);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        min-height: 260px;
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
    
    /* 🌸 櫻花隨風飄落動畫特效 */
    .sakura-bg {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        pointer-events: none; z-index: 0; overflow: hidden;
    }
    .petal {
        position: absolute; background: #FFB7C5; border-radius: 150% 0 150% 150%;
        opacity: 0.6; animation: fall linear infinite;
    }
    @keyframes fall {
        0% { transform: translateY(-20px) rotate(0deg); opacity: 0.6; }
        100% { transform: translateY(100vh) rotate(360deg); opacity: 0; }
    }
    .petal:nth-child(1) { left: 8%; width: 13px; height: 10px; animation-duration: 7s; animation-delay: 0s; }
    .petal:nth-child(2) { left: 28%; width: 16px; height: 12px; animation-duration: 9s; animation-delay: 1.2s; }
    .petal:nth-child(3) { left: 43%; width: 11px; height: 8px; animation-duration: 6s; animation-delay: 0.3s; }
    .petal:nth-child(4) { left: 60%; width: 14px; height: 11px; animation-duration: 8s; animation-delay: 2.2s; }
    .petal:nth-child(5) { left: 73%; width: 12px; height: 9px; animation-duration: 7.5s; animation-delay: 0.8s; }
    .petal:nth-child(6) { left: 88%; width: 17px; height: 13px; animation-duration: 10s; animation-delay: 1.8s; }
    </style>
    
    <div class="sakura-bg">
        <div class="petal"></div><div class="petal"></div><div class="petal"></div>
        <div class="petal"></div><div class="petal"></div><div class="petal"></div>
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
# 3. 終極相容解法：網址參數化（完美支援舊版環境，F5 刷新死鎖不跑針）
# =====================================================================
try:
    qp = st.experimental_get_query_params()
except:
    qp = {}

# A. 讀取自選幣
if "favs" in qp:
    raw_url_favs = qp["favs"]
    init_favs = [f"{f}/USDT" if not f.endswith("/USDT") else f for f in raw_url_favs]
else:
    init_favs = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

# B. 讀取刷新頻率
if "refresh" in qp:
    try: init_refresh = int(qp["refresh"][0])
    except: init_refresh = 5
else:
    init_refresh = 5

# C. 讀取自動 AI 開關
if "auto" in qp:
    init_auto = qp["auto"][0].lower() == "true"
else:
    init_auto = False

# 將經由 URL 驗證過的精神指引參數寫入記憶體
if "real_favs" not in st.session_state: st.session_state.real_favs = init_favs
if "real_refresh" not in st.session_state: st.session_state.real_refresh = init_refresh
if "ai_auto_run" not in st.session_state: st.session_state.ai_auto_run = init_auto
if "single_coin_ai" not in st.session_state: st.session_state.single_coin_ai = {}
if "last_coin_ai_time" not in st.session_state: st.session_state.last_coin_ai_time = {}
if "global_ai_cooldown" not in st.session_state: st.session_state.global_ai_cooldown = 0.0

# =====================================================================
# 4. 側邊欄控制台 (即時同步網址列，徹底拔除預設參數衝突)
# =====================================================================
st.sidebar.header("🌸 櫻之量化控制台")

api_key = None
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("🔑 已自動載入密鑰")
else:
    user_key = st.sidebar.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")
    if user_key: api_key = user_key

valid_defaults = [s for s in st.session_state.real_favs if s in all_available_cryptos]

chosen_favs = st.sidebar.multiselect(
    "🎯 自選監控區 (可滑鼠拖曳與調整自訂排序)",
    options=all_available_cryptos,
    default=valid_defaults if valid_defaults else [all_available_cryptos[0]]
)

chosen_refresh = st.sidebar.slider(
    "數據脈搏刷新頻率 (秒)", 
    min_value=3, max_value=15, 
    value=st.session_state.real_refresh
)

chosen_auto = st.sidebar.checkbox(
    "🤖 啟動 AI 全自動分時排隊調研",
    value=st.session_state.ai_auto_run
)

# 💡 核心同步鎖：只要有人工變更，立刻同步到 URL，F5 的天生剋星
if (chosen_favs != st.session_state.real_favs or 
    chosen_refresh != st.session_state.real_refresh or 
    chosen_auto != st.session_state.ai_auto_run):
    
    st.session_state.real_favs = chosen_favs
    st.session_state.real_refresh = chosen_refresh
    st.session_state.ai_auto_run = chosen_auto
    
    # 寫入舊版相容網址列
    url_favs_clean = [s.replace("/USDT", "") for s in chosen_favs]
    st.experimental_set_query_params(
        favs=url_favs_clean,
        refresh=[str(chosen_refresh)],
        auto=[str(chosen_auto).lower()]
    )
    st.rerun()

# 自動脈搏計時刷新器安全部署
st_autorefresh(interval=st.session_state.real_refresh * 1000, key="sakura_steel_heartbeat_v4")

# =====================================================================
# 5. Gemini 精準下單機會調研函數
# =====================================================================
def ask_gemini_single_coin(coin, price, change, vol_str):
    if not api_key: return "⚠️ 請先配置控制台的 Gemini API Key"
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    prompt = f"""
    你現在是精通加密貨幣主力大單資金流向與短線量化結構的頂級操盤專家。
    正在對指定自選幣進行個別調研：
    - 標的幣種：{coin}/USDT | 當前現價：{price} | 24h漲跌幅：{change}% | 24h總成交額：{vol_str}
    
    請用繁體中文給出極度精簡、一針見血的實戰報告：
    1. 【主力心理學】：拆解目前盤面背後最真實的「主力心理狀態」（洗盤吸籌、拉高出貨、動能突破、散戶踩踏）。
    2. 【下單機會精確提醒】：如果有明確的下單機會，請用【🔥 突發下單機會提醒】開頭給出具體多空方向與防守點！如果沒有，請提示觀望。
    """
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        data = response.json()
        if 'error' in data: 
            return f"❌ 頻率限制: {data['error'].get('message', '請等待下個週期重新排隊。')}"
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e: 
        return f"⚠️ 網路傳輸異常 ({e})"

# =====================================================================
# 6. 數據掃描中心 (100% 遵從自選排序、剔除無用路人代碼)
# =====================================================================
try:
    all_tickers = exchange.fetch_tickers()
except:
    st.rerun()

fav_data_list = []

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
# 7. 主畫面佈局 (正方形發光矩陣卡片艙)
# =====================================================================
st.title("🏹 CryptoHunter 智能雷達 (櫻之自選純淨艙)")
st.write(f"⏱ 數據脈搏更新時間：`{datetime.now().strftime('%H:%M:%S')}`")
st.markdown("---")

if fav_data_list:
    cols = st.columns(3)
    current_time = time.time()
    
    # 🎯 鋼鐵防爆盾邏輯：全自動開啟時，一整個重整週期「只允許更新一隻幣」，且與上一次任何請求必須間隔15秒以上！
    auto_api_triggered = False
    
    for idx, coin in enumerate(fav_data_list):
        with cols[idx % 3]:
            c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
            c_sign = "+" if coin['change'] >= 0 else ""
            
            # HTML 渲染奢華正方形卡片頂部
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
            
            # --- 雙模 AI 調研處理中心 ---
            if st.session_state.ai_auto_run:
                # 【全自動智慧排隊分時模式】
                last_update = st.session_state.last_coin_ai_time.get(coin['symbol'], 0.0)
                time_elapsed = current_time - last_update
                global_elapsed = current_time - st.session_state.global_ai_cooldown
                
                # 滿足單幣冷卻滿 300 秒，且全局間隔滿 15 秒，且本週期還沒放行過任何請求
                if time_elapsed > 300.0 and global_elapsed > 15.0 and not auto_api_triggered:
                    with st.spinner(f"🔄 自動分時排隊調研中：{coin['symbol']}..."):
                        res = ask_gemini_single_coin(coin['symbol'], coin['price'], coin['change'], coin['volume_str'])
                        if "❌" not in res and "⚠️" not in res:
                            st.session_state.single_coin_ai[coin['symbol']] = res
                            st.session_state.last_coin_ai_time[coin['symbol']] = current_time
                            st.session_state.global_ai_cooldown = current_time
                            auto_api_triggered = True # 鎖定本週期
                
                countdown = max(0, int(300 - time_elapsed))
                if countdown > 0:
                    st.caption(f"🤖 自動監控中... (防爆護盾剩餘 {countdown} 秒)")
                else:
                    st.caption("⏳ 已進入冷卻完畢隊列，等待分時排隊訊號...")
            else:
                # 【手動精確戰研模式】
                if st.button(f"⚡ 執行 {coin['symbol']} AI 戰研", key=f"btn_sakura_{coin['symbol']}", use_container_width=True):
                    with st.spinner(f"正在獨立調研 {coin['symbol']} 主力盤面心理..."):
                        res = ask_gemini_single_coin(coin['symbol'], coin['price'], coin['change'], coin['volume_str'])
                        st.session_state.single_coin_ai[coin['symbol']] = res
                        st.session_state.last_coin_ai_time[coin['symbol']] = current_time
                        st.session_state.global_ai_cooldown = current_time
                    st.rerun()
            
            # --- 持久化分析結果渲染 ---
            if coin['symbol'] in st.session_state.single_coin_ai:
                ai_text = st.session_state.single_coin_ai[coin['symbol']]
                if "下單機會" in ai_text or "🔥" in ai_text:
                    st.warning(ai_text)
                else:
                    st.info(ai_text)
            else:
                st.caption("💡 狀態：待機中。點擊按鈕或勾選全自動開始分析。")
                
            st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("💡 櫻之雷達待機中。請先在左側控制台勾選你想排列、監控的自選加密貨幣。")
