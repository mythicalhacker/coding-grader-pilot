from email.header import decode_header

from django.conf import settings
from django.core.mail import EmailMessage

if not settings.configured:
    settings.configure(DEFAULT_CHARSET='utf-8')

mail = EmailMessage(
    subject='Café',
    body='',
    from_email='sender@example.com',
    to=['reader@example.com'],
    headers={'Date': 'Mon, 01 Jan 2024 00:00:00 +0000',
             'Message-ID': '<fixed@example.com>'},
)
mail.encoding = 'iso-8859-1'
assert decode_header(str(mail.message()['Subject'])) == [(b'Caf\xe9', 'iso-8859-1')]
