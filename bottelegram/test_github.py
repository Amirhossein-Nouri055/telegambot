#!/usr/bin/env python3
"""
Test script for GitHub integration
Run this to test if your GitHub token and repository are configured correctly
"""

import asyncio
import os
import json
from bot import github_get_file, github_save_file, GITHUB_TOKEN, GITHUB_REPO

async def test_github_integration():
    print("🔍 Testing GitHub Integration...")
    print(f"Repository: {GITHUB_REPO}")
    print(f"Token configured: {'Yes' if GITHUB_TOKEN else 'No'}")
    
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN not configured!")
        print("Please set GITHUB_TOKEN environment variable")
        return False
    
    if GITHUB_REPO == 'your-username/your-repo':
        print("❌ GITHUB_REPO not configured!")
        print("Please set GITHUB_REPO environment variable to your actual repository")
        return False
    
    # Test reading from GitHub
    print("\n📖 Testing read from GitHub...")
    data = await github_get_file()
    if data is not None:
        print(f"✅ Successfully read data from GitHub: {len(data)} records")
        print(f"Sample data: {json.dumps(data, indent=2)[:200]}...")
    else:
        print("❌ Failed to read from GitHub")
        return False
    
    # Test writing to GitHub
    print("\n📝 Testing write to GitHub...")
    test_data = {
        "test": {
            "message": "This is a test record",
            "timestamp": "2024-01-01T00:00:00",
            "test": True
        }
    }
    
    success = await github_save_file(test_data)
    if success:
        print("✅ Successfully wrote test data to GitHub")
    else:
        print("❌ Failed to write to GitHub")
        return False
    
    # Verify the write worked
    print("\n🔄 Verifying write operation...")
    verify_data = await github_get_file()
    if verify_data and "test" in verify_data:
        print("✅ Write verification successful")
    else:
        print("❌ Write verification failed")
        return False
    
    print("\n🎉 GitHub integration test completed successfully!")
    return True

if __name__ == "__main__":
    asyncio.run(test_github_integration())
