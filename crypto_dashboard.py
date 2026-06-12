import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime

# =====================================================================
# 1. 網頁頂級配置與原創科技風 CSS 注入 (右側正方形，取消暗化)
# =====================================================================
st.set_page_config(
    page_title="CryptoHunter | 完美側邊版",
    layout="wide"
)

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
# 3. 側邊欄控制台 (把切換窗口完美做在刷新頻率與自選區那邊)
# =====================================================================
st.sidebar.header("⚙️ 獵手核心控制台")

# 🧭 【你的關鍵意見】：切換功能放在側邊欄控制台
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

# =====================================================================
# 4. 量化訊號演算邏輯 (0 API 消耗，永不爆 Quota)
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

# =====================================================================
# 5. 主畫面經典佈局分配 (左 7 寬度放切換面板，右 5 寬度放你最愛的正方形看板)
# =====================================================================
st.title("🏹 CryptoHunter 雙核雷達智能儀表板")
st.markdown("---")

col_left_panel, col_right_main = st.columns([7, 5])

# 獲取最新行情
try:
    all_tickers = exchange.fetch_tickers()
except Exception as e:
    st.error(f"📡 交易所數據連線異常，正在自動重新對接... ({e})")
    time.sleep(2)
    st.rerun()

fav_data_list = []
volume_anomalies = []

# 全市場數據一輪掃描與分流
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

# ---------------------------------------------------------------------
# 【左側窗口】：由側邊欄控制台的 Radio 按鈕觸發，切換時右側正方形完全不動
# ---------------------------------------------------------------------
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
                
                # 自動化量化策略建議 (不需手動輸入或點擊按鈕，0 API 消耗)
                if "開多" in coin['signal_text']:
                    st.success(f"🟢 【AI 戰略建議】多頭主力正在強力吸籌突擊。目前價格已有效站穩多頭強勢區，開盤上方動能充足，建議順勢持多或埋伏突破，防守點建立在 24h 均價線。")
                elif "開空" in coin['signal_text']:
                    st.error(f"🔴 【AI 戰略建議】空頭主力正在大單出貨或產生散戶踩踏。目前價格已跌破弱勢支撐，多頭防線失守，短線開盤建議順勢看空或等待下方前低支撐止跌，防守點建立在區間中軸。")
                else:
                    st.info(f"⚪ 該標的目前正處於安全震盪區間內，量化訊號建議觀望，多空主力心理處於均衡洗盤期，無明顯方向，暫不開盤，保持待命防禦。")
                st.markdown("---")
        else:
            st.info("請在左側邊欄多勾選幾個自選幣！")

    elif page_view == "🚨 突發爆量提醒":
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
            st.success("🔍 全網目前波動穩定，尚未偵測到暴動幣。")

# ---------------------------------------------------------------------
# 【右側主畫面】：你最愛的經典巨大正方形卡片看板 (永遠死守右側跳動行情)
# ---------------------------------------------------------------------
with col_right_main:
    st.subheader("📊 自選行情看板")
    st.markdown("---")
    
    if fav_data_list:
        # 兩欄並列巨大正方形
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
        st.info("請在左側邊欄勾選監控幣種！")

# =====================================================================
# 6. 非阻塞式自動脈搏刷新
# =====================================================================
time.sleep(refresh_interval)
st.rerun()
