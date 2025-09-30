@echo off
chcp 65001 >nul
color 0E

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║   FIX IMPORT ERRORS - Blood Donor System                ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

echo [INFO] Memperbaiki import statements di semua file...
echo.

REM Pastikan kita di folder backend
if not exist "app\main.py" (
    echo [ERROR] File app\main.py tidak ditemukan!
    echo [ERROR] Pastikan Anda menjalankan script ini di folder backend
    echo.
    pause
    exit /b 1
)

echo [1/4] Memperbaiki app\main.py...
powershell -Command "(Get-Content 'app\main.py') -replace 'from app\.database import', 'from .database import' -replace 'from app\.models import', 'from .models import' -replace 'from app\.schemas import', 'from .schemas import' -replace 'from app\.auth import', 'from .auth import' | Set-Content 'app\main.py'"
echo      ✓ app\main.py diperbaiki

echo [2/4] Memperbaiki app\database.py...
powershell -Command "(Get-Content 'app\database.py') -replace 'from app\.models import', 'from .models import' | Set-Content 'app\database.py'"
echo      ✓ app\database.py diperbaiki

echo [3/4] Memperbaiki app\auth.py...
powershell -Command "(Get-Content 'app\auth.py') -replace 'from app\.database import', 'from .database import' -replace 'from app\.models import', 'from .models import' | Set-Content 'app\auth.py'"
echo      ✓ app\auth.py diperbaiki

echo [4/4] Memperbaiki app\schemas.py...
powershell -Command "(Get-Content 'app\schemas.py') -replace 'from app\.models import', 'from .models import' | Set-Content 'app\schemas.py'"
echo      ✓ app\schemas.py diperbaiki

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║               PERBAIKAN SELESAI! ✓                       ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo Semua import statement sudah diperbaiki.
echo.
echo Sekarang coba jalankan server lagi:
echo   python run.py
echo.
pause