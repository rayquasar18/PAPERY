"""SMTP email sending utility.

Provides a single async function for sending HTML emails.
Gracefully degrades when SMTP is not configured (logs warning, does not raise).
"""

from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.configs import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html_body: str) -> None:
    """Send an HTML email via SMTP.

    If SMTP is not configured (empty host), logs a warning and returns
    without raising. Email delivery failures are logged but never propagated
    — callers should treat email as non-blocking / best-effort.

    TLS behaviour:
    - Port 465 → implicit TLS (use_tls=True)
    - Port 587 / other → STARTTLS upgrade after connect
    """
    if not settings.SMTP_HOST:
        logger.warning(
            "SMTP not configured — skipping email to=%s subject=%r",
            to,
            subject,
        )
        return

    try:
        # Lazy import to avoid hard dependency when SMTP is unused
        import aiosmtplib

        msg = MIMEMultipart("alternative")
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # Port 465 uses implicit TLS; everything else uses STARTTLS
        use_tls = settings.SMTP_PORT == 465
        start_tls = not use_tls

        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            use_tls=use_tls,
            start_tls=start_tls,
        )

        logger.info("Email sent to=%s subject=%r", to, subject)

    except Exception:
        logger.exception("Failed to send email to=%s subject=%r", to, subject)
