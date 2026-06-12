import streamlit as st
import pandas as pd
import ccxt
import pandas_ta as ta
from sklearn.ensemble import RandomForestClassifier
from openai import OpenAI
import plotly.graph_objects as go

# --- 頁面基本設定 ---
st.set_page_config(page_title="🤖 AI Crypto Dashboard", layout="wide")
st.title("🤖 AI 加密貨幣盤勢識別與下單方針系統")

# --- 側邊欄：使用者輸入 ---
st.sidebar.header("⚙️ 參數設定")
api_key = st.sidebar.text_input("輸入 OpenAI API Key", type="password")
target_coin = st.sidebar.selectbox("選擇交易對", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"])
timeframe = st.sidebar.selectbox("K線週期", ["1h", "4h", "1d"])

# --- 核心邏輯函數 ---
@st.cache_data(ttl=60) # 快取數據，避免頻繁刷網頁導致被交易所封鎖
def get_crypto_data(symbol, tf):
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=200)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def train_and_predict_ml(df):
    ml_df = df.copy().dropna()
    if len(ml_df) < 50: return 50.0
    
    # 計算特徵
    ml_df['EMA_20'] = ta.ema(ml_df['close'], length=20)
    ml_df['EMA_50'] = ta.ema(ml_df['close'], length=50)
    ml_df['RSI'] = ta.rsi(ml_df['close'], length=14)
    
    # 重新洗掉含有 NaN 的行
    ml_df = ml_df.dropna()
    
    features = ['EMA_20', 'EMA_50', 'RSI', 'volume']
    ml_df['Target'] = (ml_df['close'].shift(-1) > ml_df['close']).astype(int)
    
    X_train = ml_df[features].iloc[:-1]
    y_train = ml_df['Target'].iloc[:-1]
    X_current = ml_df[features].iloc[['-1']]
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    prob = model.predict_proba(X_current)[0][1]
    return round(prob * 100, 2)

def generate_llm_report(api_key, symbol, price, rsi, trend, ml_prob):
    if not api_key:
        return "⚠️ 請在左側側邊欄輸入您的 OpenAI API Key 以生成 AI 分析報告。"
    
    try:
        client = OpenAI(api_key=api_key)
        prompt = f"""
        你是一位精通加密貨幣量化交易的專業導師。
        請針對以下數據給出具體的「下單方針建議」：
        - 交易對: {symbol}
        - 當前價格: {price}
        - RSI (14): {rsi:.2f}
        - 均線趨勢: {trend}
        - ML預測未來上漲機率: {ml_prob}%
        
        請包含：盤勢點評、ML信心權重說明、明確的下單方針（止損/進場建議）。語氣請專業且睿智。
        """
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"LLM 報告生成失敗: {e}"

# --- 主程式執行流 ---
if st.button("🚀 啟動 AI 盤勢分析"):
    with st.spinner("正在獲取交易所數據並分析中..."):
        # 1. 抓取數據與計算指標
        df = get_crypto_data(target_coin, timeframe)
        df['EMA_20'] = ta.ema(df['close'], length=20)
        df['EMA_50'] = ta.ema(df['close'], length=50)
        df['RSI'] = ta.rsi(df['close'], length=14)
        
        latest = df.iloc[-1]
        trend_status = "📊 多頭排列 (Bullish)" if latest['EMA_20'] > latest['EMA_50'] else "📉 空頭排列 (Bearish)"
        
        # 2. ML 預測
        ml_probability = train_and_predict_ml(df)
        
        # --- 網頁畫面佈局 ---
        col1, col2, col3 = st.columns(3)
        col1.metric("當前價格", f"${latest['close']:,}")
        col2.metric("RSI (14)", f"{latest['RSI']:.2f}")
        col3.metric("ML 未來上漲機率", f"{ml_probability}%")
        
        st.markdown(f"**目前大盤趨勢：** {trend_status}")
        
        # 3. 繪製 K 線與均線圖表 (Plotly)
        fig = go.Figure(data=[go.Candlestick(
            x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="K線"
        )])
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_20'], line=dict(color='orange', width=1.5), name='EMA 20'))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_50'], line=dict(color='blue', width=1.5), name='EMA 50'))
        fig.update_layout(title=f"{target_coin} 歷史 K 線與技術指標", xaxis_rangeslider_visible=False, height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # 4. LLM 決策報告
        st.subheader("🎯 AI 操盤下單方針報告")
        ai_report = generate_llm_report(api_key, target_coin, latest['close'], latest['RSI'], trend_status, ml_probability)
        st.info(ai_report)
