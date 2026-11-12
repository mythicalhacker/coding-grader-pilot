from django import forms
from django.conf import settings
from django.contrib.postgres.forms import SplitArrayField

settings.configure(USE_I18N=False)
checkbox = forms.CheckboxInput(check_test=lambda value: value is False)
field = SplitArrayField(forms.BooleanField(widget=checkbox), size=3)
context = field.widget.get_context('flags', [False, True, False], {})
children = context['widget']['subwidgets']
assert [bool(child['attrs'].get('checked')) for child in children] == [True, False, True]
