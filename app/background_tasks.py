"""
Background Tasks for Automated Notifications
Uses APScheduler for periodic checks
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import List
import asyncio

from .database import SessionLocal
from .models import User, BloodStock, DonorHistory, UserRole, StockStatus
from .ai_service import ai_service
from .notification_service import email_service


class BackgroundTaskService:
    """Service for managing background notification tasks"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    def start(self):
        """Start the background scheduler"""
        if self.is_running:
            return
        
        # Check blood stock every 6 hours
        self.scheduler.add_job(
            self.check_blood_stock,
            CronTrigger(hour='*/6'),  # Every 6 hours
            id='check_blood_stock',
            replace_existing=True
        )
        
        # Send donation reminders daily at 9 AM
        self.scheduler.add_job(
            self.send_donation_reminders,
            CronTrigger(hour=9, minute=0),  # Daily at 9:00 AM
            id='donation_reminders',
            replace_existing=True
        )
        
        # Check weekly summary every Monday at 8 AM
        self.scheduler.add_job(
            self.send_weekly_summary,
            CronTrigger(day_of_week='mon', hour=8, minute=0),
            id='weekly_summary',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        print("✅ Background task scheduler started")
    
    def stop(self):
        """Stop the background scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            print("⏹️ Background task scheduler stopped")
    
    async def check_blood_stock(self):
        """
        Check blood stock levels and send alerts for low/critical stock
        """
        print("🔍 Checking blood stock levels...")
        
        db = SessionLocal()
        try:
            # Get all blood stocks that are low or critical
            low_stocks = db.query(BloodStock).filter(
                BloodStock.status.in_([StockStatus.MENIPIS, StockStatus.KRITIS])
            ).all()
            
            if not low_stocks:
                print("✅ All blood stocks are at safe levels")
                return
            
            # Get admin emails
            admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
            admin_emails = [admin.email for admin in admins if admin.email]
            
            if not admin_emails:
                print("⚠️ No admin emails found for notification")
                return
            
            # Send alert for each low stock
            for stock in low_stocks:
                print(f"⚠️ Low stock detected: {stock.gol_darah.value} - {stock.jumlah_kantong} bags ({stock.status.value})")
                
                # Generate AI content
                ai_content = await ai_service.generate_low_stock_alert(
                    blood_type=stock.gol_darah.value,
                    current_stock=stock.jumlah_kantong,
                    status=stock.status.value
                )
                
                # Send email to all admins
                success = await email_service.send_low_stock_alert(
                    admin_emails=admin_emails,
                    blood_type=stock.gol_darah.value,
                    current_stock=stock.jumlah_kantong,
                    status=stock.status.value,
                    ai_content=ai_content
                )
                
                if success:
                    print(f"✅ Alert sent for {stock.gol_darah.value}")
                else:
                    print(f"❌ Failed to send alert for {stock.gol_darah.value}")
                
                # Small delay between emails
                await asyncio.sleep(1)
        
        except Exception as e:
            print(f"❌ Error checking blood stock: {str(e)}")
        finally:
            db.close()
    
    async def send_donation_reminders(self):
        """
        Send reminders to donors with upcoming appointments
        Sends reminders 3 days before and 1 day before donation
        """
        print("📧 Sending donation reminders...")
        
        db = SessionLocal()
        try:
            today = datetime.utcnow().date()
            
            # Check for donations in 3 days and 1 day
            reminder_dates = [
                today + timedelta(days=3),
                today + timedelta(days=1)
            ]
            
            for reminder_date in reminder_dates:
                days_until = (reminder_date - today).days
                
                # Get scheduled donations for this date
                schedules = db.query(DonorHistory).join(User).filter(
                    DonorHistory.tanggal_donor >= datetime.combine(reminder_date, datetime.min.time()),
                    DonorHistory.tanggal_donor < datetime.combine(reminder_date + timedelta(days=1), datetime.min.time())
                ).all()
                
                if not schedules:
                    continue
                
                print(f"📅 Found {len(schedules)} donations scheduled in {days_until} days")
                
                for schedule in schedules:
                    # Get donor information
                    donor = db.query(User).filter(User.id == schedule.pendonor_id).first()
                    
                    if not donor or not donor.email:
                        continue
                    
                    # Format date in Indonesian
                    months_id = {
                        1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
                        5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
                        9: "September", 10: "Oktober", 11: "November", 12: "Desember"
                    }
                    
                    donation_date = schedule.tanggal_donor
                    formatted_date = f"{donation_date.day} {months_id[donation_date.month]} {donation_date.year}"
                    
                    # Generate AI content
                    ai_content = await ai_service.generate_donation_reminder(
                        donor_name=donor.nama,
                        blood_type=donor.gol_darah.value if donor.gol_darah else "Unknown",
                        donation_date=formatted_date,
                        location=schedule.lokasi,
                        days_until=days_until
                    )
                    
                    # Send reminder
                    success = await email_service.send_donation_reminder(
                        donor_email=donor.email,
                        donor_name=donor.nama,
                        ai_content=ai_content
                    )
                    
                    if success:
                        print(f"✅ Reminder sent to {donor.nama} ({donor.email})")
                    else:
                        print(f"❌ Failed to send reminder to {donor.email}")
                    
                    # Delay between emails
                    await asyncio.sleep(1)
        
        except Exception as e:
            print(f"❌ Error sending donation reminders: {str(e)}")
        finally:
            db.close()
    
    async def send_weekly_summary(self):
        """
        Send weekly summary to admins every Monday
        """
        print("📊 Generating weekly summary...")
        
        db = SessionLocal()
        try:
            # Get admin emails
            admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
            admin_emails = [admin.email for admin in admins if admin.email]
            
            if not admin_emails:
                return
            
            # Get statistics for last week
            week_ago = datetime.utcnow() - timedelta(days=7)
            
            # Count donations last week
            donations_last_week = db.query(DonorHistory).filter(
                DonorHistory.tanggal_donor >= week_ago
            ).count()
            
            # Get current stock status
            critical_stocks = db.query(BloodStock).filter(
                BloodStock.status == StockStatus.KRITIS
            ).count()
            
            low_stocks = db.query(BloodStock).filter(
                BloodStock.status == StockStatus.MENIPIS
            ).count()
            
            # Count upcoming donations this week
            next_week = datetime.utcnow() + timedelta(days=7)
            upcoming_donations = db.query(DonorHistory).filter(
                DonorHistory.tanggal_donor >= datetime.utcnow(),
                DonorHistory.tanggal_donor <= next_week
            ).count()
            
            # Generate email content
            subject = f"📊 Ringkasan Mingguan - {datetime.utcnow().strftime('%d %B %Y')}"
            
            body = f"""
Ringkasan Mingguan Sistem Donor Darah
RS Sentra Medika Minahasa Utara

📈 Statistik Minggu Lalu ({week_ago.strftime('%d/%m')} - {datetime.utcnow().strftime('%d/%m')}):
• Total Donasi: {donations_last_week} donor
• Stok Kritis: {critical_stocks} golongan darah
• Stok Menipis: {low_stocks} golongan darah

📅 Jadwal Minggu Depan:
• Donor Terjadwal: {upcoming_donations} orang

{'⚠️ PERHATIAN: Ada stok darah yang kritis! Mohon segera ditindaklanjuti.' if critical_stocks > 0 else '✅ Semua stok darah dalam kondisi baik.'}

Terima kasih atas dedikasi Anda dalam mengelola donor darah.

Salam,
Sistem Manajemen Donor Darah
"""
            
            # Send to all admins
            for admin_email in admin_emails:
                await email_service.send_email(
                    to_email=admin_email,
                    subject=subject,
                    body=body
                )
                await asyncio.sleep(1)
            
            print(f"✅ Weekly summary sent to {len(admin_emails)} admins")
        
        except Exception as e:
            print(f"❌ Error sending weekly summary: {str(e)}")
        finally:
            db.close()
    
    async def send_thank_you_after_donation(
        self,
        donor_id: int,
        db: Session
    ):
        """
        Send thank you email after successful donation
        
        Args:
            donor_id: ID of the donor
            db: Database session
        """
        try:
            donor = db.query(User).filter(User.id == donor_id).first()
            
            if not donor or not donor.email:
                return
            
            # Count total donations
            donation_count = db.query(DonorHistory).filter(
                DonorHistory.pendonor_id == donor_id
            ).count()
            
            # Generate AI content
            ai_content = await ai_service.generate_thank_you_message(
                donor_name=donor.nama,
                blood_type=donor.gol_darah.value if donor.gol_darah else "Unknown",
                donation_count=donation_count
            )
            
            # Send email
            success = await email_service.send_thank_you_email(
                donor_email=donor.email,
                donor_name=donor.nama,
                ai_content=ai_content
            )
            
            if success:
                print(f"✅ Thank you email sent to {donor.nama}")
            else:
                print(f"❌ Failed to send thank you email to {donor.email}")
        
        except Exception as e:
            print(f"❌ Error sending thank you email: {str(e)}")

# Create singleton instance
background_service = BackgroundTaskService()