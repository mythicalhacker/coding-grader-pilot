from django.conf import settings
from django.forms import CheckboxInput
from django.contrib.postgres.forms.array import SplitArrayWidget

settings.configure(USE_I18N=False)
checkbox = CheckboxInput(check_test=lambda value: value == "enabled")
widget = SplitArrayWidget(checkbox, size=2)
context = widget.get_context("flags", ["enabled", "disabled"], {})
states = ["checked" in child["attrs"] for child in context["widget"]["subwidgets"]]
assert states == [True, False], states
