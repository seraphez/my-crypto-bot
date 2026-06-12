import streamlit as st
import ccxt
from datetime import datetime
import requests

# 1. 配置與初始化
st.set_page_config(page_title="CryptoHunter", layout="wide")

if "single_coin_ai" not in st.session_state: 
    st.session_state.single_coin_ai = {}

# 2. 交易所連接
@st.cache_resource
def get_exchange(): return ccxt.okx()
exchange = get_exchange()

@st.cache_data(ttl=3600)
def get_all_usdt_symbols():
    try: return sorted([s for s in exchange.load_markets().keys() if s.endswith('/USDT') and ':' not in s])
    except: return ["BTC/USDT", "ETH/USDT"]

# 3. 側邊欄防禦性讀取 (解決 Secrets 讀取崩潰)
st.sidebar.header("控制台")
# 這裡加了安全檢查，避免讀取 None 時報錯
api_key = ""
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = ""

user_input_key = st.sidebar.text_input("輸入 Gemini API Key (若上方已設定則留空)", type="password")
final_key = user_input_key if user_input_key else api_key

chosen_favs = st.sidebar.multiselect("監控幣種", options=get_all_usdt_symbols(), default=["BTC/USDT", "ETH/USDT"])

# 4. AI 邏輯防禦 (如果沒有 Key 直接回傳提示，不發請求)
def ask_gemini_ai(coin, price, change, vol):
    if not final_key:
        return "⚠️ 請在左側輸入 Gemini API Key 以啟動 AI 分析。"
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={final_key}"
    prompt = f"代幣:{coin} | 現價:{price} | 漲跌:{change}%。請給出實戰報告。"
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10).json()
        if 'candidates' in response:
            return response['candidates'][0]['content']['parts'][0]['text']
        return "⚠️ API 回傳錯誤，請檢查 Key 是否有效。"
    except Exception as e:
        return f"⚠️ 網路錯誤: {str(e)}"

# 5. 主畫面渲染
st.title("CryptoHunter 監控")
all_tickers = exchange.fetch_tickers()

cols = st.columns(3)
for idx, symbol in enumerate(chosen_favs):
    if symbol in all_tickers:
        t = all_tickers[symbol]
        with cols[idx % 3]:
            st.write(f"### {symbol}")
            st.write(f"現價: {t['last']}")
            
            if st.button(f"執行分析 {symbol}", key=f"btn_{symbol}"):
                with st.spinner("分析中..."):
                    res = ask_gemini_ai(symbol, t['last'], t['percentage'], t['quoteVolume'])
                    st.session_state.single_coin_ai[symbol] = res
            
            if symbol in st.session_state.single_coin_ai:
                st.info(st.session_state.single_coin_ai[symbol])
