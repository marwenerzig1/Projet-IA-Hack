import streamlit as st
import json
import pandas as pd
import time
import base64

st.set_page_config(page_title="Leaderboard IA", layout="wide")


# ---------------- SESSION MEMORY ----------------
if "previous_ranks" not in st.session_state:
    st.session_state.previous_ranks = {}

# ---------------- UTILS ----------------
def get_base64(image_file):
    with open(image_file, "rb") as f:
        return base64.b64encode(f.read()).decode()

# ---------------- BACKGROUND ----------------
def set_bg(image_file):
    with open(image_file, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    st.markdown(f"""
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&display=swap');

    .stApp {{
        background: url("data:image/png;base64,{encoded}");
        background-size: cover;
        background-position: center;
    }}

    header, footer {{visibility: hidden;}}

    .block-container {{
        background: transparent !important;
        padding-top: 60px;
    }}

    /* TITLE */
    .title {{
        text-align: center;
        font-family: 'Orbitron', sans-serif;
        font-size: 48px;
        color: #00eaff;
        margin-bottom: 40px;

        text-shadow:
            0 0 5px #00eaff,
            0 0 10px #00eaff,
            0 0 20px #00eaff,
            0 0 40px #00eaff;

        animation: glowPulse 2s infinite alternate, float 4s ease-in-out infinite;
    }}

    @keyframes glowPulse {{
        from {{
            text-shadow:
                0 0 5px #00eaff,
                0 0 10px #00eaff,
                0 0 20px #00eaff;
        }}
        to {{
            text-shadow:
                0 0 10px #00eaff,
                0 0 20px #00eaff,
                0 0 40px #00eaff,
                0 0 80px #00eaff;
        }}
    }}

    @keyframes float {{
        0% {{ transform: translateY(0px); }}
        50% {{ transform: translateY(-6px); }}
        100% {{ transform: translateY(0px); }}
    }}


    /* TABLE */
    .custom-table {{
        width: 100%;
        border-collapse: collapse;
        font-family: 'Orbitron';
        background: rgba(0,10,30,0.5);
        backdrop-filter: blur(12px);
        border-radius: 12px;
        overflow: hidden;
    }}

    .custom-table th {{
        padding: 14px;
        color: #00eaff;
        background: rgba(0,255,255,0.1);
    }}

    .custom-table td {{
        padding: 12px;
        text-align: center;
        color: white;
        border-bottom: 1px solid rgba(0,255,255,0.1);
    }}

    .custom-table tr:hover {{
        background: rgba(0,255,255,0.08);
    }}

        .gold {{
        background: rgba(255, 215, 0, 0.1);
        box-shadow: 0 0 12px rgba(255,215,0,0.5);
    }}

    .silver {{
        background: rgba(192, 192, 192, 0.1);
    }}

    .bronze {{
        background: rgba(205, 127, 50, 0.1);
    }}

    /* LOGOS */
    .logo-container {{
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        display: flex;
        gap: 40px;
        align-items: center;
    }}

    .logo-container img {{
        height: 50px;
        filter:
            brightness(0) saturate(100%) invert(73%) sepia(96%) saturate(748%) hue-rotate(135deg)
            drop-shadow(0 0 10px #00eaff)
            drop-shadow(0 0 25px #00eaff);
    }}

    #tt {{
        height: 140px;
     }}

    </style>
    """, unsafe_allow_html=True)

set_bg("background3.png")

# ---------------- TITLE ----------------
st.markdown('<div class="title">LEADERBOARD</div>', unsafe_allow_html=True)

# ---------------- LOAD LOGOS ONCE ----------------
logo1 = get_base64("logo1.png")
logo2 = get_base64("logo2.png")

st.markdown(f"""
<div class="logo-container">
    <img src="data:image/png;base64,{logo1}" id="tt">
    <img src="data:image/png;base64,{logo2}">
</div>
""", unsafe_allow_html=True)

# ---------------- TABLE ----------------

# ---------------- TABLE ----------------
def render_table(df):
    html = "<table class='custom-table'><thead><tr>"

    for col in df.columns:
        html += f"<th>{col}</th>"

    html += "</tr></thead><tbody>"

    rank_changed = False

    for _, row in df.iterrows():
        name = row["name"]
        current_rank = row["Rank"]

        prev_rank = st.session_state.previous_ranks.get(name)

        row_class = ""

        # DETECT CHANGE
        if prev_rank is not None:
            if current_rank < prev_rank:
                row_class = "rank-up"
                rank_changed = True
            elif current_rank > prev_rank:
                row_class = "rank-down"
                rank_changed = True

        # TOP 3 STYLE
        if current_rank == 1:
            row_class += " gold"
        elif current_rank == 2:
            row_class += " silver"
        elif current_rank == 3:
            row_class += " bronze"

        html += f"<tr class='{row_class}'>"

        for val in row:
            html += f"<td>{val}</td>"

        html += "</tr>"

        st.session_state.previous_ranks[name] = current_rank

    html += "</tbody></table>"

    st.markdown(html, unsafe_allow_html=True)

    return rank_changed

# ---------------- DATA ----------------
def load_data():
    with open("results.json", "r") as f:
        return json.load(f)

placeholder = st.empty()

# ---------------- LOOP ----------------
while True:
    data = load_data()

    df = pd.DataFrame(data["teams"])

    # 🔥 SORT BY ACCURACY (dynamic ranking)
    df = df.sort_values(by="accuracy", ascending=False)

    df.insert(0, "Rank", range(1, len(df)+1))

    with placeholder.container():
        changed = render_table(df)


    time.sleep(3)