import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime

# 設定網頁標題與配置
st.set_page_config(
    page_title="加密貨幣多幣種即時監控看板",
    page_icon="🪙",
    layout="wide"
)

st.title("🪙 加密貨幣多幣種即時監控看板")
st.markdown("這個網站每隔幾秒會自動向交易所抓取最新數據，實現即時更新。")

# 初始化交易所
@st.cache_resource
def get_exchange():
    return ccxt.okx()

exchange = get_exchange()

# 側邊欄配置
st.sidebar.header("⚙️ 控制面板")
refresh_interval = st.sidebar.slider("更新頻率 (秒)", min_value=2, max_value=10, value=3)
selected_cryptos = st.sidebar.multiselect(
    "選擇要監控的幣種",
    ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT"],
    default=["BTC/USDT", "ETH/USDT", "SOL/USDT"]
)

# 用於承載即時更新內容的容器
placeholder = st.empty()

# 開始即時更新迴圈
if selected_cryptos:
    while True:
        try:
            data_list = []
            # 同時抓取多個幣種
            for symbol in selected_cryptos:
                ticker = exchange.fetch_ticker(symbol)
                data_list.append({
                    "幣種": symbol,
                    "最新價格 (USDT)": ticker['last'],
                    "24h 最高": ticker['high'],
                    "24h 最低": ticker['low'],
                    "24h 成交量": round(ticker['baseVolume'], 2)
                })
            
            # 轉換為表格
            df = pd.DataFrame(data_list)
            
            # 使用容器刷新網頁畫面
            with placeholder.container():
                # 顯示目前時間
                st.write(f"⏱️ 最後更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 數據大字報 (Metric) - 以 BTC 和 ETH 為例做重點突顯
                cols = st.columns(min(len(selected_cryptos), 4))
                for i, row in enumerate(data_list[:4]):
                    with cols[i]:
                        st.metric(label=row["幣種"], value=f"{row['最新價格 (USDT)']} USDT")
                
                st.markdown("---")
                # 顯示完整數據表格
                st.subheader("📊 所有監控幣種即時行情")
                st.dataframe(df.set_index("幣種"), use_container_width=True)
                
            # 暫停指定的秒數
            time.sleep(refresh_interval)
            
        except Exception as e:
            st.error(f"連線錯誤: {e}")
            time.sleep(5)
else:
    st.warning("請在左側邊欄選擇至少一個幣種進行監控。")
