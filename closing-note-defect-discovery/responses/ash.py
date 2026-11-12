import django
from django.conf import settings

settings.configure(USE_I18N=False, SECRET_KEY="test")
django.setup()

from django import forms
from django.contrib.postgres.forms import SplitArrayField

checkbox = forms.CheckboxInput(check_test=lambda available: available is False)
field = SplitArrayField(forms.BooleanField(widget=checkbox), size=2)
context = field.widget.get_context("unavailable", [False, True], {})
boxes = context["widget"]["subwidgets"]
assert ["checked" in box["attrs"] for box in boxes] == [True, False]
