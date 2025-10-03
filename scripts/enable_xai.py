# enable_xai.py
"""
Simple script to ensure XAI integration is properly enabled in the campaign generation system.
Run this to verify your XAI API key is configured correctly.
"""

import os
import sys
from pathlib import Path

def check_xai_config():
    """Check if XAI is properly configured"""

    print("="*60)
    print("XAI CONFIGURATION CHECKER")
    print("="*60)

    # Check for .env file
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        print("   Create .env file with: XAI_API_KEY=your_api_key_here")
        return False

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    xai_key = os.getenv("XAI_API_KEY")

    if not xai_key:
        print("❌ XAI_API_KEY not found in .env file")
        print("   Add to .env: XAI_API_KEY=your_api_key_here")
        return False

    if len(xai_key) < 10:
        print("❌ XAI_API_KEY appears to be invalid (too short)")
        return False

    print(f"✅ XAI_API_KEY found: {xai_key[:10]}...{xai_key[-4:]}")

    # Test XAI connection
    try:
        import openai
        client = openai.OpenAI(
            api_key=xai_key,
            base_url="https://api.x.ai/v1"
        )

        # Simple test call
        response = client.chat.completions.create(
            model="grok-3-mini",
            messages=[{"role": "user", "content": "Hello, this is a test. Respond with just 'OK'."}],
            max_tokens=10
        )

        result = response.choices[0].message.content.strip()
        print(f"✅ XAI connection test successful: '{result}'")

    except Exception as e:
        print(f"❌ XAI connection test failed: {e}")
        return False

    # Check if campaign generation system can import
    try:
        sys.path.append("src")
        from src.campaign_generation.stage_managers import XAIStageManager
        print("✅ Campaign generation system imports successfully")

        # Test stage manager initialization
        stage_manager = XAIStageManager()
        if stage_manager.xai_client:
            print("✅ XAI stage manager initialized successfully")
        else:
            print("❌ XAI stage manager failed to initialize")
            return False

    except Exception as e:
        print(f"❌ Campaign generation system import failed: {e}")
        return False

    print("\n" + "="*60)
    print("🎉 XAI CONFIGURATION COMPLETE!")
    print("✅ Your system is ready for professional campaign generation")
    print("✅ XAI will handle stages 1-2 (FREE with your prepaid tokens)")
    print("✅ Gemini will handle stages 3-4 (~$0.02 per campaign)")
    print("✅ Local LLM will handle stage 5 (FREE)")
    print("="*60)

    return True

if __name__ == "__main__":
    success = check_xai_config()
    if not success:
        print("\n❌ Configuration incomplete. Please fix the issues above.")
        sys.exit(1)
    else:
        print("\n🚀 Ready to generate professional 7k-line campaigns!")
        print("Run: python test_campaign_generation.py")