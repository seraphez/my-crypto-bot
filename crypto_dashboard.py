import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime
import google.generativeai as genai

# =====================================================================
# 1. 網頁頂級配置
# =====================================================================
st.set_page_config(
    page_title="CryptoHunter | AI 雙核心獵手",
    page_icon="🏹",
    layout="wide"
)

# =====================================================================
# 2. 注入黑客科技風 CSS 樣式
# =====================================================================
st.markdown("""
    <style>
    /* 全域暗色背景 */
    .stApp { background-color: #0E1117; }
    h1, h2, h3 { color: #00FFCC !important; font-family: 'Courier New', monospace; }
    
    /* 巨大正方形卡片樣式 */
    .square-card {
        background-color: #161B22;
        border: 2px solid #30363D;
        border-radius: 15px;
        padding: 25px;
        margin-bottom: 15px;
        min-height: 250px; /* 強制高度，形成大方塊 */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 8px 16px rgba(0,0,0,0.5);
    }
    .coin-title { font-size: 26px; font-weight: bold; color: #FFF; font-family: 'Courier New', monospace; }
    .coin-price { font-size: 30px; font-weight: bold; color: #00FF66; margin: 8px 0; }
    .coin-change { font-size: 18px; font-weight: bold; }
    
    /* 策略標籤樣式 */
    .trend-badge { 
        padding: 8px 12px; border-radius: 6px; font-weight: bold; font-size: 15px; text-align: center; margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏹 CryptoHunter AI 雙核心獵手系統")
st.markdown("`[雷達模式: 獨立分割看板]` 自選幣種已升級為正方形大面板，右側即時偵測全網爆量異動標的。")

# =====================================================================
# 3. 交易所與 AI 初始化（安全防禦機制）
# =====================================================================
@st.cache_resource
def get_exchange():
    return ccxt.okx() # 使用 OKX 避開 451 錯誤

exchange = get_exchange()

# --- 【安全密鑰讀取機制】 ---
# 優先嘗試讀取 Streamlit 雲端的 Secrets
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    GEMINI_API_KEY = None

# 側邊欄控制台
st.sidebar.header("⚙️ 獵手核心配置")

# 防呆密鑰輸入框：如果雲端沒設定 Key，就在側邊欄輸入，方便本機測試
if not GEMINI_API_KEY:
    st.sidebar.markdown("### 🔑 AI 密鑰配置")
    user_key = st.sidebar.text_input("請輸入 Gemini API Key", type="password", help="請至 Google AI Studio 申請免費 Key")
    if user_key:
        GEMINI_API_KEY = user_key

# 串接 AI 診斷引擎
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        has_ai = True
    except:
        has_ai = False
else:
    has_ai = False

# =====================================================================
# 4. 側邊欄其他參數設定
# =====================================================================
refresh_interval = st.sidebar.slider("數據脈搏刷新 (秒)", min_value=3, max_value=15, value=5)
enable_ai = st.sidebar.toggle("🤖 啟動 AI 即時開盤推薦", value=True)

# 自選區要監控的幣
fav_cryptos = st.sidebar.multiselect(
    "🎯 設定你的自選監控區",
    ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT", "PEPE/USDT"],
    default=["BTC/USDT", "ETH/USDT", "SOL/USDT"]
)

# =====================================================================
# 5. 量化與 AI 分析核心邏輯
# =====================================================================
def get_strategy_signal(current, high, low):
    """根據當前價格在24h高低點的位置，計算多空開盤推薦"""
    if not high or not low:
        return "⚪ 建議觀望 (數據不足)", "#888888"
    mid = (high + low) / 2
    if current > mid * 1.015:
        return "🟢 推薦開多 (突破多頭強勢區)", "#00FF66"
    elif current < mid * 0.985:
        return "🔴 推薦開空 (跌破空頭弱勢區)", "#FF3366"
    return "⚪ 建議觀望 (區間震盪盤整)", "#888888"

def ask_gemini_analysis(coin, price, change, signal):
    """向 Gemini 索取開盤具體文字報告"""
    if not has_ai:
        return "⚠️ 請在左側邊欄輸入有效的 Gemini API Key 以啟用 AI 分析。"
    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"""
        你是一位加密貨幣量化操盤專家。
        標的：{coin}/USDT | 現價：{price} | 24h漲跌：{change}% | 系統量化訊號：{signal}
        請用繁體中文給出極精簡的 2 句短評：
        1. 當前市場局面型態。
        2. 具體的操作/開盤（多/空/觀望）建議與風險提示。
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 引擎暫時無法連線 ({e})"

# =====================================================================
# 6. 主程式數據循環監控區
# =====================================================================
placeholder = st.empty()

while True:
    try:
        # 一次性打包請求全市場數據
        all_tickers = exchange.fetch_tickers()
        
        fav_data_list = []
        anomaly_data_list = []
        
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
            
            if vol_usdt_24h < 150000: # 過濾流動性極差的死幣
                continue
                
            # 計算是否屬於異常異動暴動幣
            is_anomaly = False
            if change_pct > 6 or change_pct < -6: # 24h 劇烈波動
                is_anomaly = True
            
            # 分流處理
            if symbol in fav_cryptos:
                signal_text, signal_color = get_strategy_signal(current_price, high_24h, low_24h)
                fav_data_list.append({
                    "symbol": symbol.replace('/USDT', ''),
                    "price": current_price,
                    "change": change_pct,
                    "signal_text": signal_text,
                    "signal_color": signal_color
                })
            elif is_anomaly:
                anomaly_data_list.append({
                    "異常幣種": symbol.replace('/USDT', ''),
                    "最新價格": current_price,
                    "24h 漲跌": change_pct,
                    "24h 成交額": f"{vol_usdt_24h / 1000000:.1f}M"
                })

        # 開始渲染前端雙核心畫面
        with placeholder.container():
            col_header1, col_header2 = st.columns([3, 1])
            with col_header1:
                st.write(f"⏱ *訊號同步時間：* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
            with col_header2:
                st.write(f"📡 *數據頻率：* `{refresh_interval}秒/次`")
                
            st.markdown("---")
            
            # 分割為左（自選大方塊區）、右（異常量通知區）兩大版塊
            col_left, col_right = st.columns([5, 3])
            
            # --- 左半邊：自選正方形大卡片區 ---
            with col_left:
                st.subheader("🎯 獵手自選監控（大方塊面板）")
                if fav_data_list:
                    # 每 2 個大方塊排成一列
                    fav_cols = st.columns(2)
                    for idx, coin in enumerate(fav_data_list):
                        target_col = fav_cols[idx % 2]
                        with target_col:
                            c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                            c_sign = "+" if coin['change'] >= 0 else ""
                            
                            # 渲染 HTML/CSS 正方形科技卡片
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
                            
                            # AI 分析報告顯示區
                            if enable_ai:
                                if has_ai:
                                    with st.spinner(f"AI 正在精算 {coin['symbol']}..."):
                                        ai_msg = ask_gemini_analysis(coin['symbol'], coin['price'], coin['change'], coin['signal_text'])
                                        st.info(f"🤖 **AI 獵手診斷報告:**\n{ai_msg}")
                                else:
                                    st.warning("🔑 請展開左側邊欄輸入 Gemini API Key 以解鎖 AI 開盤報告。")
                else:
                    st.info("請在側邊欄勾選加入自選追蹤幣種。")
                    
            # --- 右半邊：全網突發異動追蹤區 ---
            with col_right:
                st.subheader("🚨 全網突發【異常波動】催化區")
                if anomaly_data_list:
                    df_anomaly = pd.DataFrame(anomaly_data_list).sort_values(by="24h 漲跌", ascending=False).set_index("異常幣種")
                    
                    def color_anomaly(val):
                        return 'color: #00FF66; font-weight:bold;' if val > 0 else 'color: #FF3366; font-weight:bold;'
                    
                    st.dataframe(
                        df_anomaly.style.map(color_anomaly, subset=['24h 漲跌']),
                        use_container_width=True,
                        height=550
                    )
                else:
                    st.success("🔍 市場目前波動穩定，未偵測到突發爆量異動。")
                    
        # 動態調整頻率限制：有開 AI 且有 Key 時拉長更新，防止爆量
        time.sleep(refresh_interval if not (enable_ai and has_ai) else max(refresh_interval, 8))
        
    except Exception as e:
        st.error(f"📡 數據中斷，自動重連中... Code: {e}")
        time.sleep(5)
