"""
Test script for Local Web Fetch tool.
Run this to verify the local fetch functionality.

Usage:
    # Make sure you're in the deer-flow backend virtual environment
    cd deer-flow/backend
    # If using uv:
    uv run python deerflow/community/local_fetch/test_local_fetch.py
    # Or if dependencies are already installed:
    python deerflow/community/local_fetch/test_local_fetch.py
"""

import asyncio
import sys
import os

# Add the harness directory (deerflow package root) to path
# Current file: deer-flow/backend/packages/harness/deerflow/community/local_fetch/test_local_fetch.py
# Need to go up 3 levels: local_fetch -> community -> deerflow -> harness
harness_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, harness_dir)

print(f"Added to path: {harness_dir}")
print(f"Looking for deerflow at: {os.path.join(harness_dir, 'deerflow')}")

# Check if deerflow package exists
deeflow_init = os.path.join(harness_dir, "deerflow", "__init__.py")
if not os.path.exists(deeflow_init):
    print(f"\n❌ Error: deerflow package not found at {os.path.join(harness_dir, 'deerflow')}")
    print("Please run this script from the deer-flow project directory.")
    sys.exit(1)

try:
    from deerflow.community.local_fetch.tools import web_fetch_tool
    print("✅ Successfully imported web_fetch_tool\n")
except ImportError as e:
    print(f"\n❌ Import Error: {e}")
    print("\nPossible solutions:")
    print("1. Install dependencies: cd deer-flow/backend && uv pip install -e packages/harness")
    print("2. Or use: uv run python deerflow/community/local_fetch/test_local_fetch.py")
    print("3. Make sure readabilipy is installed (requires Node.js)")
    sys.exit(1)


async def test_local_fetch():
    """Test the local web fetch with various URLs."""
    
    test_urls = [
        # "https://en.wikipedia.org/wiki/Python_(programming_language)",  # Skip - may timeout in some networks
        "https://httpbin.org/html",
        "https://example.com",
        "https://www.baidu.com",  # Test Chinese website
    ]
    
    print("=" * 60)
    print("Testing Local Web Fetch Tool")
    print("=" * 60)
    
    for url in test_urls:
        print(f"\n{'=' * 60}")
        print(f"Testing: {url}")
        print("=" * 60)
        
        try:
            # web_fetch_tool is a StructuredTool, use .ainvoke() to call it
            result = await web_fetch_tool.ainvoke({"url": url})
            
            if result.startswith("Error:"):
                print(f"❌ Failed: {result}")
            else:
                print(f"✅ Success!")
                print(f"Content length: {len(result)} characters")
                print(f"\nPreview (first 500 chars):")
                print("-" * 60)
                print(result[:500])
                print("-" * 60)
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
        
        print()
    
    print("=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_local_fetch())
