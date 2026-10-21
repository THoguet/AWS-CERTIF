"""
Exercise cache_1 — Lazy loading (cache-aside) with a TTL
========================================================
Book: chapter 8, "Caching strategies" (book/src/ch08-caching-databases-cdn.md)
Exam: Domain 1 · Task 1.3 (caching strategies: lazy loading, write-through, TTL)

Lazy loading (a.k.a. cache-aside) with ElastiCache (Redis/Valkey or Memcached):
  1. read from the cache,
  2. on a MISS, read from the database and populate the cache,
  3. on a HIT, skip the database.

Pros: only requested data is cached, and a cache node failure is not fatal.
Cons: the first read is slow (miss penalty: 3 round trips) and data can
be STALE, because the database changed but the cache did not. A TTL
bounds the staleness.

Your task
---------
Implement `get_product(product_id, cache, db, ttl)` using cache-aside.
`cache` behaves like a tiny Redis: get(key) → value or None, set(key, value, ttl).
"""

# I AM NOT DONE


class TTLCache:
    """In-memory cache with expiry, driven by an injectable clock."""

    def __init__(self, clock):
        self.clock, self.data = clock, {}

    def get(self, key):
        value, expires = self.data.get(key, (None, 0))
        return value if self.clock() < expires else None

    def set(self, key, value, ttl):
        self.data[key] = (value, self.clock() + ttl)

    def delete(self, key):
        self.data.pop(key, None)


def get_product(product_id: str, cache: TTLCache, db, ttl: int = 300):
    return db.load(product_id)  # TODO: check the cache first, populate it on a miss


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run cache_1
# =============================================================================


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class FakeDb:
    def __init__(self, rows):
        self.rows, self.reads = rows, 0

    def load(self, product_id):
        self.reads += 1
        return self.rows.get(product_id)


def test_second_read_is_a_cache_hit():
    clock, db = Clock(), FakeDb({"p-1": {"name": "Mug"}})
    cache = TTLCache(clock)
    assert get_product("p-1", cache, db) == {"name": "Mug"}
    assert get_product("p-1", cache, db) == {"name": "Mug"}
    assert db.reads == 1


def test_ttl_bounds_staleness():
    clock, db = Clock(), FakeDb({"p-1": {"name": "Mug"}})
    cache = TTLCache(clock)
    get_product("p-1", cache, db, ttl=300)
    db.rows["p-1"] = {"name": "Big mug"}
    clock.now += 299
    assert get_product("p-1", cache, db, ttl=300) == {"name": "Mug"}, "stale but within TTL"
    clock.now += 2
    assert get_product("p-1", cache, db, ttl=300) == {"name": "Big mug"}
    assert db.reads == 2


def test_misses_are_not_cached():
    clock, db = Clock(), FakeDb({})
    cache = TTLCache(clock)
    assert get_product("p-9", cache, db) is None
    db.rows["p-9"] = {"name": "New"}
    assert get_product("p-9", cache, db) == {"name": "New"}
