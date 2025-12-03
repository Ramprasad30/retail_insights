import subprocess
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def check_python_version():
    if sys.version_info < (3, 10):
        print("[FAIL] Python 3.10 or higher is required")
        print(f"       Current version: {sys.version}")
        return False
    print(f"[OK] Python version: {sys.version.split()[0]}")
    return True


def install_requirements():
    print("\nInstalling required packages...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("[OK] All packages installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] Error installing packages: {e}")
        return False


def check_data_files():
    print("\nChecking data files...")
    data_path = Path("Sales Dataset/Sales Dataset")
    
    required_files = [
        "Amazon Sale Report.csv",
        "International sale Report.csv",
        "Sale Report.csv"
    ]
    
    all_present = True
    for file in required_files:
        file_path = data_path / file
        if file_path.exists():
            size = file_path.stat().st_size / (1024 * 1024)  # MB
            print(f"   [OK] {file} ({size:.2f} MB)")
        else:
            print(f"   [MISSING] {file}")
            all_present = False
    
    return all_present


def check_api_key():
    print("\nChecking API key...")
    api_key = os.getenv("OPENAI_API_KEY", "")
    
    if api_key:
        print(f"   [OK] OPENAI_API_KEY is set ({api_key[:8]}...)")
        return True
    else:
        print("   [WARN] OPENAI_API_KEY not set in environment")
        print("   Note: You can set it in the Streamlit UI")
        return False


def create_directories():
    print("\nCreating directories...")
    directories = ["vector_store"]
    
    for dir_name in directories:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(parents=True)
            print(f"   [OK] Created {dir_name}/")
        else:
            print(f"   [OK] {dir_name}/ already exists")


def main():
    print("=" * 60)
    print("Retail Insights Assistant - Setup")
    print("=" * 60)
    
    if not check_python_version():
        sys.exit(1)
    
    if not install_requirements():
        print("\nSome packages failed to install. Please check errors above.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    create_directories()
    
    data_present = check_data_files()
    api_key_set = check_api_key()
  
    print("\n" + "=" * 60)
    print("Setup Summary")
    print("=" * 60)
    
    if data_present and api_key_set:
        print("[OK] All checks passed! You're ready to go.")
        print("\nTo start the application, run:")
        print("   streamlit run app.py")
    elif data_present:
        print("[WARN] Data files found, but API key not set.")
        print("       You can set it in the Streamlit UI when you run the app.")
        print("\nTo start the application, run:")
        print("   streamlit run app.py")
    else:
        print("[FAIL] Some data files are missing.")
        print("       Please ensure all CSV files are in 'Sales Dataset/Sales Dataset/'")
    
    print("=" * 60)


if __name__ == "__main__":
    main()

