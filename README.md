# Blood Donor Management System - Backend

## Setup Cepat
1. Copy code Python dari artifacts ke 6 file
2. python -m venv venv
3. venv\Scripts\activate
4. pip install -r requirements.txt
5. Buat database MySQL: donor_darah_db
6. python scripts\seed_database.py
7. python run.py

## Default Accounts
- Admin: admin@hospital.com / admin123
- Pendonor: cleymency@email.com / donor123

uvicorn app.main:app --reload
python .\run.py
pip install -r requirements.txt