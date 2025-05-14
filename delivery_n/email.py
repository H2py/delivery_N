from flask_mail import Message
from flask import current_app

from instance.config import MAIL_USERNAME
from . import mail


def send_mail(cert_info, otp):
    
    msg = Message(
        '[배달N빵] 이메일 인증 번호',
        sender=MAIL_USERNAME,
        recipients=[cert_info]
    )
    msg.body = f'안녕하세요. 배달N빵입니다.\n인증 번호를 입력하여 이메일 인증을 완료해 주세요.\n인증 번호: {otp}'
    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
