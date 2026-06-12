import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime
import google.generativeai as genai

# =====================================================================
# 1. 網頁頂級配置（必須在最前面）
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
        min-height: 250px; /* 強制高度，形成大方塊 */
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

st.title("🏹 CryptoHunter AI 雙核心獵手系統")
st.markdown("`[雷達模式: 全網監控]` 自選幣種已全面升級為正方形大面板，右側即時偵測全網爆量異動標的。")

# =====================================================================
# 3. 交易所與 AI 初始化（安全防禦機制）
# =====================================================================
@st.cache_resource
def get_exchange():
    return ccxt.okx() # 使用 OKX 完美避開 451 區域限制錯誤

exchange = get_exchange()

# --- 【安全密鑰讀取機制】 ---
# 優先嘗試讀取 Streamlit 雲端設定的 Secrets (放上網路時用)
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets
