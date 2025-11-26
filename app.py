import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Beauty Rater", layout="centered")
st.title("Human Beauty Rater 🌍")
st.markdown("Help us build a fair, racially balanced AI dataset.")

# --- 1. CONNECT TO DATABASE ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. LOAD DATA (HEAVY CACHING) ---
# We cache data for 10 minutes (ttl=600) to stop hitting the API limit.
try:
    df = conn.read(worksheet="Sheet1", ttl=600)
except Exception as e:
    st.error(f"Traffic too high! Please wait 1 minute and reload. Error: {e}")
    st.stop()

# --- 3. LOCAL FILTERING ---
# Since we aren't reloading the DB constantly, we need to remember 
# what YOU just rated so we don't show it to you again.
if 'rated_session_files' not in st.session_state:
    st.session_state.rated_session_files = []

# Filter out: 
# 1. Images already rated in the database (from 10 mins ago)
# 2. Images YOU just rated in this session
unrated = df[
    (df['score'].isna() | (df['score'] == 0) | (df['score'] == '')) & 
    (~df['filename'].isin(st.session_state.rated_session_files))
]

if unrated.empty:
    st.balloons()
    st.success("No unrated images available right now! Try reloading in 10 mins.")
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

# --- 6. RATING FORM (LITE VERSION) ---
with st.form("rating_form"):
    st.write("### How attractive is this face?")
    score = st.slider("Score", 1.0, 5.0, 3.0, 0.1)
    rater_name = st.text_input("Your Name (Optional)")
    
    submitted = st.form_submit_button("Submit Rating", type="primary")

    if submitted:
        try:
            # 1. Find the index in the LOCAL dataframe
            # We trust our local copy. We do NOT fetch fresh data (Saves 1 Read Request)
            idx_list = df[df['filename'] == filename].index
            
            if not idx_list.empty:
                idx = idx_list[0]
                
                # 2. Update the dataframe in memory
                df.at[idx, 'score'] = score
                if rater_name:
                    df.at[idx, 'rater_id'] = rater_name
                
                # 3. Push the Whole Table Update (Counts as 1 Write Request)
                conn.update(worksheet="Sheet1", data=df)
                
                st.toast(f"Saved! You rated {filename} a {score}")
                
                # 4. Remember we did this so we don't pick it again
                st.session_state.rated_session_files.append(filename)
                
            else:
                st.error("Error: Filename not found.")

        except Exception as e:
            st.warning("Server busy. Waiting 2 seconds...")
            # If we hit the limit, wait a tiny bit and ignore it.
            # The user can try again or just move on.
        
        # Reset to get a new image
        del st.session_state.current_row
        st.rerun()