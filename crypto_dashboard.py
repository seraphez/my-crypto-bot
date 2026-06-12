import streamlit as st
import pandas as pd
import ccxt
import pandas_ta as ta
import time
from sklearn.ensemble import RandomForestClassifier
from groq import Groq  # 改用免費的 Groq
import plotly.graph_objects as go

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="🤖 AI Crypto Dashboard", layout="wide")
st.title("🤖 AI 加密貨幣盤勢識別與下單方針系統 (免費版)")

# --- 2. 側邊欄：使用者參數輸入 ---
st.sidebar.header("⚙️ 參數設定")
api_key = st.sidebar.text_input("輸入 Groq API Key (gsk_...)", type="password", help="請至 console.groq.com 免費申請")
target_coin = st.sidebar.selectbox("選擇交易對", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"])
timeframe = st.sidebar.selectbox("K線週期", ["1h", "4h", "1d"])

# --- 3. 核心功能函數 ---

@st.cache_data(ttl=60)
def get_crypto_data(symbol, tf):
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=200)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def train_and_predict_ml(df):
    ml_df = df.copy().dropna()
    if len(ml_df) < 50: return 50.0
    
    ml_df['EMA_20'] = ta.ema(ml_df['close'], length=20)
    ml_df['EMA_50'] = ta.ema(ml_df['close'], length=50)
    ml_df['RSI'] = ta.rsi(ml_df['close'], length=14)
    ml_df = ml_df.dropna()
    
    features = ['EMA_20', 'EMA_50', 'RSI', 'volume']
    ml_df['Target'] = (ml_df['close'].shift(-1) > ml_df['close']).astype(int)
    
    X_train = ml_df[features].iloc[:-1]
    y_train = ml_df['Target'].iloc[:-1]
    X_current = ml_df[features].iloc[[-1]]
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    prob = model.predict_proba(X_current)[0][1]
    return round(prob * 100, 2)

def generate_llm_report(api_key, symbol, price, rsi, trend, ml_prob):
    if not api_key:
        return "⚠️ 請在左側輸入 Groq API Key 以啟用分析報告。"
    
    try:
        client = Groq(api_key=api_key)
        prompt = f"""
        你是一位精通加密貨幣量化交易的導師。針對 {symbol} 給出下單方針：
        價格: {price}, RSI: {rsi:.2f}, 趨勢: {trend}, 機器學習預測上漲機率: {ml_prob}%
        請用專業語氣給出：1. 盤勢點評 2. 綜合評估 3. 具體操作建議(止損/進場)。
        """
        response = client.chat.completions.create(
            model="llama-3.3-70b-specdec",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ 報告生成失敗: {e}"

# --- 4. 主程式執行 ---
if st.button("🚀 啟動 AI 盤勢分析"):
    with st.spinner("分析中..."):
        df = get_crypto_data(target_coin, timeframe)
        df['EMA_20'] = ta.ema(df['close'], length=20)
        df['EMA_50'] = ta.ema(df['close'], length=50)
        df['RSI'] = ta.rsi(df['close'], length=14)
        latest = df.iloc[-1]
        trend_status = "多頭排列" if latest['EMA_20'] > latest['EMA_50'] else "空頭排列"
        ml_prob = train_and_predict_ml(df)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("價格", f"${latest['close']:,}")
        col2.metric("RSI", f"{latest['RSI']:.2f}")
        col3.metric("AI 上漲機率", f"{ml_prob}%")
        
        fig = go.Figure(data=[go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("🎯 AI 下單方針")
        st.info(generate_llm_report(api_key, target_coin, latest['close'], latest['RSI'], trend_status, ml_prob))
