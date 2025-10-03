@echo off
echo Activating llama_env_311 Python environment...
call llama_env_311\Scripts\activate.bat

echo.
echo Loading All D and D 5e Spells from API
echo ===================================
echo This will fetch all 319+ spells from the D and D 5e API
echo This may take 2-5 minutes depending on network speed
echo.

python load_spells.py

echo.
echo Spell loading completed. Press any key to exit...
pause