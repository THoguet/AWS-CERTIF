"""
Exercise cicd_3 — Elastic Beanstalk deployment policies
=======================================================
Book: chapter 18, "Elastic Beanstalk deployment policies" (book/src/ch18-beanstalk-containers.md)
Exam: Domain 3 · Task 3.4 (deploying an application version by using deployment strategies)

| Policy                     | Downtime | Capacity during deploy | Rollback          | Extra cost        |
|----------------------------|----------|------------------------|-------------------|-------------------|
| AllAtOnce                  | YES      | 0 during the switch    | redeploy (slow)   | none              |
| Rolling                    | no       | reduced (n - batch)    | redeploy          | none              |
| RollingWithAdditionalBatch | no       | full                   | redeploy          | 1 extra batch     |
| Immutable                  | no       | full (+ new ASG)       | fast: delete new  | double, briefly   |
| TrafficSplitting (canary)  | no       | full                   | fast: reroute     | double, briefly   |
Blue/green = clone the environment, deploy there, then "Swap environment URLs" (CNAME swap).

Your task
---------
  * `choose_policy(downtime_ok, needs_full_capacity, fast_rollback, canary_testing)`,
  * `serving_instances(policy, instances, batch_size)`: minimum number of
    instances running the app and serving traffic while the deployment runs.
"""


def choose_policy(downtime_ok: bool, needs_full_capacity: bool, fast_rollback: bool, canary_testing: bool) -> str:
    if downtime_ok:
        return "AllAtOnce"
    if canary_testing:
        return "TrafficSplitting"
    if fast_rollback:
        return "Immutable"
    if needs_full_capacity:
        return "RollingWithAdditionalBatch"
    return "Rolling"


def serving_instances(policy: str, instances: int, batch_size: int = 1) -> int:
    if policy == "AllAtOnce":
        return 0
    if policy == "Rolling":
        return instances - batch_size
    return instances


# =============================================================================
# Tests — do not edit below this line.  Run them with: awslings run cicd_3
# =============================================================================


def test_dev_environment_fastest_cheapest():
    assert choose_policy(downtime_ok=True, needs_full_capacity=False, fast_rollback=False, canary_testing=False) == "AllAtOnce"


def test_zero_downtime_reduced_capacity_ok():
    assert choose_policy(False, False, False, False) == "Rolling"


def test_zero_downtime_full_capacity():
    assert choose_policy(False, True, False, False) == "RollingWithAdditionalBatch"


def test_fast_rollback_new_instances():
    assert choose_policy(False, True, True, False) == "Immutable"


def test_canary():
    assert choose_policy(False, True, True, True) == "TrafficSplitting"


def test_serving_capacity():
    assert serving_instances("AllAtOnce", 4) == 0
    assert serving_instances("Rolling", 4, batch_size=2) == 2
    assert serving_instances("RollingWithAdditionalBatch", 4, batch_size=2) == 4
    assert serving_instances("Immutable", 4) == 4
