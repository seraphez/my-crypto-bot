import streamlit as st
import ccxt
import requests

# 設定頁面
st.set_page_config(page_title="CryptoHunter", layout="wide")

# 1. 徹底解決 API Key 讀取問題的函數
def get_api_key():
    # 優先嘗試讀取 Streamlit 的 Secrets (防禦性檢查)
    try:
        if st.secrets and "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    # 如果讀不到，直接回傳空字串 (給 UI 處理)
    return ""

# 2. 獲取資料
@st.cache_resource
def get_exchange(): return ccxt.okx()
exchange = get_exchange()

# 3. 側邊欄輸入區
st.sidebar.header("API 設定")
# 先讀取一次
current_key = get_api_key()
# 如果後台沒設定，提供手動輸入框
user_key = st.sidebar.text_input("輸入 Gemini API Key", type="password", value=current_key)
final_key = user_key if user_key else current_key

# 4. AI 分析函數
def ask_gemini(coin, price):
    if not final_key:
        return "❌ 尚未輸入 API Key，請在側邊欄填寫。"
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={final_key}"
    prompt = f"分析 {coin}，當前價格 {price}，給出簡短建議。"
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10).json()
        if 'candidates' in response:
            return response['candidates'][0]['content']['parts'][0]['text']
        return f" API 回應錯誤: {response}"
    except Exception as e:
        return f" 連線錯誤: {str(e)}"

# 5. 主畫面
st.title("Crypto AI 監控")
tickers = exchange.fetch_tickers()
coins = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

cols = st.columns(3)
for i, coin in enumerate(coins):
    with cols[i]:
        price = tickers[coin]['last']
        st.write(f"### {coin}")
        st.write(f"價格: {price}")
        if st.button(f"分析 {coin}", key=coin):
            result = ask_gemini(coin, price)
            st.info(result)
