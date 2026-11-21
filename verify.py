"""One-command submission verification."""
import subprocess, sys
from pathlib import Path

subprocess.check_call([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
subprocess.check_call([sys.executable, "generate_episodes.py"])
subprocess.check_call([sys.executable, "demo.py"])
for split in ("train", "dev"):
    episodes = list((Path("episodes") / split).glob("episode_*"))
    assert len(episodes) == 10, f"{split}: expected 10 episodes"
    assert all((item / "manifest.json").exists() and not (item / "truth.json").exists() for item in episodes)
print("Submission verification passed.")
