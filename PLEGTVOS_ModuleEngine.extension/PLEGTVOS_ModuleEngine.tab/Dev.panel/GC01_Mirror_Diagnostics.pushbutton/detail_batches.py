# -*- coding: utf-8 -*-
"""Immutable FAST parts and fail-closed continuation. No Revit API imports."""
import json
import os
import uuid
import diagnostic_core as core
import report_store


class InvalidBundle(ValueError): pass


def wrap(payload): return dict(payload=payload, sha256=core.digest(payload))


def load(path, control):
    control.check()
    with open(path, 'rb') as stream: data=stream.read(control.limits['json_bytes']+2)
    if len(data)>control.limits['json_bytes']+1: raise InvalidBundle('JSON_SIZE_LIMIT')
    value=json.loads(data.decode('utf-8'))
    if set(value)!=set(('payload','sha256')) or core.digest(value['payload'])!=value['sha256']:
        raise InvalidBundle('CONTENT_HASH_MISMATCH')
    control.check()
    return value['payload']


def prepare(report, freshness, control):
    if report['schema']!=core.SCHEMA or freshness.get('status')!='SAVED_LOCAL_MEMORY_DISK_MATCH':
        raise InvalidBundle('UNQUALIFIED_SNAPSHOT')
    snapshot=report['snapshot']
    if (freshness.get('path')!=snapshot['document'].get('path') or
            freshness.get('project_info_unique_id')!=snapshot['document'].get('project_info_unique_id')):
        raise InvalidBundle('FRESHNESS_DOCUMENT_MISMATCH')
    expected=sorted(r['key'] for r in snapshot['coverage']['classification_ledger'] if r['membership']!='OUTSIDE')
    if len(expected)!=len(set(expected)): raise InvalidBundle('DUPLICATE_EXPECTED_IDS')
    rows=sorted(snapshot['elements'], key=lambda r:r['key'])
    keys=[r['key'] for r in rows]
    if len(keys)!=len(set(keys)) or set(keys)-set(expected): raise InvalidBundle('DUPLICATE_OR_UNEXPECTED_RECORD')
    category_ids=snapshot['coverage']['collector_filter']['category_ids']
    expected_pipes=sorted(r['key'] for r in snapshot['coverage']['classification_ledger']
        if r['membership']!='OUTSIDE' and category_ids.get(r.get('category_id')) in ('OST_PipeCurves','OST_FlexPipeCurves'))
    pipe_map={}
    for pipe in snapshot['pipes']:
        key=pipe['element_key']
        if key in pipe_map or key not in keys or key not in expected_pipes: raise InvalidBundle('DUPLICATE_OR_UNEXPECTED_PIPE')
        pipe_map[key]=pipe
    contract=dict(schema=core.SCHEMA, collector_version=report['run']['collector_version'],
        code_sha256=report['run']['source_sha256'], document=snapshot['document'],
        scope=snapshot['source']['scope_box'], geometry=snapshot['source']['geometry'],
        frame=snapshot['source']['frame'], categories=snapshot['policy']['inclusion_rules'],
        ledger_sha256=core.digest(snapshot['coverage']['classification_ledger']), freshness=freshness)
    contract_hash=core.digest(contract)
    parts=[]
    size=min(500,control.limits['candidates'])
    for start in range(0,len(rows),size):
        control.check()
        batch=rows[start:start+size]
        covered=[r['key'] for r in batch]
        parts.append(dict(schema=core.SCHEMA, kind='FAST_DETAIL_PART', batch_index=len(parts),
            snapshot_sha256=contract_hash, covered_ids=covered, elements=batch,
            pipes=[pipe_map[k] for k in covered if k in pipe_map]))
    descriptors=[]
    for part in parts:
        control.canonical(wrap(part))
        descriptors.append(dict(index=part['batch_index'], file='part-%04d.json'%part['batch_index'],
            covered_ids=part['covered_ids'], pipe_ids=[r['element_key'] for r in part['pipes']],
            sha256=core.digest(part)))
    inventory=dict(snapshot);inventory.pop('elements');inventory.pop('pipes')
    plan=dict(schema=core.SCHEMA, kind='FAST_DETAIL_PLAN', complete=False, contract=contract,
        snapshot_sha256=contract_hash, expected_ids=expected, missing_ids=sorted(set(expected)-set(keys)),
        expected_pipe_ids=expected_pipes, missing_pipe_ids=sorted(set(expected_pipes)-set(pipe_map)),
        parts=descriptors, inventory=inventory, source_run=report['run'], safety=report['safety'])
    control.canonical(wrap(plan))
    return plan,parts


def validate_plan(plan):
    if plan.get('schema')!=core.SCHEMA or plan.get('kind')!='FAST_DETAIL_PLAN':
        raise InvalidBundle('PLAN_SCHEMA_MISMATCH')
    if core.digest(plan['contract'])!=plan['snapshot_sha256']: raise InvalidBundle('SNAPSHOT_HASH_MISMATCH')
    ledger=plan['inventory']['coverage']['classification_ledger']
    if core.digest(ledger)!=plan['contract']['ledger_sha256']:
        raise InvalidBundle('LEDGER_HASH_MISMATCH')
    expected=plan['expected_ids'];missing=plan['missing_ids'];covered=[]
    if expected!=sorted(r['key'] for r in ledger if r['membership']!='OUTSIDE'):
        raise InvalidBundle('LEDGER_EXPECTED_IDS_MISMATCH')
    if expected!=sorted(set(expected)) or missing!=sorted(set(missing)):
        raise InvalidBundle('DUPLICATE_EXPECTED_OR_MISSING_IDS')
    pipe_ids=[]
    for index,part in enumerate(plan['parts']):
        if part['index']!=index or part['file']!='part-%04d.json'%index or len(part['covered_ids'])>500:
            raise InvalidBundle('INVALID_BATCH_DESCRIPTOR')
        covered.extend(part['covered_ids'])
        pipe_ids.extend(part['pipe_ids'])
    if len(covered)!=len(set(covered)) or set(covered)&set(missing) or sorted(covered+missing)!=expected:
        raise InvalidBundle('EXACTLY_ONCE_COVERAGE_FAILED')
    missing_pipes=plan['missing_pipe_ids']
    if (len(pipe_ids)!=len(set(pipe_ids)) or set(pipe_ids)&set(missing_pipes)
            or sorted(pipe_ids+missing_pipes)!=plan['expected_pipe_ids']):
        raise InvalidBundle('PIPE_COVERAGE_FAILED')


def validate_part(part, descriptor, plan):
    keys=[r['key'] for r in part['elements']]
    pipes=[r['element_key'] for r in part['pipes']]
    if (part['schema']!=core.SCHEMA or part['kind']!='FAST_DETAIL_PART'
            or part['snapshot_sha256']!=plan['snapshot_sha256']
            or part['batch_index']!=descriptor['index']
            or part['covered_ids']!=descriptor['covered_ids'] or keys!=part['covered_ids']
            or len(keys)!=len(set(keys)) or pipes!=descriptor['pipe_ids']
            or len(pipes)!=len(set(pipes)) or set(pipes)-set(keys)
            or core.digest(part)!=descriptor['sha256']):
        raise InvalidBundle('PART_IDENTITY_OR_CONTENT_MISMATCH')


def validate(plan_path, control):
    plan=load(plan_path,control);validate_plan(plan)
    for descriptor in plan['parts']:
        part=load(os.path.join(os.path.dirname(plan_path),descriptor['file']),control)
        validate_part(part,descriptor,plan)
    return plan


def save(report, root, freshness, control, resume=None):
    plan,parts=prepare(report,freshness,control)
    validate_plan(plan)
    if resume:
        if os.path.basename(resume)!='plan.json': raise InvalidBundle('Select the original plan.json')
        previous=load(resume,control);validate_plan(previous)
        # Compare current fresh source and all current part hashes, never path alone.
        for field in ('contract','snapshot_sha256','expected_ids','missing_ids','expected_pipe_ids','missing_pipe_ids','parts','inventory'):
            if previous[field]!=plan[field]: raise InvalidBundle('STALE_OR_INCOMPATIBLE_SNAPSHOT: '+field)
        plan=previous
        folder=os.path.dirname(resume)
        plan_path=resume
        if os.path.exists(os.path.join(folder,'manifest.json')):
            raise InvalidBundle('ALREADY_FINALIZED; existing evidence retained')
    else:
        folder=os.path.join(root,'gc01_mirror_diagnostics',report['snapshot']['document']['key'],
                            'bundle_'+uuid.uuid4().hex)
        os.makedirs(folder)
        plan_path=os.path.join(folder,'plan.json')
        report_store.exclusive_write(plan_path,wrap(plan),control)
    control.sink(['FAST bundle plan: ' + plan_path])
    for descriptor,part in zip(plan['parts'],parts):
        control.progress('Write FAST detail batch',descriptor['index'],len(parts))
        path=os.path.join(folder,descriptor['file'])
        if os.path.exists(path):
            validate_part(load(path,control),descriptor,plan)
        else:
            report_store.exclusive_write(path,wrap(part),control)
    validated=validate(plan_path,control)
    manifest=manifest_for(validated)
    path=os.path.join(folder,'manifest.json')
    report_store.exclusive_write(path,wrap(manifest),control)
    return path


def manifest_for(validated):
    coverage=validated['inventory']['coverage']
    classification=bool(coverage.get('classification_inventory_complete',False))
    details=classification and not validated['missing_ids']
    return dict(schema=core.SCHEMA,kind='FAST_DETAIL_MANIFEST',plan='plan.json',
        plan_sha256=core.digest(validated),snapshot_sha256=validated['snapshot_sha256'],
        expected_parts=len(validated['parts']), covered_ids=sorted(set(validated['expected_ids'])-set(validated['missing_ids'])),
        missing_ids=validated['missing_ids'],
        classification_inventory_complete=classification,detail_coverage_complete=details,
        pipe_slope_detail_coverage_complete=details and not validated['missing_pipe_ids'],
        missing_pipe_ids=validated['missing_pipe_ids'],connector_topology='NOT_INSPECTED',
        snapshot_identity='SAVED_LOCAL_MEMORY_DISK_MATCH',mirror_readiness='UNRESOLVED',
        status='FAST_DETAILS_COMPLETE_MIRROR_UNRESOLVED' if details and not validated['missing_pipe_ids'] else 'PARTIAL_UNRESOLVED')


def validate_manifest(path, control):
    manifest=load(path,control)
    if manifest.get('plan')!='plan.json': raise InvalidBundle('INVALID_MANIFEST_PLAN')
    plan=validate(os.path.join(os.path.dirname(path),'plan.json'),control)
    if manifest!=manifest_for(plan): raise InvalidBundle('MANIFEST_COVERAGE_MISMATCH')
    return manifest
