"""
Hypothesis configuration for the property-test suite.

Several legacy generators build large price/volume lists that occasionally overrun
Hypothesis' default size budget, tripping the `data_too_large` health check. The
underlying calculations are correct, so we suppress that (and the slow-data) health
check and drop the per-example deadline for these data-heavy numeric tests.
"""

from hypothesis import HealthCheck, settings

settings.register_profile(
    "v3",
    suppress_health_check=[HealthCheck.data_too_large, HealthCheck.too_slow],
    deadline=None,
)
settings.load_profile("v3")
