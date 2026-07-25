# start_web_system.py
import asyncio
import logging
import socket
import subprocess
import sys
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get("DND_PORT", "8080"))


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


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def run_backend(python_exe: str) -> subprocess.Popen:
    """
    Start uvicorn without capturing stdout/stderr.
    Use --reload only when DND_UVICORN_RELOAD=1 (reload parent can confuse health checks).
    """
    cmd = [
        python_exe,
        "-m",
        "uvicorn",
        "web.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(PORT),
    ]
    if os.environ.get("DND_UVICORN_RELOAD", "").strip() in ("1", "true", "yes"):
        cmd.append("--reload")

    logger.info("Starting: %s", cmd)
    return subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        shell=False,
        stdout=None,
        stderr=None,
    )


async def start_backend():
    python_exe = resolve_python()
    logger.info("Using Python: %s", python_exe)
    if "llama_env_311" not in python_exe.replace("\\", "/"):
        logger.warning(
            "Not using llama_env_311. Activate the venv or rely on the auto-detect path."
        )

    if port_in_use(PORT):
        logger.error(
            "Port %s is already in use. Stop the other process first, e.g.:\n"
            "  netstat -ano | findstr :%s\n"
            "  taskkill /PID <pid> /F",
            PORT,
            PORT,
        )
        return None

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

    logger.info("Uvicorn process started (pid=%s) on http://localhost:%s", process.pid, PORT)
    return process


async def check_health(backend_process: subprocess.Popen) -> bool:
    """Probe /api/health (and fallbacks)."""
    import urllib.request
    import json

    urls = [
        f"http://127.0.0.1:{PORT}/api/health",
        f"http://127.0.0.1:{PORT}/docs",
        f"http://127.0.0.1:{PORT}/",
    ]

    last_err: Exception | str = "waiting for uvicorn"
    for attempt in range(90):
        if backend_process.poll() is not None:
            logger.error(
                "Backend process exited early with code %s. "
                "Scroll up for uvicorn/import errors in this terminal.",
                backend_process.returncode,
            )
            return False

        for url in urls:
            try:
                with urllib.request.urlopen(url, timeout=2) as resp:
                    if resp.status != 200:
                        continue
                    # Prefer /api/health body when that URL succeeded
                    if url.endswith("/api/health"):
                        body = resp.read().decode("utf-8", errors="ignore")
                        try:
                            data = json.loads(body)
                        except Exception:
                            data = {}
                        if data.get("ok") is True:
                            logger.info("Backend health check passed (%s)", url)
                            return True
                        logger.warning(
                            "Got HTTP 200 from %s but unexpected body: %s", url, body[:120]
                        )
                        continue
                    logger.info("Backend health check passed (%s)", url)
                    return True
            except Exception as e:
                last_err = e

        if attempt == 0 or attempt % 5 == 4:
            logger.info("Health check attempt %s/90... (%s)", attempt + 1, last_err)
        else:
            logger.info("Health check attempt %s/90...", attempt + 1)
        await asyncio.sleep(1)

    logger.error("Backend health check failed")
    return False


async def main():
    logger.info("Starting D&D AI DM Web System...")

    backend_process = await start_backend()
    if not backend_process:
        logger.error("Failed to start backend. Exiting.")
        return

    logger.info(
        "Waiting for backend to be ready (LLM load can take 1–3 minutes; keep this window open)..."
    )
    await asyncio.sleep(1)

    if not await check_health(backend_process):
        logger.error("Backend is not responding. See uvicorn output above.")
        if backend_process.poll() is None:
            backend_process.terminate()
        return

    logger.info("=" * 60)
    logger.info("D&D AI DM Web System Started Successfully!")
    logger.info("ASCII Terminal UI: http://localhost:%s/", PORT)
    logger.info("Health:            http://localhost:%s/api/health", PORT)
    logger.info("Status:            http://localhost:%s/api/status", PORT)
    logger.info("OpenAPI docs:      http://localhost:%s/docs", PORT)
    logger.info("=" * 60)
    logger.info("Press Ctrl+C to stop")

    try:
        while True:
            if backend_process.poll() is not None:
                logger.error(
                    "Backend process died unexpectedly (code=%s)", backend_process.returncode
                )
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
