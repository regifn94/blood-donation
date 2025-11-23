"""
FastAPI Main Application with AI-Powered Notifications
Blood Donor Management System - RS Sentra Medika Minahasa Utara
"""
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
from fastapi import Query

from .database import get_db, init_db
from .models import (
    User, DonorHistory, BloodStock, BloodRequest,
    UserRole, StockStatus, BloodType, DonorStatus, RequestStatus
)
from .schemas import (
    UserCreate, UserLogin, UserResponse, Token,
    DonorHistoryCreate, DonorHistoryResponse,
    BloodStockUpdate, BloodStockResponse,
    BloodRequestCreate, BloodRequestUpdate, BloodRequestResponse,
    DashboardStats, DonorDashboard, DonorScheduleResponse,
    DonorScheduleCreate, DonorScheduleUpdate, MessageResponse
)
from .auth import (
    get_password_hash, create_access_token, authenticate_user,
    get_current_user, get_current_admin
)
from .background_tasks import background_service
from .ai_service import ai_service
from .notification_service import email_service

# Create FastAPI application
app = FastAPI(
    title="Blood Donor Management System with AI",
    description="API untuk sistem manajemen donor darah dengan notifikasi AI",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware, # untuk mengizinkan komunikasi antara frontend
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

# ==================== Startup & Shutdown Events ====================

@app.on_event("startup")
async def startup_event():
    """Initialize database and start background tasks"""
    print("🚀 Starting Blood Donor Management System with AI...")
    init_db()
    background_service.start()
    print("✅ Application ready with AI-powered notifications!")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown"""
    print("⏹️ Shutting down...")
    background_service.stop()
    print("✅ Shutdown complete")

# ==================== Root Endpoint ====================

@app.get("/", tags=["Root"])
def read_root():
    """Root endpoint"""
    return {
        "message": "Blood Donor Management System API with AI",
        "version": "2.0.0",
        "features": ["AI-Generated Notifications", "Email Alerts", "Automated Reminders"],
        "hospital": "RS Sentra Medika Minahasa Utara",
        "docs": "/docs"
    }

# ==================== Health Check ====================

@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "background_tasks": "running" if background_service.is_running else "stopped"
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
        alamat=user.alamat,
        gender=user.gender
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
def get_me(current_user: User = Depends(get_current_user)): # Untuk mengambil data user yang sedang login dari JWT token, dan memastikan request memiliki token valid.
    """Get current authenticated user"""
    return current_user

# ==================== Admin Dashboard Endpoints ====================

@app.get("/api/admin/dashboard", response_model=DashboardStats, tags=["Admin"])
def get_admin_dashboard(
    current_user: User = Depends(get_current_admin), #hanya admin yang bisa akses
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
    Update blood stock quantity (triggers notification if low)
    
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
    
    old_status = stock.status
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
    
    # Trigger notification if stock became low/critical
    if stock.status in [StockStatus.KRITIS, StockStatus.MENIPIS] and old_status != stock.status:
        # Background task will handle this automatically every 6 hours
        print(f"⚠️ Stock alert will be sent for {blood_type} (status changed to {stock.status.value})")
    
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
async def create_donor_history(
    history: DonorHistoryCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Create donor history record (sends thank you email automatically)
    
    Requires admin authentication
    """
    new_history = DonorHistory(**history.dict())
    db.add(new_history)
    db.commit()
    db.refresh(new_history)
    
    # Send thank you email in background
    background_tasks.add_task(
        background_service.send_thank_you_after_donation,
        donor_id=history.pendonor_id,
        db=db
    )
    
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

async def send_approval_notification(
    pemohon_email: str,
    pemohon_name: str,
    blood_type: str,
    jumlah_kantong: int,
    keperluan: str,
    catatan_admin: str = None
):
    """
    Background task to send approval email notification
    Called by BackgroundTasks when request is approved
    """
    try:
        print(f"🔄 Generating approval email for {pemohon_name}...")
        
        # Generate AI content
        ai_content = await ai_service.generate_request_approved_email(
            pemohon_name=pemohon_name,
            blood_type=blood_type,
            jumlah_kantong=jumlah_kantong,
            keperluan=keperluan,
            catatan_admin=catatan_admin
        )
        
        # Send email
        success = await email_service.send_request_approved_email(
            pemohon_email=pemohon_email,
            pemohon_name=pemohon_name,
            ai_content=ai_content
        )
        
        if success:
            print(f"✅ Approval email sent to {pemohon_name} ({pemohon_email})")
        else:
            print(f"❌ Failed to send approval email to {pemohon_email}")
    
    except Exception as e:
        print(f"❌ Error sending approval notification: {str(e)}")


async def send_rejection_notification(
    pemohon_email: str,
    pemohon_name: str,
    blood_type: str,
    jumlah_kantong: int,
    keperluan: str,
    catatan_admin: str = None
):
    """
    Background task to send rejection email notification
    Called by BackgroundTasks when request is rejected
    """
    try:
        print(f"🔄 Generating rejection email for {pemohon_name}...")
        
        # Generate AI content
        ai_content = await ai_service.generate_request_rejected_email(
            pemohon_name=pemohon_name,
            blood_type=blood_type,
            jumlah_kantong=jumlah_kantong,
            keperluan=keperluan,
            catatan_admin=catatan_admin
        )
        
        # Send email
        success = await email_service.send_request_rejected_email(
            pemohon_email=pemohon_email,
            pemohon_name=pemohon_name,
            ai_content=ai_content
        )
        
        if success:
            print(f"✅ Rejection email sent to {pemohon_name} ({pemohon_email})")
        else:
            print(f"❌ Failed to send rejection email to {pemohon_email}")
    
    except Exception as e:
        print(f"❌ Error sending rejection notification: {str(e)}")

@app.put(
    "/api/admin/blood-requests/{request_id}",
    response_model=BloodRequestResponse,
    tags=["Admin"]
)
async def update_blood_request(
    request_id: int,
    request_update: BloodRequestUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update blood request status with automatic email notification
    
    Sends email to requester when:
    - Status changed to DISETUJUI (Approved)
    - Status changed to DITOLAK (Rejected)
    
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
    
    # Store old status to detect changes
    old_status = blood_request.status
    
    # Update status and notes
    blood_request.status = request_update.status
    if request_update.catatan_admin:
        blood_request.catatan_admin = request_update.catatan_admin
    
    # Commit changes first
    db.commit()
    db.refresh(blood_request)
    
    # Get requester information
    pemohon = db.query(User).filter(User.id == blood_request.pemohon_id).first()
    
    # Send email notification if status changed to APPROVED or REJECTED
    if pemohon and pemohon.email:
        status_changed = old_status != request_update.status
        
        if status_changed and request_update.status == RequestStatus.DISETUJUI:
            # Send APPROVAL email
            print(f"📧 Sending approval email to {pemohon.email}...")
            background_tasks.add_task(
                send_approval_notification,
                pemohon_email=pemohon.email,
                pemohon_name=pemohon.nama,
                blood_type=blood_request.gol_darah.value,
                jumlah_kantong=blood_request.jumlah_kantong,
                keperluan=blood_request.keperluan,
                catatan_admin=blood_request.catatan_admin
            )
        
        elif status_changed and request_update.status == RequestStatus.DITOLAK:
            # Send REJECTION email
            print(f"📧 Sending rejection email to {pemohon.email}...")
            background_tasks.add_task(
                send_rejection_notification,
                pemohon_email=pemohon.email,
                pemohon_name=pemohon.nama,
                blood_type=blood_request.gol_darah.value,
                jumlah_kantong=blood_request.jumlah_kantong,
                keperluan=blood_request.keperluan,
                catatan_admin=blood_request.catatan_admin
            )
    
    return blood_request

@app.get("/api/blood-requests/urgent", tags=["Blood Request"])
def get_urgent_requests(db: Session = Depends(get_db)):
    """
    Get urgent blood requests (public access)
    
    Returns pending requests sorted by urgency
    """
    urgent_requests = db.query(BloodRequest).filter(
        BloodRequest.status == RequestStatus.PENDING
    ).order_by(BloodRequest.tanggal_request.desc()).limit(10).all()
    
    result = []
    for request in urgent_requests:
        result.append({
            "id": request.id,
            "gol_darah": request.gol_darah.value if request.gol_darah else "Unknown",
            "jumlah_kantong": request.jumlah_kantong,
            "keperluan": request.keperluan,
            "nama_pasien": request.nama_pasien[:3] + "***",  # Privacy protection
            "tanggal_request": request.tanggal_request.isoformat(),
            "is_urgent": True
        })
    
    return result

@app.post("/api/blood-requests/{request_id}/fulfill", tags=["Admin"])
def fulfill_blood_request(
    request_id: int,
    notes: str = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Mark blood request as fulfilled and update stock
    
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
    
    # Update stock
    stock = db.query(BloodStock).filter(
        BloodStock.gol_darah == blood_request.gol_darah
    ).first()
    
    if stock:
        if stock.jumlah_kantong < blood_request.jumlah_kantong:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {stock.jumlah_kantong}, Requested: {blood_request.jumlah_kantong}"
            )
        
        stock.jumlah_kantong -= blood_request.jumlah_kantong
        
        # Update stock status
        if stock.jumlah_kantong < 10:
            stock.status = StockStatus.KRITIS
        elif stock.jumlah_kantong < 20:
            stock.status = StockStatus.MENIPIS
        else:
            stock.status = StockStatus.AMAN
    
    # Update request status
    blood_request.status = RequestStatus.SELESAI
    if notes:
        blood_request.catatan_admin = notes
    
    db.commit()
    
    return {
        "message": "Request fulfilled successfully",
        "remaining_stock": stock.jumlah_kantong if stock else 0
    }

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

# ==================== Donor Schedule Endpoints ====================

@app.post("/api/donor-schedules", response_model=DonorScheduleResponse, tags=["Donor Schedule"])
async def create_donor_schedule(
    schedule: DonorScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new donor schedule
    
    - Pendonor dapat membuat jadwal donor baru (termasuk masa lalu).
    - Jika tanggal di masa lalu, otomatis status = SELESAI.
    - Jika jadwal terakhir SELESAI → harus menunggu 3 bulan.
    - Jika jadwal terakhir BATAL → bisa langsung buat lagi.
    - Tidak boleh buat jadwal di hari Minggu.
    """
    from datetime import datetime, timezone
    
    # Cek apakah tanggal di masa lalu
    now = datetime.now(timezone.utc)

    # Convert tanggal_donor menjadi timezone-aware
    if schedule.tanggal_donor.tzinfo is None:
        schedule_dt = schedule.tanggal_donor.replace(tzinfo=timezone.utc)
    else:
        schedule_dt = schedule.tanggal_donor

    is_past_date = schedule_dt < now
    
    # Validasi: tidak boleh hari Minggu untuk jadwal masa depan
    if not is_past_date and schedule.tanggal_donor.weekday() == 6:  # Sunday = 6
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak dapat membuat jadwal donor pada hari Minggu"
        )
    
    if current_user.role == UserRole.PENDONOR:
        # Ambil riwayat donor terakhir yang SELESAI
        last_completed_donation = db.query(DonorHistory).filter(
            DonorHistory.pendonor_id == current_user.id,
            DonorHistory.status == DonorStatus.SELESAI
        ).order_by(DonorHistory.tanggal_donor.desc()).first()
        
        if last_completed_donation:
            # Validasi jarak 3 bulan dari donor terakhir yang SELESAI
            min_next_date = last_completed_donation.tanggal_donor + timedelta(days=90)
            
            # Untuk jadwal masa depan, cek jarak 3 bulan
            if not is_past_date and schedule.tanggal_donor < min_next_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Anda baru dapat donor setelah {min_next_date.strftime('%d-%m-%Y')} (3 bulan dari donor terakhir)"
                )
            
            # Untuk jadwal masa lalu, cek apakah minimal 3 bulan dari donor sebelumnya
            if is_past_date and schedule.tanggal_donor < min_next_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tanggal donor yang Anda masukkan terlalu dekat dengan donor terakhir. Minimal 3 bulan dari {last_completed_donation.tanggal_donor.strftime('%d-%m-%Y')}"
                )
        
        # Cek apakah ada jadwal aktif (SIAP_DONOR)
        active_schedule = db.query(DonorHistory).filter(
            DonorHistory.pendonor_id == current_user.id,
            DonorHistory.status == DonorStatus.SIAP_DONOR
        ).first()
        
        if active_schedule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Anda masih memiliki jadwal donor aktif. Silakan selesaikan atau batalkan jadwal tersebut terlebih dahulu."
            )

    # Tentukan status berdasarkan tanggal
    initial_status = DonorStatus.SELESAI if is_past_date else DonorStatus.SIAP_DONOR
    
    # Buat jadwal baru
    new_schedule = DonorHistory(
        pendonor_id=current_user.id,
        tanggal_donor=schedule.tanggal_donor,
        lokasi=schedule.lokasi,
        status=initial_status,
        catatan=schedule.catatan
    )
    
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)
    
    # ============ SEND CONFIRMATION EMAIL (hanya untuk jadwal masa depan) ============
    if not is_past_date:
        try:
            # Format date in Indonesian
            months_id = {
                1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
                5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
                9: "September", 10: "Oktober", 11: "November", 12: "Desember"
            }
            
            donation_date = schedule.tanggal_donor
            formatted_date = f"{donation_date.day} {months_id[donation_date.month]} {donation_date.year}"
            formatted_time = donation_date.strftime("%H:%M WIB")
            full_formatted_date = f"{formatted_date} pukul {formatted_time}"
            
            # Generate AI content for email
            ai_content = await ai_service.generate_schedule_confirmation(
                donor_name=current_user.nama,
                blood_type=current_user.gol_darah.value if current_user.gol_darah else "Unknown",
                donation_date=full_formatted_date,
                location=schedule.lokasi,
                notes=schedule.catatan
            )
                
        except Exception as email_error:
            # Log error but don't fail the schedule creation
            print(f"⚠️  Failed to send confirmation email: {str(email_error)}")
            import traceback
            traceback.print_exc()
    
    return new_schedule


# ============ TAMBAHAN: Background Task untuk Auto-Update Status ============
@app.get("/api/donor-schedules/update-expired", tags=["Donor Schedule"])
async def update_expired_schedules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
    ):
    """
    Update jadwal yang sudah lewat dari SIAP_DONOR menjadi SELESAI
    Endpoint ini bisa dipanggil secara manual atau dijadwalkan (cron job)
    """
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc)
    
    # Cari semua jadwal SIAP_DONOR yang sudah lewat
    expired_schedules = db.query(DonorHistory).filter(
        DonorHistory.status == DonorStatus.SIAP_DONOR,
        DonorHistory.tanggal_donor < now
    ).all()
    
    updated_count = 0
    for schedule in expired_schedules:
        schedule.status = DonorStatus.SELESAI
        updated_count += 1
    
    db.commit()
    
    return {
        "message": f"Successfully updated {updated_count} expired schedules to SELESAI",
        "updated_count": updated_count
    }

@app.get("/api/donor-schedules", response_model=List[DonorScheduleResponse], tags=["Donor Schedule"])
def get_donor_schedules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get donor schedules
    
    - Admin sees all schedules
    - Pendonor sees own schedules
    """
    if current_user.role == UserRole.ADMIN:
        schedules = db.query(DonorHistory).order_by(DonorHistory.tanggal_donor.desc()).all()
    else:
        schedules = db.query(DonorHistory).filter(
            DonorHistory.pendonor_id == current_user.id
        ).order_by(DonorHistory.tanggal_donor.desc()).all()
    
    return schedules

@app.get("/api/donor-schedules/available-dates", tags=["Donor Schedule"])
def get_available_dates(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2024, le=2030),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get available dates for donor scheduling in a specific month
    
    Returns dates that are:
    - Not in the past
    - Not on Sundays
    - Not fully booked (max 20 donors per day)
    """
    from calendar import monthrange
    
    available_dates = []
    booked_dates = []
    
    # Get number of days in the month
    num_days = monthrange(year, month)[1]
    
    # Check each day in the month
    for day in range(1, num_days + 1):
        date = datetime(year, month, day)
        
        # Skip past dates
        if date.date() < datetime.utcnow().date():
            continue
        
        # Skip Sundays
        if date.weekday() == 6:
            continue
        
        # Count existing schedules for this date
        schedule_count = db.query(DonorHistory).filter(
            DonorHistory.tanggal_donor >= date,
            DonorHistory.tanggal_donor < date + timedelta(days=1)
        ).count()
        
        if schedule_count >= 20:
            booked_dates.append(day)
        else:
            available_dates.append({
                "day": day,
                "available_slots": 20 - schedule_count
            })
    
    # Check user's eligibility
    user_eligible_date = None
    if current_user.role == UserRole.PENDONOR:
        last_donation = db.query(DonorHistory).filter(
            DonorHistory.pendonor_id == current_user.id
        ).order_by(DonorHistory.tanggal_donor.desc()).first()
        
        if last_donation:
            user_eligible_date = (last_donation.tanggal_donor + timedelta(days=90)).isoformat()
    
    return {
        "month": month,
        "year": year,
        "available_dates": available_dates,
        "booked_dates": booked_dates,
        "user_eligible_date": user_eligible_date
    }

@app.put("/api/donor-schedules/{schedule_id}", response_model=DonorScheduleResponse, tags=["Donor Schedule"])
def update_donor_schedule(
    schedule_id: int,
    schedule_update: DonorScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update donor schedule
    
    - Users can update their own schedules
    - Admins can update any schedule
    """
    schedule = db.query(DonorHistory).filter(
        DonorHistory.id == schedule_id
    ).first()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    # Check permissions
    if current_user.role != UserRole.ADMIN and schedule.pendonor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this schedule"
        )
    
    # Update fields
    if schedule_update.tanggal_donor:
        # Validate new date
        if schedule_update.tanggal_donor.date() < datetime.utcnow().date():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reschedule to past date"
            )
        schedule.tanggal_donor = schedule_update.tanggal_donor
    
    if schedule_update.status:
        schedule.status = schedule_update.status
    
    if schedule_update.catatan is not None:
        schedule.catatan = schedule_update.catatan
    
    db.commit()
    db.refresh(schedule)
    
    return schedule

@app.delete("/api/donor-schedules/{schedule_id}", tags=["Donor Schedule"])
def cancel_donor_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel/delete donor schedule
    
    - Users can cancel their own schedules
    - Admins can cancel any schedule
    """
    schedule = db.query(DonorHistory).filter(
        DonorHistory.id == schedule_id
    ).first()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    # Check permissions
    if current_user.role != UserRole.ADMIN and schedule.pendonor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this schedule"
        )
    
    # Check if schedule is in the future
    if schedule.tanggal_donor.date() < datetime.utcnow().date():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel past schedules"
        )
    
    db.delete(schedule)
    db.commit()
    
    return {"message": "Schedule cancelled successfully"}

@app.get("/api/admin/donor-schedules/today", tags=["Admin"])
def get_today_schedules(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get today's donor schedules
    
    Requires admin authentication
    """
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    
    schedules = db.query(DonorHistory).join(User).filter(
        DonorHistory.tanggal_donor >= today,
        DonorHistory.tanggal_donor < tomorrow
    ).all()
    
    result = []
    for schedule in schedules:
        donor = db.query(User).filter(User.id == schedule.pendonor_id).first()
        result.append({
            "id": schedule.id,
            "donor_name": donor.nama if donor else "Unknown",
            "donor_blood_type": donor.gol_darah.value if donor and donor.gol_darah else "Unknown",
            "time": schedule.tanggal_donor.strftime("%H:%M"),
            "status": schedule.status.value if schedule.status else "Scheduled",
            "location": schedule.lokasi,
            "notes": schedule.catatan
        })
    
    return {
        "date": today.isoformat(),
        "total_schedules": len(result),
        "schedules": result
    }

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
            BloodRequest.status == RequestStatus.PENDING
        ).count()
    }

# ==================== Notification Management Endpoints ====================

@app.post("/api/admin/notifications/test-email", tags=["Admin", "Notifications"])
async def test_email_notification(
    email: str,
    current_user: User = Depends(get_current_admin)
):
    """
    Test email notification system
    
    Send a test email to verify SMTP configuration
    """
    success = await email_service.send_email(
        to_email=email,
        subject="🧪 Test Email - Blood Donor System",
        body="This is a test email from Blood Donor Management System. If you receive this, the email system is working correctly!"
    )
    
    return {
        "success": success,
        "message": "Test email sent successfully" if success else "Failed to send test email"
    }

@app.post("/api/admin/notifications/trigger-stock-check", tags=["Admin", "Notifications"])
async def trigger_stock_check(
    current_user: User = Depends(get_current_admin)
):
    """
    Manually trigger blood stock check and notifications
    
    Useful for testing or immediate alerts
    """
    await background_service.check_blood_stock()
    return {"message": "Stock check triggered successfully"}

@app.post("/api/admin/notifications/trigger-reminders", tags=["Admin", "Notifications"])
async def trigger_donation_reminders(
    current_user: User = Depends(get_current_admin)
):
    """
    Manually trigger donation reminders
    
    Send reminders to donors with upcoming appointments
    """
    await background_service.send_donation_reminders()
    return {"message": "Donation reminders triggered successfully"}

@app.post("/api/admin/notifications/send-weekly-summary", tags=["Admin", "Notifications"])
async def trigger_weekly_summary(
    current_user: User = Depends(get_current_admin)
):
    """
    Manually trigger weekly summary email to admins
    """
    await background_service.send_weekly_summary()
    return {"message": "Weekly summary sent successfully"}

@app.get("/api/admin/notifications/status", tags=["Admin", "Notifications"])
def get_notification_status(
    current_user: User = Depends(get_current_admin)
):
    """
    Get notification system status
    
    Shows background tasks status and scheduled jobs
    """
    return {
        "background_tasks_running": background_service.is_running,
        "scheduler_jobs": [
            {
                "id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            }
            for job in background_service.scheduler.get_jobs()
        ] if background_service.is_running else []
    }

@app.post("/api/admin/notifications/send-custom", tags=["Admin", "Notifications"])
async def send_custom_notification(
    email: str,
    subject: str,
    message: str,
    use_ai: bool = False,
    current_user: User = Depends(get_current_admin)
):
    """
    Send custom notification to specific email
    
    - **email**: Recipient email
    - **subject**: Email subject
    - **message**: Email message (can be enhanced by AI if use_ai=True)
    - **use_ai**: Whether to enhance message with AI
    """
    if use_ai:
        # Use AI to enhance the message
        prompt = f"""
Buatkan email yang lebih professional dan ramah berdasarkan pesan berikut:

Subject: {subject}
Message: {message}

Tambahkan greeting dan closing yang sesuai. Format dalam Bahasa Indonesia.
"""
        try:
            ai_content = await ai_service.model.generate_content(prompt)
            enhanced_message = ai_content.text
        except:
            enhanced_message = message
    else:
        enhanced_message = message
    
    success = await email_service.send_email(
        to_email=email,
        subject=subject,
        body=enhanced_message
    )
    
    return {
        "success": success,
        "message": "Custom notification sent" if success else "Failed to send notification",
        "ai_enhanced": use_ai
    }

# ==================== Main ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)