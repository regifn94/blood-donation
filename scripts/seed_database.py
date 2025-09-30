# TODO: Copy code from artifact 
"""
Database Seeding Script
Populate database with sample data for testing and development
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal, create_tables
from app.models import (
    User, DonorHistory, BloodStock, BloodRequest,
    UserRole, BloodType, StockStatus, RequestStatus, DonorStatus
)
from app.auth import get_password_hash

def seed_database():
    """Main function to seed the database"""
    
    print("=" * 60)
    print("🌱 SEEDING DATABASE")
    print("=" * 60)
    
    # Create tables first
    print("\n📋 Creating database tables...")
    create_tables()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Check if data already exists
        existing_users = db.query(User).count()
        if existing_users > 0:
            print("\n⚠️  WARNING: Database already contains data!")
            response = input("Do you want to continue? This will add more data. (y/n): ")
            if response.lower() != 'y':
                print("❌ Seeding cancelled.")
                return
        
        print("\n🔐 Creating users...")
        
        # 1. Create Admin User
        admin = User(
            nama="Admin System",
            email="admin@hospital.com",
            password=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            gol_darah=None,
            no_telepon="08123456789",
            alamat="RS Sentra Medika Minahasa Utara"
        )
        db.add(admin)
        print("   ✓ Admin created")
        
        # 2. Create Pendonor Users
        pendonors_data = [
            {
                "nama": "Cleymency Kaparang",
                "email": "cleymency@email.com",
                "gol_darah": BloodType.O_MINUS,
                "no_telepon": "08111111111",
                "alamat": "Manado"
            },
            {
                "nama": "Briana Tumundo",
                "email": "briana@email.com",
                "gol_darah": BloodType.A_PLUS,
                "no_telepon": "08111111112",
                "alamat": "Manado"
            },
            {
                "nama": "Queenzhy Posumah",
                "email": "queenzhy@email.com",
                "gol_darah": BloodType.B_PLUS,
                "no_telepon": "08111111113",
                "alamat": "Bitung"
            },
            {
                "nama": "Joshua Mandagi",
                "email": "joshua@email.com",
                "gol_darah": BloodType.AB_PLUS,
                "no_telepon": "08111111114",
                "alamat": "Tomohon"
            },
            {
                "nama": "Angela Lengkong",
                "email": "angela@email.com",
                "gol_darah": BloodType.A_MINUS,
                "no_telepon": "08111111115",
                "alamat": "Manado"
            }
        ]
        
        pendonors = []
        for data in pendonors_data:
            pendonor = User(
                nama=data["nama"],
                email=data["email"],
                password=get_password_hash("donor123"),
                role=UserRole.PENDONOR,
                gol_darah=data["gol_darah"],
                no_telepon=data["no_telepon"],
                alamat=data["alamat"]
            )
            db.add(pendonor)
            pendonors.append(pendonor)
        print(f"   ✓ {len(pendonors)} Pendonors created")
        
        # 3. Create Pemohon Users
        pemohons_data = [
            {
                "nama": "John Doe",
                "email": "john@email.com",
                "no_telepon": "08111111120",
                "alamat": "Tomohon"
            },
            {
                "nama": "Maria Tan",
                "email": "maria@email.com",
                "no_telepon": "08111111121",
                "alamat": "Manado"
            }
        ]
        
        pemohons = []
        for data in pemohons_data:
            pemohon = User(
                nama=data["nama"],
                email=data["email"],
                password=get_password_hash("pemohon123"),
                role=UserRole.PEMOHON,
                gol_darah=None,
                no_telepon=data["no_telepon"],
                alamat=data["alamat"]
            )
            db.add(pemohon)
            pemohons.append(pemohon)
        print(f"   ✓ {len(pemohons)} Pemohons created")
        
        # Commit users to get their IDs
        db.commit()
        
        # 4. Initialize Blood Stocks
        print("\n🩸 Initializing blood stocks...")
        blood_stocks_data = [
            (BloodType.A_PLUS, 8, StockStatus.KRITIS),
            (BloodType.A_MINUS, 5, StockStatus.KRITIS),
            (BloodType.B_PLUS, 25, StockStatus.AMAN),
            (BloodType.B_MINUS, 12, StockStatus.MENIPIS),
            (BloodType.AB_PLUS, 22, StockStatus.AMAN),
            (BloodType.AB_MINUS, 8, StockStatus.KRITIS),
            (BloodType.O_PLUS, 30, StockStatus.AMAN),
            (BloodType.O_MINUS, 10, StockStatus.MENIPIS),
        ]
        
        for blood_type, jumlah, status in blood_stocks_data:
            stock = BloodStock(
                gol_darah=blood_type,
                jumlah_kantong=jumlah,
                status=status
            )
            db.add(stock)
        print(f"   ✓ {len(blood_stocks_data)} Blood types initialized")
        
        # 5. Create Donor Histories
        print("\n📝 Creating donor histories...")
        donor_histories_data = [
            # Cleymency - 7 donations
            (pendonors[0].id, datetime.now() - timedelta(days=64)),
            (pendonors[0].id, datetime.now() - timedelta(days=154)),
            (pendonors[0].id, datetime.now() - timedelta(days=244)),
            (pendonors[0].id, datetime.now() - timedelta(days=334)),
            (pendonors[0].id, datetime.now() - timedelta(days=424)),
            (pendonors[0].id, datetime.now() - timedelta(days=514)),
            (pendonors[0].id, datetime.now() - timedelta(days=604)),
            
            # Briana - 3 donations
            (pendonors[1].id, datetime.now() - timedelta(days=94)),
            (pendonors[1].id, datetime.now() - timedelta(days=184)),
            (pendonors[1].id, datetime.now() - timedelta(days=274)),
            
            # Queenzhy - 5 donations
            (pendonors[2].id, datetime.now() - timedelta(days=208)),
            (pendonors[2].id, datetime.now() - timedelta(days=298)),
            (pendonors[2].id, datetime.now() - timedelta(days=388)),
            (pendonors[2].id, datetime.now() - timedelta(days=478)),
            (pendonors[2].id, datetime.now() - timedelta(days=568)),
        ]
        
        for pendonor_id, tanggal in donor_histories_data:
            days_since = (datetime.now() - tanggal).days
            status = DonorStatus.SIAP_DONOR if days_since >= 90 else DonorStatus.MASA_TUNGGU
            
            history = DonorHistory(
                pendonor_id=pendonor_id,
                tanggal_donor=tanggal,
                lokasi="RS Sentra Medika Minahasa Utara",
                status=status,
                catatan="Donor rutin"
            )
            db.add(history)
        print(f"   ✓ {len(donor_histories_data)} Donation records created")
        
        # 6. Create Blood Requests
        print("\n🏥 Creating blood requests...")
        blood_requests_data = [
            {
                "pemohon_id": pemohons[0].id,
                "nama_pasien": "Maria Santoso",
                "gol_darah": BloodType.A_PLUS,
                "jumlah_kantong": 2,
                "keperluan": "Operasi caesar darurat",
                "tanggal": datetime.now(),
                "status": RequestStatus.PENDING,
                "catatan": None
            },
            {
                "pemohon_id": pemohons[0].id,
                "nama_pasien": "Budi Wijaya",
                "gol_darah": BloodType.O_MINUS,
                "jumlah_kantong": 3,
                "keperluan": "Kecelakaan lalu lintas, perdarahan berat",
                "tanggal": datetime.now() - timedelta(days=2),
                "status": RequestStatus.DISETUJUI,
                "catatan": "Darah tersedia dan sudah disiapkan"
            },
            {
                "pemohon_id": pemohons[1].id,
                "nama_pasien": "Siti Aminah",
                "gol_darah": BloodType.B_PLUS,
                "jumlah_kantong": 1,
                "keperluan": "Transfusi rutin untuk anemia",
                "tanggal": datetime.now() - timedelta(days=5),
                "status": RequestStatus.SELESAI,
                "catatan": "Transfusi berhasil dilakukan"
            },
            {
                "pemohon_id": pemohons[1].id,
                "nama_pasien": "Ahmad Rizki",
                "gol_darah": BloodType.AB_MINUS,
                "jumlah_kantong": 2,
                "keperluan": "Persiapan operasi jantung",
                "tanggal": datetime.now() - timedelta(days=7),
                "status": RequestStatus.DITOLAK,
                "catatan": "Stok tidak mencukupi, mohon cari alternatif RS lain"
            }
        ]
        
        for data in blood_requests_data:
            request = BloodRequest(
                pemohon_id=data["pemohon_id"],
                nama_pasien=data["nama_pasien"],
                gol_darah=data["gol_darah"],
                jumlah_kantong=data["jumlah_kantong"],
                keperluan=data["keperluan"],
                tanggal_request=data["tanggal"],
                status=data["status"],
                catatan_admin=data["catatan"]
            )
            db.add(request)
        print(f"   ✓ {len(blood_requests_data)} Blood requests created")
        
        # Commit all changes
        db.commit()
        
        print("\n" + "=" * 60)
        print("✅ DATABASE SEEDED SUCCESSFULLY!")
        print("=" * 60)
        
        print("\n📋 SAMPLE ACCOUNTS:")
        print("\n👨‍💼 ADMIN:")
        print("   Email    : admin@hospital.com")
        print("   Password : admin123")
        
        print("\n🩸 PENDONORS:")
        print("   Email    : cleymency@email.com")
        print("   Password : donor123")
        print("   Gol Darah: O-")
        print()
        print("   Email    : briana@email.com")
        print("   Password : donor123")
        print("   Gol Darah: A+")
        print()
        print("   Email    : queenzhy@email.com")
        print("   Password : donor123")
        print("   Gol Darah: B+")
        
        print("\n🏥 PEMOHONS:")
        print("   Email    : john@email.com")
        print("   Password : pemohon123")
        print()
        print("   Email    : maria@email.com")
        print("   Password : pemohon123")
        
        print("\n" + "=" * 60)
        print("🚀 You can now start the server and login!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()