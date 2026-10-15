# -*- coding: utf-8 -*-
"""Cooperative bounds on the calling API thread; never interrupts an API call."""
import json
import time
import failure_diagnostics
import diagnostic_core as core

# FULL UI access requires a separately reviewed, recorded FAST host acceptance.
FULL_HOST_ENABLED = False
DEFAULTS = dict(scanned_elements=10000, candidates=500, unknown_candidates=500, connectors=1024,
                connectors_per_element=32, references=4096, references_per_connector=32,
                dependencies=32, geometry_objects=64, links=32, parameters=12,
                unicode_failures=10, text_chars=4096, json_bytes=4*1024*1024,
                seconds=60)


class Stopped(Exception):
    pass


class Control(object):
    def __init__(self, mode='FAST', limits=None, sink=None, clock=None, cancelled=None):
        if mode not in ('FAST', 'FULL'): raise ValueError('Unknown diagnostic mode')
        self.mode = mode
        self.limits = dict(DEFAULTS)
        if mode == 'FULL': self.limits.update(candidates=2000, seconds=120)
        if limits:
            if set(limits) - set(self.limits): raise ValueError('Unknown limit')
            self.limits.update(limits)
        if any(v <= 0 for v in self.limits.values()): raise ValueError('Limits must be positive')
        self.clock = clock or getattr(time, 'monotonic', time.clock if hasattr(time, 'clock') else time.time)
        self.start = self.clock()
        self.last_output = self.start
        self.stage = None
        self.counts = {}
        self.truncated = []
        self.sink = sink or failure_diagnostics.emit
        self.cancelled = cancelled or (lambda: False)

    def check(self):
        if self.cancelled(): raise Stopped('CANCELLED_AT_CHECKPOINT')
        if self.clock() - self.start >= self.limits['seconds']:
            raise Stopped('COOPERATIVE_TIME_LIMIT; cannot interrupt an active API call')

    def progress(self, stage, processed=0, total=None, element_id=None, force=False):
        self.check()
        now = self.clock()
        if force or stage != self.stage or now-self.last_output >= 2 or (processed and processed % 100 == 0):
            self.sink(['Stage: {0}; elapsed={1:.1f}s; processed={2}; total={3}; ElementId={4}'.format(
                stage, now-self.start, processed, '?' if total is None else total,
                '-' if element_id is None else element_id)])
            self.last_output = now
        self.stage = stage

    def limit(self, name):
        if name not in self.truncated: self.truncated.append(name)

    def items(self, values, name, global_name=None, checkpoint=None):
        return BoundedIterator(self, values, name, global_name, checkpoint)

    def element_items(self, collector, name, checkpoint=None):
        return BoundedIterator(self, collector, name, checkpoint=checkpoint, native=True)

    def text(self, value):
        if isinstance(value, (str, bytes)) and len(value) > self.limits['text_chars']:
            raise Stopped('TEXT_LIMIT; model value not replaced')
        try:
            if isinstance(value, unicode) and len(value) > self.limits['text_chars']:
                raise Stopped('TEXT_LIMIT; model value not replaced')
        except NameError: pass
        return value

    def canonical(self, value):
        chunks, size = [], 0
        encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
        for chunk in encoder.iterencode(core.json_text(value)):
            self.check()
            chunk = core.ascii_json(chunk)
            size += len(chunk)
            if size > self.limits['json_bytes']: raise Stopped('JSON_SIZE_LIMIT; no report written')
            chunks.append(chunk)
        return ''.join(chunks)

    def coverage(self):
        return dict(mode=self.mode, complete=False, truncated=bool(self.truncated),
                    limits_reached=sorted(self.truncated), processing_limits=dict(self.limits),
                    processing_counts=dict(self.counts),
                    connector_topology='NOT_INSPECTED_FAST' if self.mode == 'FAST' else 'BOUNDED_DIRECT_REFERENCES')


class BoundedIterator(object):
    """No yield: avoids IPY 2.7.12/.NET8 GeneratorRewriter failure.

    Native collectors use only the documented Revit iterator protocol. Other
    bounded inputs keep their original Python iterator protocol and ordering.
    """
    def __init__(self, control, values, name, global_name=None, checkpoint=None, native=False):
        self.control, self.values, self.name = control, values, name
        self.global_name, self.checkpoint, self.native = global_name, checkpoint, native
        self.iterator = None
        self.count = 0
        self.closed = False
        self.exhausted = False

    def __iter__(self): return self

    def mark(self, operation):
        if self.checkpoint: self.checkpoint(operation)

    def close(self):
        if self.closed: return
        self.closed = True
        iterator = self.iterator
        self.iterator = None
        self.values = None
        dispose = getattr(iterator, 'Dispose', None)
        if dispose is not None: dispose()

    def next(self):
        if self.closed: raise StopIteration
        try:
            self.control.check()
            if self.count >= self.control.limits[self.name]:
                self.control.limit(self.name)
                raise StopIteration
            if self.global_name and self.control.counts.get(self.global_name, 0) >= self.control.limits[self.global_name]:
                self.control.limit(self.global_name)
                raise StopIteration
            if self.iterator is None:
                self.mark('element_iterator_get_before' if self.native else 'bounded_iterator_enter; iter_before')
                self.iterator = self.values.GetElementIterator() if self.native else iter(self.values)
                if self.native:
                    self.mark('element_iterator_get_after; reset_before')
                    self.iterator.Reset()
                self.mark('element_iterator_ready' if self.native else 'iter_after')
            if self.count == 0: self.mark('first_MoveNext_before' if self.native else 'first_next_before')
            if self.native:
                if not self.iterator.MoveNext():
                    self.control.check()
                    self.exhausted = True
                    raise StopIteration
                if self.count == 0: self.mark('first_MoveNext_after; Current_before')
                value = self.iterator.Current
            else:
                value = next(self.iterator)
            self.control.check()
            if self.count == 0: self.mark('first_Current_after' if self.native else 'first_next_after')
            self.count += 1
            self.control.counts[self.name] = self.control.counts.get(self.name, 0) + 1
            if self.global_name:
                self.control.counts[self.global_name] = self.control.counts.get(self.global_name, 0) + 1
            return value
        except Exception:
            self.close()
            raise

    __next__ = next
