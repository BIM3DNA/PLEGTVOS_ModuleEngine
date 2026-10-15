# -*- coding: utf-8 -*-
"""Bounded fake-reader checks; never imports or executes the pyRevit button."""
import itertools
import json
import os
import sys
import types
import unittest
from test_gc01_diagnostics import BUTTON
sys.path.insert(0, BUTTON)
import execution_control as execution
import diagnostic_core as core


class Object(object):
    def __init__(self, **values): self.__dict__.update(values)


def ident(value): return Object(Value=value)


class Curve(object): pass
class Family(object): pass


class Enumerator(object):
    def __init__(self, values, fail=None):
        self.values=values;self.fail=fail;self.disposals=0;self.moves=0;self.current=None
    def Reset(self):
        if self.fail=='reset': raise ValueError('reset failed')
        self.iterator=iter(self.values)
    def MoveNext(self):
        self.moves+=1
        if self.fail=='move': raise ValueError('move failed')
        try: self.current=next(self.iterator);return True
        except StopIteration:return False
    @property
    def Current(self):
        if self.fail=='current':raise ValueError('current failed')
        return self.current
    def Dispose(self):self.disposals+=1


class CategoryList(list):
    def Add(self, value): self.append(value)


class CategoryFilter(object):
    def __init__(self, categories): self.categories=list(categories); self.disposed=False
    def Dispose(self): self.disposed=True


class FilteredValues(object):
    def __init__(self, values, categories, instances_only):
        self.values=values; self.categories=categories; self.instances_only=instances_only
    def __iter__(self): self.iterator=iter(self.values); return self
    def next(self):
        while True:
            value=next(self.iterator)
            if self.instances_only and getattr(value,'is_type',False): continue
            cat=getattr(value,'Category',None)
            if self.categories is None or (cat is not None and cat.Id.Value in self.categories): return value
    __next__=next


class Collector(object):
    instances = []
    def __init__(self, doc):
        self.doc = doc; self.links = False; self.disposed = False
        self.category_filter=None; self.instances_only=False
        Collector.instances.append(self)
    def WhereElementIsNotElementType(self): self.instances_only=True; return self
    def WherePasses(self, category_filter): self.category_filter=category_filter; return self
    def OfClass(self, kind): self.links = True; return self
    def __iter__(self): return iter([]) if self.links else iter(self.doc.elements)
    def GetElementIterator(self):
        self.enumerator=Enumerator(FilteredValues(self.doc.elements,
            self.category_filter.categories if self.category_filter else None, self.instances_only))
        return self.enumerator
    def Dispose(self): self.disposed = True


def reader_module():
    # Only the read adapter is loaded with a minimal DB stub; no Revit assembly.
    autodesk = types.ModuleType('Autodesk')
    revit = types.ModuleType('Autodesk.Revit')
    revit.DB = Object(MEPCurve=Curve, FamilyInstance=Family, FilteredElementCollector=Collector,
                      RevitLinkInstance=object, BuiltInCategory=Object(), ElementMulticategoryFilter=CategoryFilter)
    original = dict((k, sys.modules.get(k)) for k in ('Autodesk', 'Autodesk.Revit'))
    try:
        sys.modules['Autodesk'] = autodesk; sys.modules['Autodesk.Revit'] = revit
        module = types.ModuleType('gc01_reader_fixture')
        with open(os.path.join(BUTTON, 'revit_reader.py'), 'rb') as stream:
            exec(compile(stream.read(), 'revit_reader.py', 'exec'), module.__dict__)
    finally:
        for k, value in original.items():
            if value is None: del sys.modules[k]
            else: sys.modules[k] = value
    for index, name in enumerate(module.CATEGORIES):
        setattr(revit.DB.BuiltInCategory, name, index+1)
    module.production_category_list = module.builtin_category_list
    module.builtin_category_list = CategoryList
    return module


reader = reader_module()


class FixtureReader(reader.Reader):
    def __init__(self, doc, control):
        reader.Reader.__init__(self, doc, control); self.connector_calls = 0
    def ref(self, element):
        if element is None: return None
        return dict(id=reader.eid(element.Id), key='doc/'+reader.eid(element.Id), unique_id='uid-'+reader.eid(element.Id), name='fixture')
    def geometry(self, scope): return []
    def bbox(self, element): return None
    def element(self, element, frame):
        return dict(self.ref(element), membership=getattr(element, 'membership', 'INSIDE'), category_id=reader.eid(element.Category.Id), family_type={},
                    parameters={}, system_key=None,
                    location=dict(is_line=True, endpoints_ft=[[0,0,1],[10,0,0]], length_ft=10))
    def connectors(self, element, row):
        self.connector_calls += 1
        return [], []


def document(count):
    return Object(Title='fixture', PathName='fixture.rvt', ProjectInformation=Object(UniqueId='doc'),
        IsWorkshared=False, IsModified=False, ActiveView=Object(UniqueId='view'), IsModelInCloud=False,
        ActiveProjectLocation=None,
        elements=(Object(Id=ident(i),Category=Object(Id=ident(1))) for i in range(count)))


class ExecutionTests(unittest.TestCase):
    def control(self, mode='FAST', **limits):
        return execution.Control(mode, limits=limits, sink=lambda lines: None, clock=lambda: 0)

    def test_infinite_iterator_stops_without_extra_next(self):
        control = self.control(candidates=3)
        visited = []
        def values():
            for n in itertools.count(): visited.append(n); yield n
        self.assertEqual([0,1,2], list(control.items(values(), 'candidates')))
        self.assertEqual(3,len(visited))
        self.assertEqual(['candidates'],control.truncated)

    def test_global_reference_budget_across_owners(self):
        control = self.control(references=3,references_per_connector=2)
        first = list(control.items(itertools.count(), 'references_per_connector','references'))
        second = list(control.items(itertools.count(), 'references_per_connector','references'))
        self.assertEqual(3,len(first)+len(second))
        self.assertIn('references',control.truncated)

    def test_large_collection_truncated_and_disposed(self):
        control = self.control(candidates=4,scanned_elements=100)
        r = FixtureReader(document(1000000), control)
        snapshot = r.collect(Object(Id=ident(1405931)))
        self.assertEqual(100,len(snapshot['elements']))
        self.assertTrue(snapshot['coverage']['truncated'])
        self.assertFalse(snapshot['coverage']['complete'])
        self.assertIn('scanned_elements',snapshot['coverage']['limits_reached'])
        self.assertTrue(Collector.instances[-1].disposed)
        self.assertEqual(0,r.connector_calls)
        self.assertIsNone(snapshot['summary']['connectors'])
        self.assertEqual(100,snapshot['summary']['measured_slopes'])
        self.assertEqual(snapshot,json.loads(control.canonical(snapshot)))

    def test_fast_full_execution(self):
        for mode, expected in (('FAST',0),('FULL',3)):
            r = FixtureReader(document(3),self.control(mode))
            snapshot = r.collect(Object(Id=ident(1405931)))
            self.assertEqual(expected,r.connector_calls)
            self.assertEqual(mode,snapshot['coverage']['mode'])
            self.assertFalse(snapshot['coverage']['truncated'])
            self.assertFalse(snapshot['coverage']['complete'])
        self.assertFalse(execution.FULL_HOST_ENABLED)

    def test_cycles_are_direct_only_and_deduplicated(self):
        control = self.control('FULL')
        r = reader.Reader(None,control)
        owner = Object(Id=ident(1))
        r.ref = lambda obj: dict(key=str(obj.Id.Value), id=str(obj.Id.Value))
        calls = []
        def descriptor(connector,key):
            calls.append(connector.Id)
            return dict(key=key+'/'+str(connector.Id), connector_type='Logical')
        r.descriptor = descriptor
        a = Object(Id=1,Owner=owner)
        b = Object(Id=2,Owner=owner)
        a.AllRefs = [a,b,b]; b.AllRefs = [a]
        element = Curve(); element.ConnectorManager = Object(Connectors=[a])
        rows, edges = r.connectors(element,dict(key='1'))
        self.assertEqual(1,len(rows))
        self.assertEqual(2,len(rows[0]['references']))
        self.assertEqual(2,len(edges))
        self.assertEqual(3,control.counts['references'])
        self.assertEqual(1,control.counts['connectors'])

    def test_infinite_connector_references_bounded(self):
        control=self.control('FULL',references_per_connector=3)
        r=reader.Reader(None,control)
        r.ref=lambda obj: dict(key='owner')
        r.descriptor=lambda obj,key:dict(key=str(obj.Id),connector_type='Logical')
        connector=Object(Id=1,Owner=object());connector.AllRefs=itertools.repeat(connector)
        element=Curve();element.ConnectorManager=Object(Connectors=[connector])
        rows,edges=r.connectors(element,dict(key='owner'))
        self.assertEqual(1,len(edges))
        self.assertIn('references_per_connector',control.truncated)

    def test_fast_element_skips_detailed_api_reads(self):
        r=reader.Reader(None,self.control())
        r.ref=lambda obj:dict(key='owner',id='1')
        r.bbox=lambda obj:None
        r.location=lambda obj:dict(kind='NONE')
        element=Object(Id=ident(1),Category=Object(Id=ident(1),Name='Pipe'),
                       GetType=lambda:Object(Name='Pipe'))
        # No GetTypeId, parameters, system, connector manager or dependencies:
        # any accidental detailed API access would fail this call.
        row=r.element(element,None)
        self.assertEqual('NOT_INSPECTED_FAST',row['detail_status'])
        self.assertEqual({},row['parameters'])
        self.assertEqual([],row['dependencies'])

    def test_category_names_and_numeric_conversion(self):
        names = ('OST_PipeCurves', 'OST_FlexPipeCurves', 'OST_PipeFitting',
                 'OST_PipeAccessory', 'OST_DuctCurves', 'OST_FlexDuctCurves',
                 'OST_DuctFitting', 'OST_DuctAccessory', 'OST_MechanicalEquipment',
                 'OST_PlumbingFixtures', 'OST_Sprinklers', 'OST_Conduit',
                 'OST_ConduitFitting', 'OST_CableTray', 'OST_CableTrayFitting',
                 'OST_PipeInsulations', 'OST_DuctInsulations', 'OST_DuctLinings')
        self.assertEqual(names,reader.CATEGORIES)
        class EnumValue(object):
            def __init__(self,value): self.value=value
            def __int__(self): return self.value
        # Synthetic negative IDs test the boundary; these are NOT Revit constants.
        values=Object(**dict((name,EnumValue(-100-index)) for index,name in enumerate(names)))
        r=reader.Reader(None,self.control())
        expected=dict((str(-100-index),name) for index,name in enumerate(names))
        self.assertEqual(expected,r.prepare_categories(values))
        self.assertEqual(core.canonical(expected),core.canonical(r.prepare_categories(values)))

    def test_missing_unsupported_category_values_are_explicit(self):
        values=Object(OST_PipeCurves=-100,OST_FlexPipeCurves=object())
        r=reader.Reader(None,self.control())
        self.assertEqual({'-100':'OST_PipeCurves'},r.prepare_categories(values))
        self.assertEqual(17,len(r.issues))
        self.assertTrue(all(issue['reason']=='READ_ERROR' for issue in r.issues))
        self.assertEqual('OST_FlexPipeCurves',r.issues[0]['field'])
        self.assertEqual('TypeError',r.issues[0]['exception_type'])
        self.assertEqual('AttributeError',r.issues[-1]['exception_type'])

    def test_candidate_checkpoint_order(self):
        events=[]
        control=self.control()
        self.assertEqual([1],list(control.items([1],'scanned_elements',checkpoint=events.append)))
        self.assertEqual(['bounded_iterator_enter; iter_before',
                         'iter_after','first_next_before','first_next_after'],events)
        self.assertEqual(1,control.counts['scanned_elements'])
        self.assertFalse(control.truncated)

    def test_failed_iterator_context_is_not_category_setup(self):
        class BrokenIterable(object):
            def __iter__(self): raise ValueError('synthetic iterator failure')
        doc=document(0);doc.elements=BrokenIterable()
        r=FixtureReader(doc,self.control())
        self.assertRaises(ValueError,r.collect,Object(Id=ident(1405931)))
        self.assertEqual('candidate_collection_setup',r.context['stage'])
        self.assertEqual('element_iterator_get_after; reset_before',r.context['field'])
        self.assertIsNone(r.context['element_id'])
        self.assertTrue(Collector.instances[-1].disposed)

    def test_first_next_failure_checkpoint(self):
        class BrokenNext(object):
            def __iter__(self): return self
            def __next__(self): raise ValueError('synthetic first next failure')
            next=__next__
        r=reader.Reader(None,self.control())
        def consume():
            return list(r.control.items(BrokenNext(),'scanned_elements',checkpoint=r.candidate_checkpoint))
        self.assertRaises(ValueError,consume)
        self.assertEqual('first_next_before',r.context['field'])

    def test_native_empty_and_one_element(self):
        for values in ([],[42]):
            enum=Enumerator(values)
            bounded=self.control().element_items(Object(GetElementIterator=lambda:enum),'scanned_elements')
            self.assertEqual(values,list(bounded))
            self.assertEqual(1,enum.disposals)
            bounded.close();self.assertEqual(1,enum.disposals)

    def test_native_limit_no_lookahead_and_deterministic_order(self):
        results=[]
        for attempt in range(2):
            enum=Enumerator(range(1000));control=self.control(scanned_elements=3)
            bounded=control.element_items(Object(GetElementIterator=lambda:enum),'scanned_elements')
            results.append(list(bounded))
            self.assertEqual(3,enum.moves)
            self.assertEqual(1,enum.disposals)
            self.assertIn('scanned_elements',control.coverage()['limits_reached'])
            self.assertFalse(control.coverage()['complete'])
        self.assertEqual([[0,1,2],[0,1,2]],results)

    def test_native_reset_move_current_errors_cleanup(self):
        for operation in ('reset','move','current'):
            enum=Enumerator([1],fail=operation)
            bounded=self.control().element_items(Object(GetElementIterator=lambda:enum),'scanned_elements')
            self.assertRaises(ValueError,list,bounded)
            self.assertEqual(1,enum.disposals)

    def test_native_creation_exception_and_no_python_adaptation(self):
        class NativeOnly(object):
            def __iter__(self):raise AssertionError('Python collector adaptation forbidden')
            def GetElementIterator(self):return Enumerator([7])
        self.assertEqual([7],list(self.control().element_items(NativeOnly(),'scanned_elements')))
        def fail():raise ValueError('get iterator failed')
        bounded=self.control().element_items(Object(GetElementIterator=fail),'scanned_elements')
        self.assertRaises(ValueError,list,bounded)
        self.assertTrue(bounded.closed)

    def test_native_stop_after_api_returns_disposes(self):
        clock=[0]
        control=execution.Control(clock=lambda:clock[0],sink=lambda lines:None,limits=dict(seconds=1))
        enum=Enumerator([1]);original=enum.MoveNext
        def move():clock[0]=2;return original()
        enum.MoveNext=move
        bounded=control.element_items(Object(GetElementIterator=lambda:enum),'scanned_elements')
        self.assertRaises(execution.Stopped,list,bounded)
        self.assertEqual(1,enum.disposals)
        self.assertEqual(0,control.counts.get('scanned_elements',0))

    def test_scope_budget_does_not_end_native_scan_and_disposes(self):
        r=FixtureReader(document(1000),self.control(candidates=2))
        snapshot=r.collect(Object(Id=ident(1405931)))
        collector=Collector.instances[-1]
        self.assertEqual(1001,collector.enumerator.moves)
        self.assertEqual(1,collector.enumerator.disposals)
        self.assertTrue(collector.disposed)
        self.assertFalse(snapshot['coverage']['truncated'])
        self.assertEqual(1000,len(snapshot['elements']))

    def test_lookup_cache(self):
        calls=[]
        r=reader.Reader(Object(GetElement=lambda ident:calls.append(ident) or object()),self.control())
        a=r.lookup(ident(42));b=r.lookup(ident(42))
        self.assertIs(a,b);self.assertEqual(1,len(calls))

    def test_stop_not_swallowed_by_read(self):
        clock=[0]
        control=execution.Control(clock=lambda:clock[0],sink=lambda lines:None,limits=dict(seconds=1))
        r=reader.Reader(None,control)
        def getter(): clock[0]=2;return 'value'
        self.assertRaises(execution.Stopped,r.read,'x','field',getter)
        self.assertFalse(r.issues)

    def test_cancel_at_checkpoint(self):
        control=execution.Control(cancelled=lambda:True)
        self.assertRaises(execution.Stopped,control.check)

    def test_progress_order_counts_unicode_and_throttle(self):
        lines=[];clock=[0]
        control=execution.Control(clock=lambda:clock[0],sink=lines.extend)
        control.progress('Classify candidates',0,3,'1405931')
        control.progress('Classify candidates',1,3,'2')
        clock[0]=2
        control.progress('Classify candidates',2,3,'3')
        control.progress('Inspect pipe slopes',0,3)
        self.assertEqual(3,len(lines))
        self.assertIn('elapsed=2.0s; processed=2; total=3; ElementId=3',lines[1])
        self.assertIn('Inspect pipe slopes',lines[2])

    def test_json_and_text_limits_stop_without_replacement(self):
        control=self.control(json_bytes=20,text_chars=4)
        self.assertRaises(execution.Stopped,control.canonical,dict(value='x'*100))
        self.assertRaises(execution.Stopped,control.text,u'abcde')
        self.assertEqual(u'?',control.text(u'?'))

    def test_unicode_read_context_preserved_and_bounded(self):
        r=reader.Reader(None,self.control(unicode_failures=1))
        r.context.update(stage='inventory',element_id='42')
        def fail(): b'\xff'.decode('utf-8')
        self.assertIsNone(r.read('owner','parameter',fail))
        self.assertIn('parameter','\n'.join(r.unicode_failures[0]))
        self.assertIn('42','\n'.join(r.unicode_failures[0]))
        self.assertRaises(execution.Stopped,r.read,'owner','parameter',fail)
        self.assertEqual(1,len(r.unicode_failures))


if __name__ == '__main__': unittest.main()
