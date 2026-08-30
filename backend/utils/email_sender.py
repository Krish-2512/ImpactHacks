"""
Email notifications via SMTP.

Supports Gmail (smtp.gmail.com:587) and any other SMTP provider.
Gmail setup: Account → Security → 2-Step Verification → App passwords → generate one.
Set SMTP_USER=you@gmail.com and SMTP_PASSWORD=<16-char app password> in .env.
"""
import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from backend.config import settings


PRIORITY_EMOJI = {"urgent": "🚨", "high": "⚠️", "medium": "📢", "low": "ℹ️"}
PRIORITY_COLOR = {"urgent": "#dc2626", "high": "#ea580c", "medium": "#ca8a04", "low": "#6b7280"}


def _build_html(notifications: list[dict], username: str) -> str:
    items_html = ""
    for n in notifications:
        color = PRIORITY_COLOR.get(n.get("priority", "low"), "#6b7280")
        icon  = n.get("icon", "🔔")
        items_html += f"""
        <tr>
          <td style="padding:12px 16px;border-bottom:1px solid #f3f4f6;">
            <table cellpadding="0" cellspacing="0" width="100%">
              <tr>
                <td width="36" style="vertical-align:top;font-size:22px;padding-right:12px;">{icon}</td>
                <td>
                  <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                    <strong style="font-size:14px;color:#111827;">{n.get("title","")}</strong>
                    <span style="font-size:11px;font-weight:600;color:{color};background:{color}18;
                                 padding:2px 8px;border-radius:99px;text-transform:capitalize;">
                      {n.get("priority","low")}
                    </span>
                  </div>
                  <p style="font-size:13px;color:#4b5563;margin:0;">{n.get("body","")}</p>
                </td>
              </tr>
            </table>
          </td>
        </tr>"""

    timestamp = datetime.utcnow().strftime("%d %b %Y, %I:%M %p UTC")
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:32px 16px;">
    <tr><td align="center">
      <table width="100%" style="max-width:560px;background:#ffffff;border-radius:12px;
                                  border:1px solid #e5e7eb;overflow:hidden;">
        <!-- Header -->
        <tr>
          <td style="background:#16a34a;padding:20px 24px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <span style="font-size:22px;">🌱</span>
                  <span style="font-size:18px;font-weight:700;color:#fff;margin-left:8px;">Agrow Intelligence</span>
                </td>
                <td align="right">
                  <span style="font-size:12px;color:#bbf7d0;">Farm Alerts</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <!-- Greeting -->
        <tr>
          <td style="padding:20px 24px 8px;">
            <p style="margin:0;font-size:15px;color:#111827;">
              Hi <strong>{username}</strong>, here are your latest farm alerts:
            </p>
          </td>
        </tr>
        <!-- Notifications -->
        <tr>
          <td style="padding:0 16px 16px;">
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">
              {items_html}
            </table>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="padding:16px 24px;border-top:1px solid #f3f4f6;background:#f9fafb;">
            <p style="margin:0;font-size:11px;color:#9ca3af;text-align:center;">
              Agrow Intelligence · {timestamp}<br>
              You received this because you're a registered farmer on the platform.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _send_smtp(to_email: str, subject: str, html_body: str) -> None:
    """Blocking SMTP send — run inside asyncio.to_thread."""
    context = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = settings.SMTP_FROM or settings.SMTP_USER
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html"))
        smtp.sendmail(msg["From"], to_email, msg.as_string())


async def send_notification_email(
    to_email: str,
    username: str,
    notifications: list[dict],
) -> None:
    """
    Send an HTML digest email for the given notifications.
    Only called if EMAIL_NOTIFICATIONS_ENABLED=true in .env.
    Filters to urgent/high priority by default (configurable via EMAIL_MIN_PRIORITY).
    Silently swallows errors so a broken SMTP config never crashes the pipeline.
    """
    if not settings.EMAIL_NOTIFICATIONS_ENABLED:
        return
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print("[email] SMTP credentials not configured — skipping email notification")
        return

    priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    min_level = priority_order.get(settings.EMAIL_MIN_PRIORITY, 1)
    to_send = [n for n in notifications if priority_order.get(n.get("priority", "low"), 3) <= min_level]
    if not to_send:
        return

    count = len(to_send)
    urgent_count = sum(1 for n in to_send if n.get("priority") == "urgent")
    subject = (
        f"🚨 {urgent_count} Urgent Farm Alert{'s' if urgent_count > 1 else ''} — Agrow"
        if urgent_count else
        f"🌾 {count} Farm Alert{'s' if count > 1 else ''} — Agrow Intelligence"
    )

    html = _build_html(to_send, username)
    try:
        await asyncio.to_thread(_send_smtp, to_email, subject, html)
        print(f"[email] Sent {count} notification(s) to {to_email}")
    except Exception as e:
        print(f"[email] Failed to send to {to_email}: {e}")
