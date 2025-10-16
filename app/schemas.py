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
        orm_mode = True

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
    pendonor_id: int
    status: DonorStatus
    
    class Config:
        from_attributes = True
        orm_mode = True

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
        orm_mode = True

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
        orm_mode = True

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

# ==================== Donor Schedule Schemas ====================

class DonorScheduleCreate(BaseModel):
    """Schema for creating donor schedule"""
    tanggal_donor: datetime
    lokasi: str = "RS Sentra Medika Minahasa Utara"
    catatan: Optional[str] = None

class DonorScheduleUpdate(BaseModel):
    """Schema for updating donor schedule"""
    tanggal_donor: Optional[datetime] = None
    status: Optional[DonorStatus] = None
    catatan: Optional[str] = None

class DonorScheduleResponse(BaseModel):
    """Schema for donor schedule response"""
    id: int
    pendonor_id: int
    tanggal_donor: datetime
    lokasi: str
    status: DonorStatus
    catatan: Optional[str] = None
    
    # Note: DonorHistory model doesn't have created_at field
    # If you need it, add this field to the model
    
    class Config:
        from_attributes = True
        orm_mode = True

# ==================== Notification Schemas ====================

class EmailTestRequest(BaseModel):
    """Schema for testing email"""
    email: EmailStr

class CustomNotificationRequest(BaseModel):
    """Schema for custom notification"""
    email: EmailStr
    subject: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=10)
    use_ai: bool = False

class NotificationStatusResponse(BaseModel):
    """Schema for notification system status"""
    background_tasks_running: bool
    scheduler_jobs: List[dict]

# ==================== Generic Response Schemas ====================

class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    success: bool = True

class ErrorResponse(BaseModel):
    """Error response"""
    detail: str
    error_code: Optional[str] = None

# ==================== Statistics Schemas ====================

class StatisticsResponse(BaseModel):
    """Schema for statistics response"""
    total_users: int
    total_pendonors: int
    total_pemohons: int
    total_donations: int
    total_requests: int
    pending_requests: int

class AvailableDatesResponse(BaseModel):
    """Schema for available dates response"""
    month: int
    year: int
    available_dates: List[dict]
    booked_dates: List[int]
    user_eligible_date: Optional[str] = None

class TodayScheduleResponse(BaseModel):
    """Schema for today's schedules"""
    date: str
    total_schedules: int
    schedules: List[dict]

# ==================== Urgent Request Schemas ====================

class UrgentRequestItem(BaseModel):
    """Schema for urgent request item"""
    id: int
    gol_darah: str
    jumlah_kantong: int
    keperluan: str
    nama_pasien: str
    tanggal_request: str
    is_urgent: bool

class FulfillRequestResponse(BaseModel):
    """Schema for fulfill request response"""
    message: str
    remaining_stock: int