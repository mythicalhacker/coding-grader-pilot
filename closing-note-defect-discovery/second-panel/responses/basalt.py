import django
from django.conf import settings
from django.db import migrations, models
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.graph import MigrationGraph
from django.db.migrations.state import ModelState, ProjectState

settings.configure(INSTALLED_APPS=[], USE_I18N=False, SECRET_KEY="test")
django.setup()

def state_with(link):
    state = ProjectState()
    state.add_model(ModelState("catalog", "Product", [("id", models.UUIDField(primary_key=True))]))
    state.add_model(ModelState("sales", "Order", [
        ("id", models.AutoField(primary_key=True)), ("product", link),
    ]))
    return state

graph = MigrationGraph()
for app in ("catalog", "sales"):
    graph.add_node((app, "0001_initial"), migrations.Migration("0001_initial", app))
before = state_with(models.UUIDField(null=True))
after = state_with(models.ForeignKey("catalog.Product", on_delete=models.SET_NULL, null=True))
changes = MigrationAutodetector(before, after).changes(graph)
dependencies = changes["sales"][0].dependencies
assert any(app == "catalog" and name in ("0001_initial", "__first__", "__latest__") for app, name in dependencies), dependencies
