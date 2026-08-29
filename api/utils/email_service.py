import threading
import logging
from django.core.mail import EmailMessage
from django.conf import settings
from django.db import connection
from api.models import EmailLog

logger = logging.getLogger(__name__)

def _async_send_email(email_log_id, email_message):
    try:
        email_message.send(fail_silently=False)
        # Update log status to SENT
        EmailLog.objects.filter(pk=email_log_id).update(status='SENT')
        logger.info(f"EmailLog {email_log_id} sent successfully.")
    except Exception as e:
        error_msg = str(e)
        EmailLog.objects.filter(pk=email_log_id).update(status='FAILED', error_message=error_msg)
        logger.error(f"EmailLog {email_log_id} failed to send: {error_msg}")
    finally:
        # Django connection is not automatically closed in manually managed threads
        connection.close()

def send_document_email(
    recipient,
    subject,
    body,
    cc=None,
    bcc=None,
    attachment_bytes=None,
    attachment_name=None,
    document_type='OTHER',
    document_id=None,
    sender=None
):
    """
    Sends an email with an optional PDF attachment.
    All email sending is offloaded to a background thread to prevent UI blocking.
    """
    def parse_emails(email_val):
        if not email_val:
            return []
        if isinstance(email_val, list):
            return [e.strip() for e in email_val if e.strip()]
        if isinstance(email_val, str):
            return [e.strip() for e in email_val.split(',') if e.strip()]
        return []

    to_list = parse_emails(recipient)
    cc_list = parse_emails(cc)
    bcc_list = parse_emails(bcc)

    # Save initial EmailLog
    email_log = EmailLog.objects.create(
        sender=sender,
        recipient=', '.join(to_list),
        cc=', '.join(cc_list) if cc_list else None,
        bcc=', '.join(bcc_list) if bcc_list else None,
        subject=subject,
        body=body,
        document_type=document_type,
        document_id=document_id,
        status='FAILED'  # Default to failed until it succeeds
    )

    if not to_list:
        email_log.error_message = "No valid recipient email address provided."
        email_log.save()
        logger.error("Failed to send email: No valid recipient.")
        return email_log

    # Create Django EmailMessage
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=to_list,
        cc=cc_list,
        bcc=bcc_list,
    )

    if attachment_bytes and attachment_name:
        email.attach(attachment_name, attachment_bytes, "application/pdf")

    # Start sending in a background thread
    thread = threading.Thread(target=_async_send_email, args=(email_log.id, email))
    thread.start()

    return email_log
