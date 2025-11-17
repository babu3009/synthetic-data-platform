import sys
import traceback
import asyncio

async def test_app():
    try:
        print("Importing app...")
        from app.main import app
        print(f"✓ App imported: {app.title}")
        
        print("\nTesting lifespan context...")
        async with app.router.lifespan_context(app):
            print("✓ Lifespan context entered successfully")
        print("✓ Lifespan context exited successfully")
        
        print("\n✅ All startup tests passed!")
        return 0
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(test_app())
    sys.exit(exit_code)
