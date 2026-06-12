import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime

# 1. 網頁頂級配置（預設寬螢幕）
st.set_page_config(
    page_title="CryptoHunter | 加密貨幣量化數據獵手",
    page_icon="🏹",
    layout="wide"
)

# 2. 注入自訂的 CSS 樣式（打造數據獵手的科技黑客風）
st.markdown("""
    <style>
    /* 全域背景與文字顏色調整 */
    .stApp {
        background-color: #0E1117;
    }
    h1, h2, h3 {
        color: #00FFCC !important; /* 螢光青色標題 */
        font-family: 'Courier New', Courier, monospace;
    }
    /* 數據卡片美化 */
    div[data-testid="stMetric"] {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 10px;
        padding: 15px 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    /* 讓表格更有科技感 */
    .dataframe {
        border: 1px solid #30363D !important;
        background-color: #161B22 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 標題區
st.title("🏹 CryptoHunter 數據獵手系統")
st.markdown("`[系統狀態: 正常監控中]` 全市即時數據流、資金異常爆量、多空量化動態分析。")

@st.cache_resource
def get_exchange():
    return ccxt.okx()

exchange = get_exchange()

# 側邊欄配置
st.sidebar.header("⚙️ 獵手核心配置")
refresh_interval = st.sidebar.slider("數據脈搏 (秒/次)", min_value=2, max_value=15, value=3)
min_volume = st.sidebar.number_input("最低過濾成交額 (USDT)", min_value=0, value=500000, step=100000)

# 用於動態刷新的容器
placeholder = st.empty()

while True:
    try:
        # 抓取全市行情
        all_tickers = exchange.fetch_tickers()
        data_list = []
        
        for symbol, ticker in all_tickers.items():
            if symbol.endswith('/USDT') and ':' not in symbol:
                vol_usdt = ticker['quoteVolume'] if ticker['quoteVolume'] else (ticker['baseVolume'] * ticker['last'] if ticker['baseVolume'] and ticker['last'] else 0)
                
                if vol_usdt >= min_volume:
                    change = ticker['percentage'] if ticker['percentage'] is not None else 0.0
                    
                    # 數據清洗與打包
                    data_list.append({
                        "幣種": symbol.replace('/USDT', ''),
                        "最新價格 (USDT)": ticker['last'],
                        "24h 漲跌": change,
                        "24h 最高": ticker['high'],
                        "24h 最低": ticker['low'],
                        "24h 成交額 (USDT)": vol_usdt
                    })
        
        df = pd.DataFrame(data_list)
        
        if not df.empty:
            df = df.sort_values(by="24h 成交額 (USDT)", ascending=False)
            
            with placeholder.container():
                # 上方狀態列
                col_status1, col_status2 = st.columns([2, 1])
                with col_status1:
                    st.markdown(f"⏱️ **訊號同步時間：** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
                with col_status2:
                    st.markdown(f"📊 **當前追蹤標的：** `{len(df)} 個現貨幣種`")
                
                # --- 核心視覺一：三大巨頭資金監控卡片 ---
                st.markdown("### ⚡ 全網資金焦點（成交額 Top 3）")
                cols = st.columns(3)
                top_3 = df.head(3).to_dict('records')
                
                for i, row in enumerate(top_3):
                    with cols[i]:
                        # 格式化成交額，變成百萬(M)或大數字
                        vol_m = f"{row['24h 成交額 (USDT)'] / 1000000:.2f}M"
                        st.metric(
                            label=f"🔥 Top {i+1} 資金主戰場: {row['幣種']}/USDT",
                            value=f"${row['最新價格 (USDT)']} USDT",
                            delta=f"{row['24h 漲跌']}% (量: {vol_m})"
                        )
                
                st.markdown("---")
                
                # --- 核心視覺二：左右雙欄數據排版 ---
                col_left, col_right = st.columns([3, 2])
                
                with col_left:
                    st.markdown("### 📊 實時獵手數據大盤")
                    
                    # 幫表格加上顏色反饋的樣式（漲變綠、跌變紅）
                    def color_change(val):
                        if val > 0:
                            return 'color: #00FF66; font-weight: bold;' # 螢光綠
                        elif val < 0:
                            return 'color: #FF3366; font-weight: bold;' # 螢光紅
                        return 'color: white;'

                    # 格式化表格顯示
                    styled_df = df.copy()
                    styled_df = styled_df.set_index("幣種")
                    
                    # 顯示精緻的數據表格
                    st.dataframe(
                        styled_df.style.map(color_change, subset=['24h 漲跌'])
                        .format({"24h 成交額 (USDT)": "{:,.2f}", "最新價格 (USDT)": "{:,}"}),
                        use_container_width=True,
                        height=500
                    )
                
                with col_right:
                    st.markdown("### 🚨 今日漲幅/跌幅敢死隊")
                    
                    # 找出漲最多和跌最多的幣
                    df_gainers = df.sort_values(by="24h 漲跌", ascending=False).head(5)
                    df_losers = df.sort_values(by="24h 漲跌", ascending=True).head(5)
                    
                    st.markdown("**📈 漲幅榜前五 (主力拉升中):**")
                    for _, r in df_gainers.iterrows():
                        st.markdown(f"`{r['幣種']}` : **+{r['24h 漲跌']}%** | 價: `{r['最新價格 (USDT)']}`")
                        
                    st.markdown("---")
                    st.markdown("**📉 跌幅榜前五 (恐慌拋售中):**")
                    for _, r in df_losers.iterrows():
                        st.markdown(f"`{r['幣種']}` : <span style='color:#FF3366'>**{r['24h 漲跌']}%**</span> | 價: `{r['最新價格 (USDT)']}`", unsafe_allow_html=True)

        time.sleep(refresh_interval)
        
    except Exception as e:
        st.error(f"📡 數據流中斷，正在重新連接... 錯誤代碼: {e}")
        time.sleep(5)
