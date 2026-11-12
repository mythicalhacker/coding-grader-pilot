import django
from django.conf import settings
from django.db import migrations, models
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.graph import MigrationGraph
from django.db.migrations.state import ModelState, ProjectState

settings.configure(INSTALLED_APPS=[], SECRET_KEY="test")
django.setup()

def project(link):
    state = ProjectState()
    state.add_model(ModelState("testapp1", "App1", [
        ("id", models.UUIDField(primary_key=True)), ("another_app", link)]))
    state.add_model(ModelState("testapp2", "App2", [
        ("id", models.UUIDField(primary_key=True))]))
    return state

before = project(models.UUIDField(null=True))
after = project(models.ForeignKey("testapp2.App2", null=True, on_delete=models.SET_NULL))
graph = MigrationGraph()
for label in ("testapp1", "testapp2"):
    graph.add_node((label, "0001_initial"), migrations.Migration("0001_initial", label))
changes = MigrationAutodetector(before, after).changes(graph=graph)
alteration, = changes["testapp1"]
assert ("testapp2", "0001_initial") in alteration.dependencies, alteration.dependencies
