"""SMTP email sending utility.

Provides async functions for sending HTML emails and rendering Jinja2 templates.
Gracefully degrades when SMTP is not configured (logs warning, does not raise).
"""

from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.configs import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Jinja2 template rendering
# ---------------------------------------------------------------------------
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"
_jinja_env: Environment | None = None


def _get_jinja_env() -> Environment:
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=True,
        )
    return _jinja_env


def render_email_template(template_name: str, locale: str, context: dict[str, str]) -> str:
    """Render an email HTML template by name and locale.

    Falls back to the English template if the requested locale is not found.
    Template files follow the naming convention: ``{template_name}_{locale}.html``.
    """
    env = _get_jinja_env()
    filename = f"{template_name}_{locale}.html"
    try:
        template = env.get_template(filename)
    except Exception:
        template = env.get_template(f"{template_name}_en.html")
    return template.render(**context)


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
