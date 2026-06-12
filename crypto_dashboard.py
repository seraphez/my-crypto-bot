import streamlit as st
import pandas as pd
import ccxt
import pandas_ta as ta
import time
from sklearn.ensemble import RandomForestClassifier
from openai import OpenAI
import plotly.graph_objects as go

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="🤖 AI Crypto Dashboard", layout="wide")
st.title("🤖 AI 加密貨幣盤勢識別與下單方針系統")

# --- 2. 側邊欄：使用者參數輸入 ---
st.sidebar.header("⚙️ 參數設定")
api_key = st.sidebar.text_input("1. 輸入 OpenAI API Key", type="password", help="請輸入您的 OpenAI API 金鑰以啟用 AI 報告功能")
target_coin = st.sidebar.selectbox("2. 選擇交易對", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"])
timeframe = st.sidebar.selectbox("3. K線週期", ["1h", "4h", "1d"])

# --- 3. 核心功能函數 ---

@st.cache_data(ttl=60)  # 快取數據 60 秒，避免重複刷新網頁導致交易所封鎖 IP
def get_crypto_data(symbol, tf):
    """從 Binance 交易所獲取歷史 K 線資料"""
    exchange = ccxt.binance()
    # 抓取 200 根 K 線，提供充足數據給技術指標與 ML 訓練
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=200)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def train_and_predict_ml(df):
    """使用隨機森林模型，預測下一根 K 線上漲的機率"""
    ml_df = df.copy().dropna()
    if len(ml_df) < 50: 
        return 50.0  # 數據量不足時返回中性機率
    
    # 計算模型要學習的特徵 (Features)
    ml_df['EMA_20'] = ta.ema(ml_df['close'], length=20)
    ml_df['EMA_50'] = ta.ema(ml_df['close'], length=50)
    ml_df['RSI'] = ta.rsi(ml_df['close'], length=14)
    ml_df = ml_df.dropna()  # 清除計算指標產生的空值
    
    features = ['EMA_20', 'EMA_50', 'RSI', 'volume']
    
    # 定義目標 (Target)：下一根收盤價高於當前收盤價則為 1 (漲)，否則為 0 (跌)
    ml_df['Target'] = (ml_df['close'].shift(-1) > ml_df['close']).astype(int)
    
    # 拆分訓練集與當前特徵
    X_train = ml_df[features].iloc[:-1]
    y_train = ml_df['Target'].iloc[:-1]
    X_current = ml_df[features].iloc[[-1]]
    
    # 訓練隨機森林
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # 預測上漲機率
    prob = model.predict_proba(X_current)[0][1]
    return round(prob * 100, 2)

def generate_llm_report(api_key, symbol, price, rsi, trend, ml_prob):
    """將所有數據打包丟給 OpenAI GPT 生成專業的下單方針"""
    if not api_key:
        return "⚠️ 請在左側側邊欄輸入您的 OpenAI API Key，即可解鎖 AI 深度操盤報告！"
    
    try:
        client = OpenAI(api_key=api_key)
        prompt = f"""
        你是一位精通加密貨幣量化交易與技術分析的頂級基金操盤導師。
        請針對以下即時市場數據進行深度剖析，並為學生撰寫一份具體的「下單方針建議」：
        
        【市場即時數據】
        - 交易對: {symbol}
        - 當前價格: {price}
        - RSI (14): {rsi:.2f}
        - 均線趨勢: {trend}
        - 機器學習預測: 未來一個週期內上漲機率為 {ml_prob}%
        
        【報告要求】
        1. 盤勢點評：用白話、專業且有條理的口吻解釋目前的市場心理與盤勢（超買、超賣、或正在蓄勢？）。
        2. 綜合評估：結合技術指標與機器學習的上漲機率，解讀當前的多空力道。
        3. 具體下單方針：給出明確的行動指南（例如：現價分批進場多單、嚴格止損位設在何處、或目前建議空倉觀望）。
        4. 語氣請保持冷靜、客觀，並在結尾送給學生一句交易員的心態鼓勵。
        """
        response = client.chat.completions.create(
            model="gpt-4o",  # 使用性能強大的 gpt-4o 模型
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ LLM 報告生成失敗，錯誤訊息: {e}"

# --- 4. 主程式執行邏輯 ---
if st.button("🚀 啟動 AI 盤勢分析與方針制定"):
    with st.spinner("🤖 AI 正在調取交易所數據並進行大腦思維分析，請稍候..."):
        try:
            # 模擬一下分析的加載感
            time.sleep(1)
            
            # 1. 獲取數據與計算網頁呈現用的指標
            df = get_crypto_data(target_coin, timeframe)
            df['EMA_20'] = ta.ema(df['close'], length=20)
            df['EMA_50'] = ta.ema(df['close'], length=50)
            df['RSI'] = ta.rsi(df['close'], length=14)
            
            latest = df.iloc[-1]
            trend_status = "📈 多頭排列 (上漲趨勢)" if latest['EMA_20'] > latest['EMA_50'] else "📉 空頭排列 (下跌趨勢)"
            
            # 2. 執行機器學習預測
            ml_probability = train_and_predict_ml(df)
            
            # 3. 網頁數據看板呈現
            st.markdown("### 📊 即時數據監控")
            col1, col2, col3 = st.columns(3)
            col1.metric("當前價格 (USDT)", f"${latest['close']:,}")
            col2.metric("RSI (14) 指標", f"{latest['RSI']:.2f}")
            col3.metric("AI 模型預測上漲機率", f"{ml_probability}%")
            
            st.write(f"**市場均線狀態：** {trend_status}")
            
            # 4. 繪製 K 線圖與均線 (Plotly 互動式圖表)
            fig = go.Figure(data=[go.Candlestick(
                x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="K線"
            )])
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_20'], line=dict(color='orange', width=1.5), name='EMA 20 (短均線)'))
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['EMA_50'], line=dict(color='blue', width=1.5), name='EMA 50 (長均線)'))
            fig.update_layout(title=f"{target_coin} 實時 K 線與移動平均線圖", xaxis_rangeslider_visible=False, height=450)
            st.plotly_chart(fig, use_container_width=True)
            
            # 5. 生成並顯示大模型決策報告
            st.markdown("---")
            st.subheader("🎯 AI 操盤下單方針報告")
            ai_report = generate_llm_report(
                api_key=api_key, 
                symbol=target_coin, 
                price=latest['close'], 
                rsi=latest['RSI'], 
                trend=trend_status, 
                ml_prob=ml_probability
            )
            st.info(ai_report)
            
        except Exception as e:
            st.error(f"💥 執行過程中發生錯誤: {e}")
