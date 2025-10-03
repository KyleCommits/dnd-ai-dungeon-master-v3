@echo off
echo Testing Spell System Integration...
call llama_env_311\Scripts\activate.bat

echo.
echo Running integration test...
python test_integration.py

echo.
echo Integration test completed. Press any key to exit...
pause