"""
github_push.py
--------------
Push the DGA project files to GitHub using the GitHub REST API.
No local git installation required.

Usage:
    python github_push.py --token YOUR_PAT_HERE
"""

import argparse
import base64
import os
import sys
import requests

REPO_OWNER = "sandeepjha2501-bot"
REPO_NAME  = "DGA"
BRANCH     = "main"
API_BASE   = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

# Files to push (relative to this script's directory)
# Large files excluded (model pkl, wordlist, Tranco cache)
FILES_TO_PUSH = [
    "dga_core.py",
    "train_dga_detector.py",
    "test_predict.py",
    "generate_dga_data.py",
    "fetch_live_data.py",
    "make_wordlist.py",
    "requirements.txt",
    "README.md",
    ".gitignore",
    "dga_data.csv",
    "DGA_Detector_Colab.ipynb",
]

NOTEBOOK_SOURCE = (
    r"C:\Users\THEXP\AppData\Local\Packages"
    r"\5319275A.WhatsAppDesktop_cv1g1gvanyjgm\LocalState\sessions"
    r"\7A1C818EBA16371751602EAD994E5F44770CD185\transfers\2026-42"
    r"\DGA_Detector_Colab.ipynb"
)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_headers(token: str) -> dict:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def get_file_sha(path: str, headers: dict) -> str | None:
    """Get the current SHA of a file in the repo (needed to update it)."""
    r = requests.get(f"{API_BASE}/contents/{path}", headers=headers)
    if r.status_code == 200:
        return r.json().get("sha")
    return None


def push_file(local_path: str, repo_path: str, headers: dict,
              commit_message: str) -> bool:
    """Push a single file to the GitHub repo."""
    try:
        with open(local_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError:
        print(f"  [skip] {repo_path} — file not found locally")
        return False

    sha = get_file_sha(repo_path, headers)
    payload = {
        "message": commit_message,
        "content": content,
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha  # required to update existing file

    r = requests.put(
        f"{API_BASE}/contents/{repo_path}",
        headers=headers,
        json=payload,
    )
    if r.status_code in (200, 201):
        action = "updated" if sha else "created"
        print(f"  [ok] {repo_path} — {action}")
        return True
    else:
        print(f"  [ERROR] {repo_path} — {r.status_code}: {r.json().get('message', r.text[:200])}")
        return False


def ensure_main_branch(token: str) -> None:
    """Create the 'main' branch from HEAD if it doesn't exist yet."""
    headers = get_headers(token)
    # Check if main exists
    r = requests.get(f"{API_BASE}/branches/main", headers=headers)
    if r.status_code == 200:
        return  # already exists

    # Try to get HEAD SHA from default branch
    r2 = requests.get(f"{API_BASE}", headers=headers)
    default = r2.json().get("default_branch", "main")
    if default == "main":
        return

    r3 = requests.get(f"{API_BASE}/git/refs/heads/{default}", headers=headers)
    if r3.status_code != 200:
        return  # repo might be empty — first push will create main

    sha = r3.json()["object"]["sha"]
    requests.post(
        f"{API_BASE}/git/refs",
        headers=headers,
        json={"ref": "refs/heads/main", "sha": sha},
    )
    print(f"[setup] Created 'main' branch from '{default}'")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--token", required=True, help="GitHub Personal Access Token")
    args = p.parse_args()

    headers = get_headers(args.token)

    # Verify token works
    r = requests.get(f"{API_BASE}", headers=headers)
    if r.status_code == 404:
        print(f"ERROR: Repo {REPO_OWNER}/{REPO_NAME} not found or token lacks access.")
        sys.exit(1)
    print(f"[ok] Authenticated — pushing to github.com/{REPO_OWNER}/{REPO_NAME}")

    ensure_main_branch(args.token)

    commit_msg = "feat: complete DGA detector project — live data + local runner"
    ok = err = skip = 0

    for filename in FILES_TO_PUSH:
        if filename == "DGA_Detector_Colab.ipynb":
            # Use the original notebook from WhatsApp downloads
            local_path = NOTEBOOK_SOURCE
        else:
            local_path = os.path.join(PROJECT_DIR, filename)

        success = push_file(local_path, filename, headers, commit_msg)
        if success:
            ok += 1
        else:
            if os.path.exists(local_path if filename != "DGA_Detector_Colab.ipynb" else NOTEBOOK_SOURCE):
                err += 1
            else:
                skip += 1

    print(f"\n{'='*50}")
    print(f"  Pushed: {ok}  |  Errors: {err}  |  Skipped: {skip}")
    print(f"  View: https://github.com/{REPO_OWNER}/{REPO_NAME}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

