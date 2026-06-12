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
    page_title="CryptoHunter | 爆量驅動復盤型",
    page_icon="🏹",
    layout="wide"
)

# =====================================================================
# 2. 注入黑客科技風 CSS 樣式
# =====================================================================
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3, h4 { color: #00FFCC !important; font-family: 'Courier New', monospace; }
    
    /* 爆量警告卡片 */
    .volume-anomaly-card {
        background-color: #1A1C23;
        border: 2px solid #FF9900;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 0 12px rgba(255, 153, 0, 0.2);
    }
    
    .coin-title { font-size: 22px; font-weight: bold; color: #FFF; font-family: 'Courier New', monospace; }
    .coin-price { font-size: 26px; font-weight: bold; color: #00FF66; margin: 5px 0; }
    .coin-vol { font-size: 16px; color: #FF9900; font-weight: bold; }
    .coin-change { font-size: 16px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("🏹 CryptoHunter 全網爆量雷達 ＆ AI 復盤系統")

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
st.sidebar.header("⚙️ 獵手控制台")

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
refresh_interval = st.sidebar.slider("全網雷達掃描頻率 (秒)", min_value=5, max_value=20, value=8)

st.sidebar.markdown("""
### 📡 雷達警戒觸發標準：
1. 24h 成交額 > **1,000 萬 USDT (10M)**
2. 24h 漲跌幅絕對值 > **5%**
*(符合以上條件之幣種將會自動被抓取並亮燈提醒)*
""")

# =====================================================================
# 5. AI 單次復盤鑑定核心邏輯 (gemini-2.5-flash 正式版)
# =====================================================================
def ask_gemini_replay_analysis(coin, price, change, volume, high, low):
    if not GEMINI_API_KEY:
        return "⚠️ 請先在左側邊欄輸入有效的 Gemini API Key 喔！"
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    你現在是精通加密貨幣『突發爆量/主力妖幣異動』的頂級短線量化操盤專家。
    正在對目前全網焦點爆量標的進行【實戰技術復盤】：
    - 標的幣種：{coin}/USDT
    - 當前現價：{price}
    - 24h漲跌幅：{change}%
    - 24h成交額：{volume}
    - 24h最高/最低價：{high} / {low}
    
    請用繁體中文給出極精簡、一針見血且極具實戰攻擊性的 2 句短評：
    1. 拆解該幣「突發爆量」背後的操盤手/主力心理狀態（是機構吸籌、主力拉高出貨、動能突破還是散戶踩踏踩踏）。
    2. 給出【下一個階段最具體的操作開盤方針與潛在埋伏點】（如：切勿追高建議逢高分批進空、短線跟隨動能突破輕倉追多、或是正值極端行情建議冷靜觀望），並附帶精準的止損/防守提示。
    """
        
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        data = response.json()
        
        if 'error' in data:
            err_msg = data['error'].get('message', '未知錯誤')
            if "API key not valid" in err_msg:
                return "❌ 【API Key 錯誤】請檢查左側輸入的金鑰。"
            elif "Resource has been exhausted" in err_msg:
                return "⏳ 【頻率超限】免費額度已滿，請等待 15 秒後再次點擊復盤。"
            return f"❌ Google 拒絕原因: {err_msg}"
            
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"⚠️ 網路傳輸異常 ({e})"

# =====================================================================
# 6. 主畫面佈局分流（左側雷達提醒，右側復盤研究室）
# =====================================================================
col_radar, col_replay = st.columns([7, 5])

with col_replay:
    st.subheader("🔬 AI 策略復盤研究室")
    st.write("🔍 當左側雷達跳出爆量警報時，可在這裡輸入該幣種進行 AI 單次復盤評估。")
    
    # 復盤輸入視窗（讓用戶手動輸入或選擇）
    replay_coin = st.text_input("輸入要復盤的幣種代號（例如: SOL, DOGE, XRP）", value="SOL").strip().upper()
    btn_replay = st.button("🏹 啟動 AI 獵手復盤鑑定", use_container_width=True)
    
    replay_placeholder = st.container()

# 左側雷達主循環
with col_radar:
    st.subheader("🚨 全網突發【爆量異動】主動雷達")
    radar_placeholder = st.empty()

# =====================================================================
# 7. 數據循環監控區
# =====================================================================
while True:
    try:
        all_tickers = exchange.fetch_tickers()
        volume_anomalies = []
        target_replay_data = None  # 用於儲存當前被復盤幣種的即時數據
        
        # 遍歷全市場篩選「爆量異動幣」
        for symbol, ticker in all_tickers.items():
            if not symbol.endswith('/USDT') or ':' in symbol:
                continue
                
            current_price = ticker['last']
            change_pct = ticker['percentage'] if ticker['percentage'] is not None else 0.0
            high_24h = ticker['high']
            low_24h = ticker['low']
            vol_base_24h = ticker['baseVolume'] if ticker['baseVolume'] else 0
            vol_usdt_24h = ticker['quoteVolume'] if ticker['quoteVolume'] else (vol_base_24h * current_price)
            
            coin_clean = symbol.replace('/USDT', '')
            
            # 1. 檢查是否符合目前用戶正在復盤的幣種數據
            if coin_clean == replay_coin:
                target_replay_data = {
                    "symbol": coin_clean,
                    "price": current_price,
                    "change": change_pct,
                    "volume": f"{vol_usdt_24h / 1000000:.2f}M USDT",
                    "high": high_24h,
                    "low": low_24h
                }
            
            # 2. 觸發雷達標準：成交額 > 10M 且 漲跌幅絕對值 > 5%
            if vol_usdt_24h >= 10000000 and (change_pct > 5 or change_pct < -5):
                volume_anomalies.append({
                    "symbol": coin_clean,
                    "price": current_price,
                    "change": change_pct,
                    "volume_usdt": vol_usdt_24h,
                    "volume_str": f"{vol_usdt_24h / 1000000:.1f}M USDT",
                    "high": high_24h,
                    "low": low_24h
                })

        # 按成交額從大到小排序
        volume_anomalies = sorted(volume_anomalies, key=lambda x: x['volume_usdt'], reverse=True)

        # 渲染左側雷達大方塊
        with radar_placeholder.container():
            st.write(f"⏱ *雷達動態更新：* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
            st.markdown("---")
            
            if volume_anomalies:
                # 每排顯示 2 個爆量大方塊
                radar_cols = st.columns(2)
                for idx, coin in enumerate(volume_anomalies):
                    tgt_col = radar_cols[idx % 2]
                    with tgt_col:
                        c_color = "#00FF66" if coin['change'] >= 0 else "#FF3366"
                        c_sign = "+" if coin['change'] >= 0 else ""
                        
                        st.markdown(f"""
                            <div class="volume-anomaly-card">
                                <div class="coin-title">🔥 爆量突擊: {coin['symbol']}/USDT</div>
                                <div class="coin-price">${coin['price']:,}</div>
                                <div class="coin-change" style="color: {c_color};">{c_sign}{coin['change']}%</div>
                                <div class="coin-vol">📊 24h 成交額: {coin['volume_str']}</div>
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.success("🔍 市場目前風平浪靜，尚未偵測到 24h 成交額 > 10M 且波動 > 5% 的爆量標的。")

        # 處理右側復盤視窗的單次 AI 點擊觸發
        if btn_replay:
            with replay_placeholder:
                if target_replay_data:
                    st.info(f"📊 **正在對 {target_replay_data['symbol']}/USDT 進行量化結構調研...**")
                    st.write(f"當前現價: `{target_replay_data['price']}` | 漲跌幅: `{target_replay_data['change']}%` | 24h總量: `{target_replay_data['volume']}`")
                    
                    with st.spinner("⚔️ AI 獵手正在解構大單資金流與主力心理..."):
                        ai_report = ask_gemini_replay_analysis(
                            target_replay_data['symbol'],
                            target_replay_data['price'],
                            target_replay_data['change'],
                            target_replay_data['volume'],
                            target_replay_data['high'],
                            target_replay_data['low']
                        )
                        st.error(f"⚔️ **AI 實戰復盤報告 ({target_replay_data['symbol']}):**\n{ai_report}")
                else:
                    st.warning(f"⚠️ 在 OKX 市場中暫時找不到 `{replay_coin}/USDT` 的即時數據，請檢查代號是否輸入正確。")
            # 點擊完畢後重置狀態，防止無限制循環觸發 API
            btn_replay = False

        # 全網雷達循環冷卻
        time.sleep(refresh_interval)
        
    except Exception as e:
        time.sleep(5)
