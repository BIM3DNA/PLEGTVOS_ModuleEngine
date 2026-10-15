# -*- coding: utf-8 -*-
"""Scope budgets with fake API records; not Revit host acceptance."""
import unittest
from test_gc01_execution import (Object, ident, document, FixtureReader, reader,
                                 execution, core, Collector)
from test_gc01_diagnostics import wireframe


class ScopeReader(FixtureReader):
    def geometry(self, scope): return wireframe()


class CoverageTests(unittest.TestCase):
    def collect(self, memberships, limits=None, reverse=False):
        doc = document(0)
        doc.elements = [Object(Id=ident(i), Category=Object(Id=ident(1)), membership=m)
                        for i, m in enumerate(memberships)]
        if reverse: doc.elements.reverse()
        # Coordinate reads need a valid harmless stub for completeness checks.
        vector = Object(X=0, Y=0, Z=0)
        transform = Object(Origin=vector, BasisX=vector, BasisY=vector, BasisZ=vector)
        doc.ActiveProjectLocation = Object(Id=ident(900), GetTotalTransform=lambda: transform)
        control = execution.Control(limits=limits, clock=lambda: 0.0, sink=lambda lines: None)
        result = ScopeReader(doc, control).collect(Object(Id=ident(1405931)))
        return result

    def test_outside_does_not_spend_scope_detail_budget(self):
        result = self.collect(['OUTSIDE']*20+['INSIDE','CROSSING'], dict(candidates=2))
        self.assertEqual(2, len(result['elements']))
        self.assertEqual(22, len(result['coverage']['classification_ledger']))
        self.assertEqual(dict(INSIDE=1,CROSSING=1,OUTSIDE=20,UNKNOWN=0), result['summary']['classifications'])
        self.assertTrue(result['coverage']['scope_inventory_complete'])
        self.assertFalse(result['coverage']['truncated'])
        self.assertFalse(result['coverage']['complete'])  # dependency/topology acceptance is separate

    def test_exact_detail_batch_and_one_over_retained(self):
        exact = self.collect(['INSIDE']*3, dict(candidates=3))
        self.assertTrue(exact['coverage']['scope_inventory_complete'])
        over = self.collect(['INSIDE']*4, dict(candidates=3))
        self.assertEqual([], over['coverage']['limits_reached'])
        self.assertTrue(over['coverage']['scope_inventory_complete'])
        self.assertEqual(4, over['coverage']['classification_counts']['INSIDE'])
        self.assertEqual(4, sum(r['detail_retained'] for r in over['coverage']['classification_ledger']))

    def test_unknown_has_separate_budget_and_never_proves_complete(self):
        result = self.collect(['UNKNOWN']*3+['INSIDE']*2, dict(candidates=2,unknown_candidates=1))
        self.assertEqual(3, len(result['elements']))
        self.assertEqual(['unknown_candidates'], result['coverage']['limits_reached'])
        self.assertEqual(3, result['coverage']['classification_counts']['UNKNOWN'])
        self.assertFalse(result['coverage']['scope_inventory_complete'])
        result = self.collect(['UNKNOWN'])
        self.assertFalse(result['coverage']['truncated'])
        self.assertFalse(result['coverage']['scope_inventory_complete'])

    def test_scan_limit_still_conservative_without_extra_native_move(self):
        for size in (3,4):
            result = self.collect(['INSIDE']*size, dict(scanned_elements=3))
            self.assertEqual(['scanned_elements'], result['coverage']['limits_reached'])
            self.assertFalse(result['coverage']['scan_exhausted'])
            self.assertEqual(3, Collector.instances[-1].enumerator.moves)

    def test_reverse_collector_order_has_same_budgeted_snapshot(self):
        memberships = ['OUTSIDE','INSIDE','CROSSING','UNKNOWN','INSIDE']
        self.assertEqual(self.collect(memberships,dict(candidates=1)),
                         self.collect(memberships,dict(candidates=1),reverse=True))

    def test_expected_fast_omissions_are_aggregated(self):
        result = self.collect(['INSIDE']*3)
        omission = result['coverage']['fast_omissions']['connector_topology']
        self.assertEqual(dict(status='NOT_INSPECTED_FAST',elements=3), omission)
        self.assertIsNone(result['summary']['connectors'])
        self.assertFalse(any(i['field']=='connector_manager' for i in result['issues']))

    def test_optional_null_is_counted_but_exception_is_retained(self):
        control=execution.Control(clock=lambda:0.0,sink=lambda lines:None)
        r=reader.Reader(None,control)
        r.read('1','category',lambda:None,optional=True)
        self.assertEqual({'category':1},r.expected_absences)
        self.assertFalse(r.issues)
        def fail(): raise ValueError('synthetic API read failure')
        r.context.update(stage='candidate_collection',element_id='2')
        r.read('2','category',fail,optional=True)
        self.assertEqual('READ_ERROR',r.issues[0]['reason'])
        self.assertEqual('ValueError',r.issues[0]['exception_type'])
        self.assertEqual('2',r.issues[0]['context']['element_id'])
        self.assertTrue(r.issues[0]['traceback'])
        r.read('2','required_field',lambda:None)
        self.assertEqual('UNAVAILABLE',r.issues[1]['reason'])

    def test_unsupported_and_no_category_are_not_silently_dropped(self):
        doc=document(0)
        doc.elements=[Object(Id=ident(1),Category=None), Object(Id=ident(2),Category=Object(Id=ident(999)))]
        result=ScopeReader(doc,execution.Control(clock=lambda:0.0,sink=lambda lines:None)).collect(Object(Id=ident(1405931)))
        self.assertIsNone(result['coverage']['excluded'])
        self.assertIsNone(result['summary']['unsupported_categories'])
        self.assertEqual('NOT_INSPECTED_BY_FILTERED_COLLECTION',result['coverage']['excluded_category_inventory'])
        self.assertEqual({},result['coverage']['expected_absences'])
        self.assertFalse(any(i['field']=='category' for i in result['issues']))

    def test_document_identity_mismatch_is_not_a_baseline(self):
        a={'path':u'C:/models/bim3dnapc6.rvt','project_info_unique_id':'same'}
        b=dict(a,path=u'C:/models/e.avdovicQREF7.rvt')
        self.assertNotEqual(core.digest(a),core.digest(b))
        self.assertEqual('PENDING_EXACT_DOCUMENT_AND_SNAPSHOT_EVIDENCE',
                         self.collect([])['coverage']['baseline_comparison'])

    def test_unicode_ledger_and_json_bound(self):
        result=self.collect(['INSIDE'])
        result['coverage']['classification_ledger'][0]['key']=u'doc/GC01-\u010d-90\u00b0'
        encoded=core.canonical(result)
        self.assertIn('\\u010d',encoded)
        control=execution.Control(limits=dict(json_bytes=10),clock=lambda:0.0,sink=lambda lines:None)
        self.assertRaises(execution.Stopped,control.canonical,result)


if __name__ == '__main__': unittest.main()
