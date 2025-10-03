# test_session_summaries.py
"""
test script for session summaries and api endpoints
tests database operations, api responses, and summary generation
"""

import sys
import os
import asyncio
import aiohttp
import json

# add project root to path so we can import src
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

BASE_URL = "http://localhost:8080"

async def test_api_status():
    """test if the api server is running"""
    print("=" * 50)
    print("testing api server status")
    print("=" * 50)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/api/status") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"SUCCESS: api server is running")
                    print(f"   campaign loaded: {data.get('campaign_loaded', 'None')}")
                    print(f"   campaign id: {data.get('campaign_id', 'None')}")
                    return data
                else:
                    print(f"ERROR: api returned status {response.status}")
                    return None

    except Exception as e:
        print(f"ERROR: failed to connect to api server: {e}")
        print("make sure to run: python start_web_system.py")
        return None

async def test_current_campaign_summaries():
    """test getting summaries for current campaign"""
    print("\n" + "=" * 50)
    print("testing current campaign summaries")
    print("=" * 50)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/api/current_campaign/summaries") as response:
                print(f"response status: {response.status}")

                if response.status == 200:
                    data = await response.json()
                    print(f"SUCCESS: got summaries for campaign")
                    print(f"   campaign name: {data.get('campaign_name')}")
                    print(f"   campaign id: {data.get('campaign_id')}")
                    print(f"   summary count: {data.get('count', 0)}")

                    summaries = data.get('summaries', [])
                    for i, summary in enumerate(summaries):
                        print(f"\n   summary {i+1}:")
                        print(f"      id: {summary.get('id')}")
                        print(f"      created: {summary.get('created_at')}")
                        summary_text = summary.get('summary', '')
                        preview = summary_text[:100] + "..." if len(summary_text) > 100 else summary_text
                        print(f"      text: {preview}")

                    return data

                elif response.status == 400:
                    error_data = await response.json()
                    print(f"WARNING: {error_data.get('detail', 'no campaign loaded')}")
                    return None

                else:
                    print(f"ERROR: api returned status {response.status}")
                    error_text = await response.text()
                    print(f"   error: {error_text}")
                    return None

    except Exception as e:
        print(f"ERROR: failed to get summaries: {e}")
        return None

async def test_database_summaries():
    """test getting summaries directly from database"""
    print("\n" + "=" * 50)
    print("testing database summary access")
    print("=" * 50)

    try:
        from src.database import get_db_session, get_session_summaries, get_campaign_by_name
        from src.campaign_state_manager import campaign_state_manager

        if not campaign_state_manager.current_state:
            print("WARNING: no campaign loaded in memory, trying to load from api status...")
            # get campaign name from api status if available
            status_data = await test_api_status()
            if status_data and status_data.get('campaign_loaded'):
                campaign_name = status_data['campaign_loaded']
                print(f"loading campaign: {campaign_name}")
                await campaign_state_manager.load_campaign(campaign_name)
            else:
                print("ERROR: no campaign available to load")
                return None

        campaign_name = campaign_state_manager.current_state.campaign_name
        print(f"current campaign: {campaign_name}")

        async for db in get_db_session():
            # get campaign from db
            campaign = await get_campaign_by_name(db, campaign_name)
            if not campaign:
                print(f"ERROR: campaign '{campaign_name}' not found in database")
                return None

            print(f"campaign id in db: {campaign.id}")

            # get summaries
            summaries = await get_session_summaries(db, campaign.id)
            print(f"found {len(summaries)} summaries in database")

            for i, summary in enumerate(summaries):
                print(f"\n   database summary {i+1}:")
                print(f"      id: {summary.id}")
                print(f"      campaign_id: {summary.campaign_id}")
                print(f"      created_at: {summary.created_at}")
                summary_text = summary.summary or ''
                preview = summary_text[:100] + "..." if len(summary_text) > 100 else summary_text
                print(f"      text: {preview}")

            return summaries

    except Exception as e:
        print(f"ERROR: database test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_create_test_summary():
    """create a test summary to ensure the system works"""
    print("\n" + "=" * 50)
    print("testing summary creation")
    print("=" * 50)

    try:
        from src.database import get_db_session, add_session_summary, get_campaign_by_name
        from src.campaign_state_manager import campaign_state_manager

        if not campaign_state_manager.current_state:
            print("WARNING: no campaign loaded - trying to load from api status...")
            status_data = await test_api_status()
            if status_data and status_data.get('campaign_loaded'):
                campaign_name = status_data['campaign_loaded']
                print(f"loading campaign: {campaign_name}")
                await campaign_state_manager.load_campaign(campaign_name)
            else:
                print("ERROR: no campaign available to load")
                return None

        campaign_name = campaign_state_manager.current_state.campaign_name
        print(f"creating test summary for campaign: {campaign_name}")

        async for db in get_db_session():
            # get campaign
            campaign = await get_campaign_by_name(db, campaign_name)
            if not campaign:
                print(f"ERROR: campaign not found in database")
                return None

            # create test summary
            test_summary_text = """
TEST SUMMARY: The party explored a mysterious cave and encountered a goblin guard.
After a brief combat encounter, they successfully defeated the goblin and discovered
a hidden treasure chest containing 50 gold pieces and a magical potion. The session
ended with the party deciding to rest for the night before continuing deeper into
the cave system.
            """.strip()

            print("adding test summary to database...")
            await add_session_summary(db, campaign.id, test_summary_text)
            print("SUCCESS: test summary created")

            return True

    except Exception as e:
        print(f"ERROR: failed to create test summary: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_end_session_api():
    """test the end session endpoint (simulated)"""
    print("\n" + "=" * 50)
    print("testing end session api")
    print("=" * 50)

    try:
        # we'll test with a fake session id since we don't have active sessions
        test_session_id = "test_session_123"

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BASE_URL}/api/sessions/end/{test_session_id}") as response:
                print(f"end session response status: {response.status}")

                if response.status == 200:
                    data = await response.json()
                    print(f"SUCCESS: session ended")
                    print(f"   message: {data.get('message')}")
                    summary = data.get('summary', '')
                    if summary:
                        preview = summary[:100] + "..." if len(summary) > 100 else summary
                        print(f"   summary: {preview}")
                    return data

                elif response.status == 404:
                    print("WARNING: session not found (expected for test session)")
                    return None

                else:
                    error_text = await response.text()
                    print(f"ERROR: api returned status {response.status}")
                    print(f"   error: {error_text}")
                    return None

    except Exception as e:
        print(f"ERROR: end session test failed: {e}")
        return None

async def test_summary_content_quality():
    """test the quality of generated summaries"""
    print("\n" + "=" * 50)
    print("testing summary content quality")
    print("=" * 50)

    try:
        # get existing summaries and analyze them
        summaries_data = await test_current_campaign_summaries()

        if not summaries_data or not summaries_data.get('summaries'):
            print("no summaries to analyze")
            return

        summaries = summaries_data['summaries']
        print(f"\nanalyzing {len(summaries)} summaries:")

        for i, summary in enumerate(summaries):
            text = summary.get('summary', '')

            print(f"\n   summary {i+1} analysis:")
            print(f"      length: {len(text)} characters")
            print(f"      has d&d keywords: {any(word in text.lower() for word in ['party', 'combat', 'dice', 'damage', 'spell', 'character', 'adventure'])}")
            print(f"      has narrative structure: {any(word in text.lower() for word in ['began', 'during', 'after', 'finally', 'concluded'])}")

            # show first few sentences
            sentences = text.split('. ')[:2]
            if sentences:
                preview = '. '.join(sentences) + '.' if len(sentences) > 1 else sentences[0]
                print(f"      preview: {preview}")

    except Exception as e:
        print(f"ERROR: summary analysis failed: {e}")

async def main():
    """run all summary tests"""
    print("session summary test suite")
    print("tests database storage, api endpoints, and content quality")

    # test api connectivity
    status_data = await test_api_status()
    if not status_data:
        print("\nERROR: cannot continue without api server")
        return

    # test database access
    await test_database_summaries()

    # test api endpoint
    await test_current_campaign_summaries()

    # create test summary if none exist
    await test_create_test_summary()

    # test after creation
    await test_current_campaign_summaries()

    # test end session api
    await test_end_session_api()

    # analyze summary quality
    await test_summary_content_quality()

    print("\n" + "=" * 50)
    print("summary test suite complete!")
    print("check http://localhost:8080/api/current_campaign/summaries for live data")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())