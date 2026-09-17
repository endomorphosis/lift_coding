
import json
import os
import sys
import subprocess
import tempfile
import shutil

# Configuration
REPO_URL = "https://github.com/yezz123/Athena"
REPO_NAME = "athena"

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def emit_allowed(payload):
    """Emit a JSON object to indicate a handler is allowed."""
    print(f"{GREEN}[ALLOWED] {payload}{RESET}")

def emit_undeclared(payload):
    """Emit a JSON object to indicate a handler is not allowed."""
    print(f"{RED}[UNDECLARED] {payload}{RESET}")

# Main function
if __name__ == "__main__":
    # Check if we have the required tools
    try:
        import flask
        import sqlite3
    except ImportError:
        print(f"{YELLOW}Flask and SQLite3 are required. Installing...{RESET}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "sqlite3"])

    # Create a temporary directory for the lab
    temp_dir = tempfile.mkdtemp()
    print(f"{YELLOW}Created temporary directory: {temp_dir}{RESET}")

    # Clone the repository
    try:
        subprocess.check_call(["git", "clone", REPO_URL, temp_dir])
    except subprocess.CalledProcessError:
        print(f"{RED}Failed to clone repository{RESET}")
        sys.exit(1)

    # Change to the repository directory
    os.chdir(temp_dir)

    # Run the application in good security mode
    try:
        subprocess.check_call([sys.executable, "app.py", "--mode", "good"])
    except subprocess.CalledProcessError:
        print(f"{RED}Failed to run good security mode{RESET}")
        sys.exit(1)

    # Run the application in bad security mode
    try:
        subprocess.check_call([sys.executable, "app.py", "--mode", "bad"])
    except subprocess.CalledProcessError:
        print(f"{RED}Failed to run bad security mode{RESET}")
        sys.exit(1)

    # Emit the final JSON record
    emit_allowed({"status": "success", "message": "Athena lab setup complete"})
