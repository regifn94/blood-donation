"""
AI Service - Google Gemini Integration
Generates email content for notifications
"""

import os # untuk akses variabel lingkungan (.env)
from typing import Optional # untuk mendefinisikan parameter opsional di fungsi
import google.generativeai as genai # library google gemini API
from dotenv import load_dotenv # untuk membaca file .env

load_dotenv() # memuat variabel dari file .env

# Configure Gemini API dengan key dari env variabel
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class AIService:
    """Service for AI-powered content generation using Gemini"""
    # kelas utama yang mengatur semua fungsi pembuatan email otomatis
    
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)

        print("\n=== LIST MODEL GEMINI YANG TERSEDIA ===")
        for m in genai.list_models():
            print("-", m.name)
        print("========================================\n")
        # inisialisasi model AI yang digunakan
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')

    async def generate_schedule_confirmation(
        self,
        donor_name: str,
        blood_type: str,
        donation_date: str,
        location: str,
        notes: Optional[str] = None
    ) -> dict:
        """
        Generate email confirmation when donor creates a new schedule
        
        Args:
            donor_name: Name of the donor
            blood_type: Blood type of donor
            donation_date: Scheduled donation date
            location: Donation location
            notes: Optional notes from donor
            
        Returns:
            dict: Email subject and body
        """
        # menyusun konteks tambahan jika ada catatan dari pendonor
        notes_context = f"\nCatatan dari pendonor: {notes}" if notes else ""
        
        prompt = f"""
            Buatkan email konfirmasi jadwal donor darah yang baru saja dibuat oleh pendonor.

            Detail:
            - Nama Pendonor: {donor_name}
            - Golongan Darah: {blood_type}
            - Tanggal Donor: {donation_date}
            - Lokasi: {location}{notes_context}

            Email harus:
            1. Mengonfirmasi bahwa jadwal telah berhasil dibuat
            2. Dalam Bahasa Indonesia yang ramah dan profesional
            3. Menyertakan detail lengkap jadwal (tanggal, waktu, lokasi)
            4. Memberikan tips persiapan singkat sebelum donor
            5. Menyertakan informasi kontak untuk reschedule/pertanyaan
            6. Mengingatkan untuk membawa KTP/identitas
            7. Memberikan motivasi tentang pentingnya donor darah
            8. Maksimal 250 kata

            Format output:
            SUBJECT: [tulis subject email]
            BODY: [tulis isi email]
            """
        
        try:
            # memanggil model AI untuk membuat isi email
            response = self.model.generate_content(prompt)
            content = response.text
            
            # memisahkan baris agar mudah di parse
            lines = content.strip().split('\n')
            subject = ""
            body = ""
            
            # mendeteksi baris subjek dan body dari hasil AI
            for i, line in enumerate(lines):
                if line.startswith("SUBJECT:"):
                    subject = line.replace("SUBJECT:", "").strip()
                elif line.startswith("BODY:"):
                    body = '\n'.join(lines[i+1:]).strip()
                    break
            
            # jiaka parsing gagal, gunakan default subjek dan isi
            if not subject or not body:
                subject = f"✅ Konfirmasi Jadwal Donor Darah - {donation_date}"
                body = content
            
            # mengembalikan hasil dalam bentuk dictionary
            return {
                "subject": subject,
                "body": body
            }
            
        except Exception as e:
            print("❌ ERROR DI AI generate_schedule_confirmation:", str(e))
            return self._fallback_schedule_confirmation_template(donor_name, blood_type, donation_date, location, notes)
    
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
1. Profesional dan urgent juga tujuannya untuk admin bank darah
2. Dalam Bahasa Indonesia
3. Menyertakan call-to-action untuk menghubungi donor
4. Ramah namun tegas
5. Departemen Bank Darah Rumah Sakit Sentra Medika
5. Maksimal 200 kata

Format output:
SUBJECT: [tulis subject email]
BODY: [tulis isi email]
"""
        
        try:
            # memanggil AI untuk membuat isi email
            response = self.model.generate_content(prompt)
            content = response.text
            
            # Parse response (parsing hasil output AI)
            lines = content.strip().split('\n')
            subject = ""
            body = ""
            
            #cari bagian subjek dan body
            for i, line in enumerate(lines):
                if line.startswith("SUBJECT:"):
                    subject = line.replace("SUBJECT:", "").strip()
                elif line.startswith("BODY:"):
                    body = '\n'.join(lines[i+1:]).strip()
                    break
            
            # Use Fallback if parsing fails
            if not subject or not body:
                subject = f"⚠️ URGENT: Stok Darah {blood_type} {status}!"
                body = content
            
            # kembalikan hasil akhir
            return {
                "subject": subject,
                "body": body
            }
            
        except Exception as e:
            # Fallback to template if AI fails (gunkan tempalate manual jika AI gagal)
            return self._fallback_low_stock_template(blood_type, current_stock, status)
        
    async def generate_approved_blood_request(
        self,
        requester_name: str,
        blood_type: str,
        quantity: int,
        request_number: str
    ) -> dict:
        """
        Generate email content for approved blood request

        Args:
            requester_name: Name of the blood requester
            blood_type: Requested blood type
            quantity: Total bags approved
            request_number: Request unique number

        Returns:
            dict: Email subject and body
        """ 
        prompt = f"""
Buatkan email pemberitahuan kepada pemohon bahwa permintaan darah mereka telah DISETUJUI.

Detail:
- Nama Pemohon: {requester_name}
- Golongan Darah: {blood_type}
- Jumlah: {quantity} kantong
- Nomor Permintaan: {request_number}

Email harus:
1. Bahasa Indonesia, profesional namun ramah
2. Berterima kasih kepada pemohon
3. Menjelaskan bahwa permintaan sudah disetujui & akan segera diproses dan kami akan menghubungi anda
4. Tidak lebih dari 180 kata

Format output:
SUBJECT: [isi subject email]
BODY: [isi body email]
"""
        
        try:
            # memanggil AI untuk membuat isi email
            response = self.model.generate_content(prompt)
            content = response.text
            
            # Parse response
            lines = content.strip().split('\n')
            subject = ""
            body = ""
            
            # ambil bagian subjek dan body
            for i, line in enumerate(lines):
                if line.startswith("SUBJECT:"):
                    subject = line.replace("SUBJECT:", "").strip()
                elif line.startswith("BODY:"):
                    body = '\n'.join(lines[i+1:]).strip()
                    break
            
            # Use Fallback if parsing fails
            if not subject or not body:
                subject = f"✅ 🩸 Permohonan Darah Disetujui"
                body = content
            
            # kembalikan hasil akhir
            return {
                "subject": subject,
                "body": body
            }
        except Exception as e:
            return self._fallback_approved_blood_request_template(requester_name, blood_type, quantity, request_number)
    
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
        
        Args:
            donor_name: Name of the donor
            blood_type: Blood type of donor
            donation_date: Scheduled donation date
            location: Donation location
            days_until: Days until donation
            
        Returns:
            dict: Email subject and body
        """
        prompt = f"""
Buatkan email pengingat donor darah untuk pendonor yang akan mendonor dalam {days_until} hari.

Detail:
- Nama Pendonor: {donor_name}
- Golongan Darah: {blood_type}
- Tanggal Donor: {donation_date}
- Lokasi: {location}

Email harus:
1. Ramah dan menghargai kontribusi pendonor
2. Dalam Bahasa Indonesia
3. Menyertakan tips persiapan sebelum donor
4. Informasi kontak jika perlu reschedule
5. Motivasi tentang pentingnya donor darah
6. Nomor yang akan di hubungi harus nomor yang sesuai dengan RS Sentra Medika: phone
(0431) 7291 899 & WhatsApp 08119999995
7. Maksimal 250 kata

Format output:
SUBJECT: [tulis subject email]
BODY: [tulis isi email]
"""
        
        try:
            # memanggil AI untuk membuat isi email
            response = self.model.generate_content(prompt)
            content = response.text
            
            # Parse response
            lines = content.strip().split('\n')
            subject = ""
            body = ""
            
            # ambil bagian subjek dan body
            for i, line in enumerate(lines):
                if line.startswith("SUBJECT:"):
                    subject = line.replace("SUBJECT:", "").strip()
                elif line.startswith("BODY:"):
                    body = '\n'.join(lines[i+1:]).strip()
                    break
            
            # Use Fallback if parsing fails
            if not subject or not body:
                subject = f"🩸 Pengingat: Jadwal Donor Darah - {donation_date}"
                body = content
            
            # kembalikan hasil akhir
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
            # memanggil AI untuk membuat email
            response = self.model.generate_content(prompt)
            content = response.text
            
            # Parse response
            lines = content.strip().split('\n')
            subject = ""
            body = ""
            
            # ambil bagian subjek dan body
            for i, line in enumerate(lines):
                if line.startswith("SUBJECT:"):
                    subject = line.replace("SUBJECT:", "").strip()
                elif line.startswith("BODY:"):
                    body = '\n'.join(lines[i+1:]).strip()
                    break
            
            # Use Fallback if parsing fails
            if not subject or not body:
                subject = f"💝 Terima Kasih {donor_name}!"
                body = content
            
            return {
                "subject": subject,
                "body": body
            }
            
        except Exception as e:
            # gunakan template manual jika AI gagal
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
    
    def _fallback_schedule_confirmation_template(
        self,
        donor_name: str,
        blood_type: str,
        donation_date: str,
        location: str,
        notes: Optional[str] = None
    ) -> dict:
        return {
            "subject": f"✅ Konfirmasi Jadwal Donor Darah - {donation_date}",
            "body": f"""
Halo {donor_name},

Jadwal donor darah Anda telah berhasil dibuat.

Detail Jadwal:
📅 Tanggal: {donation_date}
📍 Lokasi: {location}
🩸 Golongan Darah: {blood_type}
{f"📝 Catatan: {notes}" if notes else ""}

Terima kasih atas kontribusi Anda dalam membantu sesama.

Salam,
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
        """Fallback template for donation reminder"""
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
    
    def _fallback_approved_blood_request_template(
        self,
        requester_name: str,
        blood_type: str,
        quantity: int,
        request_number: str
    ) -> dict:
        """Fallback template untuk email konfirmasi bahwa permintaan darah disetujui"""
        return {
        "subject": f"🩸 Permintaan Darah Anda Telah Disetujui",
        "body": f"""
Kepada Yth. {requester_name},

Permintaan darah **{requester_name}** telah *disetujui* dan sedang diproses oleh tim Bank Darah RS Sentra Medika Minahasa Utara.

Detail Permintaan:
🩸 Golongan Darah : {blood_type}
📦 Jumlah          : {quantity} kantong
📌 Status          : Disetujui & Diproses

Kami akan segera menyiapkan kantong darah sesuai permintaan Anda.  
Petugas kami akan menghubungi Anda apabila dibutuhkan informasi tambahan.

Informasi Penting:
• Harap pastikan nomor telepon Anda aktif  
• Bawa identitas saat pengambilan  
• Pengambilan darah hanya dapat dilakukan oleh pihak yang berwenang  

Terima kasih telah menggunakan layanan Bank Darah kami.  
Semoga pasien dapat segera memperoleh perawatan terbaik.

Hormat kami,  
RS Sentra Medika Minahasa Utara
"""
    }  

    async def generate_request_approved_email(
        self,
        pemohon_name: str,
        blood_type: str,
        jumlah_kantong: int,
        keperluan: str,
        catatan_admin: Optional[str] = None
    ) -> dict:
        """
        Generate email notification when blood request is APPROVED
        
        Args:
            pemohon_name: Name of requester
            blood_type: Blood type requested
            jumlah_kantong: Number of blood bags
            keperluan: Purpose/need
            catatan_admin: Optional admin notes
            
        Returns:
            dict: Email subject and body
        """
        admin_notes = f"\n\nCatatan dari Admin:\n{catatan_admin}" if catatan_admin else ""
        
        prompt = f"""
Buatkan email notifikasi PERSETUJUAN permintaan darah yang telah diapprove oleh admin.

Detail Permintaan:
- Nama Pemohon: {pemohon_name}
- Golongan Darah: {blood_type}
- Jumlah Kantong: {jumlah_kantong}
- Keperluan: {keperluan}{admin_notes}

Email harus:
1. Menyampaikan kabar baik bahwa permintaan DISETUJUI
2. Dalam Bahasa Indonesia yang ramah dan profesional
3. Menyertakan detail lengkap permintaan
4. Memberikan instruksi pengambilan darah (lokasi, jam operasional, dokumen)
5. Mengingatkan untuk membawa surat keterangan dokter dan identitas
6. Informasi kontak untuk koordinasi lebih lanjut
7. Batas waktu pengambilan (misalnya dalam 3 hari kerja)
8. Tone positif dan supportif
9. Maksimal 250 kata

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
                subject = f"✅ Permintaan Darah {blood_type} Disetujui"
                body = content
            
            return {
                "subject": subject,
                "body": body
            }
            
        except Exception as e:
            # Fallback to template if AI fails
            return self._fallback_approved_template(
                pemohon_name, blood_type, jumlah_kantong, keperluan, catatan_admin
            )
    
    async def generate_request_rejected_email(
        self,
        pemohon_name: str,
        blood_type: str,
        jumlah_kantong: int,
        keperluan: str,
        catatan_admin: Optional[str] = None
    ) -> dict:
        """
        Generate email notification when blood request is REJECTED
        
        Args:
            pemohon_name: Name of requester
            blood_type: Blood type requested
            jumlah_kantong: Number of blood bags
            keperluan: Purpose/need
            catatan_admin: Optional admin notes (reason for rejection)
            
        Returns:
            dict: Email subject and body
        """
        rejection_reason = f"\n\nAlasan:\n{catatan_admin}" if catatan_admin else "\n\nMohon maaf, saat ini kami tidak dapat memenuhi permintaan Anda."
        
        prompt = f"""
Buatkan email notifikasi PENOLAKAN permintaan darah dengan empati dan profesional.

Detail Permintaan:
- Nama Pemohon: {pemohon_name}
- Golongan Darah: {blood_type}
- Jumlah Kantong: {jumlah_kantong}
- Keperluan: {keperluan}{rejection_reason}

Email harus:
1. Menyampaikan penolakan dengan empati dan penuh pengertian
2. Dalam Bahasa Indonesia yang sopan dan profesional
3. Menjelaskan alasan penolakan (jika ada catatan admin)
4. Menawarkan alternatif solusi (hubungi PMI, RS lain)
5. Memberikan informasi kontak untuk diskusi lebih lanjut
6. Menyampaikan penyesalan dengan tulus
7. Tone empati, supportif, namun tetap profesional
8. Maksimal 250 kata

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
                subject = f"📋 Update Status Permintaan Darah {blood_type}"
                body = content
            
            return {
                "subject": subject,
                "body": body
            }
            
        except Exception as e:
            # Fallback to template if AI fails
            return self._fallback_rejected_template(
                pemohon_name, blood_type, jumlah_kantong, keperluan, catatan_admin
            )
    
def _fallback_approved_template(
        self,
        pemohon_name: str,
        blood_type: str,
        jumlah_kantong: int,
        keperluan: str,
        catatan_admin: Optional[str] = None
    ) -> dict:
        """Fallback template for approved request"""
        admin_notes = f"\n\n📝 Catatan dari Admin:\n{catatan_admin}\n" if catatan_admin else ""
        
        return {
            "subject": f"✅ Permintaan Darah Disetujui - {blood_type} ({jumlah_kantong} Kantong)",
            "body": f"""
Kepada Yth. {pemohon_name},

Kami dengan senang hati menginformasikan bahwa permintaan darah Anda telah DISETUJUI.

📋 Detail Permintaan:
• Golongan Darah: {blood_type}
• Jumlah Kantong: {jumlah_kantong}
• Keperluan: {keperluan}{admin_notes}

📍 INFORMASI PENGAMBILAN:
• Lokasi: Bank Darah RS Sentra Medika Minahasa Utara
• Jam Operasional: Senin-Jumat 08:00-15:00, Sabtu 08:00-12:00
• Batas Waktu: 3 hari kerja dari email ini

📄 DOKUMEN YANG HARUS DIBAWA:
✓ Surat permintaan/keterangan dari dokter
✓ KTP/Identitas pemohon
✓ Email persetujuan ini (cetak/screenshot)
✓ Formulir konfirmasi (akan diberikan di lokasi)

⚠️ PENTING:
• Konfirmasi kedatangan H-1 via telepon/WhatsApp
• Darah harus diambil sesuai jadwal yang telah ditentukan
• Bawa cooler box jika diperlukan untuk transportasi

📞 Informasi & Koordinasi:
• Telepon: (0431) 123456
• WhatsApp: 0812-3456-7890
• Email: bankdarah@rssentralmedika.id

Terima kasih atas kepercayaan Anda. Kami berharap dapat membantu kebutuhan Anda.

Salam sehat,
Tim Bank Darah
RS Sentra Medika Minahasa Utara
"""
        }
    
def _fallback_rejected_template(
        self,
        pemohon_name: str,
        blood_type: str,
        jumlah_kantong: int,
        keperluan: str,
        catatan_admin: Optional[str] = None
    ) -> dict:
        """Fallback template for rejected request"""
        reason_text = f"\n\n📝 Alasan:\n{catatan_admin}\n" if catatan_admin else "\n\nMohon maaf, saat ini stok darah terbatas dan kami tidak dapat memenuhi permintaan Anda.\n"
        
        return {
            "subject": f"📋 Update Permintaan Darah {blood_type}",
            "body": f"""
Kepada Yth. {pemohon_name},

Terima kasih telah menghubungi Bank Darah RS Sentra Medika Minahasa Utara.

Dengan menyesal kami informasikan bahwa saat ini kami belum dapat memenuhi permintaan darah Anda.

📋 Detail Permintaan:
• Golongan Darah: {blood_type}
• Jumlah Kantong: {jumlah_kantong}
• Keperluan: {keperluan}{reason_text}

💡 ALTERNATIF SOLUSI:
1. Hubungi PMI (Palang Merah Indonesia) terdekat:
   • PMI Sulawesi Utara: (0431) xxx-xxx
   
2. Koordinasi dengan rumah sakit lain:
   • RS Prof. Dr. R.D. Kandou Manado
   • RS Pancaran Kasih GMIM Manado
   
3. Donor Darah Pengganti:
   • Cari donor pengganti dari keluarga/teman
   • Golongan darah yang sesuai: {blood_type}

📞 KONTAK KAMI:
• Telepon: (0431) 123456
• WhatsApp: 0812-3456-7890
• Email: bankdarah@rssentralmedika.id

Kami mohon maaf atas ketidaknyamanan ini. Jika situasi berubah atau ada pertanyaan lebih lanjut, jangan ragu untuk menghubungi kami.

Kami berharap Anda dapat menemukan solusi alternatif dan semoga kebutuhan darah dapat terpenuhi.

Salam hormat,
Tim Bank Darah
RS Sentra Medika Minahasa Utara
"""
    }

# Create singleton instance
ai_service = AIService()