import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime

# 1. 設定網頁標題與配置
st.set_page_config(
    page_title="CryptoPulse | 加密貨幣即時監控面板",
    page_icon="🪙",
    layout="wide"
)

# 使用 CSS 來美化網頁，讓格子（Metric）更有卡片感
st.markdown("""
    <style>
        /* 讓 Metric 卡片有淡淡的背景和邊框，看起來像一個個獨立的格子 */
        [data-testid="stMetricBlock"] {
            background-color: #1e293b;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #334155;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        /* 調整卡片內的文字顏色，讓它在暗色背景下更好看 */
        [data-testid="stMetricLabel"] {
            color: #94a3b8 !important;
            font-size: 14px !important;
            font-weight: 600;
        }
        [data-testid="stMetricValue"] {
            color: #38bdf8 !important; /* 價格給它亮藍色 */
            font-size: 24px !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🪙 CryptoPulse 智能監控面板")
st.markdown("本面板已串接 OKX 交易所，支援多幣種即時數據捕捉。")

# 初始化交易所（改成 okx 避免地區鎖定錯誤）
@st.cache_resource
def get_exchange():
    return ccxt.okx()

exchange = get_exchange()

# 2. 側邊欄配置
st.sidebar.header("⚙️ 控制面板")
refresh_interval = st.sidebar.slider("⏱️ 更新頻率 (秒)", min_value=2, max_value=10, value=3)

# 預設多放幾個幣種，體驗格子排列的效果
selected_cryptos = st.sidebar.multiselect(
    "🔍 選擇要監控的幣種",
    ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "LINK/USDT", "AVAX/USDT"],
    default=["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "DOGE/USDT"]
)

# 3. 建立即時刷新容器
placeholder = st.empty()

# 4. 開始即時更新迴圈
if selected_cryptos:
    while True:
        try:
            data_list = []
            # 抓取所有選中幣種的數據
            for symbol in selected_cryptos:
                ticker = exchange.fetch_ticker(symbol)
                data_list.append({
                    "幣種": symbol,
                    "最新價格 (USDT)": ticker['last'],
                    "24h 最高": ticker['high'],
                    "24h 最低": ticker['low'],
                    "24h 成交量": round(ticker['baseVolume'], 2)
                })
            
            df = pd.DataFrame(data_list)
            
            # 刷新網頁畫面
            with placeholder.container():
                st.write(f"🔄 最後更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                st.subheader("📱 即時價格看板")
                
                # 【核心修改：格子化排版邏輯】
                # 設定每排最多放 4 個格子
                MAX_COLS = 4
                total_cryptos = len(data_list)
                
                # 用迴圈每次處理 4 個幣種，自動換行
                for i in range(0, total_cryptos, MAX_COLS):
                    # 擷取這這一排要放的幣種數據（例如 0~4, 4~8...）
                    chunk = data_list[i:i + MAX_COLS]
                    
                    # 根據這這一排實際有幾個幣種，建立對應數量的欄位
                    cols = st.columns(len(chunk))
                    
                    # 在這一排的每個格子裡填入數據
                    for j, row in enumerate(chunk):
                        with cols[j]:
                            st.metric(
                                label=f"💰 {row['幣種']}", 
                                value=f"{row['最新價格 (USDT)']} USDT"
                            )
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("---")
                
                # 顯示下方完整數據表格
                st.subheader("📊 所有監控幣種詳細行情")
                st.dataframe(df.set_index("幣種"), use_container_width=True)
                
            time.sleep(refresh_interval)
            
        except Exception as e:
            st.error(f"連線錯誤: {e}")
            time.sleep(5)
else:
    st.warning("請在左側邊欄選擇至少一個幣種進行監控。")
