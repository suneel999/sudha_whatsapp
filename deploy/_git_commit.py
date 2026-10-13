import subprocess
import os

os.chdir(r"D:\sudha_hospital_whatsapp")

def run(cmd):
    print(">", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    if r.returncode != 0:
        raise SystemExit(r.returncode)

run(["git", "check-ignore", "-v", ".env"])
run(["git", "add", "-A"])
run(["git", "status", "--short"])
run(["git", "commit", "-F", "deploy/COMMIT_MSG.txt"])
run(["git", "log", "-1", "--oneline"])
run(["git", "status", "-sb"])
