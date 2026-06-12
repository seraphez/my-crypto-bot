import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime
import requests

# =====================================================================
# 1. 網頁頂級配置與記憶體狀態初始化 (防爆 Quota 安全護盾)
# =====================================================================
st.set_page_config(
    page_title="CryptoHunter | 雙核終極儀表板",
    page_icon="🏹",
    layout="wide"
)

# 核心防連發狀態鎖
if "ai_triggered" not in st.session_state:
    st.session_state.ai_triggered = False
if "last_replay_coin" not in st.session_state:
    st.session_state.last_replay_coin = ""
if "cached_ai_report" not in st.session_state:
    st.session_state.cached_ai_report = ""

# =====================================================================
# 2. 交易所初始化
# =====================================================================
@st.cache_resource
def get_exchange():
    return ccxt.okx()

exchange = get_exchange()

# =====================================================================
# 3. 側邊欄控制台 (設定區)
# =====================================================================
st.sidebar.header("⚙️ 獵手控制台")

# 🔑 API Key 輸入框
api_key = st.sidebar.text_input("Gemini API Key", type="password", placeholder="請輸入 AIzaSy... 金鑰")

st.sidebar.markdown("---")

# 獲取全市場 USDT 現貨名單
@st.cache_data(ttl=3600)
def get_all_usdt_symbols():
    try:
        markets = exchange.load_markets()
        symbols = [symbol for symbol in markets.keys() if symbol.endswith('/USDT') and ':' not in symbol]
        return sorted(symbols)
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]

all_available_cryptos = get_all_usdt_symbols()

# 自選監控區設定
fav_cryptos = st.sidebar.multiselect(
    "🎯 設定你的自選監控區",
    options=all_available_cryptos,
    default=[s for s in ["BTC/USDT", "ETH/USDT", "SOL/USDT"] if s in all_available_cryptos]
)

refresh_interval = st.sidebar.slider("數據脈搏刷新頻率 (秒)", min_value=5, max_value=20, value=10)

# =====================================================================
# 4. 量化策略與 AI 復盤核心邏輯 (HTTP 直連技術)
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

def ask_gemini_replay_analysis(coin, price, change, volume, high, low):
    if not api_key:
        return "⚠️ 請先在左側邊欄輸入有效的 Gemini API Key 才能看報告喔！"
    
    # 使用官方最相容穩定的 gemini-2.5-flash v1 通道
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    prompt = f"""
    你現在是精通加密貨幣『突發爆量/主力妖幣異動』的頂級短線量化操盤專家。
    正在對目前全網焦點爆量標的進行【實戰技術復盤】：
    - 標的幣種：{coin}/USDT
    - 當前現價：{price}
    - 24h漲跌幅：{change}%
    - 24h成交額：{volume}
    - 24h最高/最低價：{high} / {low}
    
    請用繁體中文給出極精簡、一針見血且極具實戰攻擊性的 2 句短評：
    1. 拆解該幣「突發爆量」背後的操盤手/主力心理狀態（是機構吸籌、主力拉高出貨、動能突破還是散戶恐慌踩踏）。
    2. 給出【下一個階段最具體的操作開盤方針與潛在埋伏點】，並附帶精準的止損/防守提示。
    """
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        data = response.json()
        if 'error' in data:
            err_msg = data['error'].get('message', '未知錯誤')
            if "API key not valid" in err_msg: return "❌ 【API Key 錯誤】請檢查輸入的金鑰。"
            if "Resource has been exhausted" in err_msg: return "⏳ 【頻率超限】免費額度已滿，請等待 15 秒後再次點擊復盤。"
            return f"❌ Google 拒絕原因: {err_msg}"
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"⚠️ 網路傳輸異常 ({e})"

# =====================================================================
# 5. 主畫面經典佈局 (左 7 寬度自選與復盤，右 5 寬度全網爆量雷達)
# =====================================================================
st.title("🏹 CryptoHunter 雙核自選監控 ＆ 全網爆量突擊雷達")
st.markdown("---")

col_fav, col_radar = st.columns([7, 5])

# 獲取最新即時數據
try:
    all_tickers = exchange.fetch_tickers()
except Exception as e:
    st.error(f"📡 交易所連線中斷，自動重試中... ({e})")
    time.sleep(2)
    st.rerun()

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
    
    # A. 自選幣分流
    if symbol in fav_cryptos:
        signal_text, signal_color = get_strategy_signal(current_price, high_24h, low_24h)
        fav_data_list.append({
            "symbol": coin_clean,
            "price": current_price,
            "change": change_pct,
            "signal_text": signal_text,
            "signal_color": signal_color
        })
        
    # B. 全網爆量異動雷達分流 (門檻：成交額 > 10M USDT 且波動 > 5%)
    if vol_usdt_24h >= 10000000 and (change_pct > 5 or change_pct < -5):
        volume_anomalies.append({
            "symbol": coin_clean,
            "price": current_price,
            "change": change_pct,
            "volume_usdt": vol_usdt_24h,
            "volume_str": f"{vol_usdt_24h / 1000000:.1f}M USDT"
        })
        
    # C. 捕獲目前正在準備復盤的幣種即時行情
    current_target = st.session_state.last_replay_coin if st.session_state.last_replay_coin else "SOL"
    if coin_clean == current_target:
        target_replay_data = {
            "symbol": coin_clean,
            "price": current_price,
            "change": change_pct,
            "volume": f"{vol_usdt_24h / 1000000:.2f}M USDT",
            "high": high_24h,
            "low": low_24h
        }

# ---------------------------------------------------------------------
# 【左側渲染】：自選幣核心監控區 + 復盤研究室
# ---------------------------------------------------------------------
with col_fav:
    st.subheader("🎯 自選幣核心監控區")
    st.write(f"⏱ 同步時間：`{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
    
    if fav_data_list:
        for coin in fav_data_list:
            c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
            c_sign = "+" if coin['change'] >= 0 else ""
            
            st.markdown(f"### 🪙 {coin['symbol']}/USDT")
            st.markdown(f"**現價：** `${coin['price']:,}` | **漲跌：** <span style='color:{c_color}; font-weight:bold;'>{c_sign}{coin['change']:.2% if coin['change'] < 1 else f'{coin['change']:.2f}%'}</span>", unsafe_allow_html=True)
            st.markdown(f"**系統訊號：** <span style='color:{coin['signal_color']}; font-weight:bold;'>{coin['signal_text']}</span>", unsafe_allow_html=True)
            st.markdown("---")
    else:
        st.info("請在左側邊欄勾選要監控的自選幣！")

    # 【完整加在左區下方】AI 獵手單次策略復盤室
    st.subheader("🔬 AI 獵手單次策略復盤室")
    col_input, col_btn = st.columns([8, 4])
    with col_input:
        replay_coin = st.text_input("輸入要復盤的幣種代號 (例如: SOL, DOGE, BTC)", value="SOL").strip().upper()
    with col_btn:
        st.write("") # 垂直對齊排版
        st.write("")
        if st.button("🏹 啟動 AI 獵手單次復盤鑑定", use_container_width=True):
            st.session_state.ai_triggered = True
            st.session_state.last_replay_coin = replay_coin
            st.rerun() # 點擊立刻切換狀態重繪，防止卡頓

    # 執行 AI 單次點擊發送邏輯 (防爆安全網)
    if st.session_state.ai_triggered:
        st.session_state.ai_triggered = False # 進入後立刻抹除狀態，防止 10 秒刷新時連發呼叫！
        if target_replay_data:
            with st.spinner(f"正在對 {target_replay_data['symbol']}/USDT 進行量化結構調研..."):
                report_text = ask_gemini_replay_analysis(
                    target_replay_data['symbol'], target_replay_data['price'],
                    target_replay_data['change'], target_replay_data['volume'],
                    target_replay_data['high'], target_replay_data['low']
                )
                st.session_state.cached_ai_report = report_text
        else:
            st.session_state.cached_ai_report = f"⚠️ 找不到 {replay_coin} 的即時數據，請確認代碼是否輸入正確。"

    # 顯示持久化緩存報告 (即使網頁自動重新整理，報告也不會消失或重送請求)
    if st.session_state.cached_ai_report:
        st.error(f"⚔️ **AI 實戰復盤報告 ({st.session_state.last_replay_coin if st.session_state.last_replay_coin else 'SOL'}):**\n\n{st.session_state.cached_ai_report}")

# ---------------------------------------------------------------------
# 【右側渲染】：全網【突發爆量異常】提醒窗口 (原生乾淨排版)
# ---------------------------------------------------------------------
with col_radar:
    st.subheader("🚨 全網【突發爆量異常】提醒窗口")
    st.caption("🔥 自動鎖定 24h 成交額 > 10M 且波動 > 5% 的全網異動標的")
    st.write("📡 *雷達掃描狀態：* `正常監聽全網...`")
    st.markdown("---")
    
    volume_anomalies = sorted(volume_anomalies, key=lambda x: x['volume_usdt'], reverse=True)
    if volume_anomalies:
        for coin in volume_anomalies[:12]: # 最多拉出前 12 名最瘋狂的暴動幣，保持排版整潔
            c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
            c_sign = "+" if coin['change'] >= 0 else ""
            
            st.markdown(f"**🔥 爆量: {coin['symbol']}** | <span style='color:{c_color}; font-weight:bold;'>{c_sign}{coin['change']:.2f}%</span>", unsafe_allow_html=True)
            st.write(f"現價: `${coin['price']:,}` | 24h成交額: `{coin['volume_str']}`")
            st.markdown("---")
    else:
        st.success("🔍 全網目前風平浪靜，尚未偵測到爆量妖幣。")

# =====================================================================
# 8. 終極非阻塞式脈搏刷新 (取代會卡死的 while True)
# =====================================================================
time.sleep(refresh_interval)
st.rerun()
