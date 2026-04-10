import streamlit as st
import base64
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

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


def check_team_token(token: str, teams_data: dict):
    token = token.strip()
    for team in teams_data.get("teams", []):
        if team.get("token", "").strip() == token:
            return True, team.get("team_name", "Unknown Team"), team.get("team_id", "")
    return False, None, None


def sanitize_team_name(team_name: str) -> str:
    return "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in team_name.replace(" ", "_"))


def get_venv_python_path(venv_path: Path) -> Path:
    if sys.platform == "win32":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def is_venv_ready(team_name: str) -> bool:
    safe_team_name = sanitize_team_name(team_name)
    venv_path = Path("venvs") / safe_team_name
    python_bin = get_venv_python_path(venv_path)
    return venv_path.exists() and python_bin.exists()


def setup_virtualenv(team_name: str, requirements_path: Path):
    safe_team_name = sanitize_team_name(team_name)
    venv_path = Path("venvs") / safe_team_name
    venv_path.mkdir(parents=True, exist_ok=True)

    python_bin = get_venv_python_path(venv_path)

    # Create venv only if missing
    if not python_bin.exists():
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path)],
            capture_output=True,
            text=True,
            check=True
        )

    # Upgrade pip
    pip_upgrade = subprocess.run(
        [str(python_bin), "-m", "pip", "install", "--upgrade", "pip"],
        capture_output=True,
        text=True,
        check=True
    )

    # Install requirements
    req_install = subprocess.run(
        [str(python_bin), "-m", "pip", "install", "-r", str(requirements_path)],
        capture_output=True,
        text=True,
        check=True
    )

    return {
        "python_bin": python_bin,
        "pip_stdout": pip_upgrade.stdout,
        "pip_stderr": pip_upgrade.stderr,
        "req_stdout": req_install.stdout,
        "req_stderr": req_install.stderr,
    }


def run_team_script(script_path: Path, team_name: str, python_bin: Path):
    safe_team_name = sanitize_team_name(team_name)

    model_dir = Path("model") / safe_team_name
    model_dir.mkdir(parents=True, exist_ok=True)

    result_dir = Path("result")
    result_dir.mkdir(parents=True, exist_ok=True)

    result_path = result_dir / f"{safe_team_name}_result.json"

    train_cmd = [
        str(python_bin),
        str(script_path),
        "train",
        "uploads_csv/iris_train.csv",
        str(model_dir),
    ]

    test_cmd = [
        str(python_bin),
        str(script_path),
        "test",
        "uploads_csv/iris_test.csv",
        str(model_dir),
        str(result_path),
    ]

    train_proc = subprocess.run(
        train_cmd,
        capture_output=True,
        text=True,
        check=True
    )

    test_proc = subprocess.run(
        test_cmd,
        capture_output=True,
        text=True,
        check=True
    )

    result_content = None
    if result_path.exists():
        result_content = result_path.read_text(encoding="utf-8")

    return {
        "train_stdout": train_proc.stdout,
        "train_stderr": train_proc.stderr,
        "test_stdout": test_proc.stdout,
        "test_stderr": test_proc.stderr,
        "result_path": str(result_path),
        "result_content": result_content,
    }


def update_leaderboard(team_name: str, result_content: str):
    leaderboard_path = Path("results.json")

    team_result = json.loads(result_content)

    if leaderboard_path.exists():
        with open(leaderboard_path, "r", encoding="utf-8") as f:
            leaderboard = json.load(f)
    else:
        leaderboard = {"teams": []}

    teams = leaderboard.get("teams", [])

    accuracy_raw = float(team_result.get("accuracy", 0))
    precision_raw = float(team_result.get("precision", 0))
    recall_raw = float(team_result.get("recall", 0))
    f1_raw = float(team_result.get("f1_score", 0))

    accuracy = accuracy_raw * 100 if accuracy_raw <= 1 else accuracy_raw
    precision = precision_raw * 100 if precision_raw <= 1 else precision_raw
    recall = recall_raw * 100 if recall_raw <= 1 else recall_raw
    f1_score = f1_raw * 100 if f1_raw <= 1 else f1_raw

    accuracy = round(min(max(accuracy, 0), 100), 2)
    precision = round(min(max(precision, 0), 100), 2)
    recall = round(min(max(recall, 0), 100), 2)
    f1_score = round(min(max(f1_score, 0), 100), 2)

    score = round((accuracy + precision + recall + f1_score) / 4, 2)

    old_team = next((t for t in teams if t.get("name") == team_name), None)

    if old_team is not None:
        old_score = float(old_team.get("score", 0))
        if score <= old_score:
            return False, old_score, score
        teams = [t for t in teams if t.get("name") != team_name]

    teams.append({
        "name": team_name,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "score": score,
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    teams = sorted(
        teams,
        key=lambda x: (x.get("score", 0), x.get("accuracy", 0)),
        reverse=True
    )

    leaderboard["teams"] = teams

    with open(leaderboard_path, "w", encoding="utf-8") as f:
        json.dump(leaderboard, f, indent=2)

    return True, None, score


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

query_params = st.query_params
token_from_url = query_params.get("token", "")

if isinstance(token_from_url, list):
    token_from_url = token_from_url[0] if token_from_url else ""

token_from_url = str(token_from_url).strip()

left_margin, center_col, right_margin = st.columns([1.1, 2.6, 1.1])

with center_col:
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    st.markdown('<div class="main-title">UPLOAD SCRIPT</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Téléverse d’abord requirements.txt, puis le script Python.</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="card-title">Soumission sécurisée du script</div>', unsafe_allow_html=True)

    is_valid_team = False
    team_name = None
    team_id = None

    if not token_from_url:
        st.error("Aucun token trouvé dans l’URL.")
        st.info("Exemple : https://votre-app.streamlit.app/?token=VOTRE_TOKEN_SECRET")
    else:
        is_valid_team, team_name, team_id = check_team_token(token_from_url, teams_data)

        if is_valid_team:
            st.markdown(
                f'<div class="card-text">Lien sécurisé reconnu pour l’équipe : <b>{team_name}</b></div>',
                unsafe_allow_html=True,
            )
            st.success(f"Accès autorisé — équipe reconnue : {team_name}")
        else:
            st.error("Token invalide ou non autorisé.")

    if is_valid_team:
        safe_team_name = sanitize_team_name(team_name)
        req_dir = Path("requirements")
        req_dir.mkdir(parents=True, exist_ok=True)
        req_path = req_dir / f"{safe_team_name}_requirements.txt"

        st.markdown("### Étape 1 : Upload requirements.txt")

        requirements_file = st.file_uploader(
            "Uploader requirements.txt",
            type=["txt"],
            key="requirements_upload",
            label_visibility="collapsed"
        )

        if is_venv_ready(team_name):
            current_python = get_venv_python_path(Path("venvs") / safe_team_name)
            st.success("Environnement virtuel déjà prêt pour cette équipe ✅")
            st.info(f"Python utilisé : {current_python}")

        if requirements_file is not None:
            st.info(f"Fichier requirements détecté : {requirements_file.name}")

            c1, c2, c3 = st.columns([1, 1, 1])
            with c2:
                confirm_requirements = st.button("CONFIRMER REQUIREMENTS", use_container_width=True)

            if confirm_requirements:
                with open(req_path, "wb") as f:
                    f.write(requirements_file.getbuffer())

                st.success(f"requirements.txt enregistré : {req_path}")

                try:
                    with st.spinner("Création du venv et installation des dépendances..."):
                        setup_output = setup_virtualenv(team_name, req_path)

                    st.session_state[f"python_bin_{safe_team_name}"] = str(setup_output["python_bin"])

                    st.success("Environnement prêt ✅")

                    if setup_output["pip_stdout"]:
                        with st.expander("Upgrade pip stdout"):
                            st.code(setup_output["pip_stdout"])

                    if setup_output["pip_stderr"]:
                        with st.expander("Upgrade pip stderr"):
                            st.code(setup_output["pip_stderr"])

                    if setup_output["req_stdout"]:
                        with st.expander("Install requirements stdout"):
                            st.code(setup_output["req_stdout"])

                    if setup_output["req_stderr"]:
                        with st.expander("Install requirements stderr"):
                            st.code(setup_output["req_stderr"])

                except subprocess.CalledProcessError as e:
                    st.error("Erreur pendant la création du venv ou l'installation des requirements.")
                    if e.stdout:
                        with st.expander("stdout"):
                            st.code(e.stdout)
                    if e.stderr:
                        with st.expander("stderr"):
                            st.code(e.stderr)
                except Exception as e:
                    st.error(f"Erreur inattendue pendant le setup : {e}")

        st.markdown("### Étape 2 : Upload du script Python")

        env_ready = is_venv_ready(team_name)

        if not env_ready:
            st.warning("Tu dois d’abord uploader et confirmer requirements.txt avant de soumettre le script.")
        else:
            python_bin = get_venv_python_path(Path("venvs") / safe_team_name)

            uploaded_file = st.file_uploader(
                "Choisir un fichier Python",
                type=["py"],
                key="script_upload",
                label_visibility="collapsed"
            )

            if uploaded_file is not None:
                st.info(f"Fichier script sélectionné : {uploaded_file.name}")

                v1, gap11, bc, gap22, v3 = st.columns([1, 0.15, 1, 0.15, 1])

                with bc:
                    confirm = st.button("CONFIRMER UPLOAD", use_container_width=True)

                if confirm:
                    save_dir = Path("uploads")
                    team_dir = save_dir / safe_team_name
                    team_dir.mkdir(parents=True, exist_ok=True)

                    save_path = team_dir / uploaded_file.name

                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    st.success(f"Fichier enregistré : {save_path}")

                    try:
                        with st.spinner("Exécution du script dans l’environnement virtuel..."):
                            run_output = run_team_script(save_path, team_name, python_bin)

                        st.success("Train + test exécutés avec succès dans le venv ✅")
                        st.info("Fin d’exécution — aucun besoin de désactiver manuellement le venv.")

                        if run_output["result_content"]:
                            st.subheader("Résultat JSON")
                            st.code(run_output["result_content"], language="json")

                            updated, old_score, new_score = update_leaderboard(team_name, run_output["result_content"])

                            if updated:
                                st.success(f"Leaderboard mis à jour ✅ | Nouveau score : {new_score}%")
                            else:
                                st.warning(
                                    f"Résultat non mis à jour. Ancien score : {old_score}% | Nouveau score : {new_score}%"
                                )
                        else:
                            st.warning("Résultat non trouvé après exécution.")

                        if run_output["train_stdout"]:
                            with st.expander("Train stdout"):
                                st.code(run_output["train_stdout"])

                        if run_output["test_stdout"]:
                            with st.expander("Test stdout"):
                                st.code(run_output["test_stdout"])

                        if run_output["train_stderr"]:
                            with st.expander("Train stderr"):
                                st.code(run_output["train_stderr"])

                        if run_output["test_stderr"]:
                            with st.expander("Test stderr"):
                                st.code(run_output["test_stderr"])

                    except subprocess.CalledProcessError as e:
                        st.error("Erreur pendant l'exécution du script.")
                        if e.stdout:
                            with st.expander("stdout"):
                                st.code(e.stdout)
                        if e.stderr:
                            with st.expander("stderr"):
                                st.code(e.stderr)
                    except Exception as e:
                        st.error(f"Erreur inattendue : {e}")


st.markdown(
    f'''
    <div class="logo-container">
        <img src="data:image/png;base64,{logo1}" id="big-logo">
        <img src="data:image/png;base64,{logo2}">
    </div>
    ''',
    unsafe_allow_html=True,
)