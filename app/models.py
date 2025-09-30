# TODO: Copy code from artifact 
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class UserRole(str, enum.Enum):
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
    
    # Relationships
    donor_histories = relationship("DonorHistory", back_populates="pendonor")
    blood_requests = relationship("BloodRequest", back_populates="pemohon")

class DonorHistory(Base):
    __tablename__ = "donor_histories"
    
    id = Column(Integer, primary_key=True, index=True)
    pendonor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tanggal_donor = Column(DateTime, nullable=False)
    lokasi = Column(String(200), default="RS Sentra Medika Minahasa Utara")
    status = Column(Enum(DonorStatus), default=DonorStatus.MASA_TUNGGU)
    catatan = Column(Text, nullable=True)
    
    # Relationships
    pendonor = relationship("User", back_populates="donor_histories")

class BloodStock(Base):
    __tablename__ = "blood_stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    gol_darah = Column(Enum(BloodType), unique=True, nullable=False)
    jumlah_kantong = Column(Integer, default=0)
    status = Column(Enum(StockStatus), nullable=False)
    terakhir_update = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    
    # Relationships
    pemohon = relationship("User", back_populates="blood_requests")