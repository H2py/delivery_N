from flask_mail import Message
from flask import current_app

from instance.config import MAIL_USERNAME
from . import mail


def send_mail(cert_info, title, content):
    msg = Message(
        title,
        sender=MAIL_USERNAME,
        recipients=[cert_info]
    )
    msg.body = content
    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
