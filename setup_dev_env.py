#!/usr/bin/env python3
"""
Interactive development environment setup script for StockLeague.

This script helps you set up your local development environment by:
1. Creating a virtual environment
2. Installing dependencies
3. Initializing the database
4. Running the app
"""

import os
import sys
import subprocess
import platform

def run_command(cmd, description):
    """Run a command and report success/failure."""
    print(f"\n✅ {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✓ {description} completed successfully")
            return True
        else:
            print(f"   ❌ Error during {description}:")
            print(f"   {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Exception during {description}: {e}")
        return False

def main():
    """Main setup flow."""
    print("\n" + "="*60)
    print("🚀 StockLeague Development Environment Setup")
    print("="*60)
    
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    is_windows = platform.system() == "Windows"
    python_cmd = "python" if is_windows else "python3"
    venv_activate = "venv\\Scripts\\activate" if is_windows else "source venv/bin/activate"
    
    print(f"\n📁 Project directory: {project_dir}")
    print(f"💻 Operating system: {platform.system()}")
    print(f"🐍 Python command: {python_cmd}")
    
    # Step 1: Create virtual environment
    print("\n" + "-"*60)
    print("Step 1: Create Virtual Environment")
    print("-"*60)
    
    if os.path.exists("venv"):
        print("✓ Virtual environment already exists")
    else:
        if not run_command(f"{python_cmd} -m venv venv", "Creating virtual environment"):
            print("❌ Failed to create virtual environment")
            return False
    
    # Step 2: Upgrade pip
    print("\n" + "-"*60)
    print("Step 2: Upgrade pip, setuptools, and wheel")
    print("-"*60)
    
    pip_cmd = f"{python_cmd} -m pip" if is_windows else f"{python_cmd} -m pip"
    if not run_command(f"{pip_cmd} install --upgrade pip setuptools wheel", "Upgrading pip"):
        return False
    
    # Step 3: Install requirements
    print("\n" + "-"*60)
    print("Step 3: Install Dependencies")
    print("-"*60)
    
    if not run_command(f"{pip_cmd} install -r requirements.txt", "Installing main dependencies"):
        return False
    
    if os.path.exists("dev-requirements.txt"):
        if not run_command(f"{pip_cmd} install -r dev-requirements.txt", "Installing dev dependencies"):
            print("⚠️  Warning: Failed to install dev dependencies, continuing anyway...")
    
    # Step 4: Initialize database
    print("\n" + "-"*60)
    print("Step 4: Initialize Database")
    print("-"*60)
    
    if os.path.exists("database/stocks.db"):
        print("✓ Database already exists")
        response = input("  Would you like to recreate it? (y/N): ").strip().lower()
        if response == 'y':
            os.remove("database/stocks.db")
            if not run_command(f"{python_cmd} initialize_database.py", "Creating database"):
                return False
    else:
        if not run_command(f"{python_cmd} initialize_database.py", "Creating database"):
            print("⚠️  Warning: Database initialization failed, it will be created on first run")
    
    # Step 5: Summary and next steps
    print("\n" + "="*60)
    print("✨ Setup Complete!")
    print("="*60)
    
    print("\n📌 Next steps:")
    print("\n1️⃣  Activate your virtual environment:")
    if is_windows:
        print(f"   venv\\Scripts\\activate")
    else:
        print(f"   source venv/bin/activate")
    
    print("\n2️⃣  Run the application:")
    print(f"   {python_cmd} app.py")
    
    print("\n3️⃣  Open your browser:")
    print(f"   http://localhost:5000")
    
    print("\n💡 To run tests:")
    print(f"   pytest -v")
    
    print("\n📖 For more information, see DEV_SETUP.md")
    print("\n")
    
    # Optional: Offer to run the app
    response = input("Would you like to start the app now? (Y/n): ").strip().lower()
    if response != 'n':
        print("\n🚀 Starting Flask application...")
        print("   Open http://localhost:5000 in your browser")
        print("   Press Ctrl+C to stop the server\n")
        
        if is_windows:
            os.system("venv\\Scripts\\activate && python app.py")
        else:
            os.system("source venv/bin/activate && python3 app.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
