"""
Script to reset all user passwords to SHA256 hashing
Run this ONCE after switching password algorithm
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:@localhost/blood_donor_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Password context with SHA256 (no external dependencies needed)
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
    pbkdf2_sha256__default_rounds=200000
)

def reset_all_passwords():
    """Reset all user passwords to use SHA256"""
    db = SessionLocal()
    
    try:
        # Import models
        from app.models import User
        
        # Get all users
        users = db.query(User).all()
        
        print(f"Found {len(users)} users to reset")
        print("=" * 50)
        
        # Default passwords for reset
        default_passwords = {
            "admin": "admin123",
            "pendonor": "donor123",
            "pemohon": "pemohon123"
        }
        
        for user in users:
            # Determine default password based on role
            if user.role.value == "admin":
                new_password = default_passwords["admin"]
            elif user.role.value == "pendonor":
                new_password = default_passwords["pendonor"]
            else:
                new_password = default_passwords["pemohon"]
            
            # Hash with SHA256
            hashed = pwd_context.hash(new_password)
            user.password = hashed
            
            print(f"✅ Reset: {user.email} ({user.role.value}) -> password: {new_password}")
        
        db.commit()
        
        print("=" * 50)
        print("✅ All passwords reset successfully!")
        print("\nDEFAULT PASSWORDS:")
        print("  Admin    : admin123")
        print("  Pendonor : donor123")
        print("  Pemohon  : pemohon123")
        print("\n⚠️  IMPORTANT: Ask users to change their passwords!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

def create_test_users():
    """Create test users with SHA256 passwords"""
    db = SessionLocal()
    
    try:
        from app.models import User, UserRole, BloodType
        
        # Check if admin exists
        admin = db.query(User).filter(User.email == "admin@hospital.com").first()
        
        if not admin:
            # Create admin
            admin = User(
                nama="Administrator",
                email="admin@hospital.com",
                password=pwd_context.hash("admin123"),
                role=UserRole.ADMIN,
                no_telepon="081234567890"
            )
            db.add(admin)
            print("✅ Created admin user: admin@hospital.com / admin123")
        else:
            print("ℹ️  Admin already exists, resetting password...")
            admin.password = pwd_context.hash("admin123")
        
        # Create test pendonor
        pendonor = db.query(User).filter(User.email == "donor@test.com").first()
        if not pendonor:
            pendonor = User(
                nama="Test Donor",
                email="donor@test.com",
                password=pwd_context.hash("donor123"),
                role=UserRole.PENDONOR,
                gol_darah=BloodType.O,
                no_telepon="081234567891",
                alamat="Test Address"
            )
            db.add(pendonor)
            print("✅ Created donor user: donor@test.com / donor123")
        else:
            print("ℹ️  Donor already exists, resetting password...")
            pendonor.password = pwd_context.hash("donor123")
        
        db.commit()
        print("\n✅ Test users ready!")
        print("\nLOGIN CREDENTIALS:")
        print("  Admin: admin@hospital.com / admin123")
        print("  Donor: donor@test.com / donor123")
        
    except Exception as e:
        print(f"❌ Error creating test users: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 50)
    print("Password Reset Tool (SHA256)")
    print("=" * 50)
    print("\nChoose an option:")
    print("1. Reset all existing user passwords")
    print("2. Create/Reset test users only")
    print("3. Both")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    if choice == "1":
        reset_all_passwords()
    elif choice == "2":
        create_test_users()
    elif choice == "3":
        reset_all_passwords()
        print("\n")
        create_test_users()
    else:
        print("Invalid choice!")