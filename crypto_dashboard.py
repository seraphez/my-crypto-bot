import streamlit as st
import ccxt
import time
from datetime import datetime

# 基礎設定：取消頁面邊距限制，確保左右兩欄空間充足
st.set_page_config(page_title="Crypto Dashboard", layout="wide")

# 初始化交易所
exchange = ccxt.okx()

# 側邊欄設定
st.sidebar.header("⚙️ 設定")
fav_symbols = st.sidebar.multiselect("自選幣種", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"], default=["SOL/USDT"])

# 佈局：嚴格分為兩欄，左側自選+復盤，右側異常提醒
col_left, col_right = st.columns([1, 1])

with col_left:
    st.header("🎯 自選幣核心監控區")
    st.write(f"⏱ 同步時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    fav_placeholder = st.empty()
    
    # 將復盤功能整合在左側下方
    st.markdown("---")
    st.subheader("🚀 復盤鑑定")
    replay_input = st.text_input("輸入幣種代號", value="SOL")
    if st.button("啟動復盤"):
        st.write(f"正在對 {replay_input} 進行量化分析...")
        # 這裡放置您的復盤邏輯

with col_right:
    st.header("🚨 全網【突發爆量異常】提醒窗口")
    st.write("🔥 自動鎖定 24h 成交額 > 10M 且波動 > 5% 的全網異動標的")
    anomaly_placeholder = st.empty()

# 主循環：即時刷新
while True:
    try:
        tickers = exchange.fetch_tickers()
        
        # 渲染左側自選
        with fav_placeholder.container():
            for s in fav_symbols:
                if s in tickers:
                    t = tickers[s]
                    st.write(f"**{s}**: {t['last']} ({t['percentage']}%)")
        
        # 渲染右側異常
        with anomaly_placeholder.container():
            for s, t in tickers.items():
                if '/USDT' in s and t['quoteVolume'] and t['quoteVolume'] > 10000000 and abs(t['percentage'] or 0) > 5:
                    st.write(f"🔥 爆量: {s.replace('/USDT', '')} | 漲跌: {t['percentage']}% | 量: {t['quoteVolume']/1000000:.1f}M USDT")
        
        time.sleep(10)
    except:
        time.sleep(5)
