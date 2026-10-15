# -*- coding: utf-8 -*-
"""Native filter adapter contracts with fake DB; real Revit acceptance is separate."""
import unittest
from test_gc01_execution import (Object, ident, document, reader, execution,
                                 Collector, Enumerator, CategoryFilter)
from test_gc01_scope_coverage import ScopeReader


def fixture(elements):
    doc=document(0); doc.elements=elements
    vector=Object(X=0,Y=0,Z=0)
    transform=Object(Origin=vector,BasisX=vector,BasisY=vector,BasisZ=vector)
    doc.ActiveProjectLocation=Object(Id=ident(900),GetTotalTransform=lambda:transform)
    return doc


def element(i, category=1, membership='INSIDE', is_type=False):
    return Object(Id=ident(i),Category=Object(Id=ident(category)),membership=membership,is_type=is_type)


class FilterTests(unittest.TestCase):
    def control(self, **limits):
        return execution.Control(limits=limits,clock=lambda:0.0,sink=lambda lines:None)
    def collect(self, doc, **limits):
        return ScopeReader(doc,self.control(**limits)).collect(Object(Id=ident(1405931)))

    def test_exact_category_values_and_typed_list_path(self):
        r=reader.Reader(None,self.control())
        categories=r.prepare_categories()
        f=r.category_filter(categories)
        self.assertEqual(18,len(f.categories))
        self.assertEqual([getattr(reader.DB.BuiltInCategory,n) for n in reader.CATEGORIES],f.categories)
        self.assertEqual(set(categories),set(str(int(c)) for c in f.categories))

    def test_all_18_supported_and_type_filter(self):
        values=[element(i,category=i) for i in range(1,19)]
        values.extend([element(100,category=999),element(101,category=1,is_type=True)])
        result=self.collect(fixture(values))
        self.assertEqual(18,result['coverage']['processing_counts']['scanned_elements'])
        self.assertEqual(set(str(i) for i in range(1,19)),set(r['category_id'] for r in result['elements']))
        self.assertEqual(18,result['summary']['classifications']['INSIDE'])
        self.assertTrue(result['coverage']['scope_inventory_complete'])
        self.assertTrue(Collector.instances[-1].instances_only)
        self.assertTrue(Collector.instances[-1].category_filter.disposed)

    def test_unsupported_does_not_consume_budget_or_claim_zero(self):
        values=[element(i,999) for i in range(8448)]
        values.extend([element(9000+i,membership='INSIDE' if i<460 else 'OUTSIDE') for i in range(1552)])
        result=self.collect(fixture(values))
        self.assertEqual(1552,result['coverage']['processing_counts']['scanned_elements'])
        self.assertEqual(dict(INSIDE=460,OUTSIDE=1092,CROSSING=0,UNKNOWN=0),result['summary']['classifications'])
        self.assertEqual(460,len(result['elements']))
        self.assertTrue(result['coverage']['scan_exhausted'])
        self.assertIsNone(result['coverage']['excluded'])
        self.assertIsNone(result['summary']['unsupported_categories'])
        self.assertEqual('NOT_INSPECTED_BY_FILTERED_COLLECTION',result['coverage']['excluded_category_inventory'])
        # This synthetic fixture is not a prediction of the real complete-document totals.

    def test_missing_or_changed_category_fails_closed(self):
        r=reader.Reader(None,self.control()); categories=r.prepare_categories()
        categories.pop(next(iter(categories)))
        self.assertRaises(execution.Stopped,r.category_filter,categories)
        categories=r.prepare_categories();categories['999']=categories.pop('1')
        self.assertRaises(execution.Stopped,r.category_filter,categories)

    def test_native_filter_failure_is_not_unfiltered_fallback(self):
        original=reader.DB.ElementMulticategoryFilter
        before=len(Collector.instances)
        def fail(values): raise ValueError('filter construction failed')
        try:
            reader.DB.ElementMulticategoryFilter=fail
            self.assertRaises(ValueError,self.collect,fixture([element(1)]))
        finally: reader.DB.ElementMulticategoryFilter=original
        self.assertEqual(before,len(Collector.instances))

    def test_empty_and_below_limit_exhaustion(self):
        for values in ([],[element(1)]):
            result=self.collect(fixture(values),scanned_elements=2)
            self.assertTrue(result['coverage']['scan_exhausted'])
            self.assertTrue(result['coverage']['scope_inventory_complete'])
            self.assertEqual([],result['coverage']['inventory_blockers'])

    def test_at_and_over_scan_limit_exhaustion_unproven(self):
        for size in (2,3):
            result=self.collect(fixture([element(i) for i in range(size)]),scanned_elements=2)
            self.assertFalse(result['coverage']['scan_exhausted'])
            self.assertFalse(result['coverage']['scope_inventory_complete'])
            self.assertIn('scanned_elements',result['coverage']['inventory_blockers'])
            self.assertEqual(2,Collector.instances[-1].enumerator.moves)

    def test_duplicate_id_not_counted_twice_and_blocks_acceptance(self):
        result=self.collect(fixture([element(1),element(1)]))
        self.assertEqual(1,len(result['coverage']['classification_ledger']))
        self.assertEqual(1,result['coverage']['duplicate_observations'])
        self.assertEqual(2,result['coverage']['processing_counts']['scanned_elements'])
        self.assertIn('DUPLICATE_IDENTITIES',result['coverage']['inventory_blockers'])
        self.assertIn('DUPLICATE_ELEMENT_ID',[issue['code'] for issue in result['issues']])

    def test_missing_document_identity_blocks_complete(self):
        doc=fixture([]);doc.ProjectInformation.UniqueId=None
        result=self.collect(doc)
        self.assertTrue(result['coverage']['scan_exhausted'])
        self.assertIn('IDENTITY_UNAVAILABLE',result['coverage']['inventory_blockers'])

    def test_central_guid_error_preserved_and_unavailable(self):
        class InapplicableDataException(Exception): pass
        class Workshared(Object):
            @property
            def WorksharingCentralGUID(self): raise InapplicableDataException('synthetic file-based central')
        doc=Workshared(**fixture([]).__dict__);doc.IsWorkshared=True
        doc.GetWorksharingCentralModelPath=lambda:Object(ServerPath=True,Empty=False)
        result=self.collect(doc)
        self.assertIsNone(result['document']['central_guid'])
        self.assertEqual('UNAVAILABLE',result['document']['central_guid_status'])
        errors=[i for i in result['issues'] if i['field']=='central_guid']
        self.assertEqual(1,len(errors))
        self.assertEqual('READ_ERROR',errors[0]['reason'])
        self.assertEqual('InapplicableDataException',errors[0]['exception_type'])
        self.assertTrue(errors[0]['traceback'])
        self.assertIn('API_READ_ERRORS',result['coverage']['inventory_blockers'])
        self.assertTrue(result['coverage']['scan_exhausted'])

    def test_iterator_error_never_implies_exhaustion(self):
        enum=Enumerator([],fail='move')
        bounded=self.control().element_items(Object(GetElementIterator=lambda:enum),'scanned_elements')
        self.assertRaises(ValueError,list,bounded)
        self.assertFalse(bounded.exhausted)
        self.assertTrue(bounded.closed)
        self.assertEqual(1,enum.disposals)

    def test_native_filter_failure_during_application_cleans_up(self):
        original=Collector.WherePasses
        filters=[]
        def fail(collector,category_filter):
            filters.append(category_filter)
            raise ValueError('apply failed')
        try:
            Collector.WherePasses=fail
            self.assertRaises(ValueError,self.collect,fixture([]))
        finally: Collector.WherePasses=original
        self.assertTrue(Collector.instances[-1].disposed)
        self.assertTrue(filters[0].disposed)


if __name__ == '__main__': unittest.main()
