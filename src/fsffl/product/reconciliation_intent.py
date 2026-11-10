"""Bounded manual-State-sync intent for the existing reconciliation owner."""
from threading import Lock


class ReconciliationSyncIntent:
    def __init__(self, sync_state: bool = False):
        self._lock = Lock()
        self._requested = sync_state
        self._sync_in_flight = False
        self._closed = False

    def request_sync(self) -> bool:
        with self._lock:
            if self._closed:
                return False
            if not self._sync_in_flight:
                self._requested = True
            return True

    def begin_pass(self) -> bool:
        with self._lock:
            sync = self._requested
            self._requested = False
            self._sync_in_flight = self._sync_in_flight or sync
            return sync

    def finish_pass(self) -> bool:
        with self._lock:
            if self._requested and not self._sync_in_flight:
                return True
            self._closed = True
            return False

    def close(self) -> None:
        with self._lock:
            self._closed = True
