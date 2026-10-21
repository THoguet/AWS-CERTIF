"""
Exercise cache_2 — Write-through and invalidation
=================================================
Book: chapter 8, "Caching strategies" (book/src/ch08-caching-databases-cdn.md)
Exam: Domain 1 · Task 1.3, Domain 4 · Task 4.3 (caching)

With lazy loading alone, an update in the database leaves the old value
in the cache until the TTL expires. Two classic fixes:

  * WRITE-THROUGH: every write updates the database AND the cache. Reads
    are always fresh. Downsides: every write pays a cache write, and data
    that is never read still fills the cache (use a TTL anyway).
  * INVALIDATE ON WRITE: write the database, delete the cache key. The next
    read is a miss that reloads fresh data.

Real systems combine lazy loading + write-through + TTL.

Your task
---------
  * `update_write_through(product, cache, db, ttl)`,
  * `update_and_invalidate(product, cache, db)`.
Both use the key f"product:{product['id']}" (same as cache_1).
"""

# I AM NOT DONE

from typing import Any


def _key(product: dict) -> str:
    return f"product:{product['id']}"


def update_write_through(product: dict, cache: Any, db: Any, ttl: int = 300) -> None:
    db.save(product)  # TODO: keep the cache in sync


def update_and_invalidate(product: dict, cache: Any, db: Any) -> None:
    raise NotImplementedError  # TODO


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run cache_2
# =============================================================================
import pytest  # noqa: E402


class FakeCache:
    def __init__(self):
        self.data, self.ops = {}, []

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ttl):
        self.ops.append(("set", key))
        self.data[key] = value

    def delete(self, key):
        self.ops.append(("delete", key))
        self.data.pop(key, None)


class FakeDb:
    def __init__(self, fail=False):
        self.rows, self.fail = {}, fail

    def save(self, product):
        if self.fail:
            raise IOError("database unavailable")
        self.rows[product["id"]] = product


def test_write_through_keeps_cache_fresh():
    cache, db = FakeCache(), FakeDb()
    cache.data["product:p-1"] = {"id": "p-1", "price": 10}
    update_write_through({"id": "p-1", "price": 12}, cache, db)
    assert cache.get("product:p-1") == {"id": "p-1", "price": 12}
    assert db.rows["p-1"]["price"] == 12


def test_invalidation_removes_stale_value():
    cache, db = FakeCache(), FakeDb()
    cache.data["product:p-1"] = {"id": "p-1", "price": 10}
    update_and_invalidate({"id": "p-1", "price": 12}, cache, db)
    assert cache.get("product:p-1") is None
    assert ("delete", "product:p-1") in cache.ops


def test_database_failure_does_not_poison_the_cache():
    cache, db = FakeCache(), FakeDb(fail=True)
    with pytest.raises(IOError):
        update_write_through({"id": "p-1", "price": 99}, cache, db)
    assert cache.get("product:p-1") is None
