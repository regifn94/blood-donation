"""
Database Configuration and Connection
"""

# modul yang diperlukan untuk koneksi
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
import os
from dotenv import load_dotenv # untuk membaca file .env agar konfigurasi tidak di tulis 

# Load environment variables
load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:@localhost:3306/donor_darah_db"
)

# Create SQLAlchemy engine untuk koneksi ke databse
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging (akan menampilakn semua query di terminal)
    pool_pre_ping=True,  # Enable connection health checks (agar tidak error saat idle)
    pool_recycle=3600,  # Recycle connections after 1 hour untuk mencegah timeout
)

# Create session factory untuk mengelola sesi database
# session = objek yang digunkan untuk melakukan query (SELECT, DLL)
SessionLocal = sessionmaker(
    autocommit=False, # transaksi tidak otomatis disimpan ke DB
    autoflush=False, # menyimpan data sementara sebelum commit
    bind=engine # menghubungkan session ke engine di atas
)

# TABLE MANAGEMENT FUNCTIONS
def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")

def drop_tables():
    """Drop all database tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)
    print("⚠️  All tables dropped!")

# DATABASE DEPENDENCY FOR FASTAPI
def get_db():
    """
    Dependency for getting database session
    Usage in FastAPI endpoints: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db # gunakan session di dalam route
    finally:
        db.close() # tutup koneksi setelah selesai agar tidak bocor

def init_db():
    """Initialize database - create tables if they don't exist"""
    try:
        create_tables() # jalankan fungsi create tables
        return True
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return False