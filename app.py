# --- BRANDING HEADER (LEFT ALIGNED & PROPER SIZE) ---
# Ek chhota column (30%) aur ek bada column (70%) taaki logo bada na faile
col1, col2 = st.columns([3, 7]) 

with col1:
    try:
        # EXACT file name yahan check karein
        st.image("logo-full.png", use_container_width=True)
    except Exception as e:
        # Agar image load nahi hui toh text dikhega
        st.markdown("<h1 style='text-align: left; color: #1976d2; margin-bottom: 5px; font-size: 38px; font-weight: 800;'>👑 Challengevala Trader</h1>", unsafe_allow_html=True)

st.markdown("<h2 style='text-align: left; color: #555; margin-top: -10px; margin-bottom: 25px; font-size: 22px; font-weight: 400;'>📈 Elite Quant Dashboard & Auto-Evolving AI</h2>", unsafe_allow_html=True)
st.markdown("---")
