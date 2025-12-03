import sys
import subprocess
from pathlib import Path

def main():
    app_path = Path(__file__).parent / "frontend" / "app.py"
    
    print("Starting Retail Insights Assistant...")
    print(f"Loading application from: {app_path}")
    
    try:
        subprocess.run([
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path)
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error starting application: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    main()

