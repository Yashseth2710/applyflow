"""Sending mail.

Deliberately the standard library and nothing else. The app sends exactly one
kind of message — a password reset link — and every hosted provider worth using
wants a verified sending domain, which means owning a domain, which is not free.
A Gmail account with an app password sends the same message for nothing.

With SMTP_HOST unset the message is written to the log instead. That is not a
degraded mode to apologise for: it is how development and the test suite run,
and it means the reset flow can be exercised end to end with nothing configured
and no network.
"""

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import settings

logger = logging.getLogger(__name__)

#: Slow enough for a handshake over a bad connection, short enough that a
#: hanging server does not hold a worker thread all day.
TIMEOUT_SECONDS = 15


def send_email(*, to: str, subject: str, body: str) -> None:
    """Send one plain-text message. Never raises.

    A failed send must not fail the request that triggered it. The caller here
    is the reset endpoint, which answers the same way whether or not the address
    exists — turning a broken mail server into a visible error would undo that,
    and there is nothing the person typing their address could do about it
    anyway. It goes in the log, which is where the operator will look.
    """
    if not settings.email_configured:
        logger.info("Email not configured. Would have sent to %s:\n%s\n\n%s", to, subject, body)
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((settings.EMAIL_FROM_NAME, settings.email_from_address))
    message["To"] = to
    message.set_content(body)

    try:
        # 465 is implicit TLS; everything else negotiates it with STARTTLS.
        # Both are encrypted — the difference is only when it starts.
        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(
                settings.SMTP_HOST, settings.SMTP_PORT, timeout=TIMEOUT_SECONDS
            ) as server:
                _deliver(server, message)
        else:
            with smtplib.SMTP(
                settings.SMTP_HOST, settings.SMTP_PORT, timeout=TIMEOUT_SECONDS
            ) as server:
                server.starttls()
                _deliver(server, message)
    except (smtplib.SMTPException, OSError):
        # OSError covers the network itself: refused connections, DNS, and the
        # timeout above. Some hosts block outbound SMTP entirely, and that
        # arrives here rather than as an SMTP error.
        logger.exception("Could not send mail to %s", to)


def _deliver(server: smtplib.SMTP, message: EmailMessage) -> None:
    if settings.SMTP_USER:
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
    server.send_message(message)
