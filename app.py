import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai

# --- Page Setup ---
st.set_page_config(page_title="Pro Trading Journal", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .stMetric {background-color: #f0f2f6; padding: 15px; border-radius: 10px;}
    </style>
""", unsafe_allow_html=True)

st.title("📈 Pro Trading Journal & AI Coach")

# --- API Setup ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-pro')
except:
    st.sidebar.error("🔑 API Key Missing! Manage App > Settings > Secrets mein GEMINI_API_KEY daalein.")

# --- File Uploader ---
uploaded_files = st.file_uploader("📥 Drop Dhan or Delta CSV here", accept_multiple_files=True, type=['csv'])

if uploaded_files:
    df_list = [pd.read_csv(f) for f in uploaded_files]
    df = pd.concat(df_list, ignore_index=True)
    
    st.markdown("---")
    
    df['P&L_Clean'] = 0.0
    df['Date_Clean'] = pd.NaT
    wins = 0
    losses = 0
    total_trades = 0
    total_pnl = 0.0
    currency = "₹"
    
    # ==========================================
    # 1. DETECT DELTA EXCHANGE
    # ==========================================
    if 'Time' in df.columns and 'Realised P&L' in df.columns:
        st.info("💡 Delta Exchange detected. Auto-converting USD to INR (1$ = 85₹).")
        df['Date_Clean'] = pd.to_datetime(df['Time'].astype(str).str[:10], errors='coerce').dt.date
        
        # Multiply by 85 to convert to INR
        df['P&L_Clean'] = pd.to_numeric(df['Realised P&L'], errors='coerce').fillna(0) * 85
        
        actual_trades = df[df['P&L_Clean'] != 0]
        wins = len(actual_trades[actual_trades['P&L_Clean'] > 0])
        losses = len(actual_trades[actual_trades['P&L_Clean'] < 0])
        total_pnl = df['P&L_Clean'].sum()
        total_trades = len(df[df['Status'] == 'closed']) if 'Status' in df.columns else len(df)

    # ==========================================
    # 2. DETECT DHAN EXCHANGE
    # ==========================================
    elif 'Date' in df.columns and 'Trade Value' in df.columns and 'Buy/Sell' in df.columns:
        
        # STRICT FILTER: Remove deposits/withdrawals, only keep real Trades
        valid_trades = df['Buy/Sell'].astype(str).str.upper().isin(['BUY', 'SELL'])
        df = df[valid_trades].copy()
        
        df['Date_Clean'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        
        # Dhan P&L Calculation: Sell Value - Buy Value
        df['Cashflow'] = df.apply(lambda row: row['Trade Value'] if str(row['Buy/Sell']).upper() == 'SELL' else -row['Trade Value'], axis=1)
        df['P&L_Clean'] = df['Cashflow']
        total_pnl = df['Cashflow'].sum()
        
        # Calculate Wins/Losses by grouping Day & Asset
        grouped_trades = df.groupby(['Date_Clean', 'Name'])['Cashflow'].sum().reset_index()
        wins = len(grouped_trades[grouped_trades['Cashflow'] > 0])
        losses = len(grouped_trades[grouped_trades['Cashflow'] < 0])
        total_trades = wins + losses 

    # ==========================================
    # 3. FALLBACK FOR OTHER CSVs
    # ==========================================
    else:
        date_col = next((c for c in df.columns if 'time' in c.lower() or 'date' in c.lower()), None)
        pnl_col = next((c for c in df.columns if 'pnl' in c.lower() or 'profit' in c.lower() or 'realised' in c.lower() or 'realized' in c.lower()), None)
        if date_col:
            df['Date_Clean'] = pd.to_datetime(df[date_col], errors='coerce').dt.date
        if pnl_col:
            df['P&L_Clean'] = pd.to_numeric(df[pnl_col], errors='coerce').fillna(0)
            total_pnl = df['P&L_Clean'].sum()
            wins = len(df[df['P&L_Clean'] > 0])
            losses = len(df[df['P&L_Clean'] < 0])
        total_completed = wins + losses
        total_trades = total_completed

    # --- KPI METRICS ---
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    
    st.subheader("📊 Key Performance Indicators")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Total P&L ({currency})", f"{total_pnl:.2f}")
    c2.metric("Win Rate", f"{win_rate:.1f}%")
    c3.metric("Total Trades", total_trades)
    c4.metric("Profitable Trades", wins)

    # --- CHARTS ---
    if not df['Date_Clean'].isna().all() and df['P&L_Clean'].sum() != 0:
        st.markdown("---")
        daily_pnl = df.groupby('Date_Clean')['P&L_Clean'].sum().reset_index()
        daily_pnl['Cumulative P&L'] = daily_pnl['P&L_Clean'].cumsum()
        daily_pnl['Color'] = daily_pnl['P&L_Clean'].apply(lambda x: 'Profit' if x > 0 else 'Loss')
        color_map = {'Profit': '#00CC96', 'Loss': '#EF553B'}

        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            fig1 = px.area(daily_pnl, x='Date_Clean', y='Cumulative P&L', title="📈 Equity Curve (Cumulative P&L)")
            fig1.update_layout(margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig1, use_container_width=True)
        with chart_col2:
            fig2 = px.bar(daily_pnl, x='Date_Clean', y='P&L_Clean', title="📅 Daily Net P&L", color='Color', color_discrete_map=color_map)
            fig2.update_layout(margin=dict(l=0, r=0, t=40, b=0), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

    # --- JOURNAL ---
    st.markdown("---")
    st.subheader("📝 Trade Log & Tags")
    
    if 'Setup' not in df.columns:
        df.insert(0, 'Setup', "")
    if 'Emotion' not in df.columns:
        df.insert(1, 'Emotion', "")
        
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    
    # --- AI COACH ---
    st.markdown("---")
    st.subheader("🤖 AI Trading Coach")
    if st.button("Generate Performance Analysis"):
        with st.spinner("Analyzing your setups, emotions, and P&L..."):
            try:
                ai_df = edited_df[(edited_df['P&L_Clean'] != 0) | (edited_df['Setup'] != "") | (edited_df['Emotion'] != "")].copy()
                if ai_df.empty:
                    ai_df = edited_df.head(10)
                
                cols_to_send = ['Setup', 'Emotion', 'P&L_Clean']
                if 'Name' in ai_df.columns: cols_to_send.append('Name')
                if 'Contract' in ai_df.columns: cols_to_send.append('Contract')
                
                summary_data = ai_df[cols_to_send].copy()
                
                prompt = f"""
                You are a strict, professional trading coach. Analyze this data.
                Provide:
                1. Strengths
                2. Psychological Traps/Mistakes
                3. Actionable Rule for next session.
                Data: {summary_data.to_string()}
                """
                response = model.generate_content(prompt)
                st.info(response.text)
            except Exception as e:
                st.error("Error generating AI report. Please verify your GEMINI_API_KEY in Streamlit Secrets.")
else:
    st.info("👆 Please upload your Dhan or Delta CSV files.")
