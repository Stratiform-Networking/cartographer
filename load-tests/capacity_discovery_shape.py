"""
Capacity Discovery Load Test Shape

This module implements a ramping load test that automatically discovers
system capacity by gradually increasing load until performance degrades.

Algorithm:
1. Start with initial_users (default: 10)
2. Every ramp_interval seconds (default: 30s), add ramp_step users (default: 10)
3. Monitor performance metrics:
   - P95 latency threshold (default: 200ms for normal endpoints, 10s for long ops)
   - Error rate threshold (default: 1%)
4. Stop when thresholds exceeded or max duration reached (default: 1 hour)
5. Report the "knee" point = maximum sustainable capacity

This answers: "What can my system handle right now?"
"""

import time
from typing import Optional, Tuple
from locust import LoadTestShape


class CapacityDiscoveryShape(LoadTestShape):
    """
    Capacity discovery load test shape.

    Gradually increases load to find the system's performance limits.
    Stops when P95 latency exceeds threshold, error rate > 1%, or max duration reached.
    Runs until failure - no user limit.

    Configuration via environment variables:
        RAMP_INITIAL_USERS: Starting number of users (default: 10)
        RAMP_STEP: Users to add per step (default: 10)
        RAMP_INTERVAL: Seconds between steps (default: 30)
        RAMP_MAX_DURATION: Maximum test duration in seconds (default: 3600 = 1 hour)
        RAMP_P95_THRESHOLD: P95 latency threshold in ms (default: 200)
        RAMP_ERROR_THRESHOLD: Error rate threshold (default: 0.01 = 1%)
        RAMP_SPAWN_RATE: User spawn rate per second (default: 5)
    """

    # Default configuration
    initial_users = 10          # Start with 10 users
    ramp_step = 10              # Add 10 users per step
    ramp_interval = 30          # Every 30 seconds
    max_duration = 3600         # 1 hour max duration
    p95_threshold = 200         # 200ms P95 latency threshold
    error_threshold = 0.01      # 1% error rate threshold
    spawn_rate = 5              # Spawn 5 users per second
    
    # Internal state (use _test_start_time to avoid parent class conflicts)
    _test_start_time = None
    current_step = 0
    last_logged_step = -1  # Track last logged step to avoid spam
    stopped = False
    stop_reason = None
    knee_point = None
    
    def __init__(self):
        super().__init__()
        # Explicitly override any parent class initialization of start_time
        self._test_start_time = None  # Use a different name to avoid conflicts

        # Read configuration from environment if available
        import os
        self.initial_users = int(os.getenv("RAMP_INITIAL_USERS", self.initial_users))
        self.ramp_step = int(os.getenv("RAMP_STEP", self.ramp_step))
        self.ramp_interval = int(os.getenv("RAMP_INTERVAL", self.ramp_interval))
        self.max_duration = int(os.getenv("RAMP_MAX_DURATION", self.max_duration))
        self.p95_threshold = float(os.getenv("RAMP_P95_THRESHOLD", self.p95_threshold))
        self.error_threshold = float(os.getenv("RAMP_ERROR_THRESHOLD", self.error_threshold))
        self.spawn_rate = int(os.getenv("RAMP_SPAWN_RATE", self.spawn_rate))

        print(f"\n{'='*70}")
        print(f"🔍 CAPACITY DISCOVERY LOAD TEST")
        print(f"{'='*70}")
        print(f"Configuration:")
        print(f"  Initial Users:     {self.initial_users}")
        print(f"  Ramp Step:         +{self.ramp_step} users every {self.ramp_interval}s")
        print(f"  Max Users:         unlimited (runs until failure)")
        print(f"  Max Duration:      {self.max_duration}s ({self.max_duration // 60}m)")
        print(f"  Spawn Rate:        {self.spawn_rate}/s")
        print(f"  P95 Threshold:     {self.p95_threshold}ms")
        print(f"  Error Threshold:   {self.error_threshold*100:.1f}%")
        print(f"{'='*70}")
        print(f"⚠️  NOTE: --run-time flag is IGNORED by this shape")
        print(f"⚠️  Test stops when: P95/error thresholds exceeded OR max duration reached")
        print(f"{'='*70}\n")
    
    @property
    def run_time(self):
        """
        Override run_time property to prevent Locust from using --run-time flag.
        
        When using a LoadTestShape, Locust's --run-time/-t flag should be ignored
        because the shape controls when the test stops. This property ensures that
        even if --run-time is passed, it won't affect capacity discovery.
        """
        return None
    
    def tick(self) -> Optional[Tuple[int, float]]:
        """
        Returns the current target user count and spawn rate.
        Returns None to stop the test.
        """
        # Initialize test start time on first tick (use our own variable)
        if self._test_start_time is None:
            self._test_start_time = time.time()
            print(f"[DEBUG] Initialized _test_start_time at {self._test_start_time}")

        if self.stopped:
            return None

        run_time = time.time() - self._test_start_time

        # Check if max duration reached
        if run_time >= self.max_duration:
            self.stopped = True
            target_users = self.initial_users + (self.current_step * self.ramp_step)
            self.stop_reason = f"Max duration reached ({self.max_duration}s / {self.max_duration // 60}m)"
            self.knee_point = target_users  # System was still healthy at this load
            print(f"\n⏱️  MAX DURATION REACHED: {self.stop_reason}")
            print(f"🎯 System handled {self.knee_point} concurrent users without degradation")
            print(f"   (Test ended before finding capacity limit)\n")
            return None

        # Calculate current step based on elapsed time
        self.current_step = int(run_time / self.ramp_interval)

        # Calculate target user count (no limit - runs until failure)
        target_users = self.initial_users + (self.current_step * self.ramp_step)

        # Check performance metrics (if we have stats and we're past first step)
        if self.current_step > 0 and self._should_stop_based_on_metrics():
            self.stopped = True
            # Knee point is the previous step (before degradation)
            self.knee_point = max(self.initial_users, target_users - self.ramp_step)
            print(f"\n🛑 CAPACITY LIMIT REACHED: {self.stop_reason}")
            print(f"🎯 Knee Point Found: {self.knee_point} concurrent users")
            print(f"   (Performance degraded at {target_users} users)\n")
            return None

        # Log current step only when it changes
        if self.current_step != self.last_logged_step:
            elapsed_min = int(run_time / 60)
            print(f"⏱️  Step {self.current_step + 1} ({elapsed_min}m {int(run_time % 60)}s): "
                  f"Ramping to {target_users} users...")
            self.last_logged_step = self.current_step

        return (target_users, self.spawn_rate)
    
    def _should_stop_based_on_metrics(self) -> bool:
        """
        Check if we should stop based on performance metrics.
        Returns True if performance has degraded beyond thresholds.
        """
        try:
            # Access Locust's statistics through the environment runner
            if not self.runner or not self.runner.stats:
                return False
            
            stats = self.runner.stats
            if not stats.total or stats.total.num_requests == 0:
                return False
            
            total_stats = stats.total
            
            # Check error rate
            if total_stats.num_requests > 100:  # Only check after significant traffic
                error_rate = total_stats.fail_ratio
                if error_rate > self.error_threshold:
                    self.stop_reason = f"Error rate {error_rate*100:.2f}% exceeded threshold {self.error_threshold*100:.1f}%"
                    return True
            
            # Check average response time as a proxy for P95
            if total_stats.num_requests > 100:
                avg_response_time = total_stats.avg_response_time
                # Use a heuristic: if avg exceeds 70% of threshold, performance is degrading
                if avg_response_time > self.p95_threshold * 0.7:
                    self.stop_reason = f"Avg response time {avg_response_time:.0f}ms approaching P95 threshold {self.p95_threshold}ms"
                    return True
            
            return False
            
        except Exception as e:
            # If we can't get stats, continue ramping (don't stop the test)
            print(f"⚠️  Warning: Could not check metrics: {e}")
            return False


class FastCapacityDiscoveryShape(CapacityDiscoveryShape):
    """
    Faster capacity discovery for testing/development.
    Ramps every 15 seconds (faster than default 30s).
    """
    ramp_interval = 15


class ConservativeCapacityDiscoveryShape(CapacityDiscoveryShape):
    """
    Conservative capacity discovery with longer stabilization time.
    Ramps every 60 seconds (slower than default 30s) to allow full stabilization.
    """
    ramp_interval = 60
    
    
class HighCapacityDiscoveryShape(CapacityDiscoveryShape):
    """
    High-capacity discovery for larger systems.
    Starts at 20 users, adds 20 per step.
    """
    initial_users = 20
    ramp_step = 20

