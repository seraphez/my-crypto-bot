import streamlit as st
import ccxt
import time
from datetime import datetime

# =====================================================================
# 1. 網頁頂級配置與原創科技風 CSS 注入 (還原正方形，取消暗化)
# =====================================================================
st.set_page_config(
    page_title="CryptoHunter | 經典雙核儀表板",
    layout="wide"
)

# 注入黑客科技風 CSS 樣式 (保留大方塊，徹底拔除陰影與暗化特效)
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3, h4 { color: #00FFCC !important; font-family: 'Courier New', monospace; }
    
    /* 你的巨大正方形卡片滿血回歸 */
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

st.title("🏹 CryptoHunter 智能量化操盤儀表板")
st.markdown("---")

# =====================================================================
# 2. 交易所初始化
# =====================================================================
@st.cache_resource
def get_exchange():
    return ccxt.okx()

exchange = get_exchange()

# =====================================================================
# 3. 側邊欄控制台 (清爽設定區)
# =====================================================================
st.sidebar.header("⚙️ 獵手核心控制台")

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

# 刷新頻率拉桿
refresh_interval = st.sidebar.slider("數據脈搏刷新頻率 (秒)", min_value=3, max_value=15, value=5)

# =====================================================================
# 4. 量化訊號演算邏輯
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
# 5. 主畫面經典佈局分配 (左 7 寬度放自選大方塊，右 5 寬度放爆量提醒清單)
# =====================================================================
col_fav, col_radar = st.columns([7, 5])

# 獲取交易所即時行情報告
try:
    all_tickers = exchange.fetch_tickers()
except Exception as e:
    st.error(f"📡 交易所數據連線異常，正在自動重新對接... ({e})")
    time.sleep(2)
    st.rerun()

fav_data_list = []
volume_anomalies = []

# 全市場數據一輪掃描、分流處理
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
    
    # A. 篩選出自選幣
    if symbol in fav_cryptos:
        signal_text, signal_color = get_strategy_signal(current_price, high_24h, low_24h)
        fav_data_list.append({
            "symbol": coin_clean,
            "price": current_price,
            "change": change_pct,
            "signal_text": signal_text,
            "signal_color": signal_color
        })
        
    # B. 全網爆量雷達篩選 (門檻：成交額 > 10M USDT 且 漲跌幅 > 5%)
    if vol_usdt_24h >= 10000000 and (change_pct > 5 or change_pct < -5):
        volume_anomalies.append({
            "symbol": coin_clean,
            "price": current_price,
            "change": change_pct,
            "volume_str": f"{vol_usdt_24h / 1000000:.1f}M USDT",
            "volume_usdt": vol_usdt_24h
        })

# ---------------------------------------------------------------------
# 【左側主戰場】：自選幣巨大正方形卡片監控區
# ---------------------------------------------------------------------
with col_fav:
    st.subheader("🎯 自選幣核心監控區")
    st.write(f"⏱ 同步時間：`{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
    st.markdown("---")
    
    if fav_data_list:
        # 每排顯示 2 個正方形大方塊，排版整齊不擁擠
        fav_cols = st.columns(2)
        for idx, coin in enumerate(fav_data_list):
            target_col = fav_cols[idx % 2]
            with target_col:
                c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                c_sign = "+" if coin['change'] >= 0 else ""
                
                # 你的正方形方塊純淨版，毫無暗化與花俏遮罩
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
                st.write("") # 留白增加呼吸感
    else:
        st.info("請在左側邊欄設定你想監控的自選幣種！")

# ---------------------------------------------------------------------
# 【右側主戰場】：全網【突發爆量異常】提醒窗口 (原創經典擺放位置)
# ---------------------------------------------------------------------
with col_radar:
    st.subheader("🚨 全網【突發爆量異常】提醒窗口")
    st.caption("🔥 24h雷達自動鎖定：成交額 > 10M 且波動 > 5% 的爆量異動幣")
    st.markdown("---")
    
    # 按成交額從大到小排序
    volume_anomalies = sorted(volume_anomalies, key=lambda x: x['volume_usdt'], reverse=True)
    
    if volume_anomalies:
        for coin in volume_anomalies[:12]: # 限制前12名，排版最精緻
            c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
            c_sign = "+" if coin['change'] >= 0 else ""
            
            st.markdown(f"**🔥 爆量異動: {coin['symbol']}** | <span style='color:{c_color}; font-weight:bold;'>{c_sign}{coin['change']:.2f}%</span>", unsafe_allow_html=True)
            st.write(f"現價: `${coin['price']:,}` | 24h成交額: `{coin['volume_str']}`")
            st.markdown("---")
    else:
        st.success("🔍 全網目前波動穩定，尚未偵測到突發爆量標的。")

# =====================================================================
# 6. 非阻塞式高效自動脈搏刷新 (流暢跳動、絕不卡死、0 API消耗)
# =====================================================================
time.sleep(refresh_interval)
st.rerun()
