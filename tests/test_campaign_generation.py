# test_campaign_generation.py
import asyncio
import logging
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.campaign_generation.campaign_orchestrator import CampaignOrchestrator

async def test_campaign_generation():
    """Test the complete campaign generation system"""

    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Test prompt
    test_prompt = "A dark fantasy campaign about political intrigue in a city where different guilds fight for control while an ancient evil awakens beneath the streets"

    orchestrator = CampaignOrchestrator()

    print("="*60)
    print("TESTING PROFESSIONAL CAMPAIGN GENERATION SYSTEM")
    print("="*60)
    print(f"Prompt: {test_prompt}")
    print("="*60)

    try:
        # Progress callback
        async def progress_callback(message: str, current_stage: int, total_stages: int):
            print(f"[{current_stage}/{total_stages}] {message}")

        # Stage callback
        async def stage_callback(stage_name: str, stage_results: dict):
            print(f"✓ Completed: {stage_name}")

            # Show some results
            if "outline" in stage_results:
                outline = stage_results["outline"]
                print(f"  → Campaign Title: {outline.get('title', 'Unknown')}")
                print(f"  → Estimated Sessions: {outline.get('estimated_sessions', 'Unknown')}")
                print(f"  → NPCs: {len(outline.get('key_npcs', []))}")
                print(f"  → Locations: {len(outline.get('key_locations', []))}")

            if "detailed_content" in stage_results:
                content = stage_results["detailed_content"]
                lines = len(content.split('\n')) if content else 0
                words = len(content.split()) if content else 0
                print(f"  → Generated Content: {lines} lines, {words} words")

        # Run generation
        result = await orchestrator.generate_campaign(
            test_prompt,
            progress_callback=progress_callback,
            stage_callback=stage_callback
        )

        print("\n" + "="*60)
        print("GENERATION COMPLETE!")
        print("="*60)

        metadata = result.get("metadata", {})
        print(f"Title: {result.get('title', 'Unknown')}")
        print(f"Description: {result.get('description', 'No description')}")
        print(f"Content Length: {metadata.get('line_count', 0)} lines")
        print(f"Word Count: {metadata.get('word_count', 0)} words")
        print(f"Generation Time: {metadata.get('generation_time', 0):.1f} seconds")

        # Save the campaign
        saved_path = await orchestrator.save_campaign(result)
        print(f"Saved to: {saved_path}")

        print(f"\nContent Preview (first 500 chars):")
        content = result.get("content", "")
        print(content[:500] + "..." if len(content) > 500 else content)

        print("\n" + "="*60)
        print("SUCCESS: Professional campaign generated!")
        print(f"Compare with WotC campaigns: {metadata.get('line_count', 0)} lines vs 7,341 lines (Baldur's Gate)")
        quality_ratio = (metadata.get('line_count', 0) / 7341) * 100 if metadata.get('line_count', 0) else 0
        print(f"Quality ratio: {quality_ratio:.1f}% of professional length")
        print("="*60)

    except Exception as e:
        print(f"\nERROR: Campaign generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    success = asyncio.run(test_campaign_generation())
    if not success:
        sys.exit(1)
    print("\nTest completed successfully!")