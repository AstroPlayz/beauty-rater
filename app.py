import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Beauty Rater", layout="centered")
st.title("Human Beauty Rater 🌍")
st.markdown("Help us build a fair, racially balanced AI dataset. Rate the face below!")

# --- 1. CONNECT TO DATABASE ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. LOAD DATA (OPTIMIZED) ---
try:
    # CHANGED: ttl=10 means "Only download new data if it's been 10 seconds".
    # This prevents the "Quota Exceeded" error.
    df = conn.read(worksheet="Sheet1", ttl=10)
except Exception as e:
    st.error(f"Database Connection Failed. Error: {e}")
    st.stop()

# --- 3. FIND UNRATED IMAGES ---
unrated = df[df['score'].isna() | (df['score'] == 0) | (df['score'] == '')]

if unrated.empty:
    st.balloons()
    st.success("🎉 Incredible! All 2,500 images have been rated. Thank you!")
    st.stop()

# --- 4. SELECT IMAGE ---
if 'current_row' not in st.session_state:
    st.session_state.current_row = unrated.sample(1).iloc[0]

row = st.session_state.current_row
filename = row['filename']
img_path = os.path.join("images", filename) 

# --- 5. DISPLAY IMAGE ---
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    if os.path.exists(img_path):
        st.image(img_path, caption=f"File: {filename}", width=350)
    else:
        st.error(f"Image not found: {filename}")
        del st.session_state.current_row
        st.rerun()

# --- 6. RATING FORM ---
with st.form("rating_form"):
    st.write("### How attractive is this face?")
    
    score = st.slider("Score", 1.0, 5.0, 3.0, 0.1)
    rater_name = st.text_input("Your Name (Optional)")
    
    submitted = st.form_submit_button("Submit Rating", type="primary")

    if submitted:
        # --- CONCURRENCY CHECK ---
        try:
            # We keep ttl=0 HERE to ensure we double-check right before saving
            fresh_df = conn.read(worksheet="Sheet1", ttl=0)
            
            idx_list = fresh_df[fresh_df['filename'] == filename].index
            
            if not idx_list.empty:
                idx = idx_list[0]
                current_score = fresh_df.at[idx, 'score']
                
                # Check if someone rated it in the last few seconds
                if pd.notna(current_score) and current_score != 0:
                    st.warning(f"⚠️ Someone else just rated '{filename}'! Skipping to next.")
                else:
                    # WRITE DATA
                    fresh_df.at[idx, 'score'] = score
                    if rater_name:
                        fresh_df.at[idx, 'rater_id'] = rater_name
                    
                    conn.update(worksheet="Sheet1", data=fresh_df)
                    st.toast(f"Saved! You rated {filename} a {score}")
                    
                    # Manual cache update to make the app feel faster
                    # We assume the save worked and update our local view immediately
                    st.cache_data.clear() 
            else:
                st.error("Error: Filename not found in database.")

        except Exception as e:
            st.warning("Traffic is high! Please wait 10 seconds and try again.")
        
        del st.session_state.current_row
        st.rerun()