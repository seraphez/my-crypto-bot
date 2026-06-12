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

st.title("🏹 CryptoHunter AI 全幣種雷達系統")

# =====================================================================
# 3. 交易所與 AI 初始化
# =====================================================================
@st.cache_resource
def get_exchange():
    return ccxt.okx() # 使用 OKX 避開 451 區域限制

exchange = get_exchange()

# --- 【安全密鑰讀取機制】 ---
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    GEMINI_API_KEY = None

# =====================================================================
# 4. 側邊欄控制台（包含功能切換與選項）
# =====================================================================
st.sidebar.header("⚙️ 獵手核心控制台")

# 💡 【核心修改】：在左邊多出一個選單，讓你自由切換功能，絕對不疊加在主畫面！
page_mode = st.sidebar.radio(
    "🧭 請選擇功能面板",
    ["🎯 自選幣大方塊監控", "🚨 全網突發異常波動"],
    index=0
)

st.sidebar.markdown("---")

# 防呆密鑰輸入框
if not GEMINI_API_KEY:
    st.sidebar.markdown("### 🔑 AI 密鑰配置")
    user_key = st.sidebar.text_input("請輸入 Gemini API Key", type="password")
    if user_key:
        GEMINI_API_KEY = user_key

# 串接 AI 診斷引擎
has_ai = False
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        has_ai = True
    except:
        has_ai = False

# 獲取全市場 USDT 現貨/永續標的名單 (支援搜尋)
@st.cache_data(ttl=3600)
def get_all_usdt_symbols():
    try:
        markets = exchange.load_markets()
        symbols = [symbol for symbol in markets.keys() if symbol.endswith('/USDT') and ':' not in symbol]
        return sorted(symbols)
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]

all_available_cryptos = get_all_usdt_symbols()

# 側邊欄其他參數設定
refresh_interval = st.sidebar.slider("數據脈搏刷新 (秒)", min_value=3, max_value=15, value=5)
enable_ai = st.sidebar.toggle("🤖 啟動 AI 即時開盤推薦", value=True)

# 只有在切換到「自選幣」模式時，左側才顯示選幣框
if page_mode == "🎯 自選幣大方塊監控":
    fav_cryptos = st.sidebar.multiselect(
        "🎯 設定你的自選監控區",
        options=all_available_cryptos,
        default=[s for s in ["BTC/USDT", "ETH/USDT", "SOL/USDT"] if s in all_available_cryptos]
    )

# =====================================================================
# 5. 量化與 AI 分析核心邏輯
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

def ask_gemini_analysis(coin, price, change, signal):
    if not has_ai:
        return "⚠️ 請在左側邊欄輸入有效的 Gemini API Key 以啟用 AI 分析。"
    try:
        # 💡 強制修正通道版本與對象，徹底消滅 404 models/gemini-1.5-flash is not found 錯誤
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            client=genai.client.get_default_index_client(api_version='v1')
        )
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
        return f"AI 獵手正在重新對接 v1 通道... ({e})"

# =====================================================================
# 6. 主程式數據循環監控區
# =====================================================================
placeholder = st.empty()

while True:
    try:
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
            
            if vol_usdt_24h < 150000: 
                continue
                
            # 偵測異常異動爆量幣
            is_anomaly = False
            if change_pct > 6 or change_pct < -6: 
                is_anomaly = True
            
            # 分流處理
            if page_mode == "🎯 自選幣大方塊監控" and symbol in fav_cryptos:
                signal_text, signal_color = get_strategy_signal(current_price, high_24h, low_24h)
                fav_data_list.append({
                    "symbol": symbol.replace('/USDT', ''),
                    "price": current_price,
                    "change": change_pct,
                    "signal_text": signal_text,
                    "signal_color": signal_color
                })
            elif page_mode == "🚨 全網突發異常波動" and is_anomaly:
                anomaly_data_list.append({
                    "異常幣種": symbol.replace('/USDT', ''),
                    "最新價格": current_price,
                    "24h 漲跌": change_pct,
                    "24h 成交額": f"{vol_usdt_24h / 1000000:.1f}M"
                })

        # 開始單獨渲染前端畫面（絕對不會疊加！）
        with placeholder.container():
            st.write(f"⏱ *同步時間：* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}` | 📡 *頻率：* `{refresh_interval}秒/次`")
            st.markdown("---")
            
            # 模式一：主畫面只顯示【自選正方形大方塊】（支援3列排版，更飽滿）
            if page_mode == "🎯 自選幣大方塊監控":
                st.subheader("🎯 自選監控面板 (100% 全螢幕大方塊)")
                if fav_data_list:
                    fav_cols = st.columns(3) # 每行塞 3 個大方塊，畫面非常大氣
                    for idx, coin in enumerate(fav_data_list):
                        target_col = fav_cols[idx % 3]
                        with target_col:
                            c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                            c_sign = "+" if coin['change'] >= 0 else ""
                            
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
                            
                            if enable_ai:
                                if has_ai:
                                    with st.spinner(f"AI 精算 {coin['symbol']}..."):
                                        ai_msg = ask_gemini_analysis(coin['symbol'], coin['price'], coin['change'], coin['signal_text'])
                                        st.info(f"🤖 **AI 獵手報告:**\n{ai_msg}")
                                else:
                                    st.warning("🔑 請在左選單輸入 Key 以啟用 AI 報告。")
                else:
                    st.info("請在左側邊欄搜尋並勾選想要監控的任何幣種！")
            
            # 模式二：主畫面切換為【全網突發異常波動】表格（滿版大畫面）
            elif page_mode == "🚨 全網突發異常波動":
                st.subheader("🚨 全網突發【異常波動】催化區 (獨立滿版)")
                if anomaly_data_list:
                    df_anomaly = pd.DataFrame(anomaly_data_list).sort_values(by="24h 漲跌", ascending=False).set_index("異常幣種")
                    
                    def color_anomaly(val):
                        return 'color: #00FF66; font-weight:bold;' if val > 0 else 'color: #FF3366; font-weight:bold;'
                    
                    st.dataframe(
                        df_anomaly.style.map(color_anomaly, subset=['24h 漲跌']),
                        use_container_width=True,
                        height=600
                    )
                else:
                    st.success("🔍 市場目前波動穩定，未偵測到突發爆量異動。")
                    
        time.sleep(refresh_interval if not (enable_ai and has_ai) else max(refresh_interval, 8))
        
    except Exception as e:
        st.error(f"📡 數據中斷，自動重連中... Code: {e}")
        time.sleep(5)
