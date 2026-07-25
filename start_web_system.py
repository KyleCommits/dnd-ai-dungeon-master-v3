# start_web_system.py
import asyncio
import logging
import subprocess
import sys
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent


def resolve_python() -> str:
    """Prefer llama_env_311 over whatever `python` is on PATH (often system 3.13)."""
    candidates = [
        ROOT / "llama_env_311" / "Scripts" / "python.exe",
        ROOT / "llama_env_311" / "bin" / "python",
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return sys.executable


def run_backend(python_exe: str) -> subprocess.Popen:
    """
    Start uvicorn without capturing stdout/stderr.
    Piping both streams can deadlock the child on Windows and hides crash logs.
    """
    cmd = [
        python_exe,
        "-m",
        "uvicorn",
        "web.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8080",
        "--reload",
    ]
    logger.info("Starting: %s", cmd)
    return subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        shell=False,
        # Inherit console so import errors / uvicorn logs are visible
        stdout=None,
        stderr=None,
    )


async def start_backend():
    """Start the FastAPI backend (serves ASCII terminal UI + API)."""
    python_exe = resolve_python()
    logger.info("Using Python: %s", python_exe)
    if "llama_env_311" not in python_exe.replace("\\", "/"):
        logger.warning(
            "Not using llama_env_311. Activate the venv or rely on the auto-detect path. "
            "System Python (e.g. 3.13) often cannot import project deps."
        )

    logger.info("Starting FastAPI backend...")
    try:
        subprocess.run(
            [python_exe, "-m", "uvicorn", "--help"],
            capture_output=True,
            check=True,
            cwd=str(ROOT),
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("uvicorn not found for %s. Installing web requirements...", python_exe)
        subprocess.run(
            [python_exe, "-m", "pip", "install", "-r", "web/requirements.txt"],
            check=True,
            cwd=str(ROOT),
        )

    try:
        process = run_backend(python_exe)
    except Exception as e:
        logger.error("Failed to start backend: %s", e)
        return None

    logger.info("Uvicorn process started (pid=%s) on http://localhost:8080", process.pid)
    return process


async def check_health(backend_process: subprocess.Popen) -> bool:
    """Check if the backend is healthy."""
    import aiohttp

    for attempt in range(45):
        if backend_process.poll() is not None:
            logger.error(
                "Backend process exited early with code %s. "
                "Scroll up for uvicorn/import errors in this terminal.",
                backend_process.returncode,
            )
            return False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://localhost:8080/api/status",
                    timeout=aiohttp.ClientTimeout(total=2),
                ) as response:
                    if response.status == 200:
                        logger.info("Backend health check passed")
                        return True
        except Exception:
            pass

        logger.info("Health check attempt %s/45...", attempt + 1)
        await asyncio.sleep(1)

    logger.error("Backend health check failed")
    return False


async def main():
    logger.info("Starting D&D AI DM Web System...")

    backend_process = await start_backend()
    if not backend_process:
        logger.error("Failed to start backend. Exiting.")
        return

    logger.info("Waiting for backend to be ready...")
    await asyncio.sleep(2)

    if not await check_health(backend_process):
        logger.error("Backend is not responding. See uvicorn output above.")
        if backend_process.poll() is None:
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
                logger.error("Backend process died unexpectedly (code=%s)", backend_process.returncode)
                break
            await asyncio.sleep(5)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if backend_process and backend_process.poll() is None:
            backend_process.terminate()
            try:
                backend_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                backend_process.kill()
            logger.info("Backend stopped")
        logger.info("All services stopped successfully")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Startup interrupted by user")
    except Exception as e:
        logger.error("Startup failed: %s", e)
        sys.exit(1)
