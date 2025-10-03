@echo off
echo Initializing Spells for Existing Characters...
call llama_env_311\Scripts\activate.bat

echo.
echo This will add spells to existing spellcaster characters
echo that were created before the spell system was implemented.
echo.

python initialize_existing_characters.py

echo.
echo Character initialization completed. Press any key to exit...
pause