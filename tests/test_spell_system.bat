@echo off
echo Activating llama_env_311 Python environment...
call llama_env_311\Scripts\activate.bat

echo.
echo Testing Enhanced Spell System
echo ========================================

echo Running basic spell system test...
python test_spells.py

echo.
echo Test completed. Press any key to exit...
pause