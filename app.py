import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai

# --- Page Config ---
st.set_page_config(page_title="Quant Terminal", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# --- AI Setup ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model_name = next((m for m in available_models if 'flash' in m or 'pro' in m), available_models[0])
        model = genai.GenerativeModel(model_name)
except Exception as e:
    st.sidebar.error(f"AI System Offline: {e}")

# --- Sidebar ---
with st.sidebar:
    st.title("⚡ Quant Settings")
    inr_rate = st.number_input("USD to INR Rate (For Delta)", value=85.0)
    st.markdown("---")
    st.info("Upload Dhan (Equity/F&O) or Delta (Crypto) CSV ledgers here.")
    uploaded_files = st.file_uploader("Drop CSV Files", accept_multiple_files=True, type=['csv'])

# --- Main App Header ---
st.title("Trading Analytics Terminal")
st.markdown("Institutional-grade data visualization and AI oversight.")

if uploaded_files:
    # --- Data Processing ---
    df_list = [pd.read_csv(f) for f in uploaded_files]
    df = pd.concat(df_list, ignore_index=True)
    
    analytics_df = pd.DataFrame()

    if 'Time' in df.columns and 'Realised P&L' in df.columns:
        # Delta Engine
        df['Date_Clean'] = pd.to_datetime(df['Time'].astype(str).str[:10], errors='coerce').dt.date
        df['P&L_Clean'] = pd.to_numeric(df['Realised P&L'], errors='coerce').fillna(0) * inr_rate
        analytics_df = df[df['P&L_Clean'] != 0].copy()
        analytics_df['Asset'] = analytics_df['Contract']
        analytics_df['Trade_Time'] = pd.to_datetime(analytics_df['Time'], errors='coerce')

    elif 'Date' in df.columns and 'Trade Value' in df.columns:
        # Dhan Engine
        df = df[df['Buy/Sell'].astype(str).str.upper().isin(['BUY', 'SELL'])].copy()
        df['Date_Clean'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        df['Cashflow'] = df.apply(lambda r: r['Trade Value'] if str(r['Buy/Sell']).upper() == 'SELL' else -r['Trade Value'], axis=1)
        
        grouped = df.groupby(['Date_Clean', 'Name']).agg({'Cashflow': 'sum', 'Time': 'max'}).reset_index()
        analytics_df = grouped[grouped['Cashflow'] != 0].copy()
        analytics_df.rename(columns={'Cashflow': 'P&L_Clean', 'Name': 'Asset'}, inplace=True)
        analytics_df['Trade_Time'] = pd.to_datetime(analytics_df['Time'], format='mixed', errors='coerce')

    if not analytics_df.empty:
        # Metrics Calculations
        total_pnl = analytics_df['P&L_Clean'].sum()
        wins_df = analytics_df[analytics_df['P&L_Clean'] > 0]
        losses_df = analytics_df[analytics_df['P&L_Clean'] < 0]
        win_rate = (len(wins_df) / len(analytics_df) * 100) if len(analytics_df) > 0 else 0
        profit_factor = (wins_df['P&L_Clean'].sum() / abs(losses_df['P&L_Clean'].sum())) if not losses_df.empty and losses_df['P&L_Clean'].sum() != 0 else 0

        # --- UI TABS (Clean FinTech Look) ---
        tab1, tab2, tab3 = st.tabs(["📊 Performance Overview", "📈 Deep Analytics", "🧠 AI Quant Oversight"])

        with tab1:
            st.subheader("Executive Summary")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Net Realized P&L", f"₹ {total_pnl:,.2f}")
            c2.metric("Hit Ratio (Win %)", f"{win_rate:.1f} %")
            c3.metric("Profit Factor", f"{profit_factor:.2f} x")
            c4.metric("Total Trades", len(analytics_df))
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            daily = analytics_df.groupby('Date_Clean')['P&L_Clean'].sum().reset_index()
            daily['Cumulative'] = daily['P&L_Clean'].cumsum()
            fig_equity = px.area(daily, x='Date_Clean', y='Cumulative', title="Cumulative Equity Curve")
            fig_equity.update_layout(margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig_equity, use_container_width=True)

        with tab2:
            st.subheader("Instrument & Time Analysis")
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                asset_data = analytics_df.groupby('Asset')['P&L_Clean'].sum().reset_index()
                fig_asset = px.bar(asset_data, x='Asset', y='P&L_Clean', title="P&L by Instrument", color=asset_data['P&L_Clean'] > 0, color_discrete_map={True: "#2ca02c", False: "#d62728"})
                fig_asset.update_layout(showlegend=False, margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig_asset, use_container_width=True)
                
            with col_chart2:
                analytics_df['Hour'] = analytics_df['Trade_Time'].dt.hour
                hour_data = analytics_df.groupby('Hour')['P&L_Clean'].sum().reset_index()
                fig_hour = px.bar(hour_data, x='Hour', y='P&L_Clean', title="P&L by Hour of Day", color=hour_data['P&L_Clean'] > 0, color_discrete_map={True: "#2ca02c", False: "#d62728"})
                fig_hour.update_layout(showlegend=False, margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig_hour, use_container_width=True)

        with tab3:
            st.subheader("Automated Pattern Recognition")
            st.write("Run the AI model to detect systemic flaws in your trading execution.")
            if st.button("Initialize Deep Scan", type="primary"):
                if model:
                    with st.spinner("Analyzing ledger footprints..."):
                        try:
                            ai_input = analytics_df[['Date_Clean', 'Trade_Time', 'Asset', 'P&L_Clean']].tail(40).to_string()
                            prompt = f"""
                            You are an institutional Quant Risk Manager. Analyze the following trading footprint for high-risk behaviors.
                            Data Ledger: {ai_input}
                            
                            Provide a forensic report in a professional Markdown Table with these columns:
                            | Pattern Detected | Evidence (Time/Asset) | Risk Level | Mitigation Strategy |
                            
                            Followed by ONE 'Institutional Grade Rule' in Hinglish. Be brutal and precise. No generic advice.
                            """
                            response = model.generate_content(prompt)
                            st.markdown(response.text)
                        except Exception as e:
                            st.error(f"Error generating AI report: {e}")
                else:
                    st.error("AI Model is not connected. Check API key.")
    else:
        st.warning("⚠️ Data processed, but no valid trades found. Ensure CSV format is correct.")
else:
    st.info("Awaiting data. Please use the sidebar to upload your ledger.")
