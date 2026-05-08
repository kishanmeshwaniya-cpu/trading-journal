import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json

# --- Page Config ---
st.set_page_config(page_title="Quant-Intel Pro", page_icon="⚡", layout="wide")

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
    inr_rate = st.number_input("USD to INR Rate", value=85.0)
    st.markdown("---")
    uploaded_files = st.file_uploader("📥 Drop CSV Ledgers", accept_multiple_files=True, type=['csv'])

# --- Main App Header ---
st.title("Trading Analytics Terminal")
st.markdown("<p style='color: #888;'>Institutional-grade data visualization & AI Accuracy Scoring.</p>", unsafe_allow_html=True)

if uploaded_files:
    # --- Data Processing Engine ---
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
        # Metrics
        total_pnl = analytics_df['P&L_Clean'].sum()
        wins_df = analytics_df[analytics_df['P&L_Clean'] > 0]
        losses_df = analytics_df[analytics_df['P&L_Clean'] < 0]
        win_rate = (len(wins_df) / len(analytics_df) * 100) if len(analytics_df) > 0 else 0
        pf = (wins_df['P&L_Clean'].sum() / abs(losses_df['P&L_Clean'].sum())) if not losses_df.empty and losses_df['P&L_Clean'].sum() != 0 else 0

        # --- TABS ---
        tab1, tab2, tab3 = st.tabs(["📊 Overview", "📈 Deep Edge", "🧠 AI Accuracy Engine"])

        with tab1:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Net Realized P&L", f"₹ {total_pnl:,.2f}")
            c2.metric("Hit Ratio", f"{win_rate:.1f} %")
            c3.metric("Profit Factor", f"{pf:.2f} x")
            c4.metric("Total Trades", len(analytics_df))
            
            daily = analytics_df.groupby('Date_Clean')['P&L_Clean'].sum().reset_index()
            daily['Cumulative'] = daily['P&L_Clean'].cumsum()
            fig_eq = px.area(daily, x='Date_Clean', y='Cumulative', title="Cumulative Growth Curve", color_discrete_sequence=['#4B6BFB'])
            st.plotly_chart(fig_eq, use_container_width=True)

        with tab2:
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                asset_data = analytics_df.groupby('Asset')['P&L_Clean'].sum().reset_index()
                fig_asset = px.bar(asset_data, x='Asset', y='P&L_Clean', title="Instrument Edge", color=asset_data['P&L_Clean'] > 0, color_discrete_map={True: "#00CC96", False: "#EF553B"})
                st.plotly_chart(fig_asset, use_container_width=True)
            with col_chart2:
                analytics_df['Hour'] = analytics_df['Trade_Time'].dt.hour
                hour_data = analytics_df.groupby('Hour')['P&L_Clean'].sum().reset_index()
                fig_hour = px.bar(hour_data, x='Hour', y='P&L_Clean', title="Time Edge (Hourly P&L)", color=hour_data['P&L_Clean'] > 0, color_discrete_map={True: "#00CC96", False: "#EF553B"})
                st.plotly_chart(fig_hour, use_container_width=True)

        with tab3:
            st.subheader("🧠 Algorithmic Pattern Accuracy")
            st.write("AI calculates the probability and accuracy of your trading mistakes based on data.")
            
            if st.button("RUN QUANT AI CORE", type="primary"):
                if model:
                    with st.spinner("Parsing data and calculating accuracy bars..."):
                        try:
                            ai_input = analytics_df[['Date_Clean', 'Trade_Time', 'Asset', 'P&L_Clean']].tail(40).to_string()
                            prompt = f"""
                            Analyze this trading ledger. Find the top 4 repeating patterns (e.g., Revenge trading, worst hour, best asset).
                            Assign an 'Accuracy Confidence' percentage (0-100) to how sure you are this pattern is hurting/helping them.
                            
                            RESPOND STRICTLY IN THIS JSON FORMAT ONLY. NO OTHER TEXT.
                            [
                                {{"Pattern": "Short clear description", "Instrument": "Asset Name", "Accuracy": 85, "Rule": "System rule to fix it"}}
                            ]
                            
                            Data:
                            {ai_input}
                            """
                            response = model.generate_content(prompt)
                            
                            # Clean and Parse JSON
                            raw_json = response.text.replace('```json', '').replace('```', '').strip()
                            ai_data = json.loads(raw_json)
                            ai_df = pd.DataFrame(ai_data)
                            
                            # 1. Plotly Bar Chart for Accuracy
                            st.markdown("### 📊 AI Confidence Graph")
                            fig_ai = px.bar(ai_df, x="Accuracy", y="Pattern", orientation='h', 
                                            text="Accuracy", color="Accuracy", color_continuous_scale="Viridis",
                                            title="Pattern Accuracy / Threat Level")
                            fig_ai.update_traces(texttemplate='%{text}%', textposition='inside')
                            fig_ai.update_layout(yaxis={'categoryorder':'total ascending'})
                            st.plotly_chart(fig_ai, use_container_width=True)

                            # 2. Sleek Data Grid with Progress Bars
                            st.markdown("### 🛠️ Execution Rules Grid")
                            st.dataframe(
                                ai_df,
                                column_config={
                                    "Accuracy": st.column_config.ProgressColumn(
                                        "Accuracy Score", format="%d%%", min_value=0, max_value=100
                                    ),
                                    "Pattern": st.column_config.TextColumn("Detected Behavior", width="medium"),
                                    "Instrument": st.column_config.TextColumn("Asset", width="small"),
                                    "Rule": st.column_config.TextColumn("System Upgrade", width="large")
                                },
                                hide_index=True,
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error(f"AI Parse Error (Try again): {e}")
                            st.write("Raw Output:", response.text) # Helps debug if AI sends markdown
                else:
                    st.error("AI Core Offline. Check API Key.")
    else:
        st.warning("⚠️ No valid trades found.")
else:
    st.info("Awaiting ledger data...")
