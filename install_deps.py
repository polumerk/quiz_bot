#!/usr/bin/env python3
"""
Install dependencies for Quiz Bot in Replit
"""

import subprocess
import sys
import os

def install_dependencies():
    """Install required dependencies"""
    print("🔧 Installing Quiz Bot dependencies...")
    
    try:
        # Upgrade pip first
        print("📦 Upgrading pip...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
        
        # Install dependencies from requirements.txt
        print("📋 Installing from requirements.txt...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        
        print("✅ All dependencies installed successfully!")
        print("\n🎯 You can now run the bot with: python main.py")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ requirements.txt not found!")
        sys.exit(1)

if __name__ == "__main__":
    install_dependencies()