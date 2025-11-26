import streamlit as st
from supabase import create_client, Client
import pandas as pd
import os
import time

st.set_page_config(page_title="Beauty Rater", layout="centered")
st.title("Human Beauty Rater 🌍")

@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection()

all_rows = []
start = 0
batch_size = 1000

while True:
    rows = []
    for attempt in range(3):
        try:
            response = supabase.table("ratings").select("*").range(start, start + batch_size - 1).execute()
            rows = response.data
            break
        except Exception as e:
            if attempt < 2:
                time.sleep(1)
                continue
            else:
                st.error(f"Database Fetch Failed:\n\n{e}")
                st.stop()
    
    if not rows:
        break
        
    all_rows.extend(rows)
    
    if len(rows) < batch_size:
        break
        
    start += batch_size
    time.sleep(0.1)

df = pd.DataFrame(all_rows)

if df.empty:
    st.warning("Database returned 0 rows.")
    st.stop()

df.columns = df.columns.str.strip()

if "score" not in df.columns:
    st.error("Column 'score' not found.")
    st.stop()

df["score"] = pd.to_numeric(df["score"], errors="coerce")

rated_df = df[df["score"].notna() & (df["score"] > 0)]
total = len(df)
rated_count = len(rated_df)
remaining = total - rated_count
progress = rated_count / total if total > 0 else 0

st.progress(progress)
st.caption(f"🚀 Progress: {rated_count}/{total} rated. ({remaining} left)")

unrated = df[df["score"].isna() | (df["score"] <= 0)]

if unrated.empty:
    st.balloons()
    st.success("🎉 All images have been rated!")
    st.stop()

if "current_row" not in st.session_state:
    st.session_state.current_row = unrated.sample(1).iloc[0]

row = st.session_state.current_row
filename = row["filename"]
img_path = os.path.join("images", filename)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists(img_path):
        st.image(img_path, caption=f"File: {filename}", width=350)
    else:
        st.error(f"❌ Image not found: {filename}")
        del st.session_state.current_row
        st.rerun()

with st.form("rating_form"):
    st.write("### How attractive is this face?")
    score = st.slider("Score", 1.0, 5.0, 3.0, 0.1)
    rater_name = st.text_input("Your Name (Optional)")
    
    submit = st.form_submit_button("Submit Rating", type="primary")

    if submit:
        try:
            data = {"score": float(score)}
            if rater_name:
                data["rater_id"] = rater_name.strip()

            supabase.table("ratings").update(data).eq("filename", filename).execute()

            st.toast(f"Saved! You rated **{filename}** a **{score}**")

        except Exception as e:
            st.error(f"Save failed:\n\n{e}")

        del st.session_state.current_row
        st.rerun()