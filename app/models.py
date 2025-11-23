# TODO: Copy code from artifact 
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text # import tipe data kolom dari SQLALchemy
from sqlalchemy.ext.declarative import declarative_base # untuk membuat base class model
from sqlalchemy.orm import relationship #untuk membuat relasi antara tabel
from datetime import datetime # untuk mencatat waktu (timestamp)
import enum #untuk membuat enumerasi (pilihan tetap seperti role atau status)

# membaut base class untuk semua model SQLALchemy
Base = declarative_base()

# ENUMERSASI / PILIHAN TETAP
class UserRole(str, enum.Enum): #  untuk menentukan peran pengguna
    ADMIN = "admin"
    PENDONOR = "pendonor"
    PEMOHON = "pemohon"

class BloodType(str, enum.Enum):
    A_PLUS = "A+"
    A_MINUS = "A-"
    B_PLUS = "B+"
    B_MINUS = "B-"
    AB_PLUS = "AB+"
    AB_MINUS = "AB-"
    O_PLUS = "O+"
    O_MINUS = "O-"

class DonorStatus(str, enum.Enum):
    SIAP_DONOR = "Siap Donor"
    MASA_TUNGGU = "Masa Tunggu"

class StockStatus(str, enum.Enum):
    AMAN = "Aman"
    MENIPIS = "Menipis"
    KRITIS = "Kritis"

class RequestStatus(str, enum.Enum):
    PENDING = "Pending"
    DISETUJUI = "Disetujui"
    DITOLAK = "Ditolak"
    SELESAI = "Selesai"

class User(Base):
    __tablename__ = "users" 
    
    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    gol_darah = Column(Enum(BloodType), nullable=True)
    no_telepon = Column(String(20), nullable=True)
    alamat = Column(Text, nullable=True)
    tanggal_daftar = Column(DateTime, default=datetime.utcnow)
    gender = Column(String(10), nullable=True)
    
    # Relationships to others tables
    donor_histories = relationship("DonorHistory", back_populates="pendonor")
    blood_requests = relationship("BloodRequest", back_populates="pemohon")

# TABEL RIWAYAT DONOR
class DonorHistory(Base): # model untuk tabel
    __tablename__ = "donor_histories"
    
    id = Column(Integer, primary_key=True, index=True)
    pendonor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tanggal_donor = Column(DateTime, nullable=False)
    lokasi = Column(String(200), default="RS Sentra Medika Minahasa Utara")
    status = Column(Enum(DonorStatus), default=DonorStatus.MASA_TUNGGU)
    catatan = Column(Text, nullable=True)
    reminder_sent = Column(Integer, default=0)
    # Relationships to user table
    pendonor = relationship("User", back_populates="donor_histories")

class BloodStock(Base):
    __tablename__ = "blood_stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    gol_darah = Column(Enum(BloodType), unique=True, nullable=False)
    jumlah_kantong = Column(Integer, default=0)
    status = Column(Enum(StockStatus), nullable=False)
    terakhir_update = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def update_status(self): # method untuk memperbarui status stok darah
        """Update status berdasarkan threshold (<=5 = KRITIS)"""
        if self.jumlah_kantong <= 5:
            self.status = StockStatus.KRITIS  # AUTO ALERT! jika kurang dari 5
        elif self.jumlah_kantong <= 10:
            self.status = StockStatus.MENIPIS
        else:
            self.status = StockStatus.AMAN
        self.terakhir_update = datetime.utcnow()

class BloodRequest(Base):
    __tablename__ = "blood_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    pemohon_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    nama_pasien = Column(String(100), nullable=False)
    gol_darah = Column(Enum(BloodType), nullable=False)
    jumlah_kantong = Column(Integer, nullable=False)
    keperluan = Column(Text, nullable=False)
    tanggal_request = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING)
    catatan_admin = Column(Text, nullable=True)
    nomor_pemohon = Column(String(20), nullable=True)
    
    # Relationships
    pemohon = relationship("User", back_populates="blood_requests")