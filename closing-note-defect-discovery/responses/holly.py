import django
from django.conf import settings
from django.db import migrations, models
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.graph import MigrationGraph
from django.db.migrations.state import ModelState, ProjectState

settings.configure(INSTALLED_APPS=[], SECRET_KEY="probe")
django.setup()

def entry(link):
    fields = [("id", models.AutoField(primary_key=True)), ("link", link)]
    return ModelState("alpha", "Entry", fields)

before = ProjectState({("alpha", "entry"): entry(models.UUIDField(null=True))})
target = ModelState("beta", "Target", [("id", models.UUIDField(primary_key=True))])
link = models.ForeignKey("beta.Target", null=True, on_delete=models.SET_NULL)
after = ProjectState({("alpha", "entry"): entry(link), ("beta", "target"): target})
graph = MigrationGraph()
for app in ("alpha", "beta"):
    graph.add_node((app, "0001_initial"), migrations.Migration("0001_initial", app))

changes = MigrationAutodetector(before, after).changes(graph, migration_name="link_target")
create_target, = changes["beta"]
alter_entry, = changes["alpha"]
assert ("beta", create_target.name) in alter_entry.dependencies
