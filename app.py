import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json

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
uploaded_files = st.file_uploader("📥 Upload Dhan & Delta CSVs together", accept_multiple_files=True, type=['csv'])

if uploaded_files:
    all_processed_data = []
    
    # --- DUAL ENGINE ---
    for f in uploaded_files:
        temp_df = pd.read_csv(f)
        
        # DELTA
        if 'Time' in temp_df.columns and 'Realised P&L' in temp_df.columns:
            temp_df['P&L_Clean'] = pd.to_numeric(temp_df['Realised P&L'], errors='coerce').fillna(0) * 85
            temp_df = temp_df[temp_df['P&L_Clean'] != 0].copy()
            temp_df['Date_Clean'] = pd.to_datetime(temp_df['Time'].astype(str).str[:10], errors='coerce').dt.date
            temp_df['Trade_Time'] = pd.to_datetime(temp_df['Time'].astype(str).str[:19], errors='coerce')
            temp_df['Asset'] = temp_df['Contract']
            all_processed_data.append(temp_df[['Date_Clean', 'Trade_Time', 'Asset', 'P&L_Clean']])
            
        # DHAN
        elif 'Date' in temp_df.columns and 'Trade Value' in temp_df.columns:
            temp_df = temp_df[temp_df['Buy/Sell'].astype(str).str.upper().isin(['BUY', 'SELL'])].copy()
            temp_df['Cashflow'] = temp_df.apply(lambda r: r['Trade Value'] if str(r['Buy/Sell']).upper() == 'SELL' else -r['Trade Value'], axis=1)
            dhan_grouped = temp_df.groupby([pd.to_datetime(temp_df['Date']).dt.date, 'Name']).agg({'Cashflow': 'sum', 'Time': 'max'}).reset_index()
            dhan_grouped.columns = ['Date_Clean', 'Asset', 'P&L_Clean', 'Time']
            dhan_grouped = dhan_grouped[dhan_grouped['P&L_Clean'] != 0].copy()
            dhan_grouped['Trade_Time'] = pd.to_datetime(dhan_grouped['Time'], format='mixed', errors='coerce')
            all_processed_data.append(dhan_grouped[['Date_Clean', 'Trade_Time', 'Asset', 'P&L_Clean']])

    # Master Data
    if all_processed_data:
        analytics_df = pd.concat(all_processed_data, ignore_index=True)
        analytics_df['Asset_Display'] = analytics_df['Asset'].astype(str).apply(lambda x: x[:15] + ".." if len(x) > 15 else x)
        
        total_pnl = analytics_df['P&L_Clean'].sum()
        wins = len(analytics_df[analytics_df['P&L_Clean'] > 0])
        losses = len(analytics_df[analytics_df['P&L_Clean'] < 0])
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

        st.subheader("📊 Combined Performance Matrix (Dhan + Delta)")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Net P&L", f"₹{total_pnl:,.2f}")
        c2.metric("Win Rate", f"{win_rate:.1f}%")
        c3.metric("Loss Trades", losses)
        c4.metric("Win Trades", wins)

        # ---------------------------------------------
        # GRAPHICS ENGINE 
        # ---------------------------------------------
        st.markdown("---")
        st.subheader("👁️ Visual Data Insights")
        
        daily = analytics_df.groupby('Date_Clean')['P&L_Clean'].sum().reset_index()
        daily['Equity Curve'] = daily['P&L_Clean'].cumsum()
        fig_eq = px.area(daily, x='Date_Clean', y='Equity Curve', title="📈 Total Portfolio Growth")
        fig_eq.update_layout(hovermode=False) 
        st.plotly_chart(fig_eq, use_container_width=True)
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            asset_pnl = analytics_df.groupby('Asset_Display')['P&L_Clean'].sum().reset_index()
            fig_asset = px.bar(asset_pnl, x='Asset_Display', y='P&L_Clean', title="🎯 P&L by Instrument", color=asset_pnl['P&L_Clean'] > 0, color_discrete_map={True: "#00CC96", False: "#EF553B"})
            fig_asset.update_layout(showlegend=False, hovermode=False, xaxis_tickangle=-45)
            st.plotly_chart(fig_asset, use_container_width=True)
            
        with col_g2:
            if not analytics_df['Trade_Time'].isna().all():
                analytics_df['Hour'] = analytics_df['Trade_Time'].dt.hour
                time_pnl = analytics_df.groupby('Hour')['P&L_Clean'].sum().reset_index()
                time_pnl['Hour_Label'] = time_pnl['Hour'].apply(lambda x: f"{int(x):02d}:00")
                fig_time = px.bar(time_pnl, x='Hour_Label', y='P&L_Clean', title="⏰ P&L by Hour", color=time_pnl['P&L_Clean'] > 0, color_discrete_map={True: "#00CC96", False: "#EF553B"})
                fig_time.update_layout(showlegend=False, hovermode=False)
                st.plotly_chart(fig_time, use_container_width=True)

        # ---------------------------------------------
        # VISUAL AI ENGINE (PRO GUIDANCE VERSION)
        # ---------------------------------------------
        st.markdown("---")
        st.subheader("🧠 Gemini Core: Visual Pattern Diagnostics")
        if st.button("Generate Visual Diagnostic"):
            if model is not None:
                with st.spinner("Analyzing patterns and generating guidance..."):
                    try:
                        ai_feed = analytics_df[['Date_Clean', 'Trade_Time', 'Asset', 'P&L_Clean']].tail(50).to_string(index=False)
                        
                        prompt = f"""
                        Analyze this trading data. Identify 3 critical mistakes.
                        For each mistake, provide a short Hinglish 'Avoid' instruction and a 'Benefit'.
                        
                        CRITICAL: RESPOND ONLY WITH RAW JSON. NO MARKDOWN.
                        Format:
                        {{
                            "chart_data": [
                                {{
                                    "Mistake": "Short Title", 
                                    "Impact": 85, 
                                    "Avoid": "Kya avoid karna hai (short)", 
                                    "Benefit": "Fayda kya hoga (short)"
                                }}
                            ],
                            "summary": "One line overall conclusion."
                        }}
                        
                        Data:
                        {ai_feed}
                        """
                        response = model.generate_content(prompt)
                        
                        # 100% Bulletproof JSON cleanup (No literal backticks used in string)
                        raw_json = response.text.replace("`"*3 + "json", "").replace("`"*3, "").strip()
                        ai_data = json.loads(raw_json)
                        
                        # 1. Short AI Summary
                        st.success(f"💡 **AI Overview:** {ai_data['summary']}")
                        
                        # 2. Dual Charts
                        ai_df = pd.DataFrame(ai_data['chart_data'])
                        c_pie, c_bar = st.columns(2)
                        with c_pie:
                            fig_pie = px.pie(ai_df, values='Impact', names='Mistake', title="🔥 Mistake Impact Breakdown", hole=0.4, color_discrete_sequence=px.colors.sequential.Reds_r)
                            st.plotly_chart(fig_pie, use_container_width=True)
                        with c_bar:
                            fig_bar = px.bar(ai_df, x='Mistake', y='Impact', title="📉 Severity Level", color='Impact', color_continuous_scale='Reds')
                            st.plotly_chart(fig_bar, use_container_width=True)

                        # 3. Actionable Guidance Cards (To-the-point)
                        st.markdown("### 🛡️ Actionable Guidance (Avoid & Win)")
                        cols = st.columns(len(ai_data['chart_data']))
                        
                        for i, item in enumerate(ai_data['chart_data']):
                            with cols[i]:
                                st.markdown(f'''
                                <div style="background-color:#ffebee; padding:15px; border-radius:10px; border-left: 5px solid #d32f2f; min-height: 150px;">
                                    <h4 style="color:#d32f2f; margin:0 0 10px 0; font-size:16px;">{item['Mistake']}</h4>
                                    <p style="color:#333; font-size:14px; margin:5px 0;"><b>❌ Avoid:</b> {item['Avoid']}</p>
                                    <p style="color:#333; font-size:14px; margin:5px 0;"><b>✅ Benefit:</b> {item['Benefit']}</p>
                                </div>
                                ''', unsafe_allow_html=True)
                                
                    except Exception as e:
                        st.error(f"AI Parse Error: {e}")
    else:
        st.warning("⚠️ No valid trades detected.")
else:
    st.info("👆 Please drop your CSVs to see visual analytics.")
