# -*- coding: utf-8 -*-
__persistentengine__ = True
__title__ = "F1 Probe\nROLLBACK ONLY"
__doc__ = "EXPERIMENTAL: disposable saved destination only. Never retains a sheet."
from Autodesk.Revit import DB
from pyrevit import forms
import traceback
from f1_core import execute, validate_destination, MODES
from f1_revit import Host, document_state, collect, symbol_info, same_document
from f1_reporting import reserve_directory, write, text_type

BANNER = u'EXPERIMENTAL F1 \u2014 DISPOSABLE DESTINATION ONLY'


class Choice(forms.TemplateListItem):
    @property
    def name(self): return self.item[0]


def choose(items, title):
    return forms.SelectFromList.show([Choice(x) for x in items], title=title,
                                     multiselect=False, button_name='Select explicitly')


def main():
    directory = reserve_directory()
    report = {'version': 'SHEET_TRANSFER_M2_F1/2', 'status': 'FAIL',
              'reason': 'CANCELLED_BEFORE_TRANSACTION', 'errors': [], 'lifecycle': []}
    host = None
    try:
        documents = []
        iterator = __revit__.Application.Documents.ForwardIterator()
        iterator.Reset()
        try:
            while iterator.MoveNext():
                doc = iterator.Current
                if doc.IsValidObject and not doc.IsFamilyDocument and not doc.IsLinked:
                    documents.append(doc)
                if len(documents) > 100: raise ValueError('Too many open documents')
        finally:
            if hasattr(iterator, 'Dispose'): iterator.Dispose()
        choices = []
        for index, doc in enumerate(documents):
            choices.append((u'{0}: {1} | {2}'.format(index + 1, doc.Title, doc.PathName or '[UNSAVED]'), doc))
        source = choose(choices, 'F1: select source for read-only before/after comparison')
        if not source: return
        report['source'] = document_state(source[1])
        destinations = [x for x in choices if not same_document(x[1], source[1])]
        destination = choose(destinations, 'F1: explicitly select a SAVED DISPOSABLE destination') if destinations else None
        if not destination:
            report['reason'] = 'NO_DESTINATION_OR_CANCELLED'
            return
        state = document_state(destination[1])
        report['destination'] = state
        # Structural eligibility first, then independent disposable acknowledgement.
        validate_destination(state, same_document(source[1], destination[1]), True)
        acknowledgement = forms.ask_for_string(default='', title='Disposable destination acknowledgement',
            prompt=u'{0}\n{1}\nType DISPOSABLE TEST COPY to acknowledge this exact destination.'.format(BANNER, state['path']))
        if acknowledgement != 'DISPOSABLE TEST COPY': return
        symbols = []
        for symbol in collect(destination[1], cls=DB.FamilySymbol, category=DB.BuiltInCategory.OST_TitleBlocks, cap=1000):
            info = symbol_info(destination[1], symbol)
            symbols.append((u'{0} : {1} | {2}'.format(info['family'], info['name'], info['unique_id']), symbol))
        if not symbols:
            report['reason'] = 'NO_AVAILABLE_TITLEBLOCK_TYPES'
            return
        selected = choose(sorted(symbols, key=lambda x: x[0]), 'F1: select EXISTING destination title-block TYPE')
        if not selected: return
        report['selected_type'] = symbol_info(destination[1], selected[1])
        mode = forms.SelectFromList.show(list(MODES), title='F1 experiment / fault injection', multiselect=False)
        if not mode: return
        host = Host(source[1], destination[1], selected[1], True, state, directory)
        confirmed = forms.alert(u'{0}\n\nDestination: {1}\nTitle block: {2}\nMode: {3}\n\n'
            u'This probe temporarily creates one sheet and title block, validates them, and rolls back all changes. '
            u'The destination must be a disposable test copy. No save or synchronization. Run this experiment?'.format(
                BANNER, state['path'], selected[0], mode), title='F1 separate final confirmation',
                yes=True, no=True, ok=False, warn_icon=True)
        if confirmed is not True:
            report['reason'] = 'CANCELLED_FINAL_CONFIRMATION'
            return
        report = execute(host, True, mode)
    except Exception:
        report['errors'].append({'stage': 'selection_or_preflight', 'traceback': text_type(traceback.format_exc())})
    finally:
        try:
            write(directory, report, 'final')
            message = 'Status: ' + report['status'] + '\nRollback verified: ' + str(report.get('rollback_verified', False))
            if report['status'] == 'CRITICAL': message += '\nDO NOT SAVE the disposable destination. Stop and request intervention.'
            forms.alert(BANNER + u'\n' + message + u'\nReport: ' + text_type(directory), title='F1 experiment result')
        except Exception:
            if host is not None:
                host.hold_unresolved(None, None)
            forms.alert('CRITICAL: experiment reporting failed. DO NOT SAVE the disposable destination. '
                        'Stop and request intervention. Evidence directory: ' + text_type(directory), title='F1 CRITICAL')


if __name__ == '__main__':
    main()
