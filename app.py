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
    div[data-testid="column"] {display: flex; flex-direction: column;}
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
        # TIME-BASED AI ENGINE (PRO UI VERSION)
        # ---------------------------------------------
        st.markdown("---")
        st.subheader("⏱️ Gemini Core: Time-Based Edge Analysis")
        
        if st.button("Generate Time Analysis"):
            if model is not None:
                with st.spinner("Analyzing full historical data to find your most profitable hours..."):
                    try:
                        if analytics_df['Trade_Time'].isna().all():
                            st.warning("Aapke data mein Time format missing hai, time analysis run nahi ho sakta.")
                        else:
                            # 1. Pre-calculate Hourly Data to prevent AI math errors
                            analytics_df['Hour'] = analytics_df['Trade_Time'].dt.hour
                            time_ai_df = analytics_df.groupby('Hour')['P&L_Clean'].sum().reset_index()
                            time_ai_df['Time_Label'] = time_ai_df['Hour'].apply(lambda x: f"{int(x):02d}:00")
                            
                            ai_feed = time_ai_df[['Time_Label', 'P&L_Clean']].to_string(index=False)
                            
                            prompt = f"""
                            You are a strict Quant Trading Coach. Analyze this hourly Profit/Loss data covering all trading days.
                            Identify the 'Best Time' (Golden Zone) and the 'Worst Time' (Danger Zone) to trade.
                            
                            CRITICAL: RESPOND ONLY WITH RAW JSON. NO MARKDOWN. ALL TEXT IN HINGLISH.
                            Format:
                            {{
                                "insights": [
                                    {{
                                        "Zone_Type": "Danger",
                                        "Zone_Name": "🔴 Danger Zone (Worst Time)", 
                                        "Timeframe": "e.g. 14:00 to 16:00", 
                                        "Avoid": "Kya exactly avoid karna hai is time par...", 
                                        "Improve": "Is time pe system band karna chahiye ya size kam karna chahiye...",
                                        "Benefit": "Bade losses se bachaav"
                                    }},
                                    {{
                                        "Zone_Type": "Golden",
                                        "Zone_Name": "🟢 Golden Zone (Best Time)", 
                                        "Timeframe": "e.g. 09:00 to 11:00", 
                                        "Avoid": "Jaldi fear mein exit nahi karna hai...", 
                                        "Improve": "High probability setups par pura focus rakhna...",
                                        "Benefit": "Max profit capture hoga"
                                    }}
                                ],
                                "summary": "One clear line on when they should strictly trade and when to avoid."
                            }}
                            
                            Hourly P&L Data:
                            {ai_feed}
                            """
                            response = model.generate_content(prompt)
                            
                            # Safe JSON Parsing
                            raw_json = response.text.replace("`"*3 + "json", "").replace("`"*3, "").strip()
                            ai_data = json.loads(raw_json)
                            
                            # 1. AI Summary
                            st.info(f"💡 **AI Timing Insight:** {ai_data['summary']}")
                            
                            # 2. Beautiful Line Chart (Time vs Profit)
                            fig_line = px.line(time_ai_df, x='Time_Label', y='P&L_Clean', markers=True, 
                                               title="📈 Hourly Profit & Loss Trend (All Days)")
                            fig_line.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.8)
                            
                            # Color markers based on profit/loss
                            marker_colors = ['#00CC96' if val >= 0 else '#EF553B' for val in time_ai_df['P&L_Clean']]
                            fig_line.update_traces(line_color="#1976d2", line_width=3, 
                                                   marker=dict(size=12, color=marker_colors, line=dict(width=2, color='white')))
                            
                            st.plotly_chart(fig_line, use_container_width=True)

                            # 3. Action Cards (Danger vs Golden Zone)
                            st.markdown("### ⏳ Time-Based Action Plan")
                            cols = st.columns(len(ai_data['insights']))
                            
                            for i, item in enumerate(ai_data['insights']):
                                if item.get('Zone_Type') == 'Danger':
                                    border_color = "#d32f2f"
                                    bg_color = "#ffebee"
                                else:
                                    border_color = "#388e3c"
                                    bg_color = "#e8f5e9"
                                    
                                with cols[i]:
                                    st.markdown(f'''
                                    <div style="background-color: {bg_color}; padding: 20px; border-radius: 12px; 
                                                border: 1px solid #e0e0e0; border-top: 5px solid {border_color}; 
                                                box-shadow: 0 4px 6px rgba(0,0,0,0.05); min-height: 250px; 
                                                display: flex; flex-direction: column;">
                                        <h4 style="color: {border_color}; margin-top: 0; margin-bottom: 5px; font-size: 18px;">
                                            {item['Zone_Name']}
                                        </h4>
                                        <h5 style="color: #444; margin-top: 0; margin-bottom: 15px; font-size: 15px; border-bottom: 1px solid #ccc; padding-bottom: 8px;">
                                            ⏰ <b>Time Window:</b> {item['Timeframe']}
                                        </h5>
                                        <div style="flex-grow: 1;">
                                            <p style="color: #555555; font-size: 14px; margin: 8px 0; line-height: 1.4;">
                                                <span style="color: #d32f2f; font-weight: bold;">❌ Avoid:</span> {item['Avoid']}
                                            </p>
                                            <p style="color: #555555; font-size: 14px; margin: 8px 0; line-height: 1.4;">
                                                <span style="color: #1976d2; font-weight: bold;">🛠️ Improve:</span> {item['Improve']}
                                            </p>
                                        </div>
                                        <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #dcdcdc;">
                                            <p style="color: #2e7d32; font-size: 14px; margin: 0; font-weight: 500;">
                                                ✅ Benefit: {item['Benefit']}
                                            </p>
                                        </div>
                                    </div>
                                    ''', unsafe_allow_html=True)
                                    
                    except Exception as e:
                        st.error(f"AI Parse Error: {e}")
    else:
        st.warning("⚠️ No valid trades detected.")
else:
    st.info("👆 Please drop your CSVs to see visual analytics.")
