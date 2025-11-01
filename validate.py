#!/usr/bin/env python3
"""
Validation script for Telegram Music Bot MVP v2.1
Checks if all required files and structure are present.
"""
import os
import json
from pathlib import Path

def check_file_exists(filepath: str) -> bool:
    """Check if a file exists."""
    return Path(filepath).exists()

def check_directory_exists(dirpath: str) -> bool:
    """Check if a directory exists."""
    return Path(dirpath).exists()

def validate_project():
    """Validate the complete project structure."""
    print("🔍 Validating Telegram Music Bot MVP v2.1...\n")
    
    required_files = [
        "app.py",
        "config.py", 
        "requirements.txt",
        ".env.example",
        "README.md",
        "bot/__init__.py",
        "bot/client.py",
        "bot/core/player.py",
        "bot/core/queue.py",
        "bot/helpers/assistant.py",
        "bot/helpers/keyboards.py",
        "bot/helpers/localization.py",
        "bot/helpers/formatting.py",
        "bot/helpers/youtube.py",
        "bot/persistence/state.py",
        "bot/persistence/storage.py",
        "bot/plugins/start.py",
        "bot/plugins/play.py",
        "bot/plugins/controls.py",
        "bot/plugins/queue.py",
        "bot/plugins/callbacks.py",
        "locales/en.json",
        "locales/ar.json"
    ]
    
    print("📁 Checking project structure...")
    missing_files = []
    for file_path in required_files:
        if check_file_exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path}")
            missing_files.append(file_path)
    
    print(f"\n📊 Files checked: {len(required_files)}")
    print(f"✅ Present: {len(required_files) - len(missing_files)}")
    print(f"❌ Missing: {len(missing_files)}")
    
    if missing_files:
        print("\n⚠️  Missing files:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    # Check directory structure
    print("\n📂 Checking directory structure...")
    required_dirs = [
        "bot",
        "bot/core",
        "bot/helpers", 
        "bot/persistence",
        "bot/plugins",
        "locales"
    ]
    
    for dir_path in required_dirs:
        if check_directory_exists(dir_path):
            print(f"  ✅ {dir_path}/")
        else:
            print(f"  ❌ {dir_path}/")
            return False
    
    # Validate locale files
    print("\n🌐 Validating locale files...")
    try:
        with open("locales/en.json", "r", encoding="utf-8") as f:
            en_data = json.load(f)
        print(f"  ✅ en.json ({len(en_data)} keys)")
        
        with open("locales/ar.json", "r", encoding="utf-8") as f:
            ar_data = json.load(f)
        print(f"  ✅ ar.json ({len(ar_data)} keys)")
        
        # Check if translations match
        en_keys = set(en_data.keys())
        ar_keys = set(ar_data.keys())
        
        if en_keys == ar_keys:
            print("  ✅ Translation keys match")
        else:
            missing_keys = en_keys - ar_keys
            extra_keys = ar_keys - en_keys
            if missing_keys:
                print(f"  ⚠️  Missing keys in ar.json: {missing_keys}")
            if extra_keys:
                print(f"  ⚠️  Extra keys in ar.json: {extra_keys}")
    
    except Exception as e:
        print(f"  ❌ Error validating locales: {e}")
        return False
    
    # Check requirements.txt
    print("\n📦 Checking requirements.txt...")
    try:
        with open("requirements.txt", "r") as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        
        expected_packages = [
            "pyrogram",
            "pytgcalls", 
            "tgcrypto",
            "yt-dlp",
            "ffmpeg-python",
            "aiohttp",
            "aiofiles",
            "python-dotenv",
            "pydantic",
            "motor",
            "tinydb"
        ]
        
        installed_packages = []
        for req in requirements:
            for pkg in expected_packages:
                if pkg in req:
                    installed_packages.append(pkg)
        
        print(f"  ✅ {len(installed_packages)} core packages specified")
        
        missing_packages = set(expected_packages) - set(installed_packages)
        if missing_packages:
            print(f"  ⚠️  Missing packages: {missing_packages}")
        else:
            print("  ✅ All required packages present")
            
    except Exception as e:
        print(f"  ❌ Error validating requirements: {e}")
        return False
    
    # Check .env.example
    print("\n🔐 Checking .env.example...")
    try:
        with open(".env.example", "r") as f:
            env_vars = [line.split("=")[0] for line in f if "=" in line and line.strip()]
        
        expected_vars = [
            "API_ID", "API_HASH", "BOT_TOKEN", 
            "SESSION_STRING", "ASSISTANT_USERNAME",
            "DOWNLOAD_DIR", "LOG_LEVEL", "PORT", "STATE_BACKEND"
        ]
        
        print(f"  ✅ {len(env_vars)} environment variables defined")
        
        missing_vars = set(expected_vars) - set(env_vars)
        if missing_vars:
            print(f"  ⚠️  Missing variables: {missing_vars}")
        else:
            print("  ✅ All required variables present")
            
    except Exception as e:
        print(f"  ❌ Error validating .env.example: {e}")
        return False
    
    print("\n" + "="*60)
    print("🎉 VALIDATION COMPLETE!")
    print("="*60)
    print("\n✅ All core components are present and properly structured.")
    print("📋 Next steps:")
    print("   1. Install dependencies: pip install -r requirements.txt")
    print("   2. Copy .env.example to .env and configure")
    print("   3. Generate assistant session string")
    print("   4. Run the bot: python app.py")
    print("\n🚀 Ready for deployment!")
    
    return True

if __name__ == "__main__":
    validate_project()
