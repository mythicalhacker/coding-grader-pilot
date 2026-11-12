from uuid import UUID
import django
from django.conf import settings
settings.configure(INSTALLED_APPS=["django.contrib.contenttypes"], DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}, SECRET_KEY="test")
django.setup()
from django.db import connection, models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
class Foo(models.Model):
    id = models.UUIDField(primary_key=True)
    class Meta: app_label = "contenttypes"
class Bar(models.Model):
    kind = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    key = models.CharField(max_length=255)
    foo = GenericForeignKey("kind", "key")
    class Meta: app_label = "contenttypes"
with connection.schema_editor() as schema:
    for model in (ContentType, Foo, Bar):
        schema.create_model(model)
foo = Foo.objects.create(pk=UUID("de305d54-75b4-431b-adb2-eb6b9e546014"))
Bar.objects.create(kind=ContentType.objects.get_for_model(Foo), key=foo.pk.hex)
bar = Bar.objects.prefetch_related("foo").get()
with TestCase().assertNumQueries(0):
    assert bar.foo == foo
