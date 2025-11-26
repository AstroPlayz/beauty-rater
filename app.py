import streamlit as st
from supabase import create_client, Client
import pandas as pd
import os

st.set_page_config(page_title="Beauty Rater", layout="centered")
st.title("Human Beauty Rater 🌍")

@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection()

try:
    response = supabase.table("ratings").select("*").execute()
    df = pd.DataFrame(response.data)
except Exception as e:
    st.error(f"Database Connection Failed: {e}")
    st.stop()

if df.empty:
    st.warning("⚠️ Database returned 0 rows.")
    st.info("This usually means **Row Level Security (RLS)** is on. Go to Supabase > Table Editor > 'ratings' > Turn OFF RLS.")
    st.stop()

rated_df = df[df['score'].notna() & (df['score'] != 0)]
total = len(df)
rated_count = len(rated_df)
remaining = total - rated_count
progress = float(rated_count) / float(total) if total > 0 else 0

st.progress(progress)
st.caption(f"🚀 Progress: {rated_count}/{total} rated. ({remaining} left)")

unrated = df[(df['score'].isna()) | (df['score'] == 0)]

if unrated.empty:
    st.balloons()
    st.success("🎉 All images have been rated!")
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
            data = {"score": score}
            if rater_name:
                data["rater_id"] = rater_name
                
            supabase.table("ratings").update(data).eq("filename", filename).execute()
            
            st.toast(f"Saved! You rated {filename} a {score}")
            
        except Exception as e:
            st.error(f"Save failed: {e}")
        
        del st.session_state.current_row
        st.rerun()