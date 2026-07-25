# start_web_system.py
import asyncio
import logging
import subprocess
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command, cwd=None, shell=True):
    """Run a command and return the process"""
    try:
        logger.info(f"Starting: {command}")
        process = subprocess.Popen(
            command,
            shell=shell,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return process
    except Exception as e:
        logger.error(f"Failed to start {command}: {e}")
        return None

async def start_backend():
    """Start the FastAPI backend (serves ASCII terminal UI + API)."""
    logger.info("Starting FastAPI backend...")

    try:
        subprocess.run([sys.executable, "-m", "uvicorn", "--help"],
                      capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("uvicorn not found. Installing web requirements...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "web/requirements.txt"],
                      check=True)

    backend_process = run_command([
        sys.executable, "-m", "uvicorn",
        "web.main:app",
        "--host", "0.0.0.0",
        "--port", "8080",
        "--reload"
    ])

    if backend_process:
        logger.info("FastAPI backend started on http://localhost:8080")
        return backend_process
    else:
        logger.error("Failed to start backend")
        return None

async def check_health():
    """Check if the backend is healthy"""
    import aiohttp

    for attempt in range(30):  # Try for 30 seconds
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8080/api/status") as response:
                    if response.status == 200:
                        logger.info("Backend health check passed")
                        return True
        except Exception:
            pass

        logger.info(f"Health check attempt {attempt + 1}/30...")
        await asyncio.sleep(1)

    logger.error("Backend health check failed")
    return False

async def main():
    """Main startup function"""
    logger.info("Starting D&D AI DM Web System...")

    backend_process = await start_backend()
    if not backend_process:
        logger.error("Failed to start backend. Exiting.")
        return

    logger.info("Waiting for backend to be ready...")
    await asyncio.sleep(3)

    if not await check_health():
        logger.error("Backend is not responding. Please check the logs.")
        backend_process.terminate()
        return

    logger.info("=" * 60)
    logger.info("D&D AI DM Web System Started Successfully!")
    logger.info("ASCII Terminal UI: http://localhost:8080/")
    logger.info("Backend API:       http://localhost:8080/api/status")
    logger.info("Legacy React UI:   web/frontend_legacy (manual npm start; deprecated)")
    logger.info("=" * 60)
    logger.info("Press Ctrl+C to stop")

    try:
        while True:
            if backend_process.poll() is not None:
                logger.error("Backend process died unexpectedly")
                break
            await asyncio.sleep(5)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if backend_process:
            backend_process.terminate()
            logger.info("Backend stopped")
        logger.info("All services stopped successfully")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Startup interrupted by user")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        sys.exit(1)
