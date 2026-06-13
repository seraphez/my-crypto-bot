import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
from groq import Groq
import os

# --- 1. 🌸 櫻花風視覺自訂與頁面設定 (手機優先 centered 排版) ---
st.set_page_config(page_title="🌸 SMC 櫻花獵鯨網", layout="centered")

# 使用 HTML/CSS 注入，將全站打造成高質感櫻花粉與曜石黑結合的操盤介面
st.markdown("""
    <style>
        /* 全域背景與文字顏色設定 */
        .stApp {
            background-color: #121214;
            color: #F8F9FA;
        }
        /* 標題與副標題漸層色 (櫻花粉) */
        h1 {
            color: #FFB7C5 !important;
            font-family: 'Helvetica Neue', sans-serif;
            text-shadow: 0px 0px 12px rgba(255, 183, 197, 0.4);
        }
        h2, h3 {
            color: #FFD1DC !important;
        }
        /* 側邊欄櫻花底色調整 */
        [data-testid="stSidebar"] {
            background-color: #1C1A1D;
            border-right: 2px solid #FFB7C5;
        }
        /* 啟動按鈕 - 超美櫻花粉漸層 */
        div.stButton > button:first-child {
            background: linear-gradient(135deg, #FFB7C5 0%, #FFD1DC 100%);
            color: #121214 !important;
            font-weight: bold !important;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            box-shadow: 0px 4px 15px rgba(255, 183, 197, 0.4);
            transition: all 0.3s ease;
            width: 100%;
        }
        div.stButton > button:first-child:hover {
            transform: translateY(-2px);
            box-shadow: 0px 6px 20px rgba(255, 183, 197, 0.6);
            background: linear-gradient(135deg, #FFD1DC 0%, #FFB7C5 100%);
        }
        /* 提示框與資訊框樣式 */
        .stAlert {
            background-color: #242124 !important;
            border: 1px solid #FFB7C5 !important;
            color: #FFD1DC !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🌸 獵鯨網 · 暮櫻多週期實戰系統")

# --- 2. 側邊欄：自由選擇幣種與參數 ---
st.sidebar.markdown("### 🌸 櫻花大腦核心設定")

# 讓用戶可以自己選擇主流幣，或者手動輸入任何特殊幣種
coin_option = st.sidebar.selectbox("選擇交易標的", ["SOL/USDT", "BTC/USDT", "ETH/USDT", "BNB/USDT", "自訂輸入..."])

if coin_option == "自訂輸入...":
    target_coin = st.sidebar.text_input("請輸入自訂幣對 (例如 XRP/USDT)", value="XRP/USDT").upper()
else:
    target_coin = coin_option

# 100 倍槓桿實戰參數
leverage = 100

st.sidebar.markdown("---")
st.sidebar.markdown(f"**🔥 執行槓桿:** {leverage}x")

# --- 🔒 終極安全金鑰避錯機制 (拋棄 st.secrets 直接調用，改用原生檢測) ---
SAFE_GROQ_API_KEY = ""

# 先用原生 Python 偵測硬碟上有沒有 Streamlit 規定的 secrets.toml 檔案路徑
# 這樣可以 100% 避免在 Codespaces 本地測試時觸發 Streamlit 的強制崩潰機制
possible_secrets_path = os.path.expanduser("~/.streamlit/secrets.toml")
local_project_secrets = os.path.join(os.getcwd(), ".streamlit", "secrets.toml")

if os.path.exists(possible_secrets_path) or os.path.exists(local_project_secrets):
    try:
        # 只有確認檔案存在時，才允許去執行 st.secrets 讀取 (這是在線上版 Streamlit Cloud 的運行邏輯)
        if "GROQ_API_KEY" in st.secrets:
            SAFE_GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    except Exception:
        SAFE_GROQ_API_KEY = ""

# 備份機制：如果檔案不存在但操作系統有設定環境變數，直接讀取
if not SAFE_GROQ_API_KEY:
    SAFE_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# 完美本地相容防呆：如果上面兩種方法都拿不到金鑰 (代表處於 Codespaces 本地乾淨測試環境)
# 自動在網頁左側開啟臨時輸入框供你偵錯，線上版部署後會因為讀到 Secrets 而自動完全隱形！
if not SAFE_GROQ_API_KEY:
    st.sidebar.markdown("---")
    st.sidebar.warning("🔑 偵測到本地開發環境：")
    temp_key = st.sidebar.text_input("請填入臨時測試 Groq Key", type="password")
    if temp_key:
        SAFE_GROQ_API_KEY = temp_key

# --- 3. 實時交易所數據撈取函數區 ---

def fetch_single_timeframe_data(exchange, symbol, tf):
    """安全撈取單一週期的即時盤面數據"""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=50)
        df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
        # 計算實時 RSI
        df['rsi'] = ta.rsi(df['c'], length=14)
        latest = df.iloc[-1]
        
        # 抓取近 24 根 K 線區間的最高與最低
        high_24h = df['h'].iloc[-24:].max()
        low_24h = df['l'].iloc[-24:].min()
        
        return {
            "price": round(latest['c'], 4),
            "rsi": round(latest['rsi'], 2) if not pd.isna(latest['rsi']) else 50.0,
            "high": round(high_24h, 4),
            "low": round(low_24h, 4)
        }
    except Exception:
        return {"price": "未知", "rsi": 50.0, "high": "未知", "low": "未知"}

# --- 4. 核心大模型驅動函數區 (四大時間週期全維掃描) ---

def generate_multi_timeframe_report(api_key, symbol, data_3m, data_15m, data_1h, data_4h):
    """請求 Groq 最新旗艦大模型，同時對 3m/15m/1h/4h 四大週期進行多維聯動掃描"""
    try:
        client = Groq(api_key=api_key.strip())
        
        prompt = f"""
        你現在是一位精通加密貨幣 SMC 機構智慧訂單塊（Order Block）、清算池（Liquidity Pool）佈局，且精通「隨機森林機器學習多週期聯動演算法」的傳奇對衝基金量化操盤總監。
        學生目前正在進行高強度的 {leverage} 倍槓桿實戰，操盤幣種為：【{symbol}】。
        
        【🔥 來自幣安交易所的即時真實硬數據】
        - 🎯 3m (當前最新市價): {data_3m['price']} USDT | 實時RSI: {data_3m['rsi']}
        - ⏱️ 15m (動能區間): 收盤 {data_15m['price']} | 實時RSI: {data_15m['rsi']}
        - 📊 1h (波段區間): 收盤 {data_1h['price']} | 24h最高 {data_1h['high']} | 24h最低 {data_1h['low']}
        - 📈 4h (大趨勢線): 收盤 {data_4h['price']}
        
        請立刻啟動你的 AI 滾動式自我學習回測機制，對上述四個真實時間週期數據進行全局聯動掃描與結構精算：
        
        【❌ ⚠️ 鐵律：你必須基於上面給出的真實價格 {data_3m['price']} 作為基準，算出具體的實戰下單數字，絕對不允許偏離當前價格太遠，也不允許胡言亂語！】
        
        【請嚴格按照以下格式輸出櫻花風格戰術報告】
        
        ### 🌸 一、 四大週期多維聯動掃描
        - **【4h 級別大局觀】**：（結合真實價格 {data_4h['price']} 點評大級別多空方向）
        - **【1h 級別結構塊】**：（尋找機構關鍵支撐與阻力，參考 24h高低點）
        - **【15m 級別動能監測】**：（分析實時 RSI {data_15m['rsi']} 處於超買、超賣還是中心區？）
        - **【3m 級別 AI 自學勝率】**：（大膽給出機器學習模擬出的預測歷史準確率(%)與當前方向勝率(%)）
        
        ### 🎯 二、 櫻花分批佈局行動清單 (基於實時市價 {data_3m['price']} 精確計算)
        - **核心交易方向**: (做多 Long / 做空 Short)
        - **📍 第一激進進場點 (分配 35% 倉位)**: (給出具體計算出的價格數字，必須與當前價格相近)
        - **📍 第二防禦埋伏點 (分配 65% 倉位)**: (給出具體計算出的價格數字，用於左側防禦補倉)
        - **🛑 鋼鐵清算止損線 (強制全平)**: (給出絕對不能被突破的極限防守價格數字)
        
        ### 💰 三、 風險報酬與分批止盈藍圖
        - **第一目標止盈 (TP1 - 平倉 50%)**: (給出具體獲利點價格數字)
        - **第二爆發止盈 (TP2 - 全平離場)**: (給出具體獲利點價格數字)
        - **本次戰術盈虧比評估**: (計算盈虧比數字，並指出這筆交易是否符合高盈虧比邏輯)
        
        ### 🦅 四、 總監鋼鐵心態控管
        （留下一句針對 {leverage}x 高槓桿操作，冷靜、孤高且充滿智慧的交易格言）
        """
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "user", "content": prompt}], 
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ AI 櫻花大腦掃描失敗，錯誤訊息: {e}"

def get_mentorship_feedback(api_key, user_answer, question, symbol, current_price):
    """AI 導師親自批改考驗室回答"""
    try:
        client = Groq(api_key=api_key.strip())
        prompt = f"""
        你是操盤總監。學生在考驗室裡針對你提出的問題：'{question}' 進行了交卷。
        學生的回答內容是：'{user_answer}'。
        目前學生正在操盤的標的是：{symbol}，當前即時市價為 {current_price} USDT，配合 {leverage} 倍槓桿。
        請用極其銳利、直接、且富有操盤大師風範的語氣批改他的交易心理，指出他是在盲目貪婪（Fomo）、恐懼，還是具備合格的鋼鐵紀律。
        """
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "user", "content": prompt}], 
            temperature=0.4
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ 總監考驗室系統連線失敗: {e}"

# --- 5. 主程式執行邏輯 ---
st.markdown(f"### 📍 當前掃描標的: `{target_coin}`")

if st.button("🌸 啟動四大週期聯動掃描"):
    if not SAFE_GROQ_API_KEY:
        st.error("❌ 偵測不到密鑰！請先在左側欄填入您的臨時測試 Groq Key 才能啟動本地掃描。")
    else:
        with st.spinner(f"🌸 正在連線幣安交易所，同步抓取 3m、15m、1h、4h 真實價格與 RSI 指標..."):
            try:
                # 初始化交易所
                exchange = ccxt.binance()
                
                # 安全獲取四大週期實時數據
                data_3m = fetch_single_timeframe_data(exchange, target_coin, "3m")
                data_15m = fetch_single_timeframe_data(exchange, target_coin, "15m")
                data_1h = fetch_single_timeframe_data(exchange, target_coin, "1h")
                data_4h = fetch_single_timeframe_data(exchange, target_coin, "4h")
                
                st.session_state.current_real_price = data_3m['price']
                
                # 數據看板呈現
                st.markdown("### 📊 幣安交易所即時行情")
                col1, col2, col4 = st.columns(3)
                col1.metric("當前實時市價", f"${data_3m['price']} USDT")
                col2.metric("15m 實時 RSI", f"{data_15m['rsi']}")
                col4.metric("24h 最高 / 最低", f"${data_1h['high']} / ${data_1h['low']}")
                
                st.success(f"✅ 真實行情聯動成功！已將當前最新市價 ${data_3m['price']} 發送至 AI 總監大腦進行精算。")
                
                # 呼叫多週期聯動大模型生成戰術報告
                st.markdown("---")
                st.subheader("🎯 AI 總監四維矩陣點位決策報告")
                report = generate_multi_timeframe_report(
                    api_key=SAFE_GROQ_API_KEY, symbol=target_coin,
                    data_3m=data_3m, data_15m=data_15m, data_1h=data_1h, data_4h=data_4h
                )
                st.markdown(report)
                
            except Exception as e:
                st.error(f"💥 櫻花系統運行發生崩潰: {e}")

# --- 6. 總監問答考驗室 ---
st.markdown("---")
st.subheader("🎓 🌸 暮櫻操盤手心理考驗室")
challenge_question = f"當 {target_coin} 在 4h 級別處於狂暴空頭趨勢（大盤暴跌），但在 3m 小級別剛剛踩到一個 SMC 智慧訂單塊支撐時，你會選擇『嚴格按照計畫進場接刀做多』，還是『順應 4h 大趨勢直接反手追空』？請說明你的資金風控理由。"
st.info(f"**本期思維考題：**\n{challenge_question}")

user_answer = st.text_area("在下方寫下你的真實交易邏輯與心態思考...", height=100)
if st.button("📤 提交思考給總監批改"):
    if not SAFE_GROQ_API_KEY:
        st.warning("⚠️ 密鑰未設定，無法交卷。")
    elif not user_answer:
        st.warning("⚠️ 考卷不能留白，請輸入您的思維。")
    else:
        with st.spinner("🌸 總監正在審閱你的操盤心境，進行思維診斷中..."):
            real_price_now = st.session_state.get('current_real_price', '獲取中')
            feedback = get_mentorship_feedback(
                api_key=SAFE_GROQ_API_KEY, 
                user_answer=user_answer, 
                question=challenge_question,
                symbol=target_coin,
                current_price=real_price_now
            )
            st.success("### 🦅 總監親筆批改回饋：")
            st.markdown(feedback)

st.markdown("---")
st.markdown(f"""
### 💡 🌸 暮櫻操盤鋼鐵指令：
1. **多週期共振：** 永遠不要只看單一週期，4h 看方向、1h 看區間、15m 看動能、3m 精算佈局點。
2. **無條件風控：** {leverage} 倍槓桿是一把雙面利刃，若進場防守位被跌破並觸發強制止損線，立刻平倉，絕不抗單！
3. **心態修煉：** 櫻花最美在於落下的果斷，合格的交易員停損與止盈時也應同樣果斷。
""")
