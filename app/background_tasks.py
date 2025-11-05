"""
background_tasks.py
Background Tasks for Automated Notifications
Uses APScheduler for periodic checks with H-1 reminder feature
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import List
import asyncio

from .database import SessionLocal
from .models import User, BloodStock, DonorHistory, UserRole, StockStatus, DonorStatus
from .ai_service import ai_service
from .notification_service import email_service


class BackgroundTaskService:
    """Service for managing background notification tasks"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.last_critical_stocks = set()  # Track which stocks were critical
    
    def start(self):
        """Start the background scheduler"""
        if self.is_running:
            return
        
        # 🚨 NEW: Check CRITICAL blood stock every 1 minute (< 5 bags)
        self.scheduler.add_job(
            self.check_critical_blood_stock,
            IntervalTrigger(minutes=10),  # Every 1 minute
            id='check_critical_blood_stock',
            replace_existing=True
        )
        
        # Check blood stock every 6 hours (general check for low stocks 5-10 bags)
        self.scheduler.add_job(
            self.check_blood_stock,
            CronTrigger(hour='*/6'),  # Every 6 hours
            id='check_blood_stock',
            replace_existing=True
        )
        
        # 🔔 Send donation reminders daily at 9 AM (H-3 and H-1)
        self.scheduler.add_job(
            self.send_donation_reminders,
            CronTrigger(hour=9, minute=0),  # Daily at 9:00 AM
            id='donation_reminders',
            replace_existing=True
            
            # just testing for every 1 minute
            # self.send_donation_reminders,
            # IntervalTrigger(minutes=1),  # Every 1 minute
            # id='donation_reminders',
            # replace_existing=True
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
        print("🚨 CRITICAL stock alert: Running every 1 minute for stocks < 5 bags")
        print("🔔 Donation reminders: Daily at 9:00 AM (H-3 and H-1)")
    
    def stop(self):
        """Stop the background scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            print("⏹️ Background task scheduler stopped")
    
    async def check_critical_blood_stock(self):
        """
        🚨 CRITICAL ALERT: Check blood stock < 5 bags every 1 minute
        Sends immediate email notification to all admins
        """
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n{'='*60}")
        print(f"🚨 [{current_time}] CRITICAL STOCK CHECK - Running every 1 minute")
        print(f"{'='*60}")
        
        db = SessionLocal()
        try:
            # Get all blood stocks with < 5 bags (CRITICAL)
            critical_stocks = db.query(BloodStock).filter(
                BloodStock.jumlah_kantong < 5
            ).all()
            
            if not critical_stocks:
                print("✅ No critical stock detected (all stocks >= 5 bags)")
                print(f"{'='*60}\n")
                # Clear tracking if no critical stocks
                self.last_critical_stocks.clear()
                return
            
            # Get admin emails
            admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
            admin_emails = [admin.email for admin in admins if admin.email]
            
            if not admin_emails:
                print("⚠️ No admin emails found for notification")
                print(f"{'='*60}\n")
                return
            
            print(f"📧 Admin emails found: {', '.join(admin_emails)}")
            print(f"\n🚨 CRITICAL STOCKS DETECTED ({len(critical_stocks)} types):")
            print(f"{'-'*60}")
            
            # Track current critical stocks
            current_critical = set()
            
            # Send alert for each critical stock
            for stock in critical_stocks:
                blood_type_key = stock.gol_darah.value
                current_critical.add(blood_type_key)
                
                # Console debug info
                print(f"🩸 Blood Type: {stock.gol_darah.value}")
                print(f"   📦 Current Stock: {stock.jumlah_kantong} bags")
                print(f"   ⚠️  Status: {stock.status.value}")
                print(f"   🕐 Last Update: {stock.terakhir_update}")
                
                # Check if this is a new critical stock or ongoing
                is_new = blood_type_key not in self.last_critical_stocks
                alert_type = "🆕 NEW CRITICAL ALERT" if is_new else "⚠️  ONGOING CRITICAL"
                
                print(f"   🔔 Alert Type: {alert_type}")
                
                # Generate AI content
                try:
                    ai_content = await ai_service.generate_low_stock_alert(
                        blood_type=stock.gol_darah.value,
                        current_stock=stock.jumlah_kantong,
                        status="KRITIS"
                    )
                    print(f"   ✅ AI content generated")
                except Exception as ai_error:
                    print(f"   ⚠️  AI generation failed: {ai_error}")
                    ai_content = {
                        "subject": f"🚨 CRITICAL: Stok Darah {stock.gol_darah.value} < 5 Kantong!",
                        "body": f"Stok darah {stock.gol_darah.value} KRITIS: {stock.jumlah_kantong} kantong"
                    }
                
                # Enhance subject with critical indicator
                ai_content["subject"] = f"🚨 CRITICAL ({stock.jumlah_kantong} bags): {ai_content['subject']}"
                
                # Send email to all admins
                try:
                    success = await email_service.send_low_stock_alert(
                        admin_emails=admin_emails,
                        blood_type=stock.gol_darah.value,
                        current_stock=stock.jumlah_kantong,
                        status="KRITIS",
                        ai_content=ai_content
                    )
                    
                    if success:
                        print(f"   ✅ Critical alert email SENT to {len(admin_emails)} admin(s)")
                    else:
                        print(f"   ❌ Failed to send critical alert email")
                except Exception as email_error:
                    print(f"   ❌ Email error: {email_error}")
                
                print(f"{'-'*60}")
                
                # Small delay between emails
                await asyncio.sleep(0.5)
            
            # Update tracking
            self.last_critical_stocks = current_critical
            
            print(f"\n📊 Summary:")
            print(f"   Total Critical Stocks: {len(critical_stocks)}")
            print(f"   Admin Notified: {len(admin_emails)}")
            print(f"   Next Check: In 1 minute")
            print(f"{'='*60}\n")
        
        except Exception as e:
            print(f"❌ Error in critical stock check: {str(e)}")
            print(f"{'='*60}\n")
        finally:
            db.close()
    
    async def check_blood_stock(self):
        """
        Check blood stock levels and send alerts for low/critical stock
        This runs every 6 hours for general monitoring (5-10 bags)
        """
        print("🔍 Checking blood stock levels (6-hour check)...")
        
        db = SessionLocal()
        try:
            # Get all blood stocks that are low or critical (5-10 bags)
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
        🔔 Send reminders to donors with upcoming appointments
        Sends reminders 3 days before and 1 day before donation
        Enhanced with reminder tracking to prevent duplicate sends
        """
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n{'='*60}")
        print(f"📧 [{current_time}] DONATION REMINDER CHECK - Running daily at 9 AM")
        print(f"{'='*60}")
        
        db = SessionLocal()
        try:
            today = datetime.utcnow().date()
            
            # Check for donations in 3 days and 1 day
            reminder_configs = [
                {"days": 3, "flag": 1, "label": "H-3"},
                {"days": 1, "flag": 2, "label": "H-1"}  # 🔔 H-1 REMINDER
            ]
            
            total_sent = 0
            
            for config in reminder_configs:
                days_until = config["days"]
                reminder_flag = config["flag"]
                label = config["label"]
                
                reminder_date = today + timedelta(days=days_until)
                
                # Get scheduled donations for this date that haven't received this reminder yet
                schedules = db.query(DonorHistory).join(User).filter(
                    DonorHistory.tanggal_donor >= datetime.combine(reminder_date, datetime.min.time()),
                    DonorHistory.tanggal_donor < datetime.combine(reminder_date + timedelta(days=1), datetime.min.time()),
                    DonorHistory.status == DonorStatus.SIAP_DONOR,  # Only send to confirmed donors
                    # Check if this specific reminder hasn't been sent (using bitwise check)
                    ~DonorHistory.reminder_sent.op('&')(reminder_flag).cast(Integer).is_(reminder_flag)
                ).all()
                
                if not schedules:
                    print(f"✅ No {label} reminders needed for {reminder_date}")
                    continue
                
                print(f"\n📅 {label} REMINDERS: Found {len(schedules)} donations on {reminder_date}")
                print(f"{'-'*60}")
                
                for schedule in schedules:
                    # Get donor information
                    donor = db.query(User).filter(User.id == schedule.pendonor_id).first()
                    
                    if not donor or not donor.email:
                        print(f"⚠️  Skipped: No email for donor ID {schedule.pendonor_id}")
                        continue
                    
                    # Format date in Indonesian
                    months_id = {
                        1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
                        5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
                        9: "September", 10: "Oktober", 11: "November", 12: "Desember"
                    }
                    
                    donation_date = schedule.tanggal_donor
                    formatted_date = f"{donation_date.day} {months_id[donation_date.month]} {donation_date.year}"
                    formatted_time = donation_date.strftime("%H:%M")
                    
                    print(f"\n🩸 Donor: {donor.nama}")
                    print(f"   📧 Email: {donor.email}")
                    print(f"   📅 Date: {formatted_date} {formatted_time}")
                    print(f"   🏥 Location: {schedule.lokasi}")
                    print(f"   ⏰ Reminder: {label} ({days_until} days)")
                    
                    # Generate AI content with specific H-1 emphasis if needed
                    try:
                        ai_content = await ai_service.generate_donation_reminder(
                            donor_name=donor.nama,
                            blood_type=donor.gol_darah.value if donor.gol_darah else "Unknown",
                            donation_date=formatted_date,
                            location=schedule.lokasi,
                            days_until=days_until
                        )
                        
                        # Add urgency for H-1 reminders
                        if days_until == 1:
                            ai_content["subject"] = f"🔔 BESOK! {ai_content['subject']}"
                        
                        print(f"   ✅ AI content generated")
                    except Exception as ai_error:
                        print(f"   ⚠️  AI generation failed: {ai_error}")
                        # Fallback content
                        if days_until == 1:
                            ai_content = {
                                "subject": f"🔔 BESOK: Pengingat Donor Darah - {formatted_date}",
                                "body": f"Halo {donor.nama},\n\nIni pengingat bahwa Anda memiliki jadwal donor darah BESOK:\n📅 {formatted_date}\n📍 {schedule.lokasi}\n\nJangan lupa!"
                            }
                        else:
                            ai_content = {
                                "subject": f"📅 Pengingat Donor Darah - {formatted_date}",
                                "body": f"Halo {donor.nama},\n\nAnda memiliki jadwal donor darah dalam {days_until} hari:\n📅 {formatted_date}\n📍 {schedule.lokasi}"
                            }
                    
                    # Send reminder
                    try:
                        success = await email_service.send_donation_reminder(
                            donor_email=donor.email,
                            donor_name=donor.nama,
                            ai_content=ai_content
                        )
                        
                        if success:
                            # Update reminder_sent flag using bitwise OR
                            schedule.reminder_sent = schedule.reminder_sent | reminder_flag
                            db.commit()
                            print(f"   ✅ {label} reminder sent successfully")
                            total_sent += 1
                        else:
                            print(f"   ❌ Failed to send reminder")
                    except Exception as email_error:
                        print(f"   ❌ Email error: {email_error}")
                    
                    # Delay between emails
                    await asyncio.sleep(1)
                
                print(f"{'-'*60}")
            
            print(f"\n📊 Summary:")
            print(f"   Total Reminders Sent: {total_sent}")
            print(f"   Next Check: Tomorrow at 9:00 AM")
            print(f"{'='*60}\n")
        
        except Exception as e:
            print(f"❌ Error sending donation reminders: {str(e)}")
            print(f"{'='*60}\n")
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
    
    async def send_immediate_h1_reminder(
        self,
        donor_id: int = None
    ):
        """
        🔔 MANUAL TRIGGER: Send H-1 reminder immediately
        Can be called from API endpoint or admin panel
        
        Args:
            donor_id: Optional specific donor ID, if None sends to all tomorrow's donors
        """
        print(f"\n{'='*60}")
        print(f"🔔 MANUAL H-1 REMINDER TRIGGER")
        print(f"{'='*60}")
        
        db = SessionLocal()
        try:
            tomorrow = datetime.utcnow().date() + timedelta(days=1)
            
            # Query for tomorrow's donations
            query = db.query(DonorHistory).join(User).filter(
                DonorHistory.tanggal_donor >= datetime.combine(tomorrow, datetime.min.time()),
                DonorHistory.tanggal_donor < datetime.combine(tomorrow + timedelta(days=1), datetime.min.time()),
                DonorHistory.status == DonorStatus.SIAP_DONOR
            )
            
            # Filter by specific donor if provided
            if donor_id:
                query = query.filter(DonorHistory.pendonor_id == donor_id)
            
            schedules = query.all()
            
            if not schedules:
                print("✅ No donations scheduled for tomorrow")
                print(f"{'='*60}\n")
                return {"sent": 0, "failed": 0, "message": "No donations tomorrow"}
            
            print(f"📧 Sending H-1 reminders to {len(schedules)} donor(s)")
            
            sent = 0
            failed = 0
            
            for schedule in schedules:
                donor = db.query(User).filter(User.id == schedule.pendonor_id).first()
                
                if not donor or not donor.email:
                    failed += 1
                    continue
                
                # Format date
                months_id = {
                    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
                    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
                    9: "September", 10: "Oktober", 11: "November", 12: "Desember"
                }
                
                donation_date = schedule.tanggal_donor
                formatted_date = f"{donation_date.day} {months_id[donation_date.month]} {donation_date.year}"
                
                # Generate urgent H-1 content
                ai_content = await ai_service.generate_donation_reminder(
                    donor_name=donor.nama,
                    blood_type=donor.gol_darah.value if donor.gol_darah else "Unknown",
                    donation_date=formatted_date,
                    location=schedule.lokasi,
                    days_until=1
                )
                
                ai_content["subject"] = f"🔔 BESOK! {ai_content['subject']}"
                
                # Send
                success = await email_service.send_donation_reminder(
                    donor_email=donor.email,
                    donor_name=donor.nama,
                    ai_content=ai_content
                )
                
                if success:
                    # Mark as sent
                    schedule.reminder_sent = schedule.reminder_sent | 2  # Set H-1 flag
                    db.commit()
                    sent += 1
                    print(f"✅ Sent to {donor.nama}")
                else:
                    failed += 1
                    print(f"❌ Failed: {donor.nama}")
                
                await asyncio.sleep(0.5)
            
            print(f"\n📊 Summary: {sent} sent, {failed} failed")
            print(f"{'='*60}\n")
            
            return {
                "sent": sent,
                "failed": failed,
                "message": f"H-1 reminders sent to {sent} donor(s)"
            }
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return {"sent": 0, "failed": 0, "error": str(e)}
        finally:
            db.close()

# Create singleton instance
background_service = BackgroundTaskService()