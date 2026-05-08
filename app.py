import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai

# --- Page Setup ---
st.set_page_config(page_title="Elite Quant Dashboard", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .stMetric {background-color: #f0f2f6; padding: 15px; border-radius: 10px;}
    .stExpander {border: 1px solid #e6e9ef; border-radius: 10px;}
    </style>
""", unsafe_allow_html=True)

st.title("📈 Elite Quant Dashboard & Auto-Evolving AI")

# --- API Setup ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model_name = next((m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods), "gemini-1.5-flash")
        model = genai.GenerativeModel(model_name)
    else:
        st.sidebar.warning("⚠️ API Key Missing! Settings > Secrets mein daalein.")
except Exception as e:
    pass

# --- File Uploader ---
uploaded_files = st.file_uploader("📥 Upload Dhan or Delta CSV (Upload older files too for AI evolution)", accept_multiple_files=True, type=['csv'])

if uploaded_files:
    df_list = [pd.read_csv(f) for f in uploaded_files]
    df = pd.concat(df_list, ignore_index=True)
    
    st.markdown("---")
    
    df['P&L_Clean'] = 0.0
    df['Date_Clean'] = pd.NaT
    wins, losses, total_pnl = 0, 0, 0.0
    currency = "₹"
    analytics_df = pd.DataFrame()
    
    # ---------------------------------------------
    # 1. CORE DATA ENGINE
    # ---------------------------------------------
    if 'Time' in df.columns and 'Realised P&L' in df.columns:
        # DELTA LOGIC
        df['Date_Clean'] = pd.to_datetime(df['Time'].astype(str).str[:10], errors='coerce').dt.date
        df['P&L_Clean'] = pd.to_numeric(df['Realised P&L'], errors='coerce').fillna(0) * 85
        actual_trades = df[df['P&L_Clean'] != 0].copy()
        wins = len(actual_trades[actual_trades['P&L_Clean'] > 0])
        losses = len(actual_trades[actual_trades['P&L_Clean'] < 0])
        total_pnl = actual_trades['P&L_Clean'].sum()
        
        analytics_df = actual_trades.copy()
        analytics_df['Asset'] = analytics_df['Contract']
        analytics_df['Trade_Time'] = pd.to_datetime(analytics_df['Time'].astype(str).str[:19], errors='coerce')

    elif 'Date' in df.columns and 'Trade Value' in df.columns:
        # DHAN LOGIC
        df = df[df['Buy/Sell'].astype(str).str.upper().isin(['BUY', 'SELL'])].copy()
        df['Date_Clean'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        df['Cashflow'] = df.apply(lambda r: r['Trade Value'] if str(r['Buy/Sell']).upper() == 'SELL' else -r['Trade Value'], axis=1)
        
        # Group to find NET Trade PnL and use the closing Time
        dhan_grouped = df.groupby(['Date_Clean', 'Name']).agg({'Cashflow': 'sum', 'Time': 'max'}).reset_index()
        analytics_df = dhan_grouped[dhan_grouped['Cashflow'] != 0].copy()
        analytics_df.rename(columns={'Cashflow': 'P&L_Clean', 'Name': 'Asset'}, inplace=True)
        analytics_df['Trade_Time'] = pd.to_datetime(analytics_df['Time'], format='mixed', errors='coerce')
        
        wins = len(analytics_df[analytics_df['P&L_Clean'] > 0])
        losses = len(analytics_df[analytics_df['P&L_Clean'] < 0])
        total_pnl = analytics_df['P&L_Clean'].sum()

    # --- TOP METRICS ---
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    st.subheader("📊 Performance Matrix")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Net P&L ({currency})", f"{total_pnl:,.2f}")
    c2.metric("Win Rate", f"{win_rate:.1f}%")
    c3.metric("Losing Trades", losses)
    c4.metric("Profitable Trades", wins)

    # ---------------------------------------------
    # 2. VISUAL GRAPHICS ENGINE (NEW)
    # ---------------------------------------------
    if not analytics_df.empty:
        # FIX: Clean and shorten asset names so they don't look messy
        analytics_df['Asset'] = analytics_df['Asset'].astype(str).apply(lambda x: x[:15] + ".." if len(x) > 15 else x)
        
        st.markdown("---")
        st.subheader("👁️ Visual Data Insights")
        
        # Chart 1: Equity Curve (Hover Disabled)
        daily = analytics_df.groupby('Date_Clean')['P&L_Clean'].sum().reset_index()
        daily['Equity Curve'] = daily['P&L_Clean'].cumsum()
        fig_eq = px.area(daily, x='Date_Clean', y='Equity Curve', title="📈 Portfolio Growth (Equity Curve)")
        fig_eq.update_layout(hovermode=False) # Hover off
        st.plotly_chart(fig_eq, use_container_width=True)
        
        # Chart 2 & 3: Asset and Time Analysis
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            asset_pnl = analytics_df.groupby('Asset')['P&L_Clean'].sum().reset_index()
            fig_asset = px.bar(asset_pnl, x='Asset', y='P&L_Clean', title="🎯 P&L by Asset/Strike", color=asset_pnl['P&L_Clean'] > 0, color_discrete_map={True: "#00CC96", False: "#EF553B"})
            # FIX: Hover off & X-axis labels angled for neatness
            fig_asset.update_layout(showlegend=False, hovermode=False, xaxis_tickangle=-45)
            st.plotly_chart(fig_asset, use_container_width=True)
            
        with col_g2:
            if 'Trade_Time' in analytics_df.columns:
                analytics_df['Hour'] = analytics_df['Trade_Time'].dt.hour
                time_pnl = analytics_df.groupby('Hour')['P&L_Clean'].sum().reset_index()
                # Format hour for better reading
                time_pnl['Hour_Label'] = time_pnl['Hour'].apply(lambda x: f"{int(x):02d}:00")
                fig_time = px.bar(time_pnl, x='Hour_Label', y='P&L_Clean', title="⏰ P&L by Hour of the Day", color=time_pnl['P&L_Clean'] > 0, color_discrete_map={True: "#00CC96", False: "#EF553B"})
                # FIX: Hover off
                fig_time.update_layout(showlegend=False, hovermode=False)
                st.plotly_chart(fig_time, use_container_width=True)

    # ---------------------------------------------
    # 3. SELF-EVOLVING AI ENGINE
    # ---------------------------------------------
    st.markdown("---")
    st.subheader("🧠 Gemini Core: Auto-Evolving Strategy")
    st.write("Gemini will analyze your exact trade times, assets, and adapt its advice based on your current phase.")
    
    if st.button("Initialize Deep Scan"):
        if model is not None and not analytics_df.empty:
            with st.spinner("Decoding your psychological and technical footprints..."):
                try:
                    # Feed detailed analytics logic to AI
                    ai_feed = analytics_df[['Date_Clean', 'Trade_Time', 'Asset', 'P&L_Clean']].tail(50).to_string(index=False)
                    
                    prompt = f"""
                    Tu ek elite, self-evolving Algorithmic Trading Coach hai.
                    Trader apna sequence of data de raha hai. Tera goal hai trader ko independent banana aur khud evolve hona.
                    
                    DATA RULES:
                    - 'Trade_Time': Exact time the position was closed.
                    - 'P&L_Clean': Pure Net Profit/Loss of that trade.
                    
                    Respond ONLY in direct, punchy Hinglish bullet points using this EXACT structure:
                    
                    📊 **Data Decode (Graphical Reality):**
                    * (Analyze the time. E.g., "Data shows teri sabse zyada bleeding 11 AM se 12 PM ke beech ho rahi hai.")
                    * (Analyze the asset. E.g., "Specific Nifty strikes mein tu over-leverage kar raha hai.")
                    
                    🔄 **Evolution & Pattern Check:**
                    * (Identify the behavioral loop. Are they taking revenge trades within 5 minutes of a loss? Point out the exact timestamp from the data).
                    
                    ⚙️ **Systematic Upgrade (New Rule):**
                    * (Give ONE algorithmic, mechanical rule to implement tomorrow. E.g., "System Rule: Loss ke baad screen 30 mins ke liye lock. No exceptions.")
                    
                    Trader's Chronological Ledger:
                    {ai_feed}
                    """
                    
                    response = model.generate_content(prompt)
                    st.info(response.text)
                except Exception as e:
                    st.error(f"AI Core Error: {e}")
        else:
            st.error("⚠️ System needs data to run the AI core.")
else:
    st.info("👆 Please drop your CSVs (add multiple days/weeks for evolution tracking).")
