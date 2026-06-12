import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime
import requests

# =====================================================================
# 1. 網頁頂級配置與原創科技風 CSS 注入 (右側正方形，取消暗化)
# =====================================================================
st.set_page_config(
    page_title="CryptoHunter | 雙核完全體",
    layout="wide"
)

# 緩存鎖：儲存純文字報告，防止網頁自動刷新時重新呼叫 API 導致爆掉
if "cached_ai_report" not in st.session_state:
    st.session_state.cached_ai_report = ""
if "current_replay_coin" not in st.session_state:
    st.session_state.current_replay_coin = "SOL"

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3, h4 { color: #00FFCC !important; font-family: 'Courier New', monospace; }
    
    /* 右側主畫面：巨大正方形卡片樣式 */
    .square-card {
        background-color: #161B22;
        border: 2px solid #30363D;
        border-radius: 15px;
        padding: 25px;
        margin-bottom: 20px;
        min-height: 220px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .coin-title { font-size: 26px; font-weight: bold; color: #FFF; font-family: 'Courier New', monospace; }
    .coin-price { font-size: 32px; font-weight: bold; color: #00FF66; margin: 10px 0; }
    .coin-change { font-size: 20px; font-weight: bold; }
    
    /* 策略標籤樣式 */
    .trend-badge { 
        padding: 8px 12px; border-radius: 6px; font-weight: bold; font-size: 15px; text-align: center; margin-top: 10px;
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
# 3. 量化訊號與 AI 建議演算邏輯 (使用 gemini-2.5-flash 正式通道)
# =====================================================================
def get_strategy_signal(current, high, low):
    if not high or not low:
        return "⚪ 建議觀望 (數據不足)", "#888888"
    mid = (high + low) / 2
    if current > mid * 1.015:
        return "🟢 推薦開多 (突破多頭強勢區)", "#00FF66"
    elif current < mid * 0.985:
        return "🔴 推薦開空 (跌破空頭弱勢區)", "#FF3366"
    return "⚪ 建議觀望 (區間震盪盤整)", "#888888"

def ask_gemini_replay_analysis(api_key, coin, price, change, volume, high, low):
    if not api_key:
        return "⚠️ 請先在側邊欄最下方配置有效的 Gemini API Key 才能看報告喔！"
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    prompt = f"""
    你現在是精通加密貨幣『突發爆量/主力妖幣異動』的頂級短線量化操盤專家。
    正在對目前全網焦點爆量標的進行【實戰技術復盤】：
    - 標的幣種：{coin}/USDT | 當前現價：{price} | 24h漲跌幅：{change}% | 24h成交額：{volume} | 24h最高/最低價：{high} / {low}
    請用繁體中文給出極精簡、一針見血且極具實戰攻擊性的 2 句短評：
    1. 拆解該幣「突發爆量」背後的操盤手/主力心理狀態（是機構吸籌、主力拉高出貨、動能突破還是散戶恐慌踩踏）。
    2. 給出【下一個階段最具體的操作開盤方針與潛在埋伏點】，並附帶精準的止損/防守提示。
    """
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        data = response.json()
        if 'error' in data:
            return f"❌ Google 拒絕原因: {data['error'].get('message', '頻率超限或無效金鑰')}"
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"⚠️ 網絡傳輸異常 ({e})"

# =====================================================================
# 4. 側邊欄控制台 (純粹參數設定)
# =====================================================================
st.sidebar.header("⚙️ 獵手核心控制台")

# 🔑 API Key 讀取機制 (優先讀取 Secrets)
api_key = None
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("🔑 已從後台 Secrets 自動載入密鑰")
else:
    user_key = st.sidebar.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")
    if user_key: api_key = user_key

st.sidebar.markdown("---")

# 自選監控區設定
@st.cache_data(ttl=3600)
def get_all_usdt_symbols():
    try:
        markets = exchange.load_markets()
        return sorted([s for s in markets.keys() if s.endswith('/USDT') and ':' not in s])
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]

all_available_cryptos = get_all_usdt_symbols()
fav_cryptos = st.sidebar.multiselect("🎯 設定你的自選監控區", options=all_available_cryptos, default=[s for s in ["BTC/USDT", "ETH/USDT", "SOL/USDT"] if s in all_available_cryptos])
refresh_interval = st.sidebar.slider("數據脈搏刷新頻率 (秒)", min_value=3, max_value=15, value=5)

# =====================================================================
# 5. 數據獲取與全市場雷達掃描
# =====================================================================
st.title("🏹 CryptoHunter 雙核雷達智能儀表板")
st.markdown("---")

# 建立主畫面兩大區塊 (左 7 寬度放切換分頁，右 5 寬度放不變的大方塊看板)
col_left_tabs, col_right_main = st.columns([7, 5])

try:
    all_tickers = exchange.fetch_tickers()
except Exception as e:
    st.error(f"📡 交易所連線中斷，自動重試中... ({e})")
    time.sleep(2)
    st.rerun()

fav_data_list = []
volume_anomalies = []

# 全市場掃描與數據分流
for symbol, ticker in all_tickers.items():
    if not symbol.endswith('/USDT') or ':' in symbol: continue
    current_price = ticker['last']
    change_pct = ticker['percentage'] if ticker['percentage'] is not None else 0.0
    high_24h = ticker['high']
    low_24h = ticker['low']
    vol_base = ticker['baseVolume'] if ticker['baseVolume'] else 0
    vol_usdt = ticker['quoteVolume'] if ticker['quoteVolume'] else (vol_base * current_price)
    coin_clean = symbol.replace('/USDT', '')
    
    if symbol in fav_cryptos:
        sig_txt, sig_col = get_strategy_signal(current_price, high_24h, low_24h)
        fav_data_list.append({"symbol": coin_clean, "price": current_price, "change": change_pct, "signal_text": sig_txt, "signal_color": sig_col})
        
    if vol_usdt >= 10000000 and (change_pct > 5 or change_pct < -5):
        volume_anomalies.append({"symbol": coin_clean, "price": current_price, "change": change_pct, "volume_str": f"{vol_usdt / 1000000:.1f}M USDT", "volume_usdt": vol_usdt})

# 隨時追蹤要復盤的幣種行情
current_replay_target = st.session_state.current_replay_coin
for symbol, ticker in all_tickers.items():
    if symbol.replace('/USDT', '') == current_replay_target:
        vol_base = ticker['baseVolume'] if ticker['baseVolume'] else 0
        vol_usdt = ticker['quoteVolume'] if ticker['quoteVolume'] else (vol_base * ticker['last'])
        target_replay_data = {
            "symbol": current_replay_target,
            "price": ticker['last'],
            "change": ticker['percentage'] if ticker['percentage'] is not None else 0.0,
            "volume": f"{vol_usdt / 1000000:.2f}M USDT",
            "high": ticker['high'],
            "low": ticker['low']
        }
        break

# ---------------------------------------------------------------------
# 【左側窗口】：使用 st.tabs 實現切換時右側完全不被覆蓋的效果
# ---------------------------------------------------------------------
with col_left_tabs:
    # 🧠 把「分析自選」和「復盤」綁在第一個分頁，把「異常提醒」獨立在第二個分頁
    tab_analysis, tab_anomaly = st.tabs(["📊 自選戰研與 AI 建議", "🚨 突發爆量提醒"])
    
    # 🟢 分頁一：原本上面的東西全部保留並排版乾淨
    with tab_analysis:
        st.subheader("🎯 自選幣核心數據報告")
        st.write(f"⏱ 數據更新時間：`{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
        st.markdown("---")
        
        if fav_data_list:
            for coin in fav_data_list:
                c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                c_sign = "+" if coin['change'] >= 0 else ""
                # 百分比格式化處理，解決一長串小數點的 Bug
                st.markdown(f"**🪙 {coin['symbol']}/USDT** | 現價: `${coin['price']:,}` | 漲跌: <span style='color:{c_color}; font-weight:bold;'>{c_sign}{coin['change']:.2f}%</span>", unsafe_allow_html=True)
                st.write(f"量化狀態: {coin['signal_text']}")
                st.markdown("---")
        
        # 🔬 復盤研究室區塊 (完美嵌在分頁一下方)
        st.subheader("🔬 AI 獵手單次策略復盤室")
        col_in, col_go = st.columns([8, 4])
        with col_in:
            replay_coin = st.text_input("輸入要復盤的幣種代號", value=st.session_state.current_replay_coin).strip().upper()
        with col_go:
            st.write("")
            st.write("")
            if st.button("🏹 啟動 AI 獵手單次復盤鑑定", use_container_width=True):
                st.session_state.current_replay_coin = replay_coin
                if target_replay_data:
                    with st.spinner(f"正在對 {replay_coin}/USDT 進行量化結構調研..."):
                        st.session_state.cached_ai_report = ask_gemini_replay_analysis(
                            api_key, target_replay_data['symbol'], target_replay_data['price'],
                            target_replay_data['change'], target_replay_data['volume'],
                            target_replay_data['high'], target_replay_data['low']
                        )
                else:
                    st.session_state.cached_ai_report = f"⚠️ 找不到 {replay_coin} 的行情數據。"
                    
        if st.session_state.cached_ai_report:
            st.error(f"⚔️ **AI 實戰復盤報告 ({st.session_state.current_replay_coin}):**\n\n{st.session_state.cached_ai_report}")

    # 🔴 分頁二：移過來的爆量異動提醒窗口
    with tab_anomaly:
        st.subheader("🚨 全網【突發爆量異常】提醒")
        st.caption("🔥 自動鎖定全網 24h 成交額 > 10M 且波動 > 5% 的黑馬焦點")
        st.markdown("---")
        
        volume_anomalies = sorted(volume_anomalies, key=lambda x: x['volume_usdt'], reverse=True)
        if volume_anomalies:
            for coin in volume_anomalies[:12]:
                c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                c_sign = "+" if coin['change'] >= 0 else ""
                st.markdown(f"**🔥 爆量: {coin['symbol']}** | <span style='color:{c_color}; font-weight:bold;'>{c_sign}{coin['change']:.2f}%</span>", unsafe_allow_html=True)
                st.write(f"現價: `${coin['price']:,}` | 24h總量: `{coin['volume_str']}`")
                st.markdown("---")
        else:
            st.success("🔍 全網目前波動穩定，尚未偵測到暴動幣。")

# ---------------------------------------------------------------------
# 【右側主畫面】：你最愛的經典巨大正方形卡片看板 (永遠直觀跳動、不被覆蓋)
# ---------------------------------------------------------------------
with col_right_main:
    st.subheader("📊 自選行情看板")
    st.markdown("---")
    
    if fav_data_list:
        fav_cols = st.columns(2)
        for idx, coin in enumerate(fav_data_list):
            target_col = fav_cols[idx % 2]
            with target_col:
                c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                c_sign = "+" if coin['change'] >= 0 else ""
                
                st.markdown(f"""
                    <div class="square-card">
                        <div>
                            <div class="coin-title">🪙 {coin['symbol']}/USDT</div>
                            <div class="coin-price">${coin['price']:,}</div>
                            <div class="coin-change" style="color: {c_color};">{c_sign}{coin['change']:.2f}%</div>
                        </div>
                        <div class="trend-badge" style="background-color: {coin['signal_color']}22; color: {coin['signal_color']}; border: 1px solid {coin['signal_color']};">
                            {coin['signal_text']}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("請在左側邊欄勾選要監控的自選幣！")

# =====================================================================
# 6. 非阻塞式高效自動刷新
# =====================================================================
time.sleep(refresh_interval)
st.rerun()
