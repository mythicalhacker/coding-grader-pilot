from email.header import decode_header

from django.conf import settings
from django.core.mail import EmailMessage

if not settings.configured:
    settings.configure()

mail = EmailMessage(
    subject="Café",
    body="Hello",
    from_email="from@example.com",
    to=["to@example.com"],
    headers={
        "Date": "Mon, 01 Jan 2024 00:00:00 +0000",
        "Message-ID": "<example@example.com>",
    },
)
mail.encoding = "iso-8859-1"
assert decode_header(mail.message()["Subject"]) == [(b"Caf\xe9", "iso-8859-1")]
