import django
from django.conf import settings
from django.db import migrations, models
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.graph import MigrationGraph
from django.db.migrations.state import ModelState, ProjectState

settings.configure(INSTALLED_APPS=[], SECRET_KEY="check", USE_I18N=False)
django.setup()

def order(owner):
    fields = [("id", models.AutoField(primary_key=True)), ("owner", owner)]
    return ModelState("orders", "Order", fields)

person = ModelState("people", "Person", [("id", models.UUIDField(primary_key=True))])
before, after = ProjectState(), ProjectState()
before.add_model(person)
after.add_model(person.clone())
before.add_model(order(models.UUIDField(null=True)))
after.add_model(order(models.ForeignKey("people.Person", null=True, on_delete=models.SET_NULL)))
graph = MigrationGraph()
for app in ("orders", "people"):
    graph.add_node((app, "0001_initial"), migrations.Migration("0001_initial", app))
changes = MigrationAutodetector(before, after).changes(graph, migration_name="owner_fk")
assert ("people", "0001_initial") in changes["orders"][0].dependencies
