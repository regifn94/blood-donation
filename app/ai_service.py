"""
ai_service.py
Google Gemini AI Integration for Email Content Generation
"""

import os
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class AIService:
    """Service for AI-powered content generation using Gemini"""
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-pro')
    
    async def generate_low_stock_alert(
        self, 
        blood_type: str, 
        current_stock: int,
        status: str
    ) -> dict:
        """
        Generate email content for low blood stock alert
        
        Args:
            blood_type: Blood type that is running low
            current_stock: Current number of blood bags
            status: Stock status (Menipis/Kritis)
            
        Returns:
            dict: Email subject and body
        """
        prompt = f"""
Buatkan email notifikasi untuk admin rumah sakit tentang stok darah yang {status.lower()}.

Detail:
- Golongan Darah: {blood_type}
- Stok Saat Ini: {current_stock} kantong
- Status: {status}

Email harus:
1. Profesional dan urgent
2. Dalam Bahasa Indonesia
3. Menyertakan call-to-action untuk menghubungi donor
4. Ramah namun tegas
5. Maksimal 200 kata

Format output:
SUBJECT: [tulis subject email]
BODY: [tulis isi email]
"""
        
        try:
            response = self.model.generate_content(prompt)
            content = response.text
            
            # Parse response
            lines = content.strip().split('\n')
            subject = ""
            body = ""
            
            for i, line in enumerate(lines):
                if line.startswith("SUBJECT:"):
                    subject = line.replace("SUBJECT:", "").strip()
                elif line.startswith("BODY:"):
                    body = '\n'.join(lines[i+1:]).strip()
                    break
            
            # Fallback if parsing fails
            if not subject or not body:
                subject = f"⚠️ URGENT: Stok Darah {blood_type} {status}!"
                body = content
            
            return {
                "subject": subject,
                "body": body
            }
            
        except Exception as e:
            # Fallback to template if AI fails
            return self._fallback_low_stock_template(blood_type, current_stock, status)
    
    async def generate_donation_reminder(
        self,
        donor_name: str,
        blood_type: str,
        donation_date: str,
        location: str,
        days_until: int
    ) -> dict:
        """
        Generate email reminder for upcoming donation
        Enhanced with H-1 urgency detection
        
        Args:
            donor_name: Name of the donor
            blood_type: Blood type of donor
            donation_date: Scheduled donation date
            location: Donation location
            days_until: Days until donation
            
        Returns:
            dict: Email subject and body
        """
        # Add urgency context for H-1 reminders
        urgency_note = ""
        if days_until == 1:
            urgency_note = "\nINI ADALAH PENGINGAT H-1 (BESOK)! Gunakan tone yang lebih urgent dan personal."
        
        prompt = f"""
Buatkan email pengingat donor darah untuk pendonor yang akan mendonor dalam {days_until} hari.{urgency_note}

Detail:
- Nama Pendonor: {donor_name}
- Golongan Darah: {blood_type}
- Tanggal Donor: {donation_date}
- Lokasi: {location}

Email harus:
1. {"SANGAT urgent, personal, dan mengingatkan BESOK adalah hari H" if days_until == 1 else "Ramah dan menghargai kontribusi pendonor"}
2. Dalam Bahasa Indonesia
3. Menyertakan {"checklist persiapan malam ini dan besok pagi" if days_until == 1 else "tips persiapan sebelum donor"}
4. Informasi kontak jika perlu reschedule
5. {"Reminder: bawa KTP, makan bergizi malam ini, tidur cukup" if days_until == 1 else "Motivasi tentang pentingnya donor darah"}
6. Maksimal 250 kata

Format output:
SUBJECT: [tulis subject email]
BODY: [tulis isi email]
"""
        
        try:
            response = self.model.generate_content(prompt)
            content = response.text
            
            # Parse response
            lines = content.strip().split('\n')
            subject = ""
            body = ""
            
            for i, line in enumerate(lines):
                if line.startswith("SUBJECT:"):
                    subject = line.replace("SUBJECT:", "").strip()
                elif line.startswith("BODY:"):
                    body = '\n'.join(lines[i+1:]).strip()
                    break
            
            # Fallback if parsing fails
            if not subject or not body:
                subject = f"{'🔔 BESOK! ' if days_until == 1 else ''}🩸 Pengingat: Jadwal Donor Darah - {donation_date}"
                body = content
            
            return {
                "subject": subject,
                "body": body
            }
            
        except Exception as e:
            # Fallback to template if AI fails
            return self._fallback_reminder_template(
                donor_name, blood_type, donation_date, location, days_until
            )
    
    async def generate_thank_you_message(
        self,
        donor_name: str,
        blood_type: str,
        donation_count: int
    ) -> dict:
        """
        Generate thank you message after donation
        
        Args:
            donor_name: Name of the donor
            blood_type: Blood type donated
            donation_count: Total number of donations by this donor
            
        Returns:
            dict: Email subject and body
        """
        prompt = f"""
Buatkan email terima kasih setelah donor darah berhasil dilakukan.

Detail:
- Nama Pendonor: {donor_name}
- Golongan Darah: {blood_type}
- Total Donasi: {donation_count} kali

Email harus:
1. Sangat menghargai dan warm
2. Dalam Bahasa Indonesia
3. Menyebutkan dampak positif dari donor darah
4. Informasi kapan bisa donor lagi (3 bulan)
5. Ajakan untuk terus menjadi pendonor rutin
6. Maksimal 200 kata

Format output:
SUBJECT: [tulis subject email]
BODY: [tulis isi email]
"""
        
        try:
            response = self.model.generate_content(prompt)
            content = response.text
            
            # Parse response
            lines = content.strip().split('\n')
            subject = ""
            body = ""
            
            for i, line in enumerate(lines):
                if line.startswith("SUBJECT:"):
                    subject = line.replace("SUBJECT:", "").strip()
                elif line.startswith("BODY:"):
                    body = '\n'.join(lines[i+1:]).strip()
                    break
            
            if not subject or not body:
                subject = f"💝 Terima Kasih {donor_name}!"
                body = content
            
            return {
                "subject": subject,
                "body": body
            }
            
        except Exception as e:
            return self._fallback_thank_you_template(donor_name, blood_type, donation_count)
    
    def _fallback_low_stock_template(
        self, 
        blood_type: str, 
        current_stock: int, 
        status: str
    ) -> dict:
        """Fallback template if AI generation fails"""
        return {
            "subject": f"⚠️ URGENT: Stok Darah {blood_type} {status}!",
            "body": f"""
Kepada Admin RS Sentra Medika,

Kami informasikan bahwa stok darah golongan {blood_type} saat ini dalam kondisi {status.upper()}.

Detail Stok:
• Golongan Darah: {blood_type}
• Jumlah Kantong: {current_stock}
• Status: {status}

Tindakan yang diperlukan:
1. Segera hubungi pendonor aktif golongan {blood_type}
2. Koordinasi dengan PMI untuk penambahan stok
3. Update status ke semua unit terkait

Mohon segera ditindaklanjuti untuk memastikan ketersediaan darah bagi pasien yang membutuhkan.

Terima kasih,
Sistem Manajemen Donor Darah
RS Sentra Medika Minahasa Utara
"""
        }
    
    def _fallback_reminder_template(
        self,
        donor_name: str,
        blood_type: str,
        donation_date: str,
        location: str,
        days_until: int
    ) -> dict:
        """Fallback template for donation reminder with H-1 urgency"""
        
        if days_until == 1:
            # H-1 URGENT TEMPLATE
            return {
                "subject": f"🔔 BESOK! Pengingat Donor Darah Anda - {donation_date}",
                "body": f"""
Halo {donor_name},

🚨 PENGINGAT PENTING: Donor darah Anda dijadwalkan BESOK!

Detail Jadwal:
📅 Tanggal: {donation_date} (BESOK!)
📍 Lokasi: {location}
🩸 Golongan Darah: {blood_type}
⏰ Waktu: 08:00 - 14:00 WIB

✅ CHECKLIST PERSIAPAN MALAM INI:
□ Makan malam bergizi (sayur, protein, karbohidrat)
□ Minum air putih minimal 2 liter
□ Tidur cukup (minimal 6-7 jam)
□ Hindari makanan berlemak tinggi
□ Siapkan KTP/identitas

✅ CHECKLIST BESOK PAGI:
□ Sarapan bergizi (wajib!)
□ Minum air putih 2-3 gelas
□ Bawa KTP/identitas
□ Kenakan pakaian nyaman
□ Datang tepat waktu

❗ PENTING:
• Jika kondisi tidak fit/sakit, SEGERA hubungi kami
• Jika berhalangan, reschedule minimal H-1
• Jangan lupa sarapan - ini WAJIB sebelum donor!

💪 Kontribusi Anda = Nyawa Terselamatkan
Satu kantong darah = hingga 3 nyawa!

Terima kasih atas komitmen Anda sebagai pahlawan tanpa tanda jasa.

Salam sehat,
Tim RS Sentra Medika Minahasa Utara
📞 Kontak Darurat: (0431) 123456
📧 Email: donor@rssentralmedika.id

PS: Kami tunggu BESOK ya! 🩸❤️
"""
            }
        else:
            # REGULAR H-3 TEMPLATE
            return {
                "subject": f"🩸 Pengingat: Jadwal Donor Darah {days_until} Hari Lagi",
                "body": f"""
Halo {donor_name},

Terima kasih telah mendaftar sebagai pendonor darah di RS Sentra Medika!

Detail Jadwal Donor Anda:
📅 Tanggal: {donation_date}
📍 Lokasi: {location}
🩸 Golongan Darah: {blood_type}
⏰ Waktu: 08:00 - 14:00 WIB

Persiapan Sebelum Donor:
✓ Istirahat cukup (minimal 5 jam)
✓ Makan makanan bergizi
✓ Minum air putih yang cukup
✓ Hindari makanan berlemak
✓ Bawa KTP/identitas

Kontribusi Anda sangat berarti untuk menyelamatkan nyawa!

Jika berhalangan hadir, mohon informasikan kami minimal 1 hari sebelumnya.

Salam sehat,
Tim RS Sentra Medika Minahasa Utara
📞 Kontak: (0431) 123456
"""
            }
    
    def _fallback_thank_you_template(
        self,
        donor_name: str,
        blood_type: str,
        donation_count: int
    ) -> dict:
        """Fallback template for thank you message"""
        return {
            "subject": f"💝 Terima Kasih, Pahlawan Tanpa Tanda Jasa!",
            "body": f"""
Kepada Yth. {donor_name},

Terima kasih atas donasi darah Anda! Ini adalah donasi ke-{donation_count} Anda.

Detail Donasi:
🩸 Golongan Darah: {blood_type}
📊 Total Donasi: {donation_count} kali
🏆 Status: Pendonor Aktif

Tahukah Anda?
Satu kantong darah dapat menyelamatkan hingga 3 nyawa! Kontribusi Anda sangat berarti.

Informasi Penting:
• Anda dapat donor kembali 3 bulan dari sekarang
• Kami akan mengirimkan pengingat saat Anda sudah eligible
• Jaga kesehatan dan pola makan yang baik

Tips Setelah Donor:
✓ Istirahat 10-15 menit
✓ Minum banyak air putih
✓ Hindari aktivitas berat 24 jam
✓ Konsumsi makanan bergizi

Sekali lagi, terima kasih atas kebaikan Anda!

Hormat kami,
RS Sentra Medika Minahasa Utara
"""
        }

# Create singleton instance
ai_service = AIService()