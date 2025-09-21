#!/usr/bin/env python3
import os
import subprocess
import json

def setup_firebase():
    """Setup Firebase project properly"""
    print("🔧 Setting up Firebase project...")
    
    # Check if we're already in a Firebase project
    if os.path.exists(".firebaserc"):
        print("✅ Firebase project already configured")
        return True
    
    # Set the Firebase project ID (replace with your actual project ID)
    project_id = "neethi-saarathi-ids"
    
    # Create .firebaserc
    firebaserc = {
        "projects": {
            "default": project_id
        }
    }
    
    with open(".firebaserc", "w") as f:
        json.dump(firebaserc, f, indent=2)
    
    print(f"✅ Created .firebaserc for project: {project_id}")
    
    # Create firebase.json
    firebase_config = {
        "hosting": {
            "public": "out",
            "ignore": [
                "firebase.json",
                "**/.*",
                "**/node_modules/**"
            ],
            "rewrites": [
                {
                    "source": "**",
                    "destination": "/index.html"
                }
            ]
        }
    }
    
    with open("firebase.json", "w") as f:
        json.dump(firebase_config, f, indent=2)
    
    print("✅ Created firebase.json")
    
    # Login to Firebase (if not already logged in)
    try:
        print("🔐 Checking Firebase login...")
        result = subprocess.run("firebase login", shell=True, capture_output=True, text=True, timeout=60)
        if "Already logged in" in result.stdout or "Success" in result.stdout:
            print("✅ Already logged in to Firebase")
        else:
            print("⚠️ Please login to Firebase when prompted")
            subprocess.run("firebase login", shell=True)
    except:
        print("⚠️ Firebase login check failed, continuing...")
    
    # Use the Firebase project
    try:
        print(f"🔗 Connecting to Firebase project: {project_id}")
        result = subprocess.run(f"firebase use {project_id}", shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ Connected to project: {project_id}")
        else:
            print("❌ Could not connect to project. Please make sure:")
            print(f"   1. Project '{project_id}' exists in Firebase Console")
            print(f"   2. You have access to the project")
            print(f"   3. Run: firebase use --add")
            return False
    except:
        print("⚠️ Could not set Firebase project, continuing...")
    
    return True

if __name__ == "__main__":
    setup_firebase()