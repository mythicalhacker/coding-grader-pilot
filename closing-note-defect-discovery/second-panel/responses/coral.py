from django.conf import settings

if not settings.configured:
    settings.configure(USE_I18N=False)

from django import forms
from django.contrib.postgres.forms import SplitArrayWidget

checkbox = forms.CheckboxInput(check_test=lambda value: value == 'selected')
widget = SplitArrayWidget(widget=checkbox, size=2)
context = widget.get_context('choices', ['selected', 'unselected'], {})
children = context['widget']['subwidgets']
assert [bool(child['attrs'].get('checked')) for child in children] == [True, False]
