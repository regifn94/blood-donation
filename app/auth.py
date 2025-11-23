"""
JWT Authentication and Authorization (Using SHA256 - No dependencies issues)
"""

# import libary yang dibutuhkan
from datetime import datetime, timedelta # untuk waktu token kadaluarsa
from typing import Optional
from jose import JWTError, jwt # untuk encode/decode JWT
from passlib.context import CryptContext # untuk hashing password
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv # untuk ambil variabel dari .env

# import modul lokal (dari proyek sendiri)
from .database import get_db # koneksi database
from .models import User, UserRole # model user dan peran (role)

# load file .env untuk baca konfigurasi
load_dotenv()

# main Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-please-change-in-production")
ALGORITHM = "HS256" # algoritma enskripsi JWT (menggunakan HS256)
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours KADALUARSA

# Password hashing context - Using pbkdf2_sha256 (built-in, no external dependencies)
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"], # skema hashing yang digunakan
    deprecated="auto", # tandai algoritma lama sebagai deprecated
    pbkdf2_sha256__default_rounds=200000 #jumlah iterasi hasding (semakin tinggi semakin aman)
)
print("✅ Using PBKDF2-SHA256 for password hashing")

# HTTP Bearer for token authentication
security = HTTPBearer()

# ==================== Password Functions ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
        
    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        # cocokan password input dengan hash di database
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"❌ Password verification error: {e}")
        return False

def get_password_hash(password: str) -> str:
    """
    Hash a password 
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    # mengubah password plaintext menjadi hash untuk disimpan di database
    try:
        # hash password
        return pwd_context.hash(password)
    except Exception as e:
        print(f"❌ Password hashing error: {e}")
        # jika error, kembalikan pesan HTTP error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error hashing password"
        )

# ==================== JWT Token Functions ====================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Dictionary with user data (typically {"sub": user_email})
        expires_delta: Optional custom expiration time
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy() # salid data user yang ingin di encode ke token
    
    #tentukan waktu kadaluarsa token
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # tambahkan waktu expire ke playload
    to_encode.update({"exp": expire})
    # encode data jadi JWT menggunakan secret ke dan algoritma
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt #kembalikan token ke client

def decode_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        dict: Decoded token payload or None if invalid
    """
    try:
        # decode token dengan kunci rahasia dan algoritma yang sama
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # jika token tidak valid, kembalikan none
        return None

# ==================== Authentication Dependencies ====================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    # buat exception standar jika token tidak valid
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Extract token from credentials / ambil token dari header authorization
    token = credentials.credentials
    
    # Decode token JWT
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    # Get email from token / ambil email dari playload token (biasanya disimpan di  field 'sub')
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
    
    # Get user from database / cek apakah user dengan email tsb ada di database
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    # kembalikan objek user
    return user

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Verify current user is an admin
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current admin user
        
    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required."
        )
    return current_user

def get_current_pendonor(current_user: User = Depends(get_current_user)) -> User:
    """
    Verify current user is a pendonor (donor)
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current pendonor user
        
    Raises:
        HTTPException: If user is not a pendonor
    """
    if current_user.role != UserRole.PENDONOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Pendonor access required."
        )
    return current_user

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user by email and password
    
    Args:
        db: Database session
        email: User email
        password: Plain text password
        
    Returns:
        User: Authenticated user or None if credentials invalid
    """
    # ambil user dari database berdasarkan email
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.password):
        return None
    
    return user