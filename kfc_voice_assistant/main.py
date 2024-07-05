import sys
import time, asyncio
import threading, uvicorn
from dotenv import load_dotenv
from app import app as frontend_app
from backend import main as backend_main


print("Starting up")
load_dotenv()

def run_fastapi():
    print("Starting fastapi app...")
    uvicorn.run(frontend_app, host="localhost", port=8000)

def run_backend():
    print("Starting backend...")
    backend_main()

async def main():
    # Start FastAPI in a separate thread
    fastapi_thread = threading.Thread(target=run_fastapi)
    fastapi_thread.start()

    # Wait for 10 seconds
    print("Waiting for 10 seconds before starting the backend...")
    await asyncio.sleep(10)

    # Run the backend
    backend_thread = threading.Thread(target=run_backend)
    backend_thread.start()

    fastapi_thread.join()
    backend_thread.join()

if __name__ == "__main__":
    asyncio.run(main())