import html
import logging
import smtplib
from email.message import EmailMessage, Message
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import urljoin

import markdown

from app.core.config import settings

logger = logging.getLogger(__name__)

# Content-ID for inline logo (must match HTML src="cid:...")
_BRAND_LOGO_CID = "curecompass-logo"

_logo_bytes_cache: bytes | None = None
_logo_load_attempted: bool = False


def _markdown_to_html_fragment(md: str) -> str:
    return markdown.markdown(
        md,
        extensions=["nl2br", "tables", "fenced_code"],
        output_format="html",
    )


def _digest_reply_to_header_value() -> str | None:
    """Address for Reply-To on digests only (digest-specific, then global smtp_reply_to)."""
    for raw in (settings.smtp_digest_reply_to, settings.smtp_reply_to):
        v = (raw or "").strip()
        if v:
            return v
    return None


def _brand_logo_url() -> str:
    """Absolute URL to the static logo on the frontend (fallback when no local file for CID)."""
    base = (settings.frontend_url or "").rstrip("/") + "/"
    return urljoin(base, "brand/logoCureCompass.png")


def _brand_logo_path() -> Path | None:
    app_dir = Path(__file__).resolve().parent.parent
    repo_root = app_dir.parent.parent
    for p in (
        app_dir / "static" / "brand" / "logoCureCompass.png",
        repo_root / "frontend" / "public" / "brand" / "logoCureCompass.png",
        repo_root / "logoCureCompass.png",
    ):
        if p.is_file():
            return p
    return None


def _read_brand_logo_bytes() -> bytes | None:
    """PNG bytes for CID attachment; cached. None if file missing."""
    global _logo_bytes_cache, _logo_load_attempted
    if _logo_load_attempted:
        return _logo_bytes_cache
    _logo_load_attempted = True
    path = _brand_logo_path()
    if path is None:
        logger.warning("Brand logo PNG not found (expected app/static/brand/logoCureCompass.png); email <img> will use URL.")
        _logo_bytes_cache = None
        return None
    try:
        _logo_bytes_cache = path.read_bytes()
    except OSError as exc:
        logger.warning("Could not read brand logo at %s: %s", path, exc)
        _logo_bytes_cache = None
    return _logo_bytes_cache


def _email_logo_img_src_attr() -> str:
    """Use inline CID when logo file exists; otherwise public URL (often broken for localhost)."""
    if _read_brand_logo_bytes() is not None:
        return f"cid:{_BRAND_LOGO_CID}"
    return html.escape(_brand_logo_url(), quote=True)


def _password_reset_email_html(reset_url: str) -> str:
    logo_src = _email_logo_img_src_attr()
    url_esc = html.escape(reset_url, quote=True)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Reset your CureCompass password</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f9fb;-webkit-font-smoothing:antialiased;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f9fb;padding:28px 14px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:580px;background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 10px 40px rgba(11,33,63,0.07);border:1px solid #e2e8f0;">
          <tr>
            <td style="background-color:#ffffff;padding:22px 26px 18px;border-bottom:1px solid #e8eef2;">
              <img src="{logo_src}" width="280" alt="CureCompass" style="display:block;max-width:280px;width:100%;height:auto;border:0;outline:none;text-decoration:none;" />
            </td>
          </tr>
          <tr>
            <td style="padding:26px 26px 8px;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;">
              <p style="margin:0 0 12px;font-size:18px;font-weight:600;color:#0b213f;">Reset your password</p>
              <p style="margin:0 0 20px;font-size:15px;line-height:1.6;color:#334155;">
                You requested a password reset. Use the button below to choose a new password.
              </p>
              <p style="margin:0 0 24px;">
                <a href="{url_esc}" style="display:inline-block;background-color:#2cb6af;color:#ffffff;text-decoration:none;font-weight:600;font-size:15px;padding:12px 22px;border-radius:10px;">
                  Reset password
                </a>
              </p>
              <p style="margin:0;font-size:13px;line-height:1.55;color:#64748b;">
                If you did not request this, you can ignore this email.
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:16px 26px 22px;border-top:1px solid #e2e8f0;">
              <p style="margin:0;font-size:12px;line-height:1.5;color:#94a3b8;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;">
                Link not working? Copy and paste this URL into your browser:<br />
                <span style="color:#475569;word-break:break-all;">{html.escape(reset_url, quote=False)}</span>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _digest_email_html(title: str, body_markdown: str) -> str:
    """HTML wrapper matching CureCompass UI (navy #0b213f, teal #2cb6af, calm layout)."""
    inner = _markdown_to_html_fragment(body_markdown)
    title_esc = html.escape(title, quote=False)
    logo_src = _email_logo_img_src_attr()

    auto_row = """
          <tr>
            <td style="padding:16px 26px 0;border-top:1px solid #e2e8f0;">
              <p style="margin:0;font-size:12px;line-height:1.55;color:#64748b;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;">
                <strong style="color:#475569;">Please do not reply.</strong>
                This message is automated and this inbox is not monitored.
                Use the app or your clinician for questions.
              </p>
            </td>
          </tr>"""

    disclaimer_row = """
          <tr>
            <td style="padding:18px 26px 26px;">
              <p style="margin:0;font-size:11px;line-height:1.5;color:#94a3b8;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;">
                Educational research summary only — not personal medical advice. Discuss with your clinician.
              </p>
            </td>
          </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title, quote=True)}</title>
<style type="text/css">
  .digest-content h1 {{ font-size: 1.25rem; font-weight: 600; color: #0b213f; margin: 1.1rem 0 0.5rem; }}
  .digest-content h2 {{
    font-size: 1.08rem; font-weight: 600; color: #0b213f; margin: 1.1rem 0 0.4rem;
    padding-bottom: 0.35rem; border-bottom: 2px solid #9ee5df;
  }}
  .digest-content h3 {{ font-size: 1rem; font-weight: 600; color: #0f172a; margin: 0.95rem 0 0.35rem; }}
  .digest-content p {{ margin: 0 0 0.75rem; font-size: 15px; line-height: 1.65; color: #334155; }}
  .digest-content ul, .digest-content ol {{
    margin: 0 0 0.75rem; padding-left: 1.25rem; font-size: 15px; line-height: 1.6; color: #334155;
  }}
  .digest-content li {{ margin: 0.2rem 0; }}
  .digest-content strong {{ color: #0b213f; font-weight: 600; }}
  .digest-content a {{ color: #249890; text-decoration: none; font-weight: 500; }}
  .digest-content hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 1.25rem 0; }}
  .digest-content code {{
    font-size: 0.88em; background: #e0f4f7; color: #0b213f; padding: 0.12em 0.4em; border-radius: 4px;
  }}
  .digest-content pre {{
    background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; overflow-x: auto; font-size: 13px; margin: 0 0 0.75rem;
  }}
  .digest-content pre code {{ background: none; color: #334155; padding: 0; }}
  .digest-content blockquote {{
    margin: 0 0 0.75rem; padding: 10px 14px; border-left: 4px solid #2cb6af;
    background: #f8fafc; color: #475569; border-radius: 0 8px 8px 0;
  }}
  .digest-content table {{ border-collapse: collapse; width: 100%; margin: 0 0 0.75rem; font-size: 14px; }}
  .digest-content th, .digest-content td {{ border: 1px solid #e2e8f0; padding: 8px 10px; text-align: left; }}
  .digest-content th {{ background: #e0f4f7; color: #0b213f; font-weight: 600; }}
</style>
</head>
<body style="margin:0;padding:0;background-color:#f4f9fb;-webkit-font-smoothing:antialiased;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f9fb;padding:28px 14px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:580px;background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 10px 40px rgba(11,33,63,0.07);border:1px solid #e2e8f0;">
          <tr>
            <td style="background-color:#ffffff;padding:22px 26px 18px;border-bottom:1px solid #e8eef2;">
              <img src="{logo_src}" width="300" alt="CureCompass" style="display:block;max-width:300px;width:100%;height:auto;border:0;outline:none;text-decoration:none;" />
            </td>
          </tr>
          <tr>
            <td style="background-color:#2cb6af;padding:20px 26px 18px;">
              <p style="margin:0;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:rgba(255,255,255,0.9);font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;">
                CureCompass · Research briefing
              </p>
              <p style="margin:10px 0 0;font-size:20px;font-weight:600;line-height:1.35;color:#ffffff;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;">
                {title_esc}
              </p>
            </td>
          </tr>
          <tr>
            <td class="digest-content" style="padding:24px 26px 10px;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;">
              {inner}
            </td>
          </tr>{auto_row}{disclaimer_row}
        </table>
        <p style="margin:18px 0 0;font-size:11px;color:#94a3b8;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;">
          <a href="{html.escape(settings.frontend_url.rstrip("/"), quote=True)}" style="color:#64748b;text-decoration:none;">curecompass.app</a>
        </p>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _apply_no_reply_headers(msg: Message) -> None:
    reply_to = (settings.smtp_reply_to or "").strip()
    if reply_to:
        msg["Reply-To"] = reply_to
        msg["X-Auto-Response-Suppress"] = "OOF, AutoReply"


def _apply_digest_headers(msg: Message) -> None:
    """Mark digests as automated + steer replies away from SMTP_FROM (cannot block replies in protocol)."""
    msg["Auto-Submitted"] = "auto-generated"
    msg["Precedence"] = "bulk"
    msg["X-Auto-Response-Suppress"] = "OOF, AutoReply"
    reply_to = _digest_reply_to_header_value()
    if reply_to:
        msg["Reply-To"] = reply_to


def _multipart_related_html_email(
    subject: str,
    from_addr: str,
    to_addr: str,
    plain_body: str,
    html_body: str,
    logo_bytes: bytes,
) -> MIMEMultipart:
    """multipart/related: alternative (plain+html) + inline PNG for cid logo."""
    root = MIMEMultipart("related")
    root["Subject"] = subject
    root["From"] = from_addr
    root["To"] = to_addr

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain_body, "plain", "utf-8"))
    alt.attach(MIMEText(html_body, "html", "utf-8"))
    root.attach(alt)

    image = MIMEImage(logo_bytes, _subtype="png")
    image.add_header("Content-ID", f"<{_BRAND_LOGO_CID}>")
    image.add_header("Content-Disposition", "inline", filename="logoCureCompass.png")
    root.attach(image)
    return root


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    subject = "Reset your CureCompass password"
    body = (
        "You requested a password reset.\n\n"
        f"Open this link to choose a new password:\n{reset_url}\n\n"
        "If you did not request this, you can ignore this email."
    )

    if not settings.smtp_host:
        logger.warning("SMTP not configured; password reset link for %s: %s", to_email, reset_url)
        return

    html_body = _password_reset_email_html(reset_url)
    logo_bytes = _read_brand_logo_bytes()

    if logo_bytes:
        msg = _multipart_related_html_email(subject, settings.smtp_from, to_email, body, html_body, logo_bytes)
    else:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        msg.set_content(body, subtype="plain", charset="utf-8")
        msg.add_alternative(html_body, subtype="html", charset="utf-8")

    _apply_no_reply_headers(msg)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_user and settings.smtp_password:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    except (OSError, smtplib.SMTPException) as exc:
        logger.exception("Failed to send email to %s; link=%s err=%s", to_email, reset_url, exc)
        if settings.environment == "development":
            logger.warning("Dev fallback — reset link: %s", reset_url)


def send_digest_email(to_email: str, subject: str, body_text: str) -> bool:
    """Send digest as multipart (plain + HTML). Returns True if handed to SMTP, False if not configured."""
    if not settings.smtp_host:
        logger.warning("SMTP not configured; digest for %s — subject=%s", to_email, subject)
        return False

    text = (
        f"{body_text}\n\n"
        "---\n"
        "Please do not reply — this message is automated and this inbox is not monitored.\n\n"
        "Educational research summary only — not personal medical advice. Discuss with your clinician."
    )

    html_body = _digest_email_html(subject, body_text)
    logo_bytes = _read_brand_logo_bytes()

    if logo_bytes:
        msg = _multipart_related_html_email(
            subject[:200], settings.smtp_from, to_email, text, html_body, logo_bytes
        )
    else:
        msg = EmailMessage()
        msg["Subject"] = subject[:200]
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        msg.set_content(text, subtype="plain", charset="utf-8")
        msg.add_alternative(html_body, subtype="html", charset="utf-8")

    _apply_digest_headers(msg)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_user and settings.smtp_password:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    except OSError:
        logger.exception("Failed to send digest email to %s", to_email)
        raise
    return True
