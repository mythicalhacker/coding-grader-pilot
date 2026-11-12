from codecs import lookup
from email.header import decode_header

from django.conf import settings
from django.core.mail import EmailMessage

settings.configure()
subject = 'Café'
mail = EmailMessage(
    subject, '', 'from@example.com', ['to@example.com'],
    headers={'Date': 'Thu, 01 Jan 1970 00:00:00 +0000', 'Message-ID': '<test@example.com>'},
)
mail.encoding = 'iso-8859-1'
[(payload, charset)] = decode_header(mail.message()['Subject'])
assert charset and lookup(charset).name == lookup(mail.encoding).name
assert payload.decode(charset) == subject
