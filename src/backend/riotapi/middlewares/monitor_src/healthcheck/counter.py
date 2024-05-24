import threading


class BaseCounter:
    def __init__(self):
        self._lock = threading.Lock()

    def getLock(self):
        return self._lock

    def accumulate(self, *args, **kwargs):
        raise NotImplementedError("accumulate() method must be implemented in the subclass")

    def preview(self, *args, **kwargs):
        raise NotImplementedError("preview() method must be implemented in the subclass")

    def export(self):
        raise NotImplementedError("export() method must be implemented in the subclass")
