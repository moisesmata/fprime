"""pytest configuration for soak integration tests.

The soak deployment runs the F´ GDS as a long-lived system service that owns the
ZeroMQ publish/subscribe network. Each `pytest` invocation creates its own GDS
client that connects to that already-running service. ZeroMQ pub/sub has a
"slow joiner" property: a newly connected subscriber is not registered with the
publisher instantaneously, so any downlink produced in the first moments after
connecting can be dropped. Because the integration tests send a command and then
immediately assert on the resulting events, that race makes the very first
assertion intermittently (and here, consistently) fail with zero events received.

This fixture inserts a one-time settle delay after the test pipeline has
connected (the dependency on `fprime_test_api_session` guarantees the pipeline is
already set up) and before any test sends a command, giving the subscription time
to propagate to the publisher.

The delay is configurable via the SOAK_GDS_SETTLE_SECONDS environment variable.
"""

import os
import time

import pytest


@pytest.fixture(scope="session", autouse=True)
def _gds_subscription_settle(fprime_test_api_session):
    settle_seconds = float(os.environ.get("SOAK_GDS_SETTLE_SECONDS", "5"))
    time.sleep(settle_seconds)
    yield
