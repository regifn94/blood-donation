@echo off
echo ================================================
echo Blood Donor System - Password Fix Script
echo ================================================
echo.

echo Step 1: Uninstalling ALL password libraries...
pip uninstall -y bcrypt passlib argon2-cffi

echo.
echo Step 2: Installing ONLY Argon2 (no bcrypt)...
pip install argon2-cffi==23.1.0
pip install passlib==1.7.4

echo.
echo Step 3: Testing installation...
python -c "from passlib.context import CryptContext; pwd = CryptContext(schemes=['argon2']); print('✅ Argon2 working correctly!')"

echo.
echo ================================================
echo Fix Complete!
echo ================================================
echo.
echo IMPORTANT: You need to reset all user passwords!
echo Run the reset_passwords.py script to fix existing users.
echo.
pause