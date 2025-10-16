@echo off
echo ================================================
echo Blood Donor Management System - Dependency Fix
echo ================================================
echo.

echo Step 1: Uninstalling conflicting packages...
pip uninstall -y bcrypt passlib

echo.
echo Step 2: Installing compatible versions...
pip install bcrypt==4.0.1
pip install passlib[bcrypt]==1.7.4

echo.
echo Step 3: Reinstalling all requirements...
pip install -r requirements.txt

echo.
echo ================================================
echo Setup Complete!
echo ================================================
echo.
echo Testing bcrypt installation...
python -c "from passlib.context import CryptContext; pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto'); print('✅ Bcrypt is working correctly!')"

echo.
echo You can now run the application with:
echo uvicorn app.main:app --reload
echo.
pause