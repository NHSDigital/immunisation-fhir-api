"""Profile 6 (Ramp and Sustain Whilst Finding Ceiling): ramp from cold to peak, then hold.

Ramps from a minimal user count to a high target over a short period,
then holds at peak load for a sustained validation window.

Environment variables (with defaults):
    PERF_PROFILE6_START_USERS    = 1
    PERF_PROFILE6_TARGET_USERS   = 1500
    PERF_PROFILE6_RAMP_SECONDS   = 30
    PERF_PROFILE6_HOLD_SECONDS   = 600
"""

import os

from locust import LoadTestShape, constant_throughput

from locustfile import CreateUser, SearchUser

# Prevent Locust from auto-spawning the base class in this profile.
SearchUser.abstract = True
CreateUser.abstract = True

PERF_PROFILE6_START_USERS = int(os.getenv("PERF_PROFILE6_START_USERS", "1"))
PERF_PROFILE6_TARGET_USERS = int(os.getenv("PERF_PROFILE6_TARGET_USERS", "1500"))
PERF_PROFILE6_RAMP_SECONDS = int(os.getenv("PERF_PROFILE6_RAMP_SECONDS", "30"))
PERF_PROFILE6_HOLD_SECONDS = int(os.getenv("PERF_PROFILE6_HOLD_SECONDS", "600"))


class Profile6SearchRampSustainUser(SearchUser):
    wait_time = constant_throughput(1)


class Profile6CreateRampSustainUser(CreateUser):
    wait_time = constant_throughput(1)


class ProfileSixRampSustainShape(LoadTestShape):
    """Linear ramp from start users to target users, then hold."""

    def tick(self):
        run_time = self.get_run_time()
        total_seconds = PERF_PROFILE6_RAMP_SECONDS + PERF_PROFILE6_HOLD_SECONDS

        if run_time >= total_seconds:
            return None

        if run_time < PERF_PROFILE6_RAMP_SECONDS:
            progress = run_time / max(PERF_PROFILE6_RAMP_SECONDS, 1)
            users = int(PERF_PROFILE6_START_USERS + (PERF_PROFILE6_TARGET_USERS - PERF_PROFILE6_START_USERS) * progress)
            spawn_rate = max(1, PERF_PROFILE6_TARGET_USERS // max(PERF_PROFILE6_RAMP_SECONDS, 1))
            return max(PERF_PROFILE6_START_USERS, users), spawn_rate

        return PERF_PROFILE6_TARGET_USERS, PERF_PROFILE6_TARGET_USERS
