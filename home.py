import streamlit as st
import base64

st.set_page_config(page_title="Hackathon IA", layout="wide")


# ---------------- UTILS ----------------
def get_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


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
            padding-top: 90px !important;
            padding-bottom: 170px !important;
            padding-left: 24px !important;
            padding-right: 24px !important;
        }}

        .hero {{
            text-align: center;
            width: 100%;
        }}

        .title {{
            font-family: 'Orbitron', sans-serif;
            font-size: 129px;
            font-weight: 1000;
            color: #19ecff;
            letter-spacing: 2px;
            margin-bottom: 8px;
            text-shadow:
                0 0 8px #19ecff,
                0 0 18px #19ecff,
                0 0 38px #19ecff,
                0 0 70px rgba(25,236,255,0.9);
            animation: glowPulse 2s infinite alternate, floatTitle 4s ease-in-out infinite;
        }}

        .subtitle {{
            font-family: 'Orbitron', sans-serif;
            font-size: 20px;
            color: rgba(255,255,255,0.95);
            margin-bottom: 26px;
        }}

        .welcome {{
            font-family: 'Orbitron', sans-serif;
            font-size: 40px;
            font-weight: 700;
            color: #19ecff;
            margin-bottom: 16px;
            text-shadow:
                0 0 6px #19ecff,
                0 0 14px #19ecff,
                0 0 28px rgba(25,236,255,0.7);
        }}

        .desc {{
            max-width: 760px;
            margin: 0 auto 34px auto;
            font-family: 'Orbitron', sans-serif;
            font-size: 15px;
            line-height: 1.8;
            color: rgba(255,255,255,0.88);
        }}

        div.stButton {{
            width: 100%;
        }}

        div.stButton > button {{
            width: 100%;
            min-height: 60px;
            border-radius: 18px;
            border: 1px solid rgba(25,236,255,0.30);
            font-family: 'Orbitron', sans-serif;
            font-size: 16px;
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

            .title {{
                font-size: 44px;
            }}

            .subtitle {{
                font-size: 16px;
            }}

            .welcome {{
                font-size: 28px;
            }}

            .desc {{
                font-size: 13px;
                max-width: 95%;
            }}

            div.stButton > button {{
                min-height: 54px;
                font-size: 14px;
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

# Entire content centered in the middle column
left_margin, center_col, right_margin = st.columns([1.2, 2.2, 1.2])

with center_col:
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    st.markdown('<div class="title">HACKATHON IA</div>', unsafe_allow_html=True)
    st.markdown('<div class="welcome">Bienvenue</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="desc">Choisis la section que tu veux ouvrir. Tu peux aller vers la page de soumission des scripts ou directement consulter le leaderboard.</div>',
        unsafe_allow_html=True,
    )

    b1, spacer, b2 = st.columns([1, 0.18, 1])

    with b1:
        if st.button("UPLOAD SCRIPT", use_container_width=True):
            st.switch_page("pages/upload.py")

    with b2:
        if st.button("LEADERBOARD", use_container_width=True):
            st.switch_page("pages/leaderboard.py")

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