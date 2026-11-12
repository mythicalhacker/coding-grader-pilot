from email.header import decode_header

from django.conf import settings
from django.core.mail import EmailMessage

if not settings.configured:
    settings.configure()

mail = EmailMessage(
    subject="Café",
    body="",
    from_email="sender@example.org",
    to=["reader@example.org"],
    headers={
        "Date": "Thu, 01 Jan 1970 00:00:00 +0000",
        "Message-ID": "<example@example.org>",
    },
)
mail.encoding = "iso-8859-1"
assert decode_header(mail.message()["Subject"]) == [(b"Caf\xe9", "iso-8859-1")]
