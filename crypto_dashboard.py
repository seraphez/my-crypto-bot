import streamlit as st
import ccxt
import pandas as pd
from datetime import datetime

# =====================================================================
# 1. 網頁頂級配置與黑客風 CSS 注入 (完全消滅暗化，還原高亮正方形)
# =====================================================================
st.set_page_config(
    page_title="CryptoHunter | 完美分流完全體",
    layout="wide"
)

# 強制拔除 Streamlit 計時刷新時的半透明暗化遮罩（防止畫面變暗閃爍）
st.markdown("""
    <style>
    div[data-testid="stForm"] { background-color: transparent !important; }
    .stApp div[data-testid="stVerticalBlock"] > div { opacity: 1 !important; }
    .stApp { background-color: #0E1117; }
    h1, h2, h3, h4 { color: #00FFCC !important; font-family: 'Courier New', monospace; }
    
    /* 巨大正方形卡片樣式 */
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
# 3. 側邊欄控制台 (結合你的 radio 控制器與音量拉桿)
# =====================================================================
st.sidebar.header("⚙️ 獵手核心控制台")

# 🧭 側邊欄單選分頁切換器
page_view = st.sidebar.radio(
    "🧭 請選擇左側顯示面板",
    ["📊 自選戰研與 AI 建議", "🚨 突發爆量提醒"],
    index=0
)

st.sidebar.markdown("---")

# 獲取全市場 USDT 名單
@st.cache_data(ttl=3600)
def get_all_usdt_symbols():
    try:
        markets = exchange.load_markets()
        return sorted([s for s in markets.keys() if s.endswith('/USDT') and ':' not in s])
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]

all_available_cryptos = get_all_usdt_symbols()

# 設定你的自選監控區
fav_cryptos = st.sidebar.multiselect(
    "🎯 設定你的自選監控區",
    options=all_available_cryptos,
    default=[s for s in ["BTC/USDT", "ETH/USDT", "SOL/USDT"] if s in all_available_cryptos]
)

# 數據脈搏刷新頻率
refresh_interval = st.sidebar.slider("數據脈搏刷新頻率 (秒)", min_value=3, max_value=15, value=5)

# 🔊 警報音量控制器
alert_volume = st.sidebar.slider("🔊 雷達警報音量", min_value=0.0, max_value=1.0, value=0.5, step=0.1)

# =====================================================================
# 4. 量化訊號演算邏輯
# =====================================================================
def get_strategy_signal(current, high, low):
    if not high or not low: return "⚪ 建議觀望 (數據不足)", "#888888"
    mid = (high + low) / 2
    if current > mid * 1.015: return "🟢 推薦開多 (突破多頭強勢區)", "#00FF66"
    elif current < mid * 0.985: return "🔴 推薦開空 (跌破空頭弱勢區)", "#FF3366"
    return "⚪ 建議觀望 (區間震盪盤整)", "#888888"

# =====================================================================
# 5. 數據獲取與全市場掃描
# =====================================================================
try:
    all_tickers = exchange.fetch_tickers()
except:
    st.rerun()

fav_data_list = []
volume_anomalies = []

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
        
    # 雷達標準：24h 成交額 > 10M 且 漲跌幅絕對值 > 5%
    if vol_usdt >= 10000000 and (change_pct > 5 or change_pct < -5):
        volume_anomalies.append({"symbol": coin_clean, "price": current_price, "change": change_pct, "volume_str": f"{vol_usdt / 1000000:.1f}M USDT", "volume_usdt": vol_usdt})

# =====================================================================
# 6. 主畫面雙欄排版 (左 6 窗口獨立切換，右 6 窗口永遠常駐)
# =====================================================================
col_left_panel, col_right_main = st.columns([6, 6])

# --- 【左側窗口】：嚴格分流，切換時另一方的內容會完全清空消失，絕不重疊 ---
with col_left_panel:
    if page_view == "📊 自選戰研與 AI 建議":
        st.subheader("📊 自選幣核心戰研建議")
        st.caption("⚡ 針對你的自選監控標的，秒級解構主力狀態與實戰策略")
        st.write(f"⏱ 數據更新時間：`{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
        st.markdown("---")
        
        if fav_data_list:
            for coin in fav_data_list:
                c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                c_sign = "+" if coin['change'] >= 0 else ""
                st.markdown(f"### 🪙 {coin['symbol']} 戰略報告")
                st.markdown(f"現價: `${coin['price']:,}` | 漲跌幅: <span style='color:{c_color}; font-weight:bold;'>{c_sign}{coin['change']:.2f}%</span>", unsafe_allow_html=True)
                
                if "開多" in coin['signal_text']:
                    st.success(f"🟢 【AI 戰略建議】多頭主力正在強力吸籌突擊。目前價格已有效站穩多頭強勢區，建議順勢持多或埋伏突破。")
                elif "開空" in coin['signal_text']:
                    st.error(f"🔴 【AI 戰略建議】空頭主力正在大單出貨。目前價格已跌破弱勢支撐，多頭防線失守，短線建議順勢看空。")
                else:
                    st.info(f"⚪ 該標的目前正處於安全震盪區間內，量化訊號建議觀望，主力洗盤期方向不明，暫不開盤。")
                st.markdown("---")
        else:
            st.info("請在左側邊欄多勾選幾個自選幣！")

    elif page_view == "🚨 突發爆量提醒":
        # 當切換到這裡，原本上面的「自選戰研數據」會在這裡被完全清除，絕不發生任何殘留或重疊
        st.subheader("🚨 全網【突發爆量異常】提醒窗口")
        st.caption("🔥 自動鎖定全網 24h 成交額 > 10M 且波動 > 5% 的黑馬焦點")
        st.markdown("---")
        
        volume_anomalies = sorted(volume_anomalies, key=lambda x: x['volume_usdt'], reverse=True)
        if volume_anomalies:
            for coin in volume_anomalies[:12]:
                c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                c_sign = "+" if coin['change'] >= 0 else ""
                st.markdown(f"**🔥 爆量異動: {coin['symbol']}** | <span style='color:{c_color}; font-weight:bold;'>{c_sign}{coin['change']:.2f}%</span>", unsafe_allow_html=True)
                st.write(f"現價: `${coin['price']:,}` | 24h總成交額: `{coin['volume_str']}`")
                st.markdown("---")
        else:
            st.success("🔍 全網目前波動穩定，尚未偵測到爆量標的。")

# --- 【右側窗口】：巨大的正方形自選行情卡片常駐區，永遠在右邊高亮 ---
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
        st.info("請在左側邊欄多勾選監控幣種！")

# =====================================================================
# 7. 引入計時器重繪插件 (一秒解決睡眠時畫面變暗閃爍的 Bug)
# =====================================================================
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=refresh_interval * 1000, key="crypto_hunter_heartbeat")
