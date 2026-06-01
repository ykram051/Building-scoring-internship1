#!/usr/bin/env python3
"""
Startup script for Building Analytics Dashboard
Ensures the application runs with proper environment setup
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Main startup function"""
    print("🏢 Starting Building Analytics Dashboard...")
    
    # Get the correct paths
    current_dir = Path(__file__).parent
    app_dir = current_dir / "app"
    
    if not app_dir.exists():
        print("❌ Error: app directory not found!")
        print(f"Looking for: {app_dir}")
        return 1
    
    main_file = app_dir / "main_db.py"
    if not main_file.exists():
        print("❌ Error: main_db.py not found!")
        print(f"Looking for: {main_file}")
        return 1
    
    print(f"📁 App directory: {app_dir}")
    print(f"🚀 Starting Streamlit application...")
    
    # Change to app directory and run streamlit
    os.chdir(app_dir)
    
    try:
        # Try to run with conda environment first (if available)
        import subprocess
        
        # Check if conda is available
        conda_path = "C:/Users/USER/anaconda3/Scripts/conda.exe"
        if os.path.exists(conda_path):
            print("🐍 Using conda environment...")
            result = subprocess.run([
                conda_path, "run", "-p", "C:\\Users\\USER\\anaconda3",
                "--no-capture-output", "streamlit", "run", "main_db.py"
            ], check=True)
        else:
            # Fallback to regular python
            print("🐍 Using regular python...")
            subprocess.run([sys.executable, "-m", "streamlit", "run", "main_db.py"], check=True)
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running application: {e}")
        print("\n💡 Try running manually:")
        print("   conda activate base")
        print("   cd app")
        print("   streamlit run main_db.py")
        return 1
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
        return 0

if __name__ == "__main__":
    sys.exit(main())
