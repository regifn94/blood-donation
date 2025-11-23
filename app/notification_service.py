"""
Email Notification Service (SendGrid Integration)
Handles sending email notifications using SendGrid API
"""

import os
import asyncio
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To
from concurrent.futures import ThreadPoolExecutor

load_dotenv() # memuat variable

# SendGrid configuration
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")
SENDER_NAME = os.getenv("SENDER_NAME", "RS Sentra Medika")

class EmailService:
    """Service for sending email notifications using SendGrid"""

    def __init__(self):
        self.sg = SendGridAPIClient(SENDGRID_API_KEY) # inisialisasi klien sendgrid
        self.sender_email = FROM_EMAIL # menyimpan alamat pengirim
        self.sender_name = SENDER_NAME # menyimpan nama pengirim
        self.executor = ThreadPoolExecutor(max_workers=5)

        print("📧 SendGrid Email Service initialized:")
        print(f"   FROM: {self.sender_name} <{self.sender_email}>") # menampilkan info saat inisialisasi 

    def _send_email_sync(self, to_email: str, subject: str, body: str, html: bool = False) -> bool:
        """Send email synchronously via SendGrid"""
        try:
            message = Mail(
                from_email=Email(self.sender_email, self.sender_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=body if html else f"<pre>{body}</pre>"
            )
            response = self.sg.send(message) # API sendgrid
            if response.status_code in [200, 202]:
                print(f"✅ Email sent to {to_email}")
                return True
            else:
                print(f"⚠️ SendGrid response {response.status_code}: {response.body}")
                return False
        except Exception as e:
            try:
                # Jika response tersedia dari SendGrid
                print(f"❌ Failed to send email to {to_email}: {str(e)}")
                if hasattr(e, 'body'):
                    print(f"   Response body: {e.body}")
            except Exception:
                pass
            return False

    async def send_email(self, to_email: str, subject: str, body: str, html: bool = False) -> bool:
        """Send email asynchronously"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor,
            self._send_email_sync,
            to_email,
            subject,
            body,
            html
        )
        return result

    async def send_bulk_emails(self, recipients, subject: str, body_template: str):
        """Send bulk emails concurrently"""
        results = {"success": 0, "failed": 0}
        tasks = []

        for r in recipients:
            email = r.get("email")
            name = r.get("name", "Pengguna")
            body = body_template.replace("{name}", name)
            tasks.append(self.send_email(email, subject, body, html=True))

        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results_list:
            if r is True:
                results["success"] += 1
            else:
                results["failed"] += 1
        return results

    async def send_low_stock_alert(self, admin_emails, blood_type, current_stock, status, ai_content):
        """Send alert email to admins when blood stock is low or critical"""
        subject = ai_content.get('subject', f"⚠️ Stok Darah {blood_type} {status}")
        body = self._text_to_html(ai_content.get('body', ''))
        tasks = [self.send_email(email, subject, body, html=True) for email in admin_emails]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return any(r is True for r in results)

    async def send_donation_reminder(self, donor_email, donor_name, ai_content):
        """Send reminder email to donor"""
        subject = ai_content.get('subject', '🩸 Pengingat Donor Darah')
        body = self._text_to_html(ai_content.get('body', ''))
        return await self.send_email(donor_email, subject, body, html=True)
    
    async def send_approved_blood_request(self, donor_email, donor_name, ai_content):
        """Send approved blood email"""
        subject = ai_content.get('subject', '✅ 🩸 Permohonan Darah Disetujui')
        body = self._text_to_html(ai_content.get('body', ''))
        return await self.send_email(donor_email, subject, body, html=True)

    async def send_thank_you_email(self, donor_email, donor_name, ai_content):
        """Send thank you email after donation"""
        subject = ai_content.get('subject', '💝 Terima Kasih!')
        body = self._text_to_html(ai_content.get('body', ''))
        return await self.send_email(donor_email, subject, body, html=True)

    def _text_to_html(self, text: str) -> str:
        """Convert plain text to styled HTML"""
        html = text.replace('\n', '<br>')
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px 10px 0 0;
            text-align: center;
        }}
        .content {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 0 0 10px 10px;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h2>🏥 RS Sentra Medika Minahasa Utara</h2>
    </div>
    <div class="content">{html}</div>
    <div class="footer">
        <p>Email ini dikirim otomatis oleh Sistem Manajemen Donor Darah</p>
    </div>
</body>
</html>
"""

    async def send_request_approved_email(
        self,
        pemohon_email: str,
        pemohon_name: str,
        ai_content: dict
    ) -> bool:
        """
        Send email notification when blood request is APPROVED
        
        Args:
            pemohon_email: Email of the requester
            pemohon_name: Name of the requester
            ai_content: AI-generated email content (subject and body)
            
        Returns:
            bool: True if email sent successfully
        """
        subject = ai_content.get('subject', '✅ Permintaan Darah Disetujui')
        body = ai_content.get('body', '')
        
        # Convert to HTML with enhanced formatting for approval
        html_body = self._text_to_html_enhanced(body, email_type='approval')
        
        return await self.send_email(pemohon_email, subject, html_body, html=True)


    async def send_request_rejected_email(
        self,
        pemohon_email: str,
        pemohon_name: str,
        ai_content: dict
    ) -> bool:
        """
        Send email notification when blood request is REJECTED
        
        Args:
            pemohon_email: Email of the requester
            pemohon_name: Name of the requester
            ai_content: AI-generated email content (subject and body)
            
        Returns:
            bool: True if email sent successfully
        """
        subject = ai_content.get('subject', '📋 Update Status Permintaan Darah')
        body = ai_content.get('body', '')
        
        # Convert to HTML with empathetic formatting for rejection
        html_body = self._text_to_html_enhanced(body, email_type='rejection')
        
        return await self.send_email(pemohon_email, subject, html_body, html=True)


    def _text_to_html_enhanced(self, text: str, email_type: str = 'general') -> str:
        """
        Convert plain text to HTML with enhanced formatting based on email type
        
        Args:
            text: Plain text content
            email_type: Type of email ('approval', 'rejection', 'general')
            
        Returns:
            str: HTML formatted content
        """
        # Replace newlines with <br>
        html = text.replace('\n', '<br>')
        
        # Choose color scheme based on email type
        if email_type == 'approval':
            header_gradient = 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)'
            icon = '✅'
        elif email_type == 'rejection':
            header_gradient = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
            icon = '📋'
        else:
            header_gradient = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
            icon = '🏥'
        
        # Enhanced HTML template
        html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                background: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                background: {header_gradient};
                color: white;
                padding: 30px 20px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: 600;
            }}
            .icon {{
                font-size: 48px;
                margin-bottom: 10px;
            }}
            .content {{
                padding: 30px;
                background: white;
            }}
            .content p {{
                margin: 10px 0;
            }}
            .highlight {{
                background: #f8f9fa;
                padding: 15px;
                border-left: 4px solid #667eea;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .button {{
                display: inline-block;
                padding: 12px 30px;
                background: #667eea;
                color: white !important;
                text-decoration: none;
                border-radius: 6px;
                margin: 15px 0;
                font-weight: 600;
            }}
            .footer {{
                background: #f8f9fa;
                padding: 20px;
                text-align: center;
                color: #666;
                font-size: 12px;
                border-top: 1px solid #e0e0e0;
            }}
            .footer p {{
                margin: 5px 0;
            }}
            .divider {{
                height: 1px;
                background: #e0e0e0;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="icon">{icon}</div>
                <h1>RS Sentra Medika Minahasa Utara</h1>
                <p style="margin: 0; font-size: 14px; opacity: 0.9;">Sistem Manajemen Donor Darah</p>
            </div>
            <div class="content">
                {html}
            </div>
            <div class="footer">
                <p><strong>RS Sentra Medika Minahasa Utara</strong></p>
                <p>Jl. Raya Trans Sulawesi, Minahasa Utara</p>
                <p>Email: bankdarah@rssentralmedika.id | Tel: (0431) 123456</p>
                <div class="divider"></div>
                <p style="font-size: 11px; color: #999;">
                    Email ini dikirim secara otomatis. Mohon tidak membalas email ini.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
        return html_template

# Singleton instance
email_service = EmailService()
