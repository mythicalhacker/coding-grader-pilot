import django
from uuid import UUID
from django.conf import settings
settings.configure(SECRET_KEY="test", INSTALLED_APPS=["django.contrib.contenttypes"], DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}})
django.setup()
from django.db import connection, models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

class Target(models.Model):
    id = models.UUIDField(primary_key=True)
    class Meta: app_label = "contenttypes"

class Reference(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=36)
    target = GenericForeignKey()
    class Meta: app_label = "contenttypes"

with connection.schema_editor() as schema:
    for model in (ContentType, Target, Reference):
        schema.create_model(model)
target = Target.objects.create(id=UUID("abcdef01-2345-6789-abcd-ef0123456789"))
Reference.objects.create(content_type=ContentType.objects.get_for_model(Target), object_id=target.pk.hex.upper())
ref = Reference.objects.prefetch_related("target").get()
with TestCase().assertNumQueries(0):
    assert ref.target == target
