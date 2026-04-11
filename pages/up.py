import streamlit as st
import base64
import json
import subprocess
import sys
import re
from pathlib import Path
from datetime import datetime
import shutil

st.set_page_config(page_title="Upload Script", layout="wide")


# ---------------- CONFIG ----------------
SHARED_REQUIREMENTS_FILE = Path("shared_requirements.txt")
SHARED_ENV_PATH = Path("shared_env")
LOCK_FILE = Path("running.lock")

FORBIDDEN_PACKAGES = {
    "torch",
    "torchaudio",
    "torchvision",
    "tensorflow",
    "keras",
    "ultralytics",
    "opencv-python",
    "opencv-contrib-python",
    "transformers",
    "sentence-transformers",
    "pytorch-lightning",
    "jax",
    "jaxlib",
    "dgl",
    "faiss-cpu",
    "faiss-gpu",
}

ALLOWED_PACKAGES = {
    "numpy",
    "pandas",
    "scikit-learn",
    "sklearn",
    "joblib",
    "scipy",
    "librosa",
    "soundfile",
    "matplotlib",
    "seaborn",
    "tqdm",
}

MAX_TIME_SECONDS = 900
LOCK_MAX_AGE_SECONDS = MAX_TIME_SECONDS + 120


# ---------------- CHALLENGES ----------------
CHALLENGES = {
    "audiocl": {
        "display_name": "Classification Audio Marine",
        "train_input": "datasets/Defi1/train",
        "test_input": "datasets/Defi1/test",
        "leaderboard_file": "results_challenge_defi1.json",
        "input_type": "folder",
    },
    "gpscl": {
        "display_name": "Classification Multi-classes des Comportements",
        "train_input": "datasets/Defi2/train.csv",
        "test_input": "datasets/Defi2/test.csv",
        "leaderboard_file": "results_challenge_defi2.json",
        "input_type": "csv",
    },
}


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


def clean_team_files(team_name: str, challenge_name: str):
    safe_team_name = sanitize_team_name(team_name)
    upload_dir = Path("uploads") / challenge_name / safe_team_name
    model_dir = Path("model") / challenge_name / safe_team_name

    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    if model_dir.exists():
        shutil.rmtree(model_dir)


def get_venv_python_path(venv_path: Path) -> Path:
    if sys.platform == "win32":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def get_private_venv_path(team_name: str) -> Path:
    safe_team_name = sanitize_team_name(team_name)
    return Path("venvs") / safe_team_name


def get_private_requirements_path(team_name: str) -> Path:
    safe_team_name = sanitize_team_name(team_name)
    return Path("venvs") / safe_team_name / "installed_requirements.txt"


# ---------------- LOCK LOGIC ----------------
def remove_submission_lock():
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()


def create_submission_lock(team_name: str, stage: str, challenge_name: str):
    now = datetime.now()
    LOCK_FILE.write_text(
        json.dumps({
            "team_name": team_name,
            "challenge": challenge_name,
            "stage": stage,
            "started_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp": now.timestamp()
        }, indent=2),
        encoding="utf-8"
    )


def update_submission_lock_stage(team_name: str, stage: str, challenge_name: str):
    create_submission_lock(team_name, stage, challenge_name)


def get_running_submission_info():
    if not LOCK_FILE.exists():
        return None

    try:
        info = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        ts = info.get("timestamp")
        if ts is not None:
            age_seconds = datetime.now().timestamp() - float(ts)
            if age_seconds > LOCK_MAX_AGE_SECONDS:
                remove_submission_lock()
                return None
        return info
    except Exception:
        remove_submission_lock()
        return None


def lock_belongs_to_team(team_name: str, challenge_name: str) -> bool:
    info = get_running_submission_info()
    if not info:
        return False
    return info.get("team_name") == team_name and info.get("challenge") == challenge_name


def can_start_or_resume_submission(team_name: str, challenge_name: str):
    info = get_running_submission_info()
    if not info:
        return True, None
    if info.get("team_name") == team_name and info.get("challenge") == challenge_name:
        return True, info
    return False, info


def release_lock_if_owner(team_name: str, challenge_name: str):
    info = get_running_submission_info()
    if info and info.get("team_name") == team_name and info.get("challenge") == challenge_name:
        remove_submission_lock()


def get_lock_stage_for_team(team_name: str, challenge_name: str):
    info = get_running_submission_info()
    if not info:
        return None
    if info.get("team_name") == team_name and info.get("challenge") == challenge_name:
        return info.get("stage")
    return None


def cancel_submission_if_owner(team_name: str, challenge_name: str):
    stage = get_lock_stage_for_team(team_name, challenge_name)
    if stage in ("setup_env", "script_uploaded"):
        release_lock_if_owner(team_name, challenge_name)
        clean_team_files(team_name, challenge_name)
        return True
    return False


# ---------------- REQUIREMENTS UTILS ----------------
def parse_requirement_line(line: str):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if " #" in line:
        line = line.split(" #", 1)[0].strip()
    if ";" in line:
        line = line.split(";", 1)[0].strip()

    name_part = re.split(r"[<>=!~]", line, maxsplit=1)[0].strip()
    pkg_name = re.split(r"\[", name_part, maxsplit=1)[0].strip().lower()

    if not pkg_name:
        return None

    return {"raw": line, "name": pkg_name}


def read_requirements_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_requirements_text(text: str):
    packages = []
    for line in text.splitlines():
        parsed = parse_requirement_line(line)
        if parsed:
            packages.append(parsed)
    return packages

def validate_requirements_text(text: str):
    parsed = parse_requirements_text(text)

    if not parsed:
        return False, "Le requirements.txt est vide ou invalide.", [], []

    found_names = [p["name"] for p in parsed]

    #  Check uniquement les packages interdits
    forbidden_found = sorted({name for name in found_names if name in FORBIDDEN_PACKAGES})
    if forbidden_found:
        return False, f"Packages interdits détectés : {', '.join(forbidden_found)}", parsed, forbidden_found

    #  Tout le reste est autorisé
    return True, "Requirements valides (aucun package interdit).", parsed, []


def normalize_requirements_text(text: str):
    parsed = parse_requirements_text(text)
    return sorted({p["raw"].strip().lower() for p in parsed})


def matches_shared_requirements(team_requirements_text: str, shared_requirements_text: str) -> bool:
    team_norm = normalize_requirements_text(team_requirements_text)
    shared_norm = normalize_requirements_text(shared_requirements_text)
    return set(team_norm).issubset(set(shared_norm))


def private_env_matches_requirements(team_name: str, requirements_text: str) -> bool:
    private_env_path = get_private_venv_path(team_name)
    private_req_path = get_private_requirements_path(team_name)
    python_bin = get_venv_python_path(private_env_path)

    if not private_env_path.exists() or not python_bin.exists() or not private_req_path.exists():
        return False

    saved_text = private_req_path.read_text(encoding="utf-8")
    current_norm = set(normalize_requirements_text(requirements_text))
    saved_norm = set(normalize_requirements_text(saved_text))
    return current_norm == saved_norm


def save_private_requirements_snapshot(team_name: str, requirements_text: str):
    private_req_path = get_private_requirements_path(team_name)
    private_req_path.parent.mkdir(parents=True, exist_ok=True)
    private_req_path.write_text(requirements_text, encoding="utf-8")


def is_private_venv_ready(team_name: str) -> bool:
    private_env_path = get_private_venv_path(team_name)
    python_bin = get_venv_python_path(private_env_path)
    return private_env_path.exists() and python_bin.exists()


def ensure_shared_requirements_file():
    if not SHARED_REQUIREMENTS_FILE.exists():
        SHARED_REQUIREMENTS_FILE.write_text(
            "\n".join([
                "pandas==2.2.2",
                "numpy==1.26.4",
                "scikit-learn==1.4.2",
                "joblib==1.4.2",
                "scipy==1.13.1",
                "librosa==0.10.2.post1",
                "soundfile==0.12.1",
            ]),
            encoding="utf-8"
        )


def setup_env(env_path: Path, requirements_path: Path, recreate: bool = False):
    if recreate and env_path.exists():
        shutil.rmtree(env_path)

    env_path.mkdir(parents=True, exist_ok=True)
    python_bin = get_venv_python_path(env_path)

    if not python_bin.exists():
        subprocess.run(
            [sys.executable, "-m", "venv", str(env_path)],
            capture_output=True,
            text=True,
            check=True,
            timeout=MAX_TIME_SECONDS
        )

    pip_upgrade = subprocess.run(
        [str(python_bin), "-m", "pip", "install", "--upgrade", "pip"],
        capture_output=True,
        text=True,
        check=True,
        timeout=MAX_TIME_SECONDS
    )

    req_install = subprocess.run(
        [str(python_bin), "-m", "pip", "install", "--no-cache-dir", "-r", str(requirements_path)],
        capture_output=True,
        text=True,
        check=True,
        timeout=MAX_TIME_SECONDS
    )

    return {
        "python_bin": python_bin,
        "pip_stdout": pip_upgrade.stdout,
        "pip_stderr": pip_upgrade.stderr,
        "req_stdout": req_install.stdout,
        "req_stderr": req_install.stderr,
    }


def ensure_shared_env():
    ensure_shared_requirements_file()
    return setup_env(SHARED_ENV_PATH, SHARED_REQUIREMENTS_FILE, recreate=False)


def run_team_script(script_path: Path, team_name: str, python_bin: Path, challenge_name: str, challenge_config: dict):
    safe_team_name = sanitize_team_name(team_name)

    model_dir = Path("model") / challenge_name / safe_team_name
    model_dir.mkdir(parents=True, exist_ok=True)

    result_dir = Path("result")
    result_dir.mkdir(parents=True, exist_ok=True)

    result_path = result_dir / f"{challenge_name}_{safe_team_name}_result.json"

    train_cmd = [
        str(python_bin),
        str(script_path),
        "train",
        challenge_config["train_input"],
        str(model_dir),
    ]

    test_cmd = [
        str(python_bin),
        str(script_path),
        "test",
        challenge_config["test_input"],
        str(model_dir),
        str(result_path),
    ]

    train_proc = subprocess.run(
        train_cmd,
        capture_output=True,
        text=True,
        check=True,
        timeout=MAX_TIME_SECONDS
    )

    test_proc = subprocess.run(
        test_cmd,
        capture_output=True,
        text=True,
        check=True,
        timeout=MAX_TIME_SECONDS
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


def update_leaderboard(team_name: str, result_content: str, leaderboard_file: str):
    leaderboard_path = Path(leaderboard_file)
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
    diag_mean = float(team_result.get("diag_mean", 0))

    accuracy = accuracy_raw * 100 if accuracy_raw <= 1 else accuracy_raw
    precision = precision_raw * 100 if precision_raw <= 1 else precision_raw
    recall = recall_raw * 100 if recall_raw <= 1 else recall_raw
    f1_score = f1_raw * 100 if f1_raw <= 1 else f1_raw
    diag_mean = diag_mean * 100 if diag_mean <= 1 else diag_mean

    accuracy = round(min(max(accuracy, 0), 100), 2)
    precision = round(min(max(precision, 0), 100), 2)
    recall = round(min(max(recall, 0), 100), 2)
    f1_score = round(min(max(f1_score, 0), 100), 2)
    diag_mean = round(min(max(diag_mean, 0), 100), 2)       

    score = round((accuracy + precision + recall + f1_score + diag_mean) / 5, 2)

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
        "diag_mean": diag_mean,
        "score": score,
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    teams = sorted(teams, key=lambda x: (x.get("score", 0), x.get("accuracy", 0)), reverse=True)
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
            padding-top: 60px !important;
            padding-bottom: 170px !important;
            padding-left: 24px !important;
            padding-right: 24px !important;
        }}

        .hero {{
            text-align: center;
            width: 100%;
            margin-bottom: 28px;
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
            margin-bottom: 10px;
        }}

        .card-title-left {{
            font-family: 'Orbitron', sans-serif;
            font-size: 26px;
            color: #19ecff;
            margin: 0;
            text-shadow:
                0 0 6px #19ecff,
                0 0 14px #19ecff,
                0 0 28px rgba(25,236,255,0.7);
        }}

        .section-note {{
            font-family: 'Orbitron', sans-serif;
            font-size: 12px;
            color: rgba(255,255,255,0.72);
            margin-bottom: 18px;
        }}

        .locked-panel {{
            border: 1px dashed rgba(255,255,255,0.25);
            border-radius: 20px;
            padding: 36px 18px;
            text-align: center;
            min-height: 280px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Orbitron', sans-serif;
            color: rgba(255,255,255,0.82);
            background: rgba(255,255,255,0.03);
        }}

        .status-chip {{
            display: inline-block;
            padding: 8px 12px;
            border-radius: 999px;
            font-family: 'Orbitron', sans-serif;
            font-size: 11px;
            letter-spacing: 0.5px;
            color: #dffcff;
            border: 1px solid rgba(25,236,255,0.30);
            background: rgba(25,236,255,0.10);
            margin-bottom: 10px;
        }}

        div[data-testid="stFileUploader"] {{
            width: 100%;
            max-width: 100%;
            margin: 0 auto 18px auto;
        }}

        div[data-testid="stFileUploader"] > label {{
            display: none !important;
        }}

        div[data-testid="stFileUploaderDropzone"] {{
            background: rgba(0, 18, 42, 0.22) !important;
            border: 2px dashed rgba(25,236,255,0.42) !important;
            border-radius: 22px !important;
            padding: 24px 20px !important;
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
            font-size: 14px !important;
        }}

        div[data-testid="stFileUploader"] button span {{
            display: none !important;
        }}

        div[data-testid="stFileUploader"] button {{
            border-radius: 14px !important;
        }}

        div[data-testid="stAlert"] {{
            max-width: 100%;
            margin: 0 auto 16px auto;
            border-radius: 18px !important;
            font-family: 'Orbitron', sans-serif !important;
        }}

        div.stButton {{
            width: 100%;
        }}

        div.stButton > button {{
            width: 100%;
            min-height: 54px;
            border-radius: 18px;
            border: 1px solid rgba(25,236,255,0.30);
            font-family: 'Orbitron', sans-serif;
            font-size: 14px;
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

        div.stButton > button:disabled {{
            background: linear-gradient(180deg, #62717a 0%, #4d5961 100%) !important;
            color: rgba(255,255,255,0.72) !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
            box-shadow: none !important;
            cursor: not-allowed !important;
            opacity: 0.95 !important;
            transform: none !important;
        }}

        div.stButton > button:focus {{
            outline: none !important;
            color: #00131a;
        }}

        .mini-danger div.stButton > button {{
            background: linear-gradient(180deg, #ff8d8d 0%, #ff5e5e 100%) !important;
            color: #220000 !important;
            border: 1px solid rgba(255,94,94,0.40) !important;
            box-shadow:
                0 0 10px rgba(255,94,94,0.45),
                0 0 24px rgba(255,94,94,0.25),
                inset 0 0 10px rgba(255,255,255,0.18) !important;
            min-height: 44px !important;
            font-size: 12px !important;
        }}

        .mini-danger div.stButton > button:disabled {{
            background: linear-gradient(180deg, #776565 0%, #615555 100%) !important;
            color: rgba(255,255,255,0.70) !important;
            border: 1px solid rgba(255,255,255,0.10) !important;
            box-shadow: none !important;
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

        @media (max-width: 1000px) {{
            .main-title {{
                font-size: 46px;
            }}

            .sub-title {{
                font-size: 15px;
            }}

            .card-title-left {{
                font-size: 20px;
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


def render_lock_status(team_name: str, challenge_name: str):
    stage = get_lock_stage_for_team(team_name, challenge_name)
    if stage:
        st.markdown(f'<div class="status-chip">LOCK ACTIF • {stage}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-chip">AUCUN LOCK ACTIF</div>', unsafe_allow_html=True)


# ---------------- PAGE ----------------
set_bg("background3.png")

logo1 = get_base64("logo1.png")
logo2 = get_base64("logo2.png")
teams_data = load_teams("teams.json")
ensure_shared_requirements_file()

query_params = st.query_params
token_from_url = query_params.get("token", "")
challenge_from_url = query_params.get("challenge", "")

if isinstance(token_from_url, list):
    token_from_url = token_from_url[0] if token_from_url else ""
if isinstance(challenge_from_url, list):
    challenge_from_url = challenge_from_url[0] if challenge_from_url else ""

token_from_url = str(token_from_url).strip()
challenge_from_url = str(challenge_from_url).strip()

with st.container():
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    st.markdown('<div class="main-title">UPLOAD SCRIPT</div>', unsafe_allow_html=True)

    if challenge_from_url not in CHALLENGES:
        st.error("Challenge invalide ou absent dans l’URL.")
        st.info("Exemple : ?token=VOTRE_TOKEN&challenge=challenge_csv")
        st.stop()

    challenge_config = CHALLENGES[challenge_from_url]
    challenge_display_name = challenge_config["display_name"]


    is_valid_team = False
    team_name = None
    team_id = None
    running_info = get_running_submission_info()

    if not token_from_url:
        st.error("Aucun token trouvé dans l’URL.")
        st.info("Exemple : https://votre-app.streamlit.app/?token=VOTRE_TOKEN_SECRET&challenge=challenge_csv")
    else:
        is_valid_team, team_name, team_id = check_team_token(token_from_url, teams_data)
        if is_valid_team:
                st.markdown(f'<div class="sub-title">Challenge actif : {challenge_display_name}  | équipe : {team_name} </div>',
        unsafe_allow_html=True,
    )

        if not is_valid_team:
            st.error("Token invalide ou non autorisé.")

    if running_info:
        if is_valid_team and lock_belongs_to_team(team_name, challenge_from_url):
            st.info(
                f"Reprise de votre soumission en cours | équipe : {running_info.get('team_name', 'Unknown')} "
                f"| challenge : {running_info.get('challenge', 'unknown')} "
                f"| étape : {running_info.get('stage', 'unknown')} "
                f"| démarrée à {running_info.get('started_at', 'unknown')}."
            )
        else:
            st.warning(
                f"Une soumission est déjà en cours par l'équipe {running_info.get('team_name', 'Unknown')} "
                f"| challenge : {running_info.get('challenge', 'unknown')} "
                f"| étape : {running_info.get('stage', 'unknown')} "
                f"| démarrée à {running_info.get('started_at', 'unknown')}."
            )
    st.markdown('</div>', unsafe_allow_html=True)

if is_valid_team:
    safe_team_name = sanitize_team_name(team_name)
    req_dir = Path("requirements")
    req_dir.mkdir(parents=True, exist_ok=True)
    req_path = req_dir / f"{safe_team_name}_requirements.txt"

    requirements_done_key = f"requirements_done_{safe_team_name}_{challenge_from_url}"
    upload_started_key = f"upload_started_{safe_team_name}_{challenge_from_url}"
    submission_locked_key = f"submission_locked_{safe_team_name}_{challenge_from_url}"

    if requirements_done_key not in st.session_state:
        st.session_state[requirements_done_key] = False
    if upload_started_key not in st.session_state:
        st.session_state[upload_started_key] = False
    if submission_locked_key not in st.session_state:
        st.session_state[submission_locked_key] = False

    if lock_belongs_to_team(team_name, challenge_from_url):
        st.session_state[submission_locked_key] = True

    left_col, right_col = st.columns(2, gap="large")

    # ---------------- LEFT / REQUIREMENTS ----------------
    with left_col:
        current_team_lock_stage = get_lock_stage_for_team(team_name, challenge_from_url)

        title_col, cancel_col = st.columns([2.1, 1.2], gap="small")
        with title_col:
            st.markdown('<div class="card-title-left">ENV / REQUIREMENTS</div>', unsafe_allow_html=True)

        with cancel_col:
            can_show_cancel = current_team_lock_stage in ("setup_env", "script_uploaded")
            cancel_btn = False
            if can_show_cancel:
                st.markdown('<div class="mini-danger">', unsafe_allow_html=True)
                cancel_btn = st.button(
                    "ANNULER",
                    use_container_width=True,
                    disabled=st.session_state[upload_started_key]
                )
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.write("")

            if cancel_btn:
                cancelled = cancel_submission_if_owner(team_name, challenge_from_url)
                if cancelled:
                    st.session_state[submission_locked_key] = False
                    st.session_state.pop(f"python_bin_{safe_team_name}_{challenge_from_url}", None)
                    st.session_state.pop(f"env_mode_{safe_team_name}_{challenge_from_url}", None)
                    st.session_state[requirements_done_key] = False
                    st.session_state[upload_started_key] = False
                    st.success("Votre lock a été libéré. Vous pouvez recommencer la soumission.")
                    st.rerun()
                else:
                    st.error("Impossible d'annuler cette soumission.")

        st.markdown(
            '<div class="section-note">Valider les dépendances et préparer l’environnement avant de débloquer la soumission du script.</div>',
            unsafe_allow_html=True
        )

        render_lock_status(team_name, challenge_from_url)

        if current_team_lock_stage == "run_script":
            st.info("Votre soumission est en cours d'exécution. L'annulation est désactivée pendant run_script.")

        shared_requirements_text = read_requirements_text(SHARED_REQUIREMENTS_FILE)

        requirements_file = st.file_uploader(
            "Uploader requirements.txt",
            type=["txt"],
            key="requirements_upload",
            label_visibility="collapsed"
        )

        if requirements_file is not None:
            requirements_text = requirements_file.getvalue().decode("utf-8", errors="ignore")
            st.info(f"Fichier requirements détecté : {requirements_file.name}")

            is_valid_req, req_message, parsed_reqs, issues = validate_requirements_text(requirements_text)

            if is_valid_req:
                st.success(req_message)

                use_shared_env = matches_shared_requirements(requirements_text, shared_requirements_text)

                if use_shared_env:
                    env_mode = "shared"
                else:
           
                    env_mode = "private"

                confirm_requirements = st.button(
                    "CONFIRMER REQUIREMENTS",
                    use_container_width=True,
                    disabled=st.session_state[requirements_done_key]
                )

                if confirm_requirements:
                    st.session_state[requirements_done_key] = True

                    allowed, current_lock_info = can_start_or_resume_submission(team_name, challenge_from_url)

                    if not allowed:
                        st.error(
                            f"Impossible de commencer maintenant. "
                            f"Une soumission est déjà en cours par l'équipe {current_lock_info.get('team_name', 'Unknown')} "
                            f"à l'étape {current_lock_info.get('stage', 'unknown')}."
                        )
                        st.stop()

                    with open(req_path, "wb") as f:
                        f.write(requirements_file.getbuffer())

                    st.success(f"requirements.txt enregistré : {req_path}")

                    try:
                        if not current_lock_info:
                            create_submission_lock(team_name, "setup_env", challenge_from_url)
                        else:
                            update_submission_lock_stage(team_name, "setup_env", challenge_from_url)

                        if env_mode == "shared":
                            with st.spinner("Préparation du shared environment..."):
                                setup_output = ensure_shared_env()

                            python_bin = setup_output["python_bin"]
                            st.session_state[f"python_bin_{safe_team_name}_{challenge_from_url}"] = str(python_bin)
                            st.session_state[f"env_mode_{safe_team_name}_{challenge_from_url}"] = "shared"
                            st.session_state[submission_locked_key] = True
                            st.success("Shared environment prêt ✅")

                        else:
                            private_env_path = get_private_venv_path(team_name)

                            if private_env_matches_requirements(team_name, requirements_text):
                                python_bin = get_venv_python_path(private_env_path)
                                st.session_state[f"python_bin_{safe_team_name}_{challenge_from_url}"] = str(python_bin)
                                st.session_state[f"env_mode_{safe_team_name}_{challenge_from_url}"] = "private"
                                st.session_state[submission_locked_key] = True

                                setup_output = {
                                    "python_bin": python_bin,
                                    "pip_stdout": "",
                                    "pip_stderr": "",
                                    "req_stdout": "",
                                    "req_stderr": "",
                                }

                                st.success("Environnement privé existant réutilisé ✅")
                            else:
                                with st.spinner("Création ou mise à jour de l’environnement privé..."):
                                    setup_output = setup_env(private_env_path, req_path, recreate=True)

                                python_bin = setup_output["python_bin"]
                                save_private_requirements_snapshot(team_name, requirements_text)

                                st.session_state[f"python_bin_{safe_team_name}_{challenge_from_url}"] = str(python_bin)
                                st.session_state[f"env_mode_{safe_team_name}_{challenge_from_url}"] = "private"
                                st.session_state[submission_locked_key] = True
                                st.success("Environnement privé prêt ✅")

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

                        st.session_state[upload_started_key] = False
                        st.info("Environnement prêt. La partie script est maintenant débloquée.")
                        st.rerun()

                    except subprocess.TimeoutExpired:
                        release_lock_if_owner(team_name, challenge_from_url)
                        st.session_state[submission_locked_key] = False
                        st.error("Timeout pendant l'installation des dépendances (15 minutes max).")
                    except subprocess.CalledProcessError as e:
                        release_lock_if_owner(team_name, challenge_from_url)
                        st.session_state[submission_locked_key] = False
                        st.error("Erreur pendant la création de l’environnement ou l'installation des requirements.")
                        if e.stdout:
                            with st.expander("stdout"):
                                st.code(e.stdout)
                        if e.stderr:
                            with st.expander("stderr"):
                                st.code(e.stderr)
                    except Exception as e:
                        release_lock_if_owner(team_name, challenge_from_url)
                        st.session_state[submission_locked_key] = False
                        st.error(f"Erreur inattendue pendant le setup : {e}")
            else:
                st.error(req_message)

        env_mode_saved = st.session_state.get(f"env_mode_{safe_team_name}_{challenge_from_url}")
        python_bin_saved = st.session_state.get(f"python_bin_{safe_team_name}_{challenge_from_url}")

        if env_mode_saved == "shared" and python_bin_saved:
            st.success(f"Python utilisé : {python_bin_saved}")
        elif env_mode_saved == "private" and python_bin_saved:
            st.success(f"Python utilisé : {python_bin_saved}")
        elif is_private_venv_ready(team_name):
            current_python = get_venv_python_path(get_private_venv_path(team_name))
            st.success(f"Python utilisé : {current_python}")

    # ---------------- RIGHT / SCRIPT ----------------
    with right_col:
        st.markdown('<div class="card-title-left">SCRIPT / EXÉCUTION</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-note">Uploader le script Python, lancer train + test, puis publier le score dans le leaderboard.</div>',
            unsafe_allow_html=True
        )

        python_bin_saved = st.session_state.get(f"python_bin_{safe_team_name}_{challenge_from_url}")
        submission_locked = st.session_state.get(submission_locked_key, False) or lock_belongs_to_team(team_name, challenge_from_url)
        env_ready = python_bin_saved is not None or is_private_venv_ready(team_name)

        if not env_ready or not submission_locked:
            st.markdown(
                """
                <div class="locked-panel">
                    <div>
                        <div style="font-size:18px; margin-bottom:10px;">🔒 SECTION VERROUILLÉE</div>
                        <div style="font-size:13px; line-height:1.7;">
                            Confirmez d’abord les requirements et préparez l’environnement
                            dans la colonne de gauche pour débloquer cette zone.
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            if python_bin_saved:
                python_bin = Path(python_bin_saved)
            else:
                python_bin = get_venv_python_path(get_private_venv_path(team_name))

            uploaded_file = st.file_uploader(
                "Choisir un fichier Python",
                type=["py"],
                key="script_upload",
                label_visibility="collapsed"
            )

            if uploaded_file is not None:
                st.info(f"Fichier script sélectionné : {uploaded_file.name}")

                confirm = st.button(
                    "CONFIRMER UPLOAD",
                    use_container_width=True,
                    disabled=st.session_state[upload_started_key]
                )

                if confirm:
                    st.session_state[upload_started_key] = True
                    st.rerun()

                if st.session_state[upload_started_key]:
                    running_info = get_running_submission_info()

                    if not running_info:
                        create_submission_lock(team_name, "script_uploaded", challenge_from_url)
                        running_info = get_running_submission_info()
                    elif not lock_belongs_to_team(team_name, challenge_from_url):
                        st.error(
                            f"Impossible de lancer l'exécution maintenant. "
                            f"Une autre équipe est en cours : {running_info.get('team_name', 'Unknown')}."
                        )
                        st.stop()
                    elif running_info.get("stage") != "run_script":
                        update_submission_lock_stage(team_name, "script_uploaded", challenge_from_url)

                    save_dir = Path("uploads") / challenge_from_url
                    team_dir = save_dir / safe_team_name
                    team_dir.mkdir(parents=True, exist_ok=True)

                    save_path = team_dir / uploaded_file.name

                    if not save_path.exists():
                        with open(save_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        

                    if get_lock_stage_for_team(team_name, challenge_from_url) != "run_script":
                        try:
                            update_submission_lock_stage(team_name, "run_script", challenge_from_url)

                            with st.spinner("Exécution du script dans l’environnement sélectionné..."):
                                run_output = run_team_script(
                                    save_path,
                                    team_name,
                                    python_bin,
                                    challenge_from_url,
                                    challenge_config
                                )

                            st.success("Train + test exécutés avec succès ✅")

                            if run_output["result_content"]:
                                st.subheader("Résultat JSON")
                                st.code(run_output["result_content"], language="json")

                                updated, old_score, new_score = update_leaderboard(
                                    team_name,
                                    run_output["result_content"],
                                    challenge_config["leaderboard_file"]
                                )

                                if updated:
                                    st.success(f"Leaderboard mis à jour ✅ | Nouveau score : {new_score}%")
                                else:
                                    st.warning(
                                        f"Résultat non mis à jour. Ancien score : {old_score}% | Nouveau score : {new_score}%"
                                    )
                            else:
                                st.warning("Résultat non trouvé après exécution.")

                            clean_team_files(team_name, challenge_from_url)
                            

                        except subprocess.TimeoutExpired:
                            st.error("Timeout pendant l'exécution du script (15 minutes max).")
                            clean_team_files(team_name, challenge_from_url)
                        except subprocess.CalledProcessError as e:
                            st.error("Erreur pendant l'exécution du script.")
                            clean_team_files(team_name, challenge_from_url)
                            if e.stdout:
                                with st.expander("stdout"):
                                    st.code(e.stdout)
                            if e.stderr:
                                with st.expander("stderr"):
                                    st.code(e.stderr)
                        except Exception as e:
                            st.error(f"Erreur inattendue : {e}")
                            clean_team_files(team_name, challenge_from_url)
                        finally:
                            release_lock_if_owner(team_name, challenge_from_url)
                            st.session_state[submission_locked_key] = False

                            if 'run_output' in locals():
                                if run_output.get("train_stdout"):
                                    with st.expander("Train stdout"):
                                        st.code(run_output["train_stdout"])
                                if run_output.get("test_stdout"):
                                    with st.expander("Test stdout"):
                                        st.code(run_output["test_stdout"])
                                if run_output.get("train_stderr"):
                                    with st.expander("Train stderr"):
                                        st.code(run_output["train_stderr"])
                                if run_output.get("test_stderr"):
                                    with st.expander("Test stderr"):
                                        st.code(run_output["test_stderr"])


st.markdown(
    f'''
    <div class="logo-container">
        <img src="data:image/png;base64,{logo1}" id="big-logo">
        <img src="data:image/png;base64,{logo2}">
    </div>
    ''',
    unsafe_allow_html=True,
)