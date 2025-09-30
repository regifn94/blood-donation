"""
FastAPI Main Application
Blood Donor Management System - RS Sentra Medika Minahasa Utara
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from .database import get_db, init_db
from .models import (
    User, DonorHistory, BloodStock, BloodRequest,
    UserRole, StockStatus, BloodType, DonorStatus
)
from .schemas import (
    UserCreate, UserLogin, UserResponse, Token,
    DonorHistoryCreate, DonorHistoryResponse,
    BloodStockUpdate, BloodStockResponse,
    BloodRequestCreate, BloodRequestUpdate, BloodRequestResponse,
    DashboardStats, DonorDashboard, MessageResponse
)
from .auth import (
    get_password_hash, create_access_token, authenticate_user,
    get_current_user, get_current_admin
)

# Create FastAPI application
app = FastAPI(
    title="Blood Donor Management System",
    description="API untuk sistem manajemen donor darah RS Sentra Medika",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Startup Event ====================

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    print("🚀 Starting Blood Donor Management System...")
    init_db()
    print("✅ Application ready!")

# ==================== Root Endpoint ====================

@app.get("/", tags=["Root"])
def read_root():
    """Root endpoint"""
    return {
        "message": "Blood Donor Management System API",
        "version": "1.0.0",
        "hospital": "RS Sentra Medika Minahasa Utara",
        "docs": "/docs"
    }

# ==================== Health Check ====================

@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

# ==================== Authentication Endpoints ====================

@app.post("/api/register", response_model=UserResponse, tags=["Authentication"])
def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user
    
    - **nama**: Full name
    - **email**: Valid email address
    - **password**: Minimum 6 characters
    - **role**: User role (admin, pendonor, pemohon)
    - **gol_darah**: Blood type (required for pendonor)
    """
    # Check if email already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate blood type for pendonor
    if user.role == UserRole.PENDONOR and user.gol_darah is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Blood type is required for pendonor"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    new_user = User(
        nama=user.nama,
        email=user.email,
        password=hashed_password,
        role=user.role,
        gol_darah=user.gol_darah,
        no_telepon=user.no_telepon,
        alamat=user.alamat
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@app.post("/api/login", response_model=Token, tags=["Authentication"])
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    """
    Login to get access token
    
    - **email**: User email
    - **password**: User password
    """
    user = authenticate_user(db, user_login.email, user_login.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@app.get("/api/me", response_model=UserResponse, tags=["Authentication"])
def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user"""
    return current_user

# ==================== Admin Dashboard Endpoints ====================

@app.get("/api/admin/dashboard", response_model=DashboardStats, tags=["Admin"])
def get_admin_dashboard(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get admin dashboard statistics
    
    Requires admin authentication
    """
    # Total registered pendonors
    total_pendonor = db.query(User).filter(User.role == UserRole.PENDONOR).count()
    
    # Critical blood stocks
    stok_kritis = db.query(BloodStock).filter(
        BloodStock.status == StockStatus.KRITIS
    ).count()
    
    # Eligible donors this week (donors who can donate - 3 months since last donation)
    three_months_ago = datetime.utcnow() - timedelta(days=90)
    eligible_donors = db.query(User).filter(
        User.role == UserRole.PENDONOR
    ).all()
    
    jadwal_minggu_ini = 0
    for donor in eligible_donors:
        last_donation = db.query(DonorHistory).filter(
            DonorHistory.pendonor_id == donor.id
        ).order_by(DonorHistory.tanggal_donor.desc()).first()
        
        if not last_donation or last_donation.tanggal_donor <= three_months_ago:
            jadwal_minggu_ini += 1
    
    return {
        "total_pendonor": total_pendonor,
        "stok_kritis": stok_kritis,
        "jadwal_minggu_ini": jadwal_minggu_ini
    }

# ==================== Pendonor Dashboard Endpoints ====================

@app.get("/api/pendonor/dashboard", response_model=DonorDashboard, tags=["Pendonor"])
def get_donor_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get pendonor dashboard information
    
    Requires pendonor authentication
    """
    if current_user.role != UserRole.PENDONOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a pendonor"
        )
    
    # Get donation history
    histories = db.query(DonorHistory).filter(
        DonorHistory.pendonor_id == current_user.id
    ).order_by(DonorHistory.tanggal_donor.desc()).all()
    
    total_donasi = len(histories)
    
    # Calculate next donation date (3 months after last donation)
    jadwal_donor_berikutnya = None
    if histories:
        last_donation = histories[0].tanggal_donor
        next_date = last_donation + timedelta(days=90)
        
        # Format in Indonesian
        months_id = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
            5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
            9: "September", 10: "Oktober", 11: "November", 12: "Desember"
        }
        jadwal_donor_berikutnya = f"{next_date.day} {months_id[next_date.month]} {next_date.year}"
    
    # Format donation history
    riwayat_donasi = []
    for h in histories[:5]:  # Last 5 donations
        months_id = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
            5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
            9: "September", 10: "Oktober", 11: "November", 12: "Desember"
        }
        tanggal = f"{h.tanggal_donor.day} {months_id[h.tanggal_donor.month]} {h.tanggal_donor.year}"
        riwayat_donasi.append(f"{tanggal} - {h.lokasi}")
    
    return {
        "nama": current_user.nama,
        "gol_darah": current_user.gol_darah.value if current_user.gol_darah else "",
        "jadwal_donor_berikutnya": jadwal_donor_berikutnya,
        "total_donasi": total_donasi,
        "riwayat_donasi": riwayat_donasi
    }

# ==================== Blood Stock Endpoints ====================

@app.get("/api/blood-stocks", response_model=List[BloodStockResponse], tags=["Blood Stock"])
def get_blood_stocks(db: Session = Depends(get_db)):
    """Get all blood stocks (public access)"""
    stocks = db.query(BloodStock).all()
    
    # Initialize all blood types if not exists
    if not stocks:
        for blood_type in BloodType:
            stock = BloodStock(
                gol_darah=blood_type,
                jumlah_kantong=8,
                status=StockStatus.AMAN
            )
            db.add(stock)
        db.commit()
        stocks = db.query(BloodStock).all()
    
    return stocks

@app.put(
    "/api/admin/blood-stocks/{blood_type}",
    response_model=BloodStockResponse,
    tags=["Admin"]
)
def update_blood_stock(
    blood_type: str,
    stock_update: BloodStockUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update blood stock quantity
    
    Requires admin authentication
    """
    # Find blood stock
    stock = db.query(BloodStock).filter(
        BloodStock.gol_darah == blood_type
    ).first()
    
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blood type not found"
        )
    
    # Update quantity
    stock.jumlah_kantong = stock_update.jumlah_kantong
    
    # Auto-update status based on quantity
    if stock_update.jumlah_kantong < 10:
        stock.status = StockStatus.KRITIS
    elif stock_update.jumlah_kantong < 20:
        stock.status = StockStatus.MENIPIS
    else:
        stock.status = StockStatus.AMAN
    
    stock.terakhir_update = datetime.utcnow()
    
    db.commit()
    db.refresh(stock)
    
    return stock

# ==================== Donor History Endpoints ====================

@app.get("/api/donor-histories", response_model=List[DonorHistoryResponse], tags=["Donor History"])
def get_donor_histories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get donor histories (admin sees all, pendonor sees own)"""
    if current_user.role == UserRole.ADMIN:
        histories = db.query(DonorHistory).all()
    else:
        histories = db.query(DonorHistory).filter(
            DonorHistory.pendonor_id == current_user.id
        ).all()
    
    return histories

@app.post("/api/admin/donor-histories", response_model=DonorHistoryResponse, tags=["Admin"])
def create_donor_history(
    history: DonorHistoryCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Create donor history record
    
    Requires admin authentication
    """
    new_history = DonorHistory(**history.dict())
    db.add(new_history)
    db.commit()
    db.refresh(new_history)
    
    return new_history

# ==================== Blood Request Endpoints ====================

@app.get("/api/blood-requests", response_model=List[BloodRequestResponse], tags=["Blood Request"])
def get_blood_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get blood requests (admin sees all, users see own)"""
    if current_user.role == UserRole.ADMIN:
        requests = db.query(BloodRequest).all()
    else:
        requests = db.query(BloodRequest).filter(
            BloodRequest.pemohon_id == current_user.id
        ).all()
    
    return requests

@app.post("/api/blood-requests", response_model=BloodRequestResponse, tags=["Blood Request"])
def create_blood_request(
    request: BloodRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new blood request"""
    new_request = BloodRequest(
        **request.dict(),
        pemohon_id=current_user.id
    )
    
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    
    return new_request

@app.put(
    "/api/admin/blood-requests/{request_id}",
    response_model=BloodRequestResponse,
    tags=["Admin"]
)
def update_blood_request(
    request_id: int,
    request_update: BloodRequestUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update blood request status
    
    Requires admin authentication
    """
    blood_request = db.query(BloodRequest).filter(
        BloodRequest.id == request_id
    ).first()
    
    if not blood_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    
    blood_request.status = request_update.status
    if request_update.catatan_admin:
        blood_request.catatan_admin = request_update.catatan_admin
    
    db.commit()
    db.refresh(blood_request)
    
    return blood_request

# ==================== User Management Endpoints ====================

@app.get("/api/admin/pendonors", response_model=List[UserResponse], tags=["Admin"])
def get_all_pendonors(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all registered pendonors
    
    Requires admin authentication
    """
    pendonors = db.query(User).filter(User.role == UserRole.PENDONOR).all()
    return pendonors

@app.get("/api/admin/users", response_model=List[UserResponse], tags=["Admin"])
def get_all_users(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all users
    
    Requires admin authentication
    """
    users = db.query(User).all()
    return users

# ==================== Statistics Endpoints ====================

@app.get("/api/admin/statistics", tags=["Admin"])
def get_statistics(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive statistics
    
    Requires admin authentication
    """
    return {
        "total_users": db.query(User).count(),
        "total_pendonors": db.query(User).filter(User.role == UserRole.PENDONOR).count(),
        "total_pemohons": db.query(User).filter(User.role == UserRole.PEMOHON).count(),
        "total_donations": db.query(DonorHistory).count(),
        "total_requests": db.query(BloodRequest).count(),
        "pending_requests": db.query(BloodRequest).filter(
            BloodRequest.status == "Pending"
        ).count()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)