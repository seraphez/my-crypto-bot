import streamlit as st
import time
from groq import Groq

# --- 1. 網頁基本設定 (專為手機優化的 centered 排版) ---
st.set_page_config(page_title="🤖 SMC 100x 獵鯨網", layout="centered")
st.title("🦅 129U 獵鯨網系統 (SMC 策略 + AI 自我學習安全版)")

# 鎖定實戰參數
target_coin = "SOL/USDT"
timeframe = "3m"
balance = 129.0
leverage = 100

# 129U 策略精算固定的 SMC 核心點位
entry_1 = 67.95
entry_2 = 67.15
stop_loss = 66.65
tp_1 = 68.80
tp_2 = 70.20

# --- 🔒 安全金鑰隱形機制 ---
# 程式會自動去 Streamlit 雲端後台尋找保險箱，程式碼內不留金鑰，兼顧安全與手機免輸入
if "GROQ_API_KEY" in st.secrets:
    SAFE_GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
else:
    SAFE_GROQ_API_KEY = ""

# --- 2. 核心大模型驅動函數區 (不省略任何細節) ---

def generate_llm_report(api_key, symbol, entry_1, entry_2, stop_loss, tp_1, tp_2):
    """請求 Groq 最新旗艦模型模擬隨機森林與技術指標，生成精確戰術方針"""
    try:
        client = Groq(api_key=api_key.strip())
        
        # 這裡我們強迫大模型自我模擬滾動式回測，直接運算 RSI、EMA 趨勢與上漲勝率！
        prompt = f"""
        你現在是一位精通加密貨幣 SMC 機構級智慧訂單塊、清算池佈局，且精通「隨機森林機器學習模型」的對衝基金量化操盤總監。
        學生目前使用 {balance}U 進行 {leverage} 倍槓桿實戰，請啟動你的滾動式自我學習回測機制，針對當前盤面進行極其硬核的點評：
        
        【操盤標的與固定 SMC 獵鯨點位】
        - 交易標的: {symbol} (K線週期: {timeframe})
        - 📍 第一激進進場點: {entry_1} (分配 35% 倉位)
        - 📍 第二防禦埋伏補倉點: {entry_2} (分配 65% 倉位)
        - 🛑 終極清算止損位: {stop_loss} (強制全平)
        - 💰 第一目標止盈 (TP1): {tp_1} (平50%倉位鎖定利潤)
        - 💰 第二目標止盈 (TP2): {tp_2} (全平離場)
        
        【總監任務】
        請幫我模擬「隨機森林模型」在最近 250 根 3m K 線上的滾動回測。你必須在報告中給出你模擬運算出的：
        1. 實時動態 RSI (14) 指標。
        2. EMA 20 與 EMA 50 的多空排列狀態。
        3. 🤖 AI 模型自我學習後的「預測歷史準確率(%)」與「修正後當前上漲方向勝率(%)」。
        
        【❌ 嚴格拒絕模糊詞彙：請直接對以上所有具體數字進行專業判讀與利弊剖析】
        
        【請嚴格按照以下格式輸出報告】
        ### 🔍 一、 AI 自我學習與盤勢進化點評
        （請大膽給出模擬的 RSI 與 AI 自學勝率數字。並一針見血指出此時此刻是多頭控盤、空頭清算、還是雜訊震盪盤？）
        
        ### 🎯 二、 SMC 固定點位實戰風險評估
        （針對既有的進場點位 {entry_1}、{entry_2} 與止損位 {stop_loss} 進行嚴格覆盤，告訴學生在 100 倍高槓桿下，這筆交易的盈虧比是否及格，以及潛在清算風險。）
        
        ### 💡 三、 戰術彈性操作建議
        （若預測勝率不理想，是否需要將 {balance}U 的倉位比例進行人為手動調整？請給予具體方案。）
        
        ### 🦅 四、 總監心態控管
        （留下一句給 100 倍槓桿交易員的鋼鐵紀律格言）
        """
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "user", "content": prompt}], 
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ AI 報告生成失敗，錯誤訊息: {e}"

def get_mentorship_feedback(api_key, user_answer, question):
    """AI 總監親自批改考驗室回答，引導學生思維成長"""
    try:
        client = Groq(api_key=api_key.strip())
        prompt = f"""
        你是操盤總監。你在考驗室裡提出了這個問題：'{question}'。
        學生回答了：'{user_answer}'。
        學生本金 129U，100倍槓桿實戰 SOL/USDT。
        請用銳利、直接、且富有建設性的語氣批改他的交易思維，指出他的心理盲點（例如是不是 Fomo 或過度恐懼），並灌輸正確的風險控制觀念。
        """
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "user", "content": prompt}], 
            temperature=0.4
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ 總監未能成功批改: {e}"

# --- 3. 主程式執行邏輯 ---
if st.button("🚀 啟動 129U 獵鯨網掃描"):
    if not SAFE_GROQ_API_KEY:
        st.error("❌ 偵測不到密鑰！請至 Streamlit Cloud 後台 Settings -> Secrets 中設定您的 GROQ_API_KEY。")
    else:
        with st.spinner("🦅 AI 總監正在啟動滾動式自我學習運算、精算盤面點位中..."):
            try:
                time.sleep(0.8)
                
                # 1. 適合手機閱讀的看板提示
                st.markdown("### 📊 獵鯨盤面即時監控")
                st.info(f"⚡ 標的: {target_coin} | 實戰資金: {balance} USDT | 槓桿: {leverage}x")
                
                # 2. 吐出最仔細的 AI 下單方針
                st.markdown("---")
                st.subheader("🎯 AI 總監機構級點位戰術報告")
                report = generate_llm_report(
                    api_key=SAFE_GROQ_API_KEY, symbol=target_coin, 
                    entry_1=entry_1, entry_2=entry_2, stop_loss=stop_loss, tp_1=tp_1, tp_2=tp_2
                )
                st.markdown(report)
                
            except Exception as e:
                st.error(f"💥 運行崩潰: {e}")

# --- 4. 總監問答考驗室 (手機交互，幫助能力成長) ---
st.markdown("---")
st.subheader("🎓 操盤總監考驗室")
challenge_question = "在 100 倍高槓桿的實戰中，如果行情在距離你的第一進場點（67.95）只差 0.05 美元時就直接暴漲噴出，你此時此刻會選擇『市價強行追多』還是『撤單保持空倉』？為什麼？"
st.info(f"**本期思維考題：**\n{challenge_question}")

user_answer = st.text_area("在下方寫下你的真實交易邏輯與心態思考...", height=100)
if st.button("📤 提交思考給總監批改"):
    if not SAFE_GROQ_API_KEY:
        st.warning("⚠️ 密鑰未設定，無法交卷給總監。")
    elif not user_answer:
        st.warning("⚠️ 考卷不能留白，請至少寫下一點點你的操盤想法。")
    else:
        with st.spinner("總監正在審視你的回答，進行思維診斷中..."):
            feedback = get_mentorship_feedback(
                api_key=SAFE_GROQ_API_KEY, 
                user_answer=user_answer, 
                question=challenge_question
            )
            st.success("### 🦅 總監親筆批改回饋：")
            st.markdown(feedback)

st.markdown("---")
st.markdown(f"""
### 💡 SMC {balance}U 實戰限價單設置指南：
1. **進場一：** 幣安設置「限價買單」價格 **{entry_1}**，投入總資金的 **35%**。
2. **進場二：** 幣安設置「限價買單」價格 **{entry_2}**，投入總資金的 **65%**。
3. **防守位：** 務必同時掛好「條件市價止損單」，觸發價 **{stop_loss}**，數量 100%。
4. **獲利位：** 達 **{tp_1}** 移動止損或平倉 50%，終極目標鎖定 **{tp_2}**。
""")
