# start_system.py — LEGACY Discord bot entrypoint (deprecated)
"""
The Discord bot is preserved but not the primary play path (3s interaction limits).

Use the web/ASCII system instead:

    python start_web_system.py

Then open http://localhost:8080/
"""
import sys

print("ERROR: start_system.py launches the legacy Discord bot.")
print("Use the ASCII web system instead:")
print()
print("  python start_web_system.py")
print()
print("Then open http://localhost:8080/")
print()
print("(Discord entrypoint is deprecated; bot.py still imports removed helpers.)")
sys.exit(1)
