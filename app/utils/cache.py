import time
class TTLCache:
    def __init__(self, ttl_s: int, max_items: int = 2000):
        self.ttl, self.max, self._d = ttl_s, max_items, {}
    def get(self, k):
        v = self._d.get(k)
        if v and v[0] > time.time():
            return v[1]
        self._d.pop(k, None)
        return None
    def set(self, k, val):
        if len(self._d) >= self.max:
            self._d.pop(next(iter(self._d)))
        self._d[k] = (time.time() + self.ttl, val)
