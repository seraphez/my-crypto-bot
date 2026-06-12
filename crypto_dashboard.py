import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime
import requests

# =====================================================================
# 1. 網頁頂級配置
# =====================================================================
st.set_page_config(
    page_title="CryptoHunter | 異常驅動 AI 獵手",
    page_icon="🏹",
    layout="wide"
)

# =====================================================================
# 2. 注入黑客科技風 CSS 樣式
# =====================================================================
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3 { color: #00FFCC !important; font-family: 'Courier New', monospace; }
    
    /* 巨大正方形卡片樣式 */
    .square-card {
        background-color: #161B22;
        border: 2px solid #30363D;
        border-radius: 15px;
        padding: 25px;
        margin-bottom: 15px;
        min-height: 220px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 8px 16px rgba(0,0,0,0.5);
    }
    /* 異常暴動卡片樣式：帶有紅色警告外框與微弱呼吸燈效果 */
    .anomaly-card {
        background-color: #1A1115;
        border: 2px solid #FF3366;
        border-radius: 15px;
        padding: 25px;
        margin-bottom: 15px;
        min-height: 220px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 0 15px rgba(255, 51, 102, 0.3);
    }
    .coin-title { font-size: 26px; font-weight: bold; color: #FFF; font-family: 'Courier New', monospace; }
    .coin-price { font-size: 30px; font-weight: bold; color: #00FF66; margin: 8px 0; }
    .coin-change { font-size: 18px; font-weight: bold; }
    
    .trend-badge { 
        padding: 8px 12px; border-radius: 6px; font-weight: bold; font-size: 15px; text-align: center; margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏹 CryptoHunter AI 異常驅動智能監控系統")

# =====================================================================
# 3. 交易所初始化
# =====================================================================
@st.cache_resource
def get_exchange():
    return ccxt.okx()

exchange = get_exchange()

# =====================================================================
# 4. 側邊欄控制台
# =====================================================================
st.sidebar.header("⚙️ 獵手核心控制台")

# 🔒 密鑰輸入框
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

# 自選監控區設定
fav_cryptos = st.sidebar.multiselect(
    "🎯 設定你的自選監控區（可多選、打字搜尋）",
    options=all_available_cryptos,
    default=[s for s in ["BTC/USDT", "ETH/USDT", "SOL/USDT"] if s in all_available_cryptos]
)

st.sidebar.markdown("---")
refresh_interval = st.sidebar.slider("數據脈搏刷新 (秒)", min_value=3, max_value=15, value=5)

# =====================================================================
# 5. AI 分析核心邏輯（底層 HTTP 直連，使用官方最新萬用模型 gemini-2.5-flash）
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

def ask_gemini_anomaly_analysis(coin, price, change):
    if not GEMINI_API_KEY:
        return "⚠️ 請先在左側邊欄輸入有效的 Gemini API Key 才能看報告喔！"
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    你現在是精通加密貨幣『山寨幣/妖幣暴動盤』的短線量化操盤專家。
    當前自選監控標的發生【突發異常波動】：{coin}/USDT | 現價：{price} | 24h漲跌幅：{change}%
    請用繁體中文給出極精簡且極具攻擊性的 2 句短評：
    1. 分析此時異常暴漲或暴跌的背後主力心理型態（是拉高出貨、動能突破還是恐慌踩踏）。
    2. 給出【最具體的操作方法與建議】（例如：切勿追高建議逢高分批進空、短線跟隨動能突破輕倉追多、或是正值極端行情建議冷靜觀望），並附帶精準的止損/風險提示。
    """
        
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        data = response.json()
        
        if 'error' in data:
            err_msg = data['error'].get('message', '未知錯誤')
            if "API key not valid" in err_msg:
                return "❌ 【API Key 錯誤】請檢查左側輸入的金鑰。"
            elif "Resource has been exhausted" in err_msg:
                return "⏳ 【頻率超限】免費額度已滿，系統正在自動降頻排隊。"
            return f"❌ Google 拒絕原因: {err_msg}"
            
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"⚠️ 網絡傳輸異常 ({e})"

# =====================================================================
# 6. 主程式數據循環監控區
# =====================================================================
placeholder = st.empty()

while True:
    try:
        all_tickers = exchange.fetch_tickers()
        render_data_list = []
        
        # 只篩選自選幣種
        for symbol, ticker in all_tickers.items():
            if symbol in fav_cryptos:
                current_price = ticker['last']
                change_pct = ticker['percentage'] if ticker['percentage'] is not None else 0.0
                high_24h = ticker['high']
                low_24h = ticker['low']
                
                signal_text, signal_color = get_strategy_signal(current_price, high_24h, low_24h)
                
                # 🧠 關鍵核心：判斷該自選幣此時是否「異常波動」(絕對值大於 6%)
                is_anomaly = True if (change_pct > 6 or change_pct < -6) else False
                
                render_data_list.append({
                    "symbol": symbol.replace('/USDT', ''),
                    "price": current_price,
                    "change": change_pct,
                    "signal_text": signal_text,
                    "signal_color": signal_color,
                    "is_anomaly": is_anomaly
                })

        # 開始渲染全螢幕大方塊畫面
        with placeholder.container():
            st.write(f"⏱ *同步時間：* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}` | 📡 *頻率：* `{refresh_interval}秒/次`")
            st.markdown("---")
            
            st.subheader("🎯 自選標的監控大區（異常爆量將會自動亮燈觸發 AI）")
            
            if render_data_list:
                fav_cols = st.columns(3)
                for idx, coin in enumerate(render_data_list):
                    target_col = fav_cols[idx % 3]
                    with target_col:
                        c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                        c_sign = "+" if coin['change'] >= 0 else ""
                        
                        # 💡 如果異常，換成紅色亮點框框樣式，平時則是低調暗色框
                        card_class = "anomaly-card" if coin['is_anomaly'] else "square-card"
                        anomaly_prefix = "🚨 突發異動!! " if coin['is_anomaly'] else ""
                        
                        st.markdown(f"""
                            <div class="{card_class}">
                                <div>
                                    <div class="coin-title">{anomaly_prefix}🪙 {coin['symbol']}/USDT</div>
                                    <div class="coin-price">${coin['price']:,}</div>
                                    <div class="coin-change" style="color: {c_color};">{c_sign}{coin['change']}%</div>
                                </div>
                                <div class="trend-badge" style="background-color: {coin['signal_color']}22; color: {coin['signal_color']}; border: 1px solid {coin['signal_color']};">
                                    {coin['signal_text']}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # 🔥 【核心進化】：只有當該自選幣觸發異常（>6% 或 <-6%）時，才啟動 AI 診斷
                        if coin['is_anomaly']:
                            if GEMINI_API_KEY:
                                with st.spinner(f"🚨 正在攔截 {coin['symbol']} 主力資金流..."):
                                    ai_msg = ask_gemini_anomaly_analysis(coin['symbol'], coin['price'], coin['change'])
                                    st.error(f"⚔️ **AI 實戰操作方法:**\n{ai_msg}")
                            else:
                                st.warning("🔑 請在左選單最上方輸入 Key 以啟用異常 AI 分析。")
                        else:
                            # 平時波瀾不驚，顯示靜態安全提示，完全不佔用 API 額度
                            st.info("🟢 行情波動在安全區間內，AI 待命防禦中。")
            else:
                st.info("請在左側邊欄搜尋並勾選想要監控的自選幣種！")
                
        # 動態冷卻防爆機制
        time.sleep(refresh_interval)
        
    except Exception as e:
        st.error(f"📡 數據中斷，自動重連中... Code: {e}")
        time.sleep(5)
