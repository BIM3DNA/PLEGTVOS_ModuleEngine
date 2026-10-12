# -*- coding: utf-8 -*-
"""Offline pure-logic/storage tests. These are NOT Revit host acceptance."""
import ast
import json
import math
import os
import shutil
import sys
import tempfile
import unittest

BUTTON = os.path.abspath(os.path.join(os.path.dirname(__file__), '..',
    'PLEGTVOS_ModuleEngine.extension', 'PLEGTVOS_ModuleEngine.tab', 'Dev.panel',
    'GC01_Mirror_Diagnostics.pushbutton'))
sys.path.insert(0, BUTTON)
import diagnostic_core as core
import report_store


def wireframe(angle=0):
    c, s = math.cos(angle), math.sin(angle)
    points = [[10+x*c-y*s, 20+x*s+y*c, z] for x in (0, 4) for y in (0, 6) for z in (0, 8)]
    return [[points[i], points[j]] for i in range(8) for j in range(i+1, 8) if bin(i^j).count('1')==1]


def corners(a, b):
    return [[x,y,z] for x in (a[0],b[0]) for y in (a[1],b[1]) for z in (a[2],b[2])]


class GeometryTests(unittest.TestCase):
    def test_frame_and_rotated_frame(self):
        for angle in (0, .37, math.pi/2):
            frame = core.scope_frame(wireframe(angle))
            self.assertIsNotNone(frame)
            self.assertFalse(frame['approved'])
            for edge in wireframe(angle):
                for point in edge: self.assertTrue(core.point_inside(point, frame))

    def test_frame_order_independent(self):
        lines = wireframe(.37)
        self.assertEqual(core.scope_frame(lines), core.scope_frame([list(reversed(e)) for e in reversed(lines)]))

    def test_invalid_geometry(self):
        lines = wireframe()
        for value in ([], lines[:-1], lines[:-1]+[lines[0]]): self.assertIsNone(core.scope_frame(value))
        bad = wireframe(); bad[0][0] = [float('nan'),0,0]
        self.assertIsNone(core.scope_frame(bad))

    def test_inside_outside_unknown(self):
        frame = core.scope_frame(wireframe())
        self.assertEqual('INSIDE', core.classify(corners([11,21,1],[12,22,2]), frame))
        self.assertEqual('OUTSIDE', core.classify(corners([0,0,0],[1,1,1]), frame))
        self.assertEqual('UNKNOWN', core.classify(corners([9,19,0],[11,21,1]), frame))
        self.assertEqual('UNKNOWN', core.classify(None, frame))
        self.assertEqual('UNKNOWN', core.classify(corners([11,21,1],[12,22,2]), None))

    def test_crossing_curve(self):
        frame = core.scope_frame(wireframe())
        self.assertEqual('CROSSING', core.classify(corners([9,21,1],[15,22,2]), frame, [[9,21,1],[15,21,1]]))
        self.assertEqual('UNKNOWN', core.classify(corners([9,19,0],[11,21,1]), frame, [[9,19,0],[9,21,1]]))

    def test_reflection_and_vector(self):
        self.assertEqual([-1,2,3], core.reflect([5,2,3],[1,0,0],[2,0,0]))
        self.assertEqual([-1,0,0], core.reflect([1,0,0],[1,0,0]))
        v=[5,-2,7]; n=[2**-.5,2**-.5,0]
        for a,b in zip(v,core.reflect(core.reflect(v,n),n)): self.assertAlmostEqual(a,b)
        self.assertAlmostEqual(core.norm(v), core.norm(core.reflect(v,n)))

    def test_composed_map_then_reflect(self):
        source=dict(origin_ft=[10,0,0],axes=[[1,0,0],[0,1,0],[0,0,1]])
        target=dict(origin_ft=[0,20,5],axes=[[0,1,0],[-1,0,0],[0,0,1]])
        mapped=core.map_frame([12,3,4],source,target)
        self.assertEqual([-3,22,9],mapped)
        self.assertEqual([3,22,9],core.reflect(mapped,[1,0,0],[0,20,5]))
        self.assertEqual([0,1,0],core.map_frame([1,0,0],source,target,True))
        target['axes'][0]=[2,0,0]
        self.assertRaises(ValueError,core.map_frame,[1,2,3],source,target)

    def test_invalid_normal(self):
        for n in ([0,0,0],[2,0,0],[float('inf'),0,0]):
            self.assertRaises(ValueError, core.reflect, [1,2,3], n)

        self.assertRaises(ValueError, core.reflect, [1,2,3], [1,0,0], [float('nan'),0,0])

    def test_unapproved_prediction(self):
        p=core.prediction()
        self.assertEqual('MIRROR_FRAME_UNCONFIRMED',p['status'])
        self.assertIsNone(p['plane'])
        self.assertEqual([],p['expected_connectors'])


class SlopeTests(unittest.TestCase):
    def test_signed_endpoint_convention(self):
        ends=[[0,0,10],[3,4,9.95]]
        p=core.slope(ends); r=core.slope(list(reversed(ends)))
        self.assertAlmostEqual(-.01,p['slope_signed_ratio'])
        self.assertAlmostEqual(.01,r['slope_signed_ratio'])
        self.assertEqual(p['slope_abs_ratio'],r['slope_abs_ratio'])
        self.assertEqual('UNKNOWN',p['flow_status'])
        self.assertEqual('UNKNOWN',p['compliance'])

    def test_vertical_and_zero(self):
        for ends,status in [([[0,0,0],[0,0,4]],'VERTICAL'),([[1,1,1],[1,1,1]],'DEGENERATE')]:
            p=core.slope(ends); self.assertEqual(status,p['status']); self.assertIsNone(p['slope_abs_ratio'])

    def test_missing_and_curved(self):
        for ends in (None,[],[[0,0,0]],[[0,0,0],[float('nan'),0,0]]):
            self.assertEqual('UNAVAILABLE',core.slope(ends)['status'])
        p=core.slope([[0,0,0],[1,1,1]],False)
        self.assertEqual('UNSUPPORTED_CURVE',p['status']); self.assertIsNone(p['slope_abs_ratio'])


class IdentityTests(unittest.TestCase):
    def test_invalid_selection(self):
        for categories in ([],[None],['pipe'],['scope','scope'],['scope','pipe']):
            self.assertFalse(core.valid_selection(categories,'scope'))
        self.assertTrue(core.valid_selection(['scope'],'scope'))

    def test_connector_descriptor(self):
        a=dict(api_id=None,connector_type='End',domain='Piping',origin_ft=[1,2,3],coordinate_system=None)
        b=dict(reversed(list(a.items())))
        self.assertEqual(core.connector_key('owner',a),core.connector_key('owner',b))
        self.assertNotEqual(core.connector_key('owner',a),core.connector_key('other',a))
        b['origin_ft']=[2,2,3]
        self.assertNotEqual(core.connector_key('owner',a),core.connector_key('owner',b))
        a['api_id']='42'; self.assertEqual('owner/connector/42',core.connector_key('owner',a))

    def test_stable_snapshot(self):
        a=core.finalize(dict(elements=[dict(key='b'),dict(key='a')],issues=[dict(code='z'),dict(code='a')]))
        b=core.finalize(dict(issues=[dict(code='a'),dict(code='z')],elements=[dict(key='a'),dict(key='b')]))
        self.assertEqual(core.canonical(a),core.canonical(b)); self.assertEqual(core.digest(a),core.digest(b))
        self.assertEqual(core.canonical(-0.0),core.canonical(0.0))
        self.assertRaises(ValueError,core.canonical,float('nan'))


class StorageTests(unittest.TestCase):
    def setUp(self): self.folder=tempfile.mkdtemp(prefix='gc01-offline-')
    def tearDown(self): shutil.rmtree(self.folder)

    def test_immutable_reports_and_pointer(self):
        sentinel=os.path.join(self.folder,'latest.json')
        with open(sentinel,'w') as f: f.write('extractor sentinel')
        snapshot=dict(document=dict(key='fixture'))
        report=dict(snapshot=snapshot,content_sha256=core.digest(snapshot))
        first,w=report_store.save(report,self.folder); self.assertIsNone(w)
        second,w=report_store.save(report,self.folder); self.assertIsNone(w)
        self.assertNotEqual(first,second)
        with open(first) as f: self.assertEqual(report,json.load(f))
        with open(sentinel) as f: self.assertEqual('extractor sentinel',f.read())
        with open(os.path.join(os.path.dirname(first),'latest-report.json')) as f:
            self.assertEqual(os.path.basename(second),json.load(f)['report'])
        self.assertRaises(OSError,report_store.exclusive_write,first,report)

    def test_pointer_failure_preserves_report(self):
        folder=os.path.join(self.folder,'gc01_mirror_diagnostics','fixture')
        os.makedirs(os.path.join(folder,'latest-report.json'))
        report=dict(snapshot=dict(document=dict(key='fixture')),content_sha256='x')
        path,warning=report_store.save(report,self.folder)
        self.assertTrue(os.path.isfile(path))
        self.assertTrue(warning.startswith('LATEST_POINTER_FAILED'))

    def test_export_failure(self):
        blocked=os.path.join(self.folder,'file')
        with open(blocked,'w') as f: f.write('preserve')
        self.assertRaises(OSError,report_store.save,dict(snapshot=dict(document=dict(key='fixture')),content_sha256='x'),blocked)


class StaticSafetyTests(unittest.TestCase):
    def test_no_mutation_calls_or_button_imports(self):
        prohibited=set(('Transaction','TransactionGroup','SubTransaction','Regenerate','Set',
            'SetElementIds','MirrorElements','MirrorElement','MoveElement','MoveElements','RotateElement',
            'CopyElements','CopyElement','Delete','Create','Save','SaveAs','SynchronizeWithCentral',
            'ConnectTo','DisconnectFrom','OpenDocumentFile','Close','HideElements','IsolateElementsTemporary'))
        for name in ('script.py','revit_reader.py','diagnostic_core.py','report_store.py','failure_diagnostics.py'):
            with open(os.path.join(BUTTON,name),'rb') as f: tree=ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node,ast.Call):
                    called=getattr(node.func,'attr',getattr(node.func,'id',''))
                    self.assertNotIn(called,prohibited,(name,called))
                if isinstance(node,ast.Assign):
                    for target in node.targets:
                        if isinstance(target,ast.Attribute): self.assertNotIn(target.attr,('ActiveView','Location','Curve','Pinned'))
                if isinstance(node,ast.Import):
                    self.assertTrue(all(n.name!='module_state' for n in node.names))


if __name__ == '__main__': unittest.main()
