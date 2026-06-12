import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime
import requests

# =====================================================================
# 1. 網頁頂級配置
# =====================================================================
st.set_page_config(
    page_title="CryptoHunter | 雙核雷達儀表板",
    page_icon="🏹",
    layout="wide"
)

# 記憶體狀態初始化（核心防禦：防止按鈕連發導致 API 額度爆掉）
if "ai_triggered" not in st.session_state:
    st.session_state.ai_triggered = False
if "last_replay_coin" not in st.session_state:
    st.session_state.last_replay_coin = ""

# =====================================================================
# 2. 注入黑客科技風 CSS 樣式
# =====================================================================
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3, h4 { color: #00FFCC !important; font-family: 'Courier New', monospace; }
    
    /* 自選幣巨大正方形卡片 */
    .square-card {
        background-color: #161B22;
        border: 2px solid #30363D;
        border-radius: 15px;
        padding: 25px;
        margin-bottom: 15px;
        min-height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 8px 16px rgba(0,0,0,0.5);
    }
    
    /* 爆量警告卡片 */
    .volume-anomaly-card {
        background-color: #1A1C23;
        border: 2px solid #FF9900;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 12px;
        box-shadow: 0 0 12px rgba(255, 153, 0, 0.2);
    }
    
    .coin-title { font-size: 24px; font-weight: bold; color: #FFF; font-family: 'Courier New', monospace; }
    .coin-price { font-size: 28px; font-weight: bold; color: #00FF66; margin: 5px 0; }
    .coin-vol { font-size: 15px; color: #FF9900; font-weight: bold; }
    .coin-change { font-size: 18px; font-weight: bold; }
    
    .trend-badge { 
        padding: 6px 10px; border-radius: 6px; font-weight: bold; font-size: 14px; text-align: center; margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏹 CryptoHunter 雙核自選監控 ＆ 全網爆量突擊雷達")

# =====================================================================
# 3. 交易所初始化
# =====================================================================
@st.cache_resource
def get_exchange():
    return ccxt.okx()

exchange = get_exchange()

# =====================================================================
# 4. 側邊欄控制台
# =====================================================================
st.sidebar.header("⚙️ 獵手控制台")

if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("🔑 已從後台 Secrets 自動載入密鑰")
else:
    st.sidebar.markdown("### 🔑 認證：請輸入 Gemini API Key")
    GEMINI_API_KEY = st.sidebar.text_input(
        "請貼上你的 API Key：", 
        type="password", 
        placeholder="AI Studio 申請的 AIzaSy..."
    )

st.sidebar.markdown("---")

# 獲取全市場 USDT 名單
@st.cache_data(ttl=3600)
def get_all_usdt_symbols():
    try:
        markets = exchange.load_markets()
        symbols = [symbol for symbol in markets.keys() if symbol.endswith('/USDT') and ':' not in symbol]
        return sorted(symbols)
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]

all_available_cryptos = get_all_usdt_symbols()

# 【完整保留】自選監控區設定
fav_cryptos = st.sidebar.multiselect(
    "🎯 設定你的自選監控區（可打字搜尋）",
    options=all_available_cryptos,
    default=[s for s in ["BTC/USDT", "ETH/USDT", "SOL/USDT"] if s in all_available_cryptos]
)

refresh_interval = st.sidebar.slider("數據脈搏刷新頻率 (秒)", min_value=5, max_value=20, value=8)

# =====================================================================
# 5. AI 單次復盤鑑定核心邏輯
# =====================================================================
def ask_gemini_replay_analysis(coin, price, change, volume, high, low):
    if not GEMINI_API_KEY:
        return "⚠️ 請先在左側邊欄輸入有效的 Gemini API Key 才能看報告喔！"
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    你現在是精通加密貨幣『突發爆量/主力妖幣異動』的頂級短線量化操盤專家。
    正在對目前全網焦點爆量標的進行【實戰技術復盤】：
    - 標的幣種：{coin}/USDT
    - 當前現價：{price}
    - 24h漲跌幅：{change}%
    - 24h成交額：{volume}
    - 24h最高/最低價：{high} / {low}
    
    請用繁體中文給出極精簡、一針見血且極具實戰攻擊性的 2 句短評：
    1. 拆解該幣「突發爆量」背後的操盤手/主力心理狀態（是機構吸籌、主力拉高出貨、動能突破還是散戶踩踏）。
    2. 給出【下一個階段最具體的操作開盤方針與潛在埋伏點】，並附帶精準的止損/防守提示。
    """
        
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        data = response.json()
        
        if 'error' in data:
            err_msg = data['error'].get('message', '未知錯誤')
            if "API key not valid" in err_msg:
                return "❌ 【API Key 錯誤】請檢查左側輸入的金鑰。"
            elif "Resource has been exhausted" in err_msg:
                return "⏳ 【頻率超限】免費額度已滿，請等待 15 秒後再次點擊復盤。"
            return f"❌ Google 拒絕原因: {err_msg}"
            
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"⚠️ 網路傳輸異常 ({e})"

def get_strategy_signal(current, high, low):
    if not high or not low:
        return "⚪ 建議觀望 (數據不足)", "#888888"
    mid = (high + low) / 2
    if current > mid * 1.015:
        return "🟢 推薦開多 (突破多頭強勢區)", "#00FF66"
    elif current < mid * 0.985:
        return "🔴 推薦開空 (跌破空頭弱勢區)", "#FF3366"
    return "⚪ 建議觀望 (區間震盪盤整)", "#888888"

# =====================================================================
# 6. 主畫面佈局（左 7 寬度放自選方塊，右 5 寬度放獨立爆量異常提醒窗口）
# =====================================================================
col_fav, col_radar = st.columns([7, 5])

with col_fav:
    st.subheader("🎯 自選幣核心監控區")
    fav_placeholder = st.empty()

with col_radar:
    st.subheader("🚨 全網【突發爆量異常】提醒窗口")
    st.caption("🔥 自動鎖定 24h 成交額 > 10M 且波動 > 5% 的全網異動標的")
    radar_placeholder = st.empty()

# 佈局中下方：獨立的復盤研究室窗口
st.markdown("---")
st.subheader("🔬 AI 獵手單次策略復盤室")
col_input, col_btn = st.columns([8, 4])
with col_input:
    replay_coin = st.text_input("輸入要復盤的幣種代號（例如: SOL, DOGE, BTC）", value="SOL").strip().upper()
with col_btn:
    st.write(" ") # 換行對齊
    st.write(" ") 
    btn_replay = st.button("🏹 啟動 AI 獵手單次復盤鑑定", use_container_width=True)

# 按鈕觸發鎖定
if btn_replay:
    st.session_state.ai_triggered = True
    st.session_state.last_replay_coin = replay_coin

replay_placeholder = st.container()

# =====================================================================
# 7. 主數據無限循環監控區
# =====================================================================
while True:
    try:
        all_tickers = exchange.fetch_tickers()
        fav_data_list = []
        volume_anomalies = []
        target_replay_data = None
        
        # 遍歷全市場進行篩選與分流
        for symbol, ticker in all_tickers.items():
            if not symbol.endswith('/USDT') or ':' in symbol:
                continue
                
            current_price = ticker['last']
            change_pct = ticker['percentage'] if ticker['percentage'] is not None else 0.0
            high_24h = ticker['high']
            low_24h = ticker['low']
            vol_base_24h = ticker['baseVolume'] if ticker['baseVolume'] else 0
            vol_usdt_24h = ticker['quoteVolume'] if ticker['quoteVolume'] else (vol_base_24h * current_price)
            
            coin_clean = symbol.replace('/USDT', '')
            
            # A. 收集自選幣數據
            if symbol in fav_cryptos:
                signal_text, signal_color = get_strategy_signal(current_price, high_24h, low_24h)
                fav_data_list.append({
                    "symbol": coin_clean,
                    "price": current_price,
                    "change": change_pct,
                    "signal_text": signal_text,
                    "signal_color": signal_color
                })
                
            # B. 收集全網爆量異常幣數據（門檻：>10M USDT 且波動 >5%）
            if vol_usdt_24h >= 10000000 and (change_pct > 5 or change_pct < -5):
                volume_anomalies.append({
                    "symbol": coin_clean,
                    "price": current_price,
                    "change": change_pct,
                    "volume_usdt": vol_usdt_24h,
                    "volume_str": f"{vol_usdt_24h / 1000000:.1f}M USDT"
                })
                
            # C. 隨時捕獲目前用戶點擊要復盤的即時幣種行情
            if coin_clean == st.session_state.last_replay_coin or (not st.session_state.last_replay_coin and coin_clean == replay_coin):
                target_replay_data = {
                    "symbol": coin_clean,
                    "price": current_price,
                    "change": change_pct,
                    "volume": f"{vol_usdt_24h / 1000000:.2f}M USDT",
                    "high": high_24h,
                    "low": low_24h
                }

        # -------------------------------------------------------------
        # 渲染左側：自選幣大方塊（不含 AI，0 消耗額度）
        # -------------------------------------------------------------
        with fav_placeholder.container():
            st.write(f"⏱ *同步時間：* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
            if fav_data_list:
                fav_cols = st.columns(2) # 兩列佈局大方塊
                for idx, coin in enumerate(fav_data_list):
                    tgt_col = fav_cols[idx % 2]
                    with tgt_col:
                        c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                        c_sign = "+" if coin['change'] >= 0 else ""
                        st.markdown(f"""
                            <div class="square-card">
                                <div>
                                    <div class="coin-title">🪙 {coin['symbol']}/USDT</div>
                                    <div class="coin-price">${coin['price']:,}</div>
                                    <div class="coin-change" style="color: {c_color};">{c_sign}{coin['change']}%</div>
                                </div>
                                <div class="trend-badge" style="background-color: {coin['signal_color']}22; color: {coin['signal_color']}; border: 1px solid {coin['signal_color']};">
                                    {coin['signal_text']}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("請在左側邊欄設定自選監控幣種！")

        # -------------------------------------------------------------
        # 渲染右側：全網突發爆量提醒窗口（獨立滾動，不疊加方塊）
        # -------------------------------------------------------------
        volume_anomalies = sorted(volume_anomalies, key=lambda x: x['volume_usdt'], reverse=True)
        with radar_placeholder.container():
            st.write(f"📡 *雷達掃描狀態：* `正常監聽全網...`")
            if volume_anomalies:
                for coin in volume_anomalies:
                    c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                    c_sign = "+" if coin['change'] >= 0 else ""
                    st.markdown(f"""
                        <div class="volume-anomaly-card">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span class="coin-title" style="font-size:18px; color:#FF9900;">🔥 爆量: {coin['symbol']}</span>
                                <span class="coin-change" style="color: {c_color};">{c_sign}{coin['change']}%</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px;">
                                <span style="color:#FFF; font-size:16px;">${coin['price']:,}</span>
                                <span class="coin-vol" style="font-size:14px;">量: {coin['volume_str']}</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("🔍 全網目前無突發暴動幣種，波動正常。")

        # -------------------------------------------------------------
        # 處理下方的 AI 單次鎖定復盤（按一次、跑一次、立刻解鎖）
        # -------------------------------------------------------------
        if st.session_state.ai_triggered:
            with replay_placeholder:
                if target_replay_data:
                    st.info(f"📊 **正在針對爆量標的 {target_replay_data['symbol']}/USDT 進行主力結構鑑定...**")
                    with st.spinner("⚔️ AI 獵手正在剖析主力心理..."):
                        ai_report = ask_gemini_replay_analysis(
                            target_replay_data['symbol'], target_replay_data['price'],
                            target_replay_data['change'], target_replay_data['volume'],
                            target_replay_data['high'], target_replay_data['low']
                        )
                        st.error(f"⚔️ **AI 實戰復盤報告 ({target_replay_data['symbol']}):**\n{ai_report}")
                else:
                    st.warning(f"⚠️ 在市場上找不到 `{replay_coin}` 的即時數據，請確認代碼是否輸入正確。")
            
            # 🔒 終極解除連發鎖：執行完立刻歸零，下一輪迴圈絕不再重複調用！
            st.session_state.ai_triggered = False

        # 雷達與方塊的整體冷卻時間
        time.sleep(refresh_interval)
        
    except Exception as e:
        time.sleep(5)
