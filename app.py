import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os

st.set_page_config(page_title="Beauty Rater", layout="centered")
st.title("Human Beauty Rater 🌍")

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df = conn.read(worksheet="Sheet1", ttl=600)
except Exception as e:
    st.error(f"Database Connection Failed: {e}")
    st.stop()

total_images = len(df)
rated_images = len(df[df['score'].notna() & (df['score'] != 0) & (df['score'] != '')])
remaining = total_images - rated_images
progress = float(rated_images) / float(total_images) if total_images > 0 else 0

st.progress(progress)
st.caption(f"🚀 Progress: {rated_images}/{total_images} rated. ({remaining} left)")

unrated = df[df['score'].isna() | (df['score'] == 0) | (df['score'] == '')]

if unrated.empty:
    st.balloons()
    st.success("🎉 All images have been rated! Thank you!")
    st.stop()

if 'current_row' not in st.session_state:
    st.session_state.current_row = unrated.sample(1).iloc[0]

row = st.session_state.current_row
filename = row['filename']
img_path = os.path.join("images", filename)

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    if os.path.exists(img_path):
        st.image(img_path, caption=f"File: {filename}", width=350)
    else:
        st.error(f"Image not found: {filename}")
        del st.session_state.current_row
        st.rerun()

with st.form("rating_form"):
    st.write("### How attractive is this face?")
    
    score = st.slider("Score", 1.0, 5.0, 3.0, 0.1)
    rater_name = st.text_input("Your Name (Optional)")
    
    submitted = st.form_submit_button("Submit Rating", type="primary")

    if submitted:
        try:
            fresh_df = conn.read(worksheet="Sheet1", ttl=0)
            
            idx_list = fresh_df[fresh_df['filename'] == filename].index
            
            if not idx_list.empty:
                idx = idx_list[0]
                
                current_val = fresh_df.at[idx, 'score']
                if pd.notna(current_val) and current_val != 0 and current_val != "":
                    st.warning(f"Someone else just rated '{filename}'! Skipping.")
                else:
                    fresh_df.at[idx, 'score'] = score
                    if rater_name:
                        fresh_df.at[idx, 'rater_id'] = rater_name
                    
                    conn.update(worksheet="Sheet1", data=fresh_df)
                    st.toast(f"Saved! You rated {filename} a {score}")
                    st.cache_data.clear()
            else:
                st.error("Error: Filename not found in database.")

        except Exception as e:
            st.warning("Traffic is high! Please wait 5 seconds and try again.")
        
        del st.session_state.current_row
        st.rerun()