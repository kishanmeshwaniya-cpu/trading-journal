# ---------------------------------------------
        # VISUAL AI ENGINE (PRO GUIDANCE VERSION)
        # ---------------------------------------------
        st.markdown("---")
        st.subheader("🧠 Gemini Core: Visual Pattern Diagnostics")
        if st.button("Generate Visual Diagnostic"):
            if model is not None:
                with st.spinner("Analyzing patterns and generating guidance..."):
                    try:
                        # Sirf last 50 trades ka data bhej rahe hain for context
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
                        
                        # JSON Cleaning
                        raw_json = response.text.strip().replace("```json", "").replace("
```", "").strip()
                        ai_data = json.loads(raw_json)
                        
                        # 1. AI Summary Header
                        st.success(f"💡 **AI Overview:** {ai_data['summary']}")
                        
                        # 2. Charts Section
                        ai_df = pd.DataFrame(ai_data['chart_data'])
                        c_pie, c_bar = st.columns(2)
                        with c_pie:
                            fig_pie = px.pie(ai_df, values='Impact', names='Mistake', title="🔥 Mistake Impact Breakdown", hole=0.4, color_discrete_sequence=px.colors.sequential.Reds_r)
                            st.plotly_chart(fig_pie, use_container_width=True)
                        with c_bar:
                            fig_bar = px.bar(ai_df, x='Mistake', y='Impact', title="📉 Severity Level", color='Impact', color_continuous_scale='Reds')
                            st.plotly_chart(fig_bar, use_container_width=True)

                        # 3. NEW: Pro-Guidance Section (Visual Cards)
                        st.markdown("### 🛡️ Actionable Guidance (Avoid & Win)")
                        cols = st.columns(len(ai_data['chart_data']))
                        
                        for i, item in enumerate(ai_data['chart_data']):
                            with cols[i]:
                                st.markdown(f"""
                                <div style="background-color:#ffebee; padding:15px; border-radius:10px; border-left: 5px solid #d32f2f;">
                                    <h4 style="color:#d32f2f; margin-top:0;">{item['Mistake']}</h4>
                                    <p><b>❌ Avoid:</b> {item['Avoid']}</p>
                                    <p><b>✅ Benefit:</b> {item['Benefit']}</p>
                                </div>
                                """, unsafe_allow_html=True)
                                
                    except Exception as e:
                        st.error(f"AI Error: {e}")
