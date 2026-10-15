# -*- coding: utf-8 -*-
"""Host-independent F1 lifecycle. No retain path; no source mutations."""
import traceback

MODES = ('NORMAL', 'DURING_CREATE', 'AFTER_CREATE', 'AFTER_COMMIT')


def validate_destination(state, same_source, acknowledged):
    if same_source or acknowledged is not True:
        raise ValueError('Distinct explicitly acknowledged disposable destination required')
    for field in ('valid', 'saved_local', 'project'):
        if state.get(field) is not True:
            raise ValueError('Unsupported destination: ' + field)
    for field in ('read_only', 'linked', 'modifiable', 'workshared', 'cloud', 'modified'):
        if state.get(field) is not False:
            raise ValueError('Destination must be false for: ' + field)


def execute(host, confirmed, mode='NORMAL'):
    report = {'version': 'SHEET_TRANSFER_M2_F1/2', 'status': 'FAIL',
              'mode': mode, 'lifecycle': [], 'errors': [], 'created': None,
              'rollback_verified': False, 'verification_scope':
              'source/destination sheet and titleblock instance inventories, selected type, observable document state; other elements and Undo NOT_INSPECTED'}
    group = None
    transaction = None
    group_attempted = False
    cleanup_ok = True
    experiment_ok = False

    def error(stage):
        report['errors'].append({'stage': stage, 'traceback': traceback.format_exc()})

    def record(label, value):
        report['lifecycle'].append({'operation': label, 'status': value})
        return value

    def checked_start(obj, label):
        result = record(label + '.Start', obj.Start())
        actual = record(label + '.GetStatus', obj.GetStatus())
        if result != 'Started' or actual != 'Started':
            raise RuntimeError(label + ' did not start')

    try:
        if not confirmed:
            report['reason'] = 'CANCELLED_BEFORE_TRANSACTION'
            return report
        if mode not in MODES:
            raise ValueError('Unknown fault mode')
        report['context'] = host.validate()
        report['before'] = host.snapshot()
        host.preflight_report(report)
        group = host.group()
        group_attempted = True
        checked_start(group, 'group')
        transaction = host.transaction()
        checked_start(transaction, 'transaction')
        host.configure_failures(transaction)
        # Adapter records a created identity immediately, even if later inspection fails.
        host.create(report, mode == 'DURING_CREATE')
        host.verify_created(report)
        if mode == 'AFTER_CREATE':
            raise RuntimeError('INJECTED_AFTER_CREATE_BEFORE_COMMIT')
        result = record('transaction.Commit', transaction.Commit())
        actual = record('transaction.GetStatus', transaction.GetStatus())
        if result != 'Committed' or actual != 'Committed':
            raise RuntimeError('Inner commit not confirmed')
        host.verify_created(report)
        if mode == 'AFTER_COMMIT':
            raise RuntimeError('INJECTED_AFTER_COMMIT_BEFORE_GROUP_ROLLBACK')
        experiment_ok = True
    except Exception:
        error('experiment')
    finally:
        # Query real status even if Start raised after changing native state.
        if transaction is not None:
            try:
                status = record('transaction.cleanup.GetStatus', transaction.GetStatus())
                if status in ('Started', 'Pending'):
                    result = record('transaction.RollBack', transaction.RollBack())
                    status = record('transaction.after_rollback.GetStatus', transaction.GetStatus())
                    if result != 'RolledBack' or status != 'RolledBack':
                        cleanup_ok = False
                elif status not in ('Uninitialized', 'Committed', 'RolledBack'):
                    cleanup_ok = False
            except Exception:
                cleanup_ok = False
                error('transaction_cleanup')
        if group is not None:
            try:
                status = record('group.cleanup.GetStatus', group.GetStatus())
                if status in ('Started', 'Pending'):
                    result = record('group.RollBack', group.RollBack())
                    status = record('group.after_rollback.GetStatus', group.GetStatus())
                    if result != 'RolledBack' or status != 'RolledBack':
                        cleanup_ok = False
                elif status != 'RolledBack':
                    cleanup_ok = False
            except Exception:
                cleanup_ok = False
                error('group_cleanup')
        # Never Dispose unresolved native transactions: retain for explicit intervention.
        if cleanup_ok:
            for obj in (transaction, group):
                if obj is not None:
                    try:
                        obj.Dispose()
                    except Exception:
                        cleanup_ok = False
                        error('dispose')
        if not cleanup_ok:
            host.hold_unresolved(transaction, group)

    if group_attempted:
        report['status'] = 'CRITICAL'
        if cleanup_ok:
            try:
                report['after'] = host.snapshot()
                report['created_absent'] = host.created_absent(report)
                report['inventories_equal'] = report['before'] == report['after']
                report['rollback_verified'] = report['created_absent'] and report['inventories_equal']
                if report['rollback_verified']:
                    report['status'] = 'PASS' if experiment_ok else 'FAIL'
            except Exception:
                error('post_rollback_verification')
    if report['status'] == 'CRITICAL':
        host.hold_unresolved(transaction, group)
        report['instruction'] = 'CRITICAL: DO NOT SAVE the disposable destination. Stop testing and request intervention.'
    report['failures'] = host.failures
    return report
