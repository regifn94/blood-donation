import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

load_dotenv()

message = Mail(
    from_email=os.getenv("FROM_EMAIL"),
    to_emails="brianatessa29@gmail.com",
    subject="Tes Email SendGrid 🚀",
    html_content="<strong>Halo! Ini percobaan kirim email dari SendGrid + FastAPI.</strong>"
)

try:
    print("🔹 Mengirim email...")
    sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    response = sg.send(message)
    print("✅ Email berhasil dikirim!")
    print("Status code:", response.status_code)
except Exception as e:
    print("❌ Gagal kirim email:", e)
