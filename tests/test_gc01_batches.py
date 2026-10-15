# -*- coding: utf-8 -*-
"""Multipart/freshness tests with fake Revit objects, never host acceptance."""
import copy
import hashlib
import os
import shutil
import tempfile
import unittest
from test_gc01_filtering import fixture, element
from test_gc01_scope_coverage import ScopeReader
from test_gc01_execution import Object, ident, execution, core, reader
import detail_batches as batches
import report_store
import snapshot_guard as guard


def control(**limits):
    return execution.Control(limits=limits,clock=lambda:0.0,sink=lambda lines:None)


def report(count):
    snapshot=ScopeReader(fixture([element(i) for i in range(count)]),control()).collect(Object(Id=ident(1405931)))
    return dict(schema=core.SCHEMA,snapshot=snapshot,run=dict(collector_version='1.1h',source_sha256='code'),
                safety=dict(model_write_apis_invoked=False))


def freshness():
    return dict(status='SAVED_LOCAL_MEMORY_DISK_MATCH',path='fixture.rvt',project_info_unique_id='doc',rvt_sha256='fixture-bytes',document_version=dict(guid='version',saves=1))


class BatchTests(unittest.TestCase):
    def setUp(self): self.folder=tempfile.mkdtemp(prefix='gc01-batch-test-')
    def tearDown(self):
        target=os.path.realpath(self.folder)
        assert target.startswith(os.path.realpath(tempfile.gettempdir())+os.sep)
        assert os.path.basename(target).startswith('gc01-batch-test-')
        shutil.rmtree(target)
    def test_boundaries_and_exactly_once(self):
        for count in (0,1,499,500,501,763):
            plan,parts=batches.prepare(report(count),freshness(),control())
            batches.validate_plan(plan)
            self.assertEqual((count+499)//500,len(parts))
            ids=[]
            for part,descriptor in zip(parts,plan['parts']):
                self.assertLessEqual(len(part['elements']),500)
                batches.validate_part(part,descriptor,plan)
                ids.extend(part['covered_ids'])
            self.assertEqual(count,len(ids));self.assertEqual(count,len(set(ids)))
            self.assertEqual(plan['expected_ids'],ids)
            self.assertFalse(plan['missing_ids'])
    def test_deterministic_batches_and_unicode(self):
        value=report(501);value['snapshot']['elements'][0]['name']=u'GC01-\u010d-90\u00b0'
        other=copy.deepcopy(value);other['snapshot']['elements'].reverse();other['snapshot']['pipes'].reverse()
        self.assertEqual(batches.prepare(value,freshness(),control()),batches.prepare(other,freshness(),control()))
        path=batches.save(value,self.folder,freshness(),control())
        manifest=batches.validate_manifest(path,control())
        self.assertTrue(manifest['detail_coverage_complete'])
        self.assertEqual('NOT_INSPECTED',manifest['connector_topology'])
        self.assertEqual('UNRESOLVED',manifest['mirror_readiness'])
    def test_manifest_763_and_part_sizes(self):
        path=batches.save(report(763),self.folder,freshness(),control())
        manifest=batches.validate_manifest(path,control())
        self.assertEqual(2,manifest['expected_parts']);self.assertEqual(763,len(manifest['covered_ids']))
        self.assertTrue(manifest['pipe_slope_detail_coverage_complete'])
        plan=batches.load(os.path.join(os.path.dirname(path),'plan.json'),control())
        self.assertEqual([500,263],[len(p['covered_ids']) for p in plan['parts']])
    def test_duplicate_and_missing_records(self):
        value=report(2);value['snapshot']['elements'].append(value['snapshot']['elements'][0])
        self.assertRaises(batches.InvalidBundle,batches.prepare,value,freshness(),control())
        value=report(2);missing=value['snapshot']['elements'].pop()['key']
        value['snapshot']['pipes']=[p for p in value['snapshot']['pipes'] if p['element_key']!=missing]
        path=batches.save(value,self.folder,freshness(),control())
        manifest=batches.validate_manifest(path,control())
        self.assertFalse(manifest['detail_coverage_complete']);self.assertEqual([missing],manifest['missing_ids'])
    def test_missing_pipe_record_separate_from_detail_completeness(self):
        value=report(2);value['snapshot']['pipes'].pop()
        path=batches.save(value,self.folder,freshness(),control())
        result=batches.validate_manifest(path,control())
        self.assertTrue(result['detail_coverage_complete'])
        self.assertFalse(result['pipe_slope_detail_coverage_complete'])
        self.assertEqual(1,len(result['missing_pipe_ids']))
    def interrupted(self):
        value=report(501);original=report_store.exclusive_write
        def fail(path,data,ctl=None):
            if os.path.basename(path)=='part-0001.json': raise execution.Stopped('synthetic interrupted second batch')
            original(path,data,ctl)
        report_store.exclusive_write=fail
        try: self.assertRaises(execution.Stopped,batches.save,value,self.folder,freshness(),control())
        finally: report_store.exclusive_write=original
        plans=[]
        for folder,dirs,files in os.walk(self.folder):
            if 'plan.json' in files: plans.append(os.path.join(folder,'plan.json'))
        self.assertEqual(1,len(plans))
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(plans[0]),'manifest.json')))
        self.assertRaises(IOError,batches.validate,plans[0],control())
        return value,plans[0]
    def test_interruption_resume_preserves_first_part(self):
        value,plan=self.interrupted()
        first=os.path.join(os.path.dirname(plan),'part-0000.json')
        with open(first,'rb') as stream: old=stream.read()
        manifest=batches.save(value,self.folder,freshness(),control(),resume=plan)
        self.assertTrue(batches.validate_manifest(manifest,control())['detail_coverage_complete'])
        with open(first,'rb') as stream:self.assertEqual(old,stream.read())
        self.assertRaises(batches.InvalidBundle,batches.save,value,self.folder,freshness(),control(),plan)
    def test_cross_run_mismatches_rejected(self):
        value,plan=self.interrupted()
        for field in ('document','scope','geometry','ledger','code','freshness','detail','read_error'):
            changed=copy.deepcopy(value);fresh=freshness()
            if field=='document':changed['snapshot']['document']['key']='other'
            elif field=='scope':changed['snapshot']['source']['scope_box']['unique_id']='other'
            elif field=='geometry':changed['snapshot']['source']['geometry']=[[[0,0,0],[1,1,1]]]
            elif field=='ledger':changed['snapshot']['coverage']['classification_ledger'][0]['category_id']='other'
            elif field=='code':changed['run']['source_sha256']='other'
            elif field=='freshness':fresh['rvt_sha256']='other'
            elif field=='read_error':changed['snapshot']['issues'].append(dict(reason='READ_ERROR'))
            else:changed['snapshot']['elements'][0]['name']='changed'
            self.assertRaises(batches.InvalidBundle,batches.save,changed,self.folder,fresh,control(),plan)
    def test_corrupted_partial_part_rejected_without_overwrite(self):
        value,plan=self.interrupted();path=os.path.join(os.path.dirname(plan),'part-0001.json')
        with open(path,'wb') as stream:stream.write(b'{partial')
        self.assertRaises(ValueError,batches.save,value,self.folder,freshness(),control(),plan)
        with open(path,'rb') as stream:self.assertEqual(b'{partial',stream.read())
    def test_hash_and_manifest_coverage_validation(self):
        path=batches.save(report(1),self.folder,freshness(),control())
        manifest=batches.load(path,control());manifest['covered_ids']=[]
        with open(path,'wb') as stream:stream.write(core.canonical(batches.wrap(manifest)).encode('utf-8'))
        self.assertRaises(batches.InvalidBundle,batches.validate_manifest,path,control())
        with open(path,'wb') as stream:stream.write(b'{"payload":{},"sha256":"wrong"}')
        self.assertRaises(batches.InvalidBundle,batches.load,path,control())
    def test_json_size_and_cooperative_stopping(self):
        self.assertRaises(execution.Stopped,batches.prepare,report(1),freshness(),control(json_bytes=10))
        ctl=execution.Control(clock=lambda:0.0,cancelled=lambda:True,sink=lambda lines:None)
        self.assertRaises(execution.Stopped,batches.prepare,report(1),freshness(),ctl)
        clock=[0.0];ctl=execution.Control(clock=lambda:clock[0],sink=lambda lines:None)
        clock[0]=60.0
        self.assertRaises(execution.Stopped,batches.prepare,report(1),freshness(),ctl)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        handle,self.path=tempfile.mkstemp(prefix='gc01-snapshot-',suffix='.rvt')
        with os.fdopen(handle,'wb') as stream:stream.write(b'\x00\x80\xffbinary-fixture')
        self.doc=Object(IsModified=False,IsModelInCloud=False,PathName=self.path,
                        ProjectInformation=Object(UniqueId='project'))
        self.version=lambda:Object(VersionGUID='test-guid',NumberOfSaves=3)
        self.db=Object(Document=Object(GetDocumentVersion=lambda doc:self.version()),
            BasicFileInfo=Object(Extract=lambda path:Object(GetDocumentVersion=self.version,Dispose=lambda:None)))
    def tearDown(self):os.remove(self.path)
    def test_saved_memory_disk_and_binary_hash(self):
        result=guard.capture(self.doc,self.db,control())
        self.assertEqual(hashlib.sha256(b'\x00\x80\xffbinary-fixture').hexdigest(),result['rvt_sha256'])
        self.assertEqual('SAVED_LOCAL_MEMORY_DISK_MATCH',result['status'])
    def test_modified_cloud_and_version_mismatch_fail_closed(self):
        self.doc.IsModified=True
        self.assertRaises(guard.UnqualifiedSnapshot,guard.capture,self.doc,self.db,control())
        self.doc.IsModified=False;self.doc.IsModelInCloud=True
        self.assertRaises(guard.UnqualifiedSnapshot,guard.capture,self.doc,self.db,control())
        self.doc.IsModelInCloud=False
        self.db.Document.GetDocumentVersion=lambda doc:Object(VersionGUID='other',NumberOfSaves=3)
        self.assertRaises(guard.UnqualifiedSnapshot,guard.capture,self.doc,self.db,control())
    def test_central_guid_non_server_is_explicit_not_a_failed_read(self):
        doc=fixture([]);doc.IsWorkshared=True
        doc.GetWorksharingCentralModelPath=lambda:Object(ServerPath=False,Empty=False)
        # Deliberately no WorksharingCentralGUID property: it must not be read.
        result=ScopeReader(doc,control()).collect(Object(Id=ident(1405931)))
        self.assertIsNone(result['document']['central_guid'])
        self.assertEqual('NOT_APPLICABLE_NON_SERVER_CENTRAL',result['document']['central_guid_status'])
        self.assertFalse(any(i['field']=='central_guid' for i in result['issues']))
        self.assertTrue(result['coverage']['classification_inventory_complete'])
    def test_unexpected_central_path_error_is_not_suppressed(self):
        doc=fixture([]);doc.IsWorkshared=True
        def fail():raise RuntimeError('An internal error has occurred.')
        doc.GetWorksharingCentralModelPath=fail
        result=ScopeReader(doc,control()).collect(Object(Id=ident(1405931)))
        self.assertEqual('UNAVAILABLE',result['document']['central_guid_status'])
        self.assertFalse(result['coverage']['classification_inventory_complete'])
        errors=[i for i in result['issues'] if i['field']=='central_model_path']
        self.assertEqual('RuntimeError',errors[0]['exception_type']);self.assertTrue(errors[0]['traceback'])


if __name__ == '__main__':unittest.main()
