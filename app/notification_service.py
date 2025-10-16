"""
Email Notification Service (Fixed SMTP Connection)
Handles sending email notifications using SMTP
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from dotenv import load_dotenv
import asyncio
from concurrent.futures import ThreadPoolExecutor
import ssl

load_dotenv()

# Email configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", SMTP_USER)
SENDER_NAME = os.getenv("SENDER_NAME", "RS Sentra Medika")
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

class EmailService:
    """Service for sending email notifications"""
    
    def __init__(self):
        self.smtp_host = SMTP_HOST
        self.smtp_port = SMTP_PORT
        self.smtp_user = SMTP_USER
        self.smtp_password = SMTP_PASSWORD
        self.sender_email = SENDER_EMAIL
        self.sender_name = SENDER_NAME
        self.use_ssl = SMTP_USE_SSL
        self.use_tls = SMTP_USE_TLS
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        print(f"📧 Email Service initialized:")
        print(f"   SMTP: {self.smtp_host}:{self.smtp_port}")
        print(f"   User: {self.smtp_user}")
        print(f"   SSL: {self.use_ssl}, TLS: {self.use_tls}")
    
    def _send_email_sync(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = False
    ) -> bool:
        """
        Send email synchronously
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body content
            html: Whether body is HTML format
            
        Returns:
            bool: Success status
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add body
            if html:
                msg.attach(MIMEText(body, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Connect based on SSL/TLS configuration
            if self.use_ssl:
                # Use SMTP_SSL for port 465
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
                    if self.smtp_user and self.smtp_password:
                        server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            else:
                # Use regular SMTP with optional STARTTLS
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10)
                
                # Try EHLO first
                server.ehlo()
                
                # Try STARTTLS if enabled and supported
                if self.use_tls:
                    try:
                        if server.has_extn('STARTTLS'):
                            context = ssl.create_default_context()
                            server.starttls(context=context)
                            server.ehlo()  # Re-identify after STARTTLS
                        else:
                            print("⚠️ STARTTLS not supported, continuing without encryption")
                    except Exception as tls_error:
                        print(f"⚠️ STARTTLS failed: {tls_error}, continuing without encryption")
                
                # Login if credentials provided
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                
                # Send email
                server.send_message(msg)
                server.quit()
            
            print(f"✅ Email sent successfully to {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ SMTP Authentication failed for {to_email}: {str(e)}")
            print("   Check your SMTP_USER and SMTP_PASSWORD in .env file")
            return False
        except smtplib.SMTPException as e:
            print(f"❌ SMTP error sending to {to_email}: {str(e)}")
            return False
        except Exception as e:
            print(f"❌ Failed to send email to {to_email}: {str(e)}")
            return False
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = False
    ) -> bool:
        """
        Send email asynchronously
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body content
            html: Whether body is HTML format
            
        Returns:
            bool: Success status
        """
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
    
    async def send_bulk_emails(
        self,
        recipients: List[dict],
        subject: str,
        body_template: str
    ) -> dict:
        """
        Send bulk emails to multiple recipients
        
        Args:
            recipients: List of dicts with 'email' and optional 'name'
            subject: Email subject
            body_template: Email body template (can use {name} placeholder)
            
        Returns:
            dict: Success and failure counts
        """
        results = {"success": 0, "failed": 0}
        
        tasks = []
        for recipient in recipients:
            email = recipient.get('email')
            name = recipient.get('name', 'Pengguna')
            
            # Replace placeholders
            body = body_template.replace('{name}', name)
            
            task = self.send_email(email, subject, body)
            tasks.append(task)
        
        # Send all emails concurrently
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results_list:
            if isinstance(result, Exception) or not result:
                results["failed"] += 1
            else:
                results["success"] += 1
        
        return results
    
    async def send_low_stock_alert(
        self,
        admin_emails: List[str],
        blood_type: str,
        current_stock: int,
        status: str,
        ai_content: dict
    ) -> bool:
        """
        Send low stock alert to admins
        
        Args:
            admin_emails: List of admin email addresses
            blood_type: Blood type that is low
            current_stock: Current stock count
            status: Stock status
            ai_content: Content generated by AI (subject and body)
            
        Returns:
            bool: Success status
        """
        subject = ai_content.get('subject', f"⚠️ Stok Darah {blood_type} {status}")
        body = ai_content.get('body', '')
        
        # Convert to HTML for better formatting
        html_body = self._text_to_html(body)
        
        # Send to all admins
        tasks = [
            self.send_email(email, subject, html_body, html=True)
            for email in admin_emails
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Return True if at least one email was sent successfully
        return any(r is True for r in results)
    
    async def send_donation_reminder(
        self,
        donor_email: str,
        donor_name: str,
        ai_content: dict
    ) -> bool:
        """
        Send donation reminder to donor
        
        Args:
            donor_email: Donor's email address
            donor_name: Donor's name
            ai_content: Content generated by AI (subject and body)
            
        Returns:
            bool: Success status
        """
        subject = ai_content.get('subject', '🩸 Pengingat Donor Darah')
        body = ai_content.get('body', '')
        
        # Convert to HTML
        html_body = self._text_to_html(body)
        
        return await self.send_email(donor_email, subject, html_body, html=True)
    
    async def send_thank_you_email(
        self,
        donor_email: str,
        donor_name: str,
        ai_content: dict
    ) -> bool:
        """
        Send thank you email after donation
        
        Args:
            donor_email: Donor's email address
            donor_name: Donor's name
            ai_content: Content generated by AI (subject and body)
            
        Returns:
            bool: Success status
        """
        subject = ai_content.get('subject', '💝 Terima Kasih!')
        body = ai_content.get('body', '')
        
        html_body = self._text_to_html(body)
        
        return await self.send_email(donor_email, subject, html_body, html=True)
    
    def _text_to_html(self, text: str) -> str:
        """
        Convert plain text to HTML with basic formatting
        
        Args:
            text: Plain text content
            
        Returns:
            str: HTML formatted content
        """
        # Replace newlines with <br>
        html = text.replace('\n', '<br>')
        
        # Basic HTML template
        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
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
        .button {{
            display: inline-block;
            padding: 10px 20px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h2>🏥 RS Sentra Medika Minahasa Utara</h2>
    </div>
    <div class="content">
        {html}
    </div>
    <div class="footer">
        <p>Email ini dikirim secara otomatis oleh Sistem Manajemen Donor Darah</p>
        <p>RS Sentra Medika Minahasa Utara</p>
    </div>
</body>
</html>
"""
        return html_template

# Create singleton instance
email_service = EmailService()