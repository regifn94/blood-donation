"""
Pydantic Schemas for Request/Response Validation
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from .models import UserRole, BloodType, DonorStatus, StockStatus, RequestStatus

# ==================== User Schemas ====================

class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    nama: str = Field(..., min_length=3, max_length=100)
    role: UserRole
    gol_darah: Optional[BloodType] = None
    no_telepon: Optional[str] = Field(None, max_length=20)
    alamat: Optional[str] = None

class UserCreate(UserBase):
    """Schema for user creation"""
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str

class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    tanggal_daftar: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str
    user: UserResponse

# ==================== Donor History Schemas ====================

class DonorHistoryBase(BaseModel):
    """Base donor history schema"""
    tanggal_donor: datetime
    lokasi: str = "RS Sentra Medika Minahasa Utara"
    catatan: Optional[str] = None

class DonorHistoryCreate(DonorHistoryBase):
    """Schema for creating donor history"""
    pendonor_id: int

class DonorHistoryResponse(DonorHistoryBase):
    """Schema for donor history response"""
    id: int
    status: DonorStatus
    
    class Config:
        from_attributes = True

# ==================== Blood Stock Schemas ====================

class BloodStockBase(BaseModel):
    """Base blood stock schema"""
    gol_darah: BloodType
    jumlah_kantong: int = Field(..., ge=0)

class BloodStockUpdate(BaseModel):
    """Schema for updating blood stock"""
    jumlah_kantong: int = Field(..., ge=0)

class BloodStockResponse(BloodStockBase):
    """Schema for blood stock response"""
    id: int
    status: StockStatus
    terakhir_update: datetime
    
    class Config:
        from_attributes = True

# ==================== Blood Request Schemas ====================

class BloodRequestBase(BaseModel):
    """Base blood request schema"""
    nama_pasien: str = Field(..., min_length=3, max_length=100)
    gol_darah: BloodType
    jumlah_kantong: int = Field(..., ge=1, le=10)
    keperluan: str = Field(..., min_length=10)

class BloodRequestCreate(BloodRequestBase):
    """Schema for creating blood request"""
    pass

class BloodRequestUpdate(BaseModel):
    """Schema for updating blood request (admin only)"""
    status: RequestStatus
    catatan_admin: Optional[str] = None

class BloodRequestResponse(BloodRequestBase):
    """Schema for blood request response"""
    id: int
    pemohon_id: int
    tanggal_request: datetime
    status: RequestStatus
    catatan_admin: Optional[str] = None
    
    class Config:
        from_attributes = True

# ==================== Dashboard Schemas ====================

class DashboardStats(BaseModel):
    """Schema for admin dashboard statistics"""
    total_pendonor: int
    stok_kritis: int
    jadwal_minggu_ini: int

class DonorDashboard(BaseModel):
    """Schema for donor dashboard"""
    nama: str
    gol_darah: str
    jadwal_donor_berikutnya: Optional[str] = None
    total_donasi: int
    riwayat_donasi: List[str]

# ==================== Generic Response Schemas ====================

class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    success: bool = True

class ErrorResponse(BaseModel):
    """Error response"""
    detail: str
    error_code: Optional[str] = None