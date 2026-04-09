import streamlit as st
import base64
import json
from pathlib import Path

st.set_page_config(page_title="Upload Script", layout="wide")


# ---------------- UTILS ----------------
def get_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def load_teams(json_path: str = "teams.json") -> dict:
    path = Path(json_path)
    if not path.exists():
        return {"teams": []}

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_team_id(team_id: str, teams_data: dict):
    team_id = team_id.strip()
    for team in teams_data.get("teams", []):
        if team.get("team_id", "").strip() == team_id:
            return True, team.get("team_name", "Unknown Team")
    return False, None


# ---------------- STYLE ----------------
def set_bg(image_file: str):
    encoded = get_base64(image_file)

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;800&display=swap');

        html, body, [data-testid="stAppViewContainer"], .stApp {{
            margin: 0;
            padding: 0;
        }}

        [data-testid="stHeader"], header, footer {{
            display: none !important;
            visibility: hidden !important;
        }}

        .stApp {{
            background: url("data:image/png;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}

        [data-testid="stAppViewContainer"] {{
            padding: 0 !important;
        }}

        .block-container {{
            max-width: 100% !important;
            padding-top: 80px !important;
            padding-bottom: 170px !important;
            padding-left: 24px !important;
            padding-right: 24px !important;
        }}

        .hero {{
            text-align: center;
            width: 100%;
        }}

        .main-title {{
            font-family: 'Orbitron', sans-serif;
            font-size: 68px;
            font-weight: 800;
            color: #19ecff;
            letter-spacing: 2px;
            margin-bottom: 10px;
            text-shadow:
                0 0 8px #19ecff,
                0 0 18px #19ecff,
                0 0 38px #19ecff,
                0 0 70px rgba(25,236,255,0.9);
            animation: glowPulse 2s infinite alternate, floatTitle 4s ease-in-out infinite;
        }}

        .sub-title {{
            font-family: 'Orbitron', sans-serif;
            font-size: 18px;
            color: rgba(255,255,255,0.95);
            margin-bottom: 20px;
        }}

        .card-title {{
            font-family: 'Orbitron', sans-serif;
            font-size: 34px;
            color: #19ecff;
            margin-bottom: 12px;
            text-shadow:
                0 0 6px #19ecff,
                0 0 14px #19ecff,
                0 0 28px rgba(25,236,255,0.7);
        }}

        .card-text {{
            max-width: 760px;
            margin: 0 auto 24px auto;
            font-family: 'Orbitron', sans-serif;
            font-size: 15px;
            line-height: 1.8;
            color: rgba(255,255,255,0.88);
        }}

        div[data-testid="stTextInput"] {{
            max-width: 980px;
            margin: 0 auto 22px auto;
        }}

        div[data-testid="stTextInput"] input {{
            background: rgba(0, 18, 42, 0.28) !important;
            color: white !important;
            border: 2px solid rgba(25,236,255,0.35) !important;
            border-radius: 18px !important;
            padding: 14px 16px !important;
            font-family: 'Orbitron', sans-serif !important;
            font-size: 15px !important;
        }}

        div[data-testid="stTextInput"] label {{
            font-family: 'Orbitron', sans-serif !important;
            color: #19ecff !important;
        }}

        div[data-testid="stFileUploader"] {{
            width: 100%;
            max-width: 980px;
            margin: 0 auto 24px auto;
        }}

        div[data-testid="stFileUploader"] > label {{
            display: none !important;
        }}

        div[data-testid="stFileUploaderDropzone"] {{
            background: rgba(0, 18, 42, 0.22) !important;
            border: 2px dashed rgba(25,236,255,0.42) !important;
            border-radius: 24px !important;
            padding: 26px 24px !important;
        }}

        div[data-testid="stFileUploaderDropzone"]:hover {{
            background: rgba(0, 18, 42, 0.30) !important;
            border: 2px dashed rgba(25,236,255,0.62) !important;
        }}

        div[data-testid="stFileUploaderDropzoneInstructions"] {{
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 18px !important;
            flex-wrap: wrap !important;
        }}

        div[data-testid="stFileUploaderDropzoneInstructions"] > div {{
            font-family: 'Orbitron', sans-serif !important;
            color: rgba(255,255,255,0.88) !important;
            font-size: 15px !important;
        }}

        div[data-testid="stFileUploader"] button span {{
            display: none !important;
        }}

        div[data-testid="stFileUploader"] button {{
            border-radius: 14px !important;
        }}

        div[data-testid="stAlert"] {{
            max-width: 980px;
            margin: 0 auto 18px auto;
            border-radius: 18px !important;
            font-family: 'Orbitron', sans-serif !important;
        }}

        div.stButton {{
            width: 100%;
        }}

        div.stButton > button {{
            width: 100%;
            min-height: 58px;
            border-radius: 18px;
            border: 1px solid rgba(25,236,255,0.30);
            font-family: 'Orbitron', sans-serif;
            font-size: 15px;
            font-weight: 700;
            letter-spacing: 0.5px;
            color: #00131a;
            background: linear-gradient(180deg, #38f3ff 0%, #12dfee 100%);
            box-shadow:
                0 0 10px #19ecff,
                0 0 24px rgba(25,236,255,0.45),
                inset 0 0 10px rgba(255,255,255,0.20);
            transition: all 0.25s ease;
        }}

        div.stButton > button:hover {{
            transform: translateY(-2px) scale(1.02);
            box-shadow:
                0 0 16px #19ecff,
                0 0 36px rgba(25,236,255,0.70),
                inset 0 0 12px rgba(255,255,255,0.30);
            color: #00131a;
            border: 1px solid rgba(25,236,255,0.45);
        }}

        div.stButton > button:focus {{
            outline: none !important;
            color: #00131a;
        }}

        .logo-container {{
            position: fixed;
            bottom: 18px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 34px;
            z-index: 999;
            flex-wrap: wrap;
        }}

        .logo-container img {{
            height: 52px;
            object-fit: contain;
            filter:
                brightness(0) saturate(100%) invert(73%) sepia(96%) saturate(748%) hue-rotate(135deg)
                drop-shadow(0 0 10px #19ecff)
                drop-shadow(0 0 24px #19ecff);
        }}

        #big-logo {{
            height: 130px;
        }}

        @keyframes glowPulse {{
            from {{
                text-shadow:
                    0 0 8px #19ecff,
                    0 0 18px #19ecff,
                    0 0 38px #19ecff;
            }}
            to {{
                text-shadow:
                    0 0 12px #19ecff,
                    0 0 24px #19ecff,
                    0 0 50px #19ecff,
                    0 0 90px rgba(25,236,255,1);
            }}
        }}

        @keyframes floatTitle {{
            0% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-5px); }}
            100% {{ transform: translateY(0px); }}
        }}

        @media (max-width: 900px) {{
            .block-container {{
                padding-top: 70px !important;
                padding-bottom: 150px !important;
            }}

            .main-title {{
                font-size: 44px;
            }}

            .sub-title {{
                font-size: 15px;
            }}

            .card-title {{
                font-size: 26px;
            }}

            .card-text {{
                font-size: 13px;
                max-width: 95%;
            }}

            div[data-testid="stFileUploaderDropzone"] {{
                padding: 18px 14px !important;
            }}

            div.stButton > button {{
                min-height: 52px;
                font-size: 13px;
            }}

            #big-logo {{
                height: 88px;
            }}

            .logo-container img {{
                height: 38px;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------- PAGE ----------------
set_bg("background3.png")

logo1 = get_base64("logo1.png")
logo2 = get_base64("logo2.png")
teams_data = load_teams("teams.json")

left_margin, center_col, right_margin = st.columns([1.1, 2.6, 1.1])

with center_col:
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    st.markdown('<div class="main-title">UPLOAD SCRIPT</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Téléverse un script Python puis ouvre la page des résultats / leaderboard.</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="card-title">Soumission du script</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-text">Entre ton Team ID pour autoriser la soumission du script.</div>',
        unsafe_allow_html=True,
    )

    team_id_input = st.text_input("Team ID", placeholder="Ex: ALPHA2026")

    is_valid_team = False
    team_name = None

    if team_id_input.strip():
        is_valid_team, team_name = check_team_id(team_id_input, teams_data)

        if is_valid_team:
            st.success(f"ID valide — équipe reconnue : {team_name}")
        else:
            st.error("ID invalide. Impossible de soumettre un script.")

    if is_valid_team:
        uploaded_file = st.file_uploader(
            "Choisir un fichier Python",
            type=["py"],
            label_visibility="collapsed"
        )

        if uploaded_file is not None:

            st.info(f"Fichier sélectionné : {uploaded_file.name}")

            v1, gap11, bc, gap22, v3 = st.columns([1, 0.15, 1, 0.15, 1])

            with bc:
                confirm = st.button("CONFIRMER UPLOAD", use_container_width=True)

            if confirm:
                save_dir = Path("uploads")

                safe_team_name = team_name.replace(" ", "_")
                team_dir = save_dir / safe_team_name

                # create team folder
                team_dir.mkdir(parents=True, exist_ok=True)

                save_path = team_dir / uploaded_file.name

                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

    st.success(f"Fichier enregistré : {save_path}")
    b1, gap1, b2, gap2, b3 = st.columns([1, 0.15, 1, 0.15, 1])

    with b1:
        if st.button("ACCUEIL", use_container_width=True):
            st.switch_page("home.py")

    with b2:
        if st.button("VOIR LES RÉSULTATS", use_container_width=True):
            st.switch_page("pages/leaderboard.py")

    with b3:
        if st.button("RAFRAÎCHIR", use_container_width=True):
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

st.markdown(
    f'''
    <div class="logo-container">
        <img src="data:image/png;base64,{logo1}" id="big-logo">
        <img src="data:image/png;base64,{logo2}">
    </div>
    ''',
    unsafe_allow_html=True,
)