from uuid import UUID
import django
from django.conf import settings
settings.configure(INSTALLED_APPS=["django.contrib.contenttypes"], DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}, SECRET_KEY="test")
django.setup()
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models

class Target(models.Model):
    id = models.UUIDField(primary_key=True)
    class Meta:
        app_label = "contenttypes"

class Link(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=32)
    target = GenericForeignKey()
    class Meta:
        app_label = "contenttypes"

with connection.schema_editor() as editor:
    for model in (ContentType, Target, Link):
        editor.create_model(model)
target = Target.objects.create(pk=UUID("12345678-1234-5678-a123-0123456789ab"))
Link.objects.create(content_type=ContentType.objects.get_for_model(Target), object_id=target.pk.hex)
prefetched = Link.objects.prefetch_related(models.Prefetch("target", to_attr="resolved")).get()
assert prefetched.resolved == target
