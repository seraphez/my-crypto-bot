import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime
import requests  # 終極直連秘密武器，繞過 SDK 的 404 地雷

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
        min-height: 250px;
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

st.title("🏹 CryptoHunter AI 全幣種智能系統")

# =====================================================================
# 3. 交易所初始化
# =====================================================================
@st.cache_resource
def get_exchange():
    return ccxt.okx()

exchange = get_exchange()

# =====================================================================
# 4. 側邊欄控制台（API 輸入位置永遠置頂）
# =====================================================================
st.sidebar.header("⚙️ 獵手核心控制台")

# 🔒 密鑰輸入框（永遠在側邊欄第一格，絕不隱藏）
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("🔑 已從後台 Secrets 自動載入密鑰")
else:
    st.sidebar.markdown("### 🔑 認證：請輸入 Gemini API Key")
    GEMINI_API_KEY = st.sidebar.text_input(
        "請貼上你的 API Key：", 
        type="password", 
        placeholder="AI Studio 申請的 AIzaSy..."
    )

st.sidebar.markdown("---")

# 功能面板切換（完美分離不疊加主畫面）
page_mode = st.sidebar.radio(
    "🧭 請選擇功能面板",
    ["🎯 自選幣大方塊監控", "🚨 全網突發異常波動"],
    index=0
)

st.sidebar.markdown("---")

# 獲取全市場 USDT 名單
@st.cache_data(ttl=3600)
def get_all_usdt_symbols():
    try:
        markets = exchange.load_markets()
        symbols = [symbol for symbol in markets.keys() if symbol.endswith('/USDT') and ':' not in symbol]
        return sorted(symbols)
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]

all_available_cryptos = get_all_usdt_symbols()

# 其他設定參數
refresh_interval = st.sidebar.slider("數據脈搏刷新 (秒)", min_value=3, max_value=15, value=5)
enable_ai = st.sidebar.toggle("🤖 啟動 AI 即時開盤推薦", value=True)

# 只有在「自選幣」模式時，左側才顯示選幣搜尋框
if page_mode == "🎯 自選幣大方塊監控":
    fav_cryptos = st.sidebar.multiselect(
        "🎯 設定你的自選監控區（可打字搜尋）",
        options=all_available_cryptos,
        default=[s for s in ["BTC/USDT", "ETH/USDT", "SOL/USDT"] if s in all_available_cryptos]
    )

# =====================================================================
# 5. 量化與 AI 分析核心邏輯（底層 HTTP 直連，使用 gemini-2.5-flash 正式版模型）
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

def ask_gemini_analysis(coin, price, change, signal, is_anomaly_mode=False):
    if not GEMINI_API_KEY:
        return "⚠️ 請先在左側邊欄輸入有效的 Gemini API Key 才能看報告喔！"
    
    # 🎯 直擊 Google 官方全面標準支援的 gemini-2.5-flash 通道，徹底根除 404 Bug
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    # 💡 兩套分流的 AI 分析與操作判斷方針
    if is_anomaly_mode:
        prompt = f"""
        你現在是精通加密貨幣『山寨幣/妖幣暴動盤』的短線量化操盤專家。
        當前偵測到突發【異常波動標的】：{coin}/USDT | 現價：{price} | 24h漲跌幅：{change}%
        請用繁體中文給出極精簡且極具攻擊性的 2 句短評：
        1. 分析此時異常暴漲或暴跌的背後主力心理型態（是拉高出貨、動能突破還是恐慌踩踏）。
        2. 給出【最具體的操作方法與建議】（例如：切勿追高建議逢高分批進空、短線跟隨動能突破輕倉追多、或是正值極端行情建議冷靜觀望），並附帶精準的止損/風險提示。
        """
    else:
        prompt = f"""
        你現在是加密貨幣量化操盤專家。
        標的：{coin}/USDT | 現價：{price} | 24h漲跌：{change}% | 系統量化訊號：{signal}
        請用繁體中文給出極精簡的 2 句短評：
        1. 當前市場局面型態。
        2. 具體的操作/開盤（多/空/觀望）建議與風險提示。
        """
        
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        data = response.json()
        
        # 自動識別並攔截 Google 返回的錯誤
        if 'error' in data:
            err_msg = data['error'].get('message', '未知錯誤')
            if "API key not valid" in err_msg:
                return "❌ 【API Key 錯誤】請檢查左側輸入的金鑰是否複製完整，前後是否有空格。"
            elif "Resource has been exhausted" in err_msg:
                return "⏳ 【頻率超限】免費 Key 每分鐘呼叫次數有限，請在左側將「數據脈搏刷新」拉長至 12~15 秒。"
            return f"❌ Google 拒絕原因: {err_msg}"
            
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"⚠️ 網路傳輸異常，正在重新橋接通道... ({e})"

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
                
            # 偵測異常異動爆量幣 (漲跌幅絕對值大於 6%)
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
                signal_text, signal_color = get_strategy_signal(current_price, high_24h, low_24h)
                anomaly_data_list.append({
                    "symbol": symbol.replace('/USDT', ''),
                    "price": current_price,
                    "change": change_pct,
                    "vol_usdt": f"{vol_usdt_24h / 1000000:.1f}M",
                    "signal_text": signal_text,
                    "signal_color": signal_color
                })

        # 開始渲染前端
        with placeholder.container():
            st.write(f"⏱ *同步時間：* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}` | 📡 *頻率：* `{refresh_interval}秒/次`")
            st.markdown("---")
            
            # =================================================================
            # 模式一：自選監控面板 (100% 全螢幕大方塊，絕不疊加表格)
            # =================================================================
            if page_mode == "🎯 自選幣大方塊監控":
                st.subheader("🎯 自選監控面板")
                if fav_data_list:
                    fav_cols = st.columns(3)
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
                                if GEMINI_API_KEY:
                                    with st.spinner(f"AI 精算 {coin['symbol']}..."):
                                        ai_msg = ask_gemini_analysis(coin['symbol'], coin['price'], coin['change'], coin['signal_text'], is_anomaly_mode=False)
                                        st.info(f"🤖 **AI 獵手報告:**\n{ai_msg}")
                                else:
                                    st.warning("🔑 請在左選單最上方輸入 Key 以啟用 AI 報告。")
                else:
                    st.info("請在左側邊欄搜尋並勾選想要監控的任何幣種！")
            
            # =================================================================
            # 模式二：異常波動面板 (自帶專屬 AI 實戰方針，絕不疊加方塊)
            # =================================================================
            elif page_mode == "🚨 全網突發異常波動":
                st.subheader("🚨 全網突發【異常波動】追蹤總表")
                if anomaly_data_list:
                    df_rows = [{
                        "異常幣種": item["symbol"],
                        "最新價格": item["price"],
                        "24h 漲跌": item["change"],
                        "24h 成交額": item["vol_usdt"]
                    } for item in anomaly_data_list]
                    df_anomaly = pd.DataFrame(df_rows).sort_values(by="24h 漲跌", ascending=False).set_index("異常幣種")
                    
                    def color_anomaly(val):
                        return 'color: #00FF66; font-weight:bold;' if val > 0 else 'color: #FF3366; font-weight:bold;'
                    
                    st.dataframe(
                        df_anomaly.style.map(color_anomaly, subset=['24h 漲跌']),
                        use_container_width=True,
                        height=250
                    )
                    
                    st.markdown("---")
                    st.subheader("⚡ 暴動標的：AI 獵手實戰操作方法")
                    
                    # 抓前 4 名異動最猛的幣進行深度剖析
                    top_anomalies = sorted(anomaly_data_list, key=lambda x: abs(x['change']), reverse=True)[:4]
                    anom_cols = st.columns(2)
                    for idx, coin in enumerate(top_anomalies):
                        target_col = anom_cols[idx % 2]
                        with target_col:
                            c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                            c_sign = "+" if coin['change'] >= 0 else ""
                            
                            st.markdown(f"""
                                <div class="square-card" style="min-height: 180px;">
                                    <div>
                                        <div class="coin-title" style="color: #FFCC00;">🔥 突發暴動: {coin['symbol']}/USDT</div>
                                        <div class="coin-price">${coin['price']:,}</div>
                                        <div class="coin-change" style="color: {c_color};">{c_sign}{coin['change']}% (成交額: {coin['vol_usdt']})</div>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            if enable_ai:
                                if GEMINI_API_KEY:
                                    with st.spinner(f"AI 正在解構 {coin['symbol']}..."):
                                        ai_msg = ask_gemini_analysis(coin['symbol'], coin['price'], coin['change'], coin['signal_text'], is_anomaly_mode=True)
                                        st.error(f"⚔️ **AI 實戰操作方法:**\n{ai_msg}")
                                else:
                                    st.warning("🔑 請在左選單最上方輸入 Key 以啟用 AI 實戰操作分析。")
                else:
                    st.success("🔍 市場目前波動穩定，未偵測到 24h 漲跌超過 ±6% 的突發異動幣種。")
                    
        # 動態限流：當有啟用 AI 分析時，自動限制循環頻率不低於 8 秒，防止免費 Key 頻繁請求而爆掉
        time.sleep(refresh_interval if not (enable_ai and GEMINI_API_KEY) else max(refresh_interval, 8))
        
    except Exception as e:
        st.error(f"📡 數據中斷，自動重連中... Code: {e}")
        time.sleep(5)
