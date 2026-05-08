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
    
    # --- AUTO-DETECT DELTA COLUMNS & CLEAN DATA ---
    if 'Time' in df.columns and 'Realised P&L' in df.columns:
        date_col = 'Time'
        pnl_col = 'Realised P&L'
        # Parse Delta Date (extracting just the 'YYYY-MM-DD' part intelligently)
        df['Date_Clean'] = pd.to_datetime(df[date_col].astype(str).str[:10], errors='coerce').dt.date
    else:
        # Fallback for Dhan or other CSVs
        date_col = next((c for c in df.columns if 'time' in c.lower() or 'date' in c.lower()), None)
        pnl_col = next((c for c in df.columns if 'pnl' in c.lower() or 'profit' in c.lower() or 'realised' in c.lower() or 'realized' in c.lower()), None)
        if date_col:
            df['Date_Clean'] = pd.to_datetime(df[date_col], errors='coerce').dt.date

    # Total Executions
    if 'Status' in df.columns:
        total_trades = len(df[df['Status'] == 'closed'])
    else:
        total_trades = len(df)
        
    total_pnl = 0
    win_rate = 0
    wins = 0
    
    if pnl_col and pnl_col in df.columns:
        # Clean P&L
        df['P&L_Clean'] = pd.to_numeric(df[pnl_col], errors='coerce').fillna(0)
        total_pnl = df['P&L_Clean'].sum()
        
        # Win Rate logic (Only count trades where P&L is not exactly 0)
        actual_trades = df[df['P&L_Clean'] != 0]
        wins = len(actual_trades[actual_trades['P&L_Clean'] > 0])
        losses = len(actual_trades[actual_trades['P&L_Clean'] < 0])
        total_completed = wins + losses
        win_rate = (wins / total_completed * 100) if total_completed > 0 else 0

    # --- KPI METRICS ---
    st.subheader("📊 Key Performance Indicators")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total P&L (USDT)", f"{total_pnl:.2f}")
    c2.metric("Win Rate", f"{win_rate:.1f}%")
    c3.metric("Total Executions", total_trades)
    c4.metric("Profitable Trades", wins)

    # --- CHARTS ---
    if 'Date_Clean' in df.columns and pnl_col in df.columns:
        st.markdown("---")
        
        # Daily P&L calculation
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
                # Sirf P&L wale ya tagged trades bhejna AI ko taaki analyze theek se ho
                ai_df = edited_df[(edited_df['P&L_Clean'] != 0) | (edited_df['Setup'] != "") | (edited_df['Emotion'] != "")].copy()
                if ai_df.empty:
                    ai_df = edited_df.head(10)
                
                summary_data = ai_df[['Setup', 'Emotion', pnl_col, 'Contract', 'Side']].copy()
                
                prompt = f"""
                You are a professional trading coach. Analyze this data.
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
