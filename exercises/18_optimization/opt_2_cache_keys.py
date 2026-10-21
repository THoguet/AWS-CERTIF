"""
Exercise opt_2 — Caching content based on request headers
=========================================================
Book: chapter 23, "Caching for performance" and chapter 8, "CloudFront"
Exam: Domain 4 · Task 4.3 (caching content based on request headers)

CloudFront (and API Gateway caching) store one copy of a response per
CACHE KEY. Every header, cookie or query string parameter you add to the
key multiplies the number of variants and divides the hit ratio:
  * vary on Accept-Language if the page is translated → good,
  * vary on User-Agent (thousands of values) → the cache becomes useless,
  * values that the origin needs but that do not change the response
    belong in an origin request policy (forwarded, NOT in the cache key).

Your task
---------
  * `cache_key(request, key_headers, key_query)`,
  * `hit_ratio(requests, key_headers, key_query)`: fraction of requests
    served from cache (the first request for each key is a miss, assuming
    nothing expires),
  * `cache_policy()`: CloudFront CachePolicyConfig named "localized-pages",
    TTLs min 0 / default 86400 / max 31536000, gzip and brotli enabled,
    cache key = header Accept-Language + query string "lang", no cookies.
"""

# I AM NOT DONE


def cache_key(request: dict, key_headers: list[str], key_query: list[str]) -> tuple:
    raise NotImplementedError  # TODO


def hit_ratio(requests: list[dict], key_headers: list[str], key_query: list[str]) -> float:
    raise NotImplementedError  # TODO


def cache_policy() -> dict:
    raise NotImplementedError  # TODO


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run opt_2
# =============================================================================
import random  # noqa: E402

LANGS = ["fr-FR", "en-US", "de-DE"]


def _traffic(n=600, seed=7):
    rng = random.Random(seed)
    return [
        {
            "path": rng.choice(["/", "/pricing", "/docs"]),
            "headers": {"Accept-Language": rng.choice(LANGS), "User-Agent": f"Browser/{rng.randint(1, 5000)}"},
            "query": {"utm_source": f"campaign-{rng.randint(1, 1000)}"},
        }
        for _ in range(n)
    ]


def test_cache_key():
    request = {"path": "/docs", "headers": {"accept-language": "fr-FR", "User-Agent": "x"}, "query": {"lang": "fr", "utm_source": "ad"}}
    assert cache_key(request, ["Accept-Language"], ["lang"]) == ("/docs", ("fr-FR",), ("fr",))


def test_good_key_has_high_hit_ratio():
    assert hit_ratio(_traffic(), ["Accept-Language"], []) > 0.95


def test_user_agent_or_tracking_params_kill_the_cache():
    traffic = _traffic()
    assert hit_ratio(traffic, ["Accept-Language", "User-Agent"], []) < 0.1
    assert hit_ratio(traffic, ["Accept-Language"], ["utm_source"]) < 0.5


def test_cache_policy():
    policy = cache_policy()
    params = policy["ParametersInCacheKeyAndForwardedToOrigin"]
    assert (policy["MinTTL"], policy["DefaultTTL"], policy["MaxTTL"]) == (0, 86400, 31536000)
    assert params["EnableAcceptEncodingGzip"] and params["EnableAcceptEncodingBrotli"]
    assert params["HeadersConfig"] == {"HeaderBehavior": "whitelist", "Headers": {"Quantity": 1, "Items": ["Accept-Language"]}}
    assert params["CookiesConfig"] == {"CookieBehavior": "none"}
    assert params["QueryStringsConfig"]["QueryStrings"]["Items"] == ["lang"]
