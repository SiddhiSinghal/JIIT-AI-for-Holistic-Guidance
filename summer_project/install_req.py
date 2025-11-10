import subprocess
import sys

def install_requirements(requirements_file="requirements.txt"):
    """Install packages from a requirements.txt file."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])
        print("All packages installed successfully!")
    except subprocess.CalledProcessError as e:
        print("Error installing packages:", e)

if __name__ == "__main__":
    install_requirements()
