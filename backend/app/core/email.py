import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..config import settings

logger = logging.getLogger(__name__)


def send_password_reset_email(to_email: str, reset_token: str, frontend_url: str = None) -> bool:
    """发送密码重置邮件"""
    base_url = frontend_url if frontend_url else settings.FRONTEND_URL
    reset_link = f"{base_url}/reset-password?token={reset_token}"

    subject = "智慧校园平台 - 密码重置"

    html_body = f"""
    <div style="max-width: 600px; margin: 0 auto; font-family: 'Segoe UI', Arial, sans-serif; color: #333;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 24px;">智慧校园服务平台</h1>
        </div>
        <div style="padding: 30px; background: #ffffff; border: 1px solid #e0e0e0;">
            <h2 style="color: #333; margin-top: 0;">密码重置请求</h2>
            <p>您好，</p>
            <p>我们收到了您的密码重置请求。请点击下方按钮重置您的密码：</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_link}"
                   style="display: inline-block; padding: 12px 32px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                          color: white; text-decoration: none; border-radius: 6px; font-size: 16px; font-weight: bold;">
                    重置密码
                </a>
            </div>
            <p style="color: #666; font-size: 14px;">如果按钮无法点击，请复制以下链接到浏览器中打开：</p>
            <p style="color: #667eea; word-break: break-all; font-size: 13px;">{reset_link}</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="color: #999; font-size: 12px;">
                此链接将在30分钟后失效。如果您没有请求重置密码，请忽略此邮件。
            </p>
        </div>
        <div style="padding: 15px; text-align: center; color: #999; font-size: 12px;">
            &copy; 智慧校园服务平台
        </div>
    </div>
    """

    text_body = f"""
智慧校园服务平台 - 密码重置

您好，

我们收到了您的密码重置请求。请访问以下链接重置您的密码：

{reset_link}

此链接将在30分钟后失效。如果您没有请求重置密码，请忽略此邮件。
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        # 端口465使用SSL，端口587使用STARTTLS
        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())
        logger.info(f"密码重置邮件已发送到 {to_email}")
        return True
    except Exception as e:
        logger.error(f"发送邮件失败: {e}")
        return False
