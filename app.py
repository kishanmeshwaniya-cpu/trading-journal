import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json

# --- Professional Terminal Config ---
st.set_page_config(page_title="Quant-Intel Pro", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# --- Institutional Dark Theme CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Roboto+Mono:wght@500;700&display=swap');
    
    /* Base Terminal Vibe */
    .stApp {
        background-color: #0B0E11; /* Deep Slate/Charcoal */
        color: #848E9C; /* Muted Grey for normal text */
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3 {
        color: #EAECEF !important;
        font-weight: 600;
    }

    /* Metric Cards - Sleek & Borderless */
    [data-testid="stMetricValue"] {
        font-family: 'Roboto Mono', monospace;
        color: #EAECEF;
        font-size: 28px !important;
    }
    [data-testid="stMetricDelta"] {
        font-family: 'Roboto Mono', monospace;
    }
    
    /* Clean DataFrame/Grid Styling */
    [data-testid="stDataFrame"] {
        background-color: #181A20;
        border-radius: 8px;
    }
    
    /* Custom Button */
    .stButton>button {
        background-color: #2B3139;
        color: #EAECEF;
        border: 1px solid #4B6BFB;
        border-radius: 4px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #4B6BFB;
        border-color: #4B6BFB;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #181A20;
        border-right: 1px solid #2B3139;
    }
    </style>
""", unsafe_allow_html=True)

# --- AI Core Setup ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model_name = next((m for m in available_models if 'flash' in m or 'pro' in m), available_models[0])
        model = genai.GenerativeModel(model_name)
except Exception as e:
    st.sidebar.error("AI Offline")

# --- Sidebar ---
with st.sidebar:
    st.markdown("<h2 style='color:#EAECEF;'>⚡ Engine Settings</h2>", unsafe_allow_html=True)
    inr_rate = st.number_input("USD/INR Rate (Delta)", value=85.0)
    st.markdown("---")
    uploaded_files = st.file_uploader("Drop Ledger CSVs", accept_multiple_files=True, type=['csv'])

# --- Header ---
st.title("Quant-Intel Terminal")
st.markdown("Precision tracking & AI oversight for serious execution.")

if uploaded_files:
    # --- Data Engine ---
    df_list = [pd.read_csv(f) for f in uploaded_files]
    df = pd.concat(df_list, ignore_index=True)
    analytics_df = pd.DataFrame()

    if 'Time' in df.columns and 'Realised P&L' in df.columns:
        # Delta
        df['Date_Clean'] = pd.to_datetime(df['Time'].astype(str).str[:10], errors='coerce').dt.date
        df['P&L_Clean'] = pd.to_numeric(df['Realised P&L'], errors='coerce').fillna(0) * inr_rate
        analytics_df = df[df['P&L_Clean'] != 0].copy()
        analytics_df['Asset'] = analytics_df['Contract']
        analytics_df['Trade_Time'] = pd.to_datetime(analytics_df['Time'], errors='coerce')

    elif 'Date' in df.columns and 'Trade Value' in df.columns:
        # Dhan
        df = df[df['Buy/Sell'].astype(str).str.upper().isin(['BUY', 'SELL'])].copy()
        df['Date_Clean'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        df['Cashflow'] = df.apply(lambda r: r['Trade Value'] if str(r['Buy/Sell']).upper() == 'SELL' else -r['Trade Value'], axis=1)
        grouped = df.groupby(['Date_Clean', 'Name']).agg({'Cashflow': 'sum', 'Time': 'max'}).reset_index()
        analytics_df = grouped[grouped['Cashflow'] != 0].copy()
        analytics_df.rename(columns={'Cashflow': 'P&L_Clean', 'Name': 'Asset'}, inplace=True)
        analytics_df['Trade_Time'] = pd.to_datetime(analytics_df['Time'], format='mixed', errors='coerce')

    if not analytics_df.empty:
        # --- Top KPIs ---
        total_pnl = analytics_df['P&L_Clean'].sum()
        wins_df = analytics_df[analytics_df['P&L_Clean'] > 0]
        losses_df = analytics_df[analytics_df['P&L_Clean'] < 0]
        win_rate = (len(wins_df) / len(analytics_df) * 100) if len(analytics_df) > 0 else 0
        pf = (wins_df['P&L_Clean'].sum() / abs(losses_df['P&L_Clean'].sum())) if not losses_df.empty and losses_df['P&L_Clean'].sum() != 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Net Realized", f"₹ {total_pnl:,.2f}")
        c2.metric("Hit Ratio", f"{win_rate:.1f} %")
        c3.metric("Profit Factor", f"{pf:.2f} x")
        c4.metric("Executions", len(analytics_df))
        st.markdown("---")

        # --- Graphics Engine (Pro Charts) ---
        col_main, col_side = st.columns([1.5, 1])
        
        with col_main:
            # Clean Area Chart (No grids)
            daily = analytics_df.groupby('Date_Clean')['P&L_Clean'].sum().reset_index()
            daily['Cumulative'] = daily['P&L_Clean'].cumsum()
            fig_eq = px.area(daily, x='Date_Clean', y='Cumulative', title="Cumulative Equity Curve", color_discrete_sequence=['#4B6BFB'])
            fig_eq.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False, title=""), yaxis=dict(showgrid=True, gridcolor='#2B3139', title="")
            )
            st.plotly_chart(fig_eq, use_container_width=True)

        with col_side:
            # Hourly Edge Chart
            analytics_df['Hour'] = analytics_df['Trade_Time'].dt.hour
            hour_data = analytics_df.groupby('Hour')['P&L_Clean'].sum().reset_index()
            # Professional Matte Colors (Green/Red)
            color_map = ["#0ECB81" if x > 0 else "#F6465D" for x in hour_data['P&L_Clean']]
            fig_hour = px.bar(hour_data, x='Hour', y='P&L_Clean', title="Market Hourly Edge", color='P&L_Clean', color_continuous_scale=['#F6465D', '#0ECB81'])
            fig_hour.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False,
                xaxis=dict(showgrid=False, title="Hour of Day"), yaxis=dict(showgrid=False, title="")
            )
            fig_hour.update_traces(marker_color=color_map)
            st.plotly_chart(fig_hour, use_container_width=True)

        st.markdown("---")

        # --- AI Forensics Grid ---
        st.markdown("### 🧠 AI Execution Forensics")
        
        if st.button("Initialize Deep Scan"):
            if model:
                with st.spinner("Extracting hidden patterns..."):
                    try:
                        ai_input = analytics_df[['Date_Clean', 'Trade_Time', 'Asset', 'P&L_Clean']].tail(40).to_string()
                        prompt = f"""
                        Analyze this trading ledger. Find the top 3-4 repeating patterns/mistakes (e.g., Revenge trading, specific bad hours).
                        Assign an 'Accuracy' percentage (0-100) indicating how damaging this pattern is.
                        
                        CRITICAL: Your response MUST BE IN STRICT JSON FORMAT ONLY. 
                        CRITICAL: The text inside "Pattern" and "Rule" MUST BE IN HINGLISH (e.g., "11 baje loss ho raha hai").
                        
                        [
                            {{"Pattern": "Hinglish pattern description", "Instrument": "Asset name", "Accuracy": 85, "Rule": "Hinglish strict execution rule to fix it"}}
                        ]
                        
                        Data:
                        {ai_input}
                        """
                        response = model.generate_content(prompt)
                        
                        raw_json = response.text.replace('```json', '').replace('```', '').strip()
                        ai_data = json.loads(raw_json)
                        ai_df = pd.DataFrame(ai_data)
                        
                        # Render Sleek Table with Progress Bars
                        st.dataframe(
                            ai_df,
                            column_config={
                                "Accuracy": st.column_config.ProgressColumn(
                                    "Threat / Accuracy %", format="%d%%", min_value=0, max_value=100
                                ),
                                "Pattern": st.column_config.TextColumn("Detected Pattern (Hinglish)", width="medium"),
                                "Instrument": st.column_config.TextColumn("Trigger Asset", width="small"),
                                "Rule": st.column_config.TextColumn("System Upgrade (Hinglish)", width="large")
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error("AI Parsing Error. Please click again. (JSON issue)")
            else:
                st.error("AI Core Offline. Check API Key.")
    else:
        st.warning("Ledger uploaded, but no executable trades found.")
else:
    st.info("Awaiting execution data...")
