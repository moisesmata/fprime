"""pytest settle fixture for the soak integration tests.

Why this is needed here but not in ext-aarch64-linux-led-blinker.yml:

In the regular workflow the GDS launches the FSW app itself, so the GDS comm layer
and the flight software start together. The GDS consumes the downlink from the
moment the app emits it, there is no backlog, and the ZeroMQ subscription is live
before any command is sent.

In the soak setup the FSW runs as a long-lived systemd service. By the time the
test job starts its own GDS client and pytest connects, the FSW has been emitting
telemetry/events with no consumer, so a backlog has queued on the FSW side.
pytest's fixture connects an ephemeral ZeroMQ subscriber and immediately sends a
command, but ZeroMQ's "slow joiner" behavior means the subscription is not live
yet (and the backlog is still flushing). The command's response events land in
that gap and are dropped, so the first assertion fails with 0 events.

A shell `sleep` before pytest cannot fix this because the dead window is inside
the pytest process, right after its fixture connects. This session-scoped,
autouse fixture runs once after the pipeline is connected (the dependency on
fprime_test_api_session guarantees that) and before any test sends a command. It
waits until telemetry is actually being received - which proves the subscription
is live and current - then settles briefly so any backlog has flushed.
"""

import os
import time

import pytest


@pytest.fixture(scope="session", autouse=True)
def gds_subscription_settle(fprime_test_api_session):
    api = fprime_test_api_session
    live_timeout = float(os.environ.get("SOAK_GDS_SETTLE_TIMEOUT", "30"))
    extra_settle = float(os.environ.get("SOAK_GDS_SETTLE_SECONDS", "5"))

    # Telemetry is produced every rate-group cycle, so a growing telemetry history
    # confirms the subscription is live and receiving current data.
    deadline = time.time() + live_timeout
    baseline = api.telemetry_history.size()
    while time.time() < deadline and api.telemetry_history.size() == baseline:
        time.sleep(0.5)

    # Brief extra settle so any FSW downlink backlog finishes flushing before the
    # first command is sent.
    time.sleep(extra_settle)
    yield
