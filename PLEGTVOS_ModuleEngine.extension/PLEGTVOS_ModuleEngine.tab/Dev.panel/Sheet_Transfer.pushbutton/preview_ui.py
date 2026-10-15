# -*- coding: utf-8 -*-
from pyrevit import forms
from preview_models import BANNER

class Choice(forms.TemplateListItem):
    @property
    def name(self):
        return self.item[0]

def choose_document(pairs, title):
    choices = []
    for doc, row in sorted(pairs, key=lambda p: (not p[1]['proposed_source'], p[1]['title'], p[1]['key'])):
        label = u'{0}{1} | {2} | {3}'.format('[Proposed source] ' if row['proposed_source'] else '', row['title'], row['path'] or '[unsaved]', row['key'])
        choices.append(Choice((label, doc, row)))
    chosen = forms.SelectFromList.show(choices, title=title, multiselect=False, button_name='Select')
    return (chosen[1], chosen[2]) if chosen else None

def choose_sheets(pairs):
    choices = []
    for element, row in pairs:
        choices.append(Choice((u'{0} | {1} | {2}'.format(row['number'], row['name'], row['unique_id']), element, row)))
    selected = forms.SelectFromList.show(choices, title='Select source sheets - preview only', multiselect=True, button_name='Preview')
    return [(x[1], x[2]) for x in selected] if selected else []

def notice(message):
    forms.alert(BANNER + u'\n\n' + message, title='Sheet Transfer - M1 preview', warn_icon=False)
