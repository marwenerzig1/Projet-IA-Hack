import streamlit as st
import json
import pandas as pd
import time
import base64
from pathlib import Path

st.set_page_config(page_title="Classement IA", layout="wide")

# ---------------- SESSION MEMORY ----------------
if "previous_ranks_ch1" not in st.session_state:
    st.session_state.previous_ranks_ch1 = {}

if "previous_ranks_ch2" not in st.session_state:
    st.session_state.previous_ranks_ch2 = {}

if "last_alert" not in st.session_state:
    st.session_state.last_alert = None

if "alert_time" not in st.session_state:
    st.session_state.alert_time = 0

# ---------------- FILES ----------------
RESULTS_FILE_CH1 = "results_challenge_iris.json"
RESULTS_FILE_CH2 = "results_challenge_audio.json"

CHALLENGE_1_TITLE = "CHALLENGE IRIS"
CHALLENGE_2_TITLE = "CHALLENGE AUDIO"

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
        padding-left: 14px;
        padding-right: 14px;
        max-width: 100% !important;
    }}

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

    .challenge-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 18px;
        align-items: start;
        width: 100%;
    }}

    .challenge-card {{
        min-width: 0;
        width: 100%;
    }}

    .challenge-title {{
        text-align: center;
        font-family: 'Orbitron', sans-serif;
        font-size: 26px;
        color: #00eaff;
        margin-bottom: 16px;
        margin-top: 8px;
        text-shadow:
            0 0 4px #00eaff,
            0 0 8px #00eaff,
            0 0 16px #00eaff;
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

    @keyframes zoomAlert {{
        0% {{ transform: scale(1); }}
        50% {{ transform: scale(1.22); }}
        100% {{ transform: scale(1); }}
    }}

    .table-wrapper {{
        width: 100%;
        overflow-x: auto;
        overflow-y: hidden;
        -webkit-overflow-scrolling: touch;
    }}

    .custom-table {{
        width: 100%;
        min-width: 0;
        border-collapse: collapse;
        font-family: 'Orbitron';
        background: rgba(0,10,30,0.5);
        backdrop-filter: blur(12px);
        border-radius: 12px;
        overflow: hidden;
        table-layout: auto;
    }}

    .custom-table th {{
        padding: 12px 10px;
        color: #00eaff;
        background: rgba(0,255,255,0.1);
        font-size: 14px;
        white-space: nowrap;
    }}

    .custom-table td {{
        padding: 10px 10px;
        text-align: center;
        color: white;
        border-bottom: 1px solid rgba(0,255,255,0.1);
        font-size: 13px;
        white-space: nowrap;
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

    .rank-alert-overlay {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        display: flex;
        justify-content: center;
        align-items: center;
        flex-direction: column;
        background: rgba(0, 0, 20, 0.60);
        backdrop-filter: blur(8px);
        z-index: 99999;
        padding: 20px;
    }}

    .rank-alert-text {{
        font-family: 'Orbitron', sans-serif;
        font-size: 86px;
        font-weight: 700;
        color: #00eaff;
        text-align: center;
        line-height: 1.2;
        text-shadow:
            0 0 10px #00eaff,
            0 0 20px #00eaff,
            0 0 40px #00eaff,
            0 0 80px #00eaff;
        animation: glowPulse 1.2s infinite alternate, zoomAlert 0.85s ease-in-out infinite;
    }}

    .rank-alert-sub {{
        margin-top: 20px;
        font-family: 'Orbitron', sans-serif;
        font-size: 36px;
        color: white;
        text-align: center;
        text-shadow:
            0 0 5px #00eaff,
            0 0 10px #00eaff,
            0 0 20px #00eaff;
    }}

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

    /* Grand laptop */
    @media (max-width: 1600px) {{
        .title {{
            font-size: 42px;
            margin-bottom: 28px;
        }}

        .challenge-title {{
            font-size: 22px;
            margin-bottom: 10px;
        }}

        .challenge-grid {{
            gap: 12px;
        }}

        .custom-table th {{
            padding: 10px 8px;
            font-size: 12px;
        }}

        .custom-table td {{
            padding: 9px 8px;
            font-size: 11px;
        }}

        .logo-container img {{
            height: 38px;
        }}

        #tt {{
            height: 95px;
        }}

        .rank-alert-text {{
            font-size: 64px;
        }}

        .rank-alert-sub {{
            font-size: 28px;
        }}
    }}

    /* Laptop */
    @media (max-width: 1300px) {{
        .title {{
            font-size: 34px;
        }}

        .challenge-title {{
            font-size: 18px;
        }}

        .challenge-grid {{
            grid-template-columns: 1fr;
            gap: 18px;
        }}

        .custom-table th {{
            padding: 8px 6px;
            font-size: 11px;
        }}

        .custom-table td {{
            padding: 7px 6px;
            font-size: 10px;
        }}

        .rank-alert-text {{
            font-size: 46px;
        }}

        .rank-alert-sub {{
            font-size: 22px;
        }}
    }}

    /* Small screen */
    @media (max-width: 768px) {{
        .title {{
            font-size: 28px;
        }}

        .challenge-title {{
            font-size: 16px;
        }}

        .custom-table th {{
            font-size: 10px;
            padding: 6px 5px;
        }}

        .custom-table td {{
            font-size: 9px;
            padding: 6px 5px;
        }}

        .logo-container {{
            gap: 14px;
            bottom: 10px;
        }}

        .logo-container img {{
            height: 28px;
        }}

        #tt {{
            height: 65px;
        }}

        .rank-alert-text {{
            font-size: 34px;
        }}

        .rank-alert-sub {{
            font-size: 16px;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)

set_bg("background3.png")

# ---------------- TITLE ----------------
st.markdown('<div class="title">CLASSEMENT</div>', unsafe_allow_html=True)

# ---------------- LOAD LOGOS ONCE ----------------
logo1 = get_base64("logo1.png")
logo2 = get_base64("logo2.png")

st.markdown(f"""
<div class="logo-container">
    <img src="data:image/png;base64,{logo1}" id="tt">
    <img src="data:image/png;base64,{logo2}">
</div>
""", unsafe_allow_html=True)

# ---------------- ALERT ----------------
def render_alert(alert_placeholder, alert_data):
    if not alert_data:
        alert_placeholder.empty()
        return

    name = alert_data["name"]
    direction = alert_data["direction"]
    old_rank = alert_data["old_rank"]
    new_rank = alert_data["new_rank"]
    challenge = alert_data["challenge"]

    main_text = f"{name} MONTE !" if direction == "up" else f"{name} DESCEND !"
    sub_text = f"{challenge} • Rang {old_rank} → {new_rank}"

    alert_placeholder.markdown(f"""
    <div class="rank-alert-overlay">
        <div class="rank-alert-text">{main_text}</div>
        <div class="rank-alert-sub">{sub_text}</div>
    </div>
    """, unsafe_allow_html=True)

# ---------------- TABLE ----------------
def render_table(df, previous_ranks_key, challenge_label):
    columns_to_show = [col for col in df.columns if col not in ["f1_score", "last_update"]]

    html = "<table class='custom-table'><thead><tr>"

    for col in columns_to_show:
        html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"

    rank_changed = False
    alert_data = None
    previous_ranks = st.session_state[previous_ranks_key]

    for _, row in df.iterrows():
        name = row["name"]
        current_rank = row["Rank"]
        prev_rank = previous_ranks.get(name)
        row_class = ""

        if prev_rank is not None:
            if current_rank < prev_rank:
                rank_changed = True
                row_class = "rank-up"
                if alert_data is None:
                    alert_data = {
                        "name": name,
                        "direction": "up",
                        "old_rank": prev_rank,
                        "new_rank": current_rank,
                        "challenge": challenge_label
                    }
            elif current_rank > prev_rank:
                rank_changed = True
                row_class = "rank-down"
                if alert_data is None:
                    alert_data = {
                        "name": name,
                        "direction": "down",
                        "old_rank": prev_rank,
                        "new_rank": current_rank,
                        "challenge": challenge_label
                    }

        if current_rank == 1:
            row_class += " gold"
        elif current_rank == 2:
            row_class += " silver"
        elif current_rank == 3:
            row_class += " bronze"

        html += f"<tr class='{row_class.strip()}'>"
        for col in columns_to_show:
            html += f"<td>{row[col]}</td>"
        html += "</tr>"

        previous_ranks[name] = current_rank

    html += "</tbody></table>"
    return html, rank_changed, alert_data

# ---------------- DATA ----------------
def load_data(file_name):
    path = Path(file_name)
    if not path.exists():
        return {"teams": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

tables_placeholder = st.empty()
alert_placeholder = st.empty()

# ---------------- LOOP ----------------
while True:
    data_ch1 = load_data(RESULTS_FILE_CH1)
    data_ch2 = load_data(RESULTS_FILE_CH2)

    df1 = pd.DataFrame(data_ch1["teams"])
    df2 = pd.DataFrame(data_ch2["teams"])

    if not df1.empty:
        df1 = df1.sort_values(by="score", ascending=False).reset_index(drop=True)
        df1.insert(0, "Rank", range(1, len(df1) + 1))
    else:
        df1 = pd.DataFrame(columns=["Rank", "name", "accuracy", "precision", "recall", "f1_score", "score", "last_update"])

    if not df2.empty:
        df2 = df2.sort_values(by="score", ascending=False).reset_index(drop=True)
        df2.insert(0, "Rank", range(1, len(df2) + 1))
    else:
        df2 = pd.DataFrame(columns=["Rank", "name", "accuracy", "precision", "recall", "f1_score", "score", "last_update"])

    table_html_1, changed_1, alert_data_1 = render_table(df1, "previous_ranks_ch1", CHALLENGE_1_TITLE)
    table_html_2, changed_2, alert_data_2 = render_table(df2, "previous_ranks_ch2", CHALLENGE_2_TITLE)

    with tables_placeholder.container():
        st.markdown(f"""
        <div class="challenge-grid">
            <div class="challenge-card">
                <div class="challenge-title">{CHALLENGE_1_TITLE}</div>
                <div class="table-wrapper">{table_html_1}</div>
            </div>
            <div class="challenge-card">
                <div class="challenge-title">{CHALLENGE_2_TITLE}</div>
                <div class="table-wrapper">{table_html_2}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    chosen_alert = None
    if changed_1 and alert_data_1 is not None:
        chosen_alert = alert_data_1
    elif changed_2 and alert_data_2 is not None:
        chosen_alert = alert_data_2

    if chosen_alert:
        st.session_state.alert_time = time.time()
        st.session_state.last_alert = chosen_alert

    if time.time() - st.session_state.alert_time < 3:
        render_alert(alert_placeholder, st.session_state.last_alert)
    else:
        alert_placeholder.empty()

    time.sleep(1)