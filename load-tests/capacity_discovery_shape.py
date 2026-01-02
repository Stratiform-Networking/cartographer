"""
Capacity Discovery Load Test Shape

This module implements a ramping load test that automatically discovers
system capacity by gradually increasing load until performance degrades.

Algorithm:
1. Start with initial_users (default: 10)
2. Every ramp_interval seconds (default: 90s), add ramp_step users (default: 10)
3. Monitor performance metrics:
   - P95 latency threshold (default: 200ms for normal endpoints, 10s for long ops)
   - Error rate threshold (default: 1%)
4. Stop when thresholds are exceeded or max_users reached
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
    Stops when P95 latency exceeds threshold or error rate > 1%.
    
    Configuration via environment variables:
        RAMP_INITIAL_USERS: Starting number of users (default: 10)
        RAMP_STEP: Users to add per step (default: 10)
        RAMP_INTERVAL: Seconds between steps (default: 90)
        RAMP_MAX_USERS: Maximum users before stopping (default: 200)
        RAMP_P95_THRESHOLD: P95 latency threshold in ms (default: 200)
        RAMP_ERROR_THRESHOLD: Error rate threshold (default: 0.01 = 1%)
        RAMP_SPAWN_RATE: User spawn rate per second (default: 5)
    """
    
    # Default configuration
    initial_users = 10          # Start with 10 users
    ramp_step = 10              # Add 10 users per step
    ramp_interval = 90          # Every 90 seconds (1.5 min)
    max_users = 200             # Stop at 200 users max
    p95_threshold = 200         # 200ms P95 latency threshold
    error_threshold = 0.01      # 1% error rate threshold
    spawn_rate = 5              # Spawn 5 users per second
    
    # Internal state
    start_time = None
    current_step = 0
    stopped = False
    stop_reason = None
    knee_point = None
    
    def __init__(self):
        super().__init__()
        self.start_time = time.time()
        
        # Read configuration from environment if available
        import os
        self.initial_users = int(os.getenv("RAMP_INITIAL_USERS", self.initial_users))
        self.ramp_step = int(os.getenv("RAMP_STEP", self.ramp_step))
        self.ramp_interval = int(os.getenv("RAMP_INTERVAL", self.ramp_interval))
        self.max_users = int(os.getenv("RAMP_MAX_USERS", self.max_users))
        self.p95_threshold = float(os.getenv("RAMP_P95_THRESHOLD", self.p95_threshold))
        self.error_threshold = float(os.getenv("RAMP_ERROR_THRESHOLD", self.error_threshold))
        self.spawn_rate = int(os.getenv("RAMP_SPAWN_RATE", self.spawn_rate))
        
        print(f"\n{'='*70}")
        print(f"🔍 CAPACITY DISCOVERY LOAD TEST")
        print(f"{'='*70}")
        print(f"Configuration:")
        print(f"  Initial Users:     {self.initial_users}")
        print(f"  Ramp Step:         +{self.ramp_step} users every {self.ramp_interval}s")
        print(f"  Max Users:         {self.max_users}")
        print(f"  Spawn Rate:        {self.spawn_rate}/s")
        print(f"  P95 Threshold:     {self.p95_threshold}ms")
        print(f"  Error Threshold:   {self.error_threshold*100:.1f}%")
        print(f"{'='*70}\n")
    
    def tick(self) -> Optional[Tuple[int, float]]:
        """
        Returns the current target user count and spawn rate.
        Returns None to stop the test.
        """
        if self.stopped:
            return None
        
        run_time = time.time() - self.start_time
        
        # Calculate current step based on elapsed time
        self.current_step = int(run_time / self.ramp_interval)
        
        # Calculate target user count
        target_users = self.initial_users + (self.current_step * self.ramp_step)
        
        # Cap at max_users
        if target_users > self.max_users:
            target_users = self.max_users
        
        # Debug: Log what we're calculating
        print(f"[DEBUG] run_time={run_time:.1f}s, step={self.current_step}, target={target_users}")
        
        # Check if we've hit max users and should stop
        if target_users >= self.max_users and self.current_step > 0:
            self.stopped = True
            self.stop_reason = f"Max users reached ({self.max_users})"
            self.knee_point = self.max_users
            print(f"\n⚠️  CAPACITY TEST COMPLETE: {self.stop_reason}")
            print(f"🎯 System handled {self.knee_point} concurrent users successfully\n")
            # Return max_users one last time, then stop on next tick
            return (target_users, self.spawn_rate)
        
        # Check performance metrics (if we have stats and we're past first step)
        if self.current_step > 0 and self._should_stop_based_on_metrics():
            self.stopped = True
            # Knee point is the previous step (before degradation)
            self.knee_point = max(self.initial_users, target_users - self.ramp_step)
            print(f"\n🛑 CAPACITY LIMIT REACHED: {self.stop_reason}")
            print(f"🎯 Knee Point Found: {self.knee_point} concurrent users")
            print(f"   (Performance degraded at {target_users} users)\n")
            return None
        
        # Log current step
        if self.current_step == 0 or (run_time > 0 and run_time % self.ramp_interval < 1):
            elapsed_min = int(run_time / 60)
            print(f"⏱️  Step {self.current_step + 1} ({elapsed_min}m {int(run_time % 60)}s): "
                  f"Ramping to {target_users} users...")
        
        return (target_users, self.spawn_rate)
    
    def _should_stop_based_on_metrics(self) -> bool:
        """
        Check if we should stop based on performance metrics.
        Returns True if performance has degraded beyond thresholds.
        """
        try:
            # Access Locust's statistics
            from locust import stats as locust_stats
            
            if not locust_stats.stats or not locust_stats.stats.total:
                return False
            
            total_stats = locust_stats.stats.total
            
            # Check error rate
            if total_stats.num_requests > 100:  # Only check after significant traffic
                error_rate = total_stats.num_failures / total_stats.num_requests
                if error_rate > self.error_threshold:
                    self.stop_reason = f"Error rate {error_rate*100:.2f}% exceeded threshold {self.error_threshold*100:.1f}%"
                    return True
            
            # Check P95 latency (if available)
            # Note: Locust doesn't expose percentiles directly in real-time
            # We approximate using average response time as a proxy
            if total_stats.num_requests > 100:
                avg_response_time = total_stats.avg_response_time
                # Use a heuristic: if avg exceeds threshold, P95 likely does too
                if avg_response_time > self.p95_threshold * 0.7:  # 70% of threshold
                    self.stop_reason = f"Avg response time {avg_response_time:.0f}ms approaching P95 threshold {self.p95_threshold}ms"
                    return True
            
            return False
            
        except Exception as e:
            # If we can't get stats, continue ramping
            print(f"⚠️  Warning: Could not check metrics: {e}")
            return False


class FastCapacityDiscoveryShape(CapacityDiscoveryShape):
    """
    Faster capacity discovery for testing/development.
    Ramps every 60 seconds instead of 90.
    """
    ramp_interval = 60


class ConservativeCapacityDiscoveryShape(CapacityDiscoveryShape):
    """
    Conservative capacity discovery with longer stabilization time.
    Ramps every 120 seconds (2 minutes) to allow full stabilization.
    """
    ramp_interval = 120
    
    
class HighCapacityDiscoveryShape(CapacityDiscoveryShape):
    """
    High-capacity discovery for larger systems.
    Starts at 20 users, adds 20 per step, up to 500 max.
    """
    initial_users = 20
    ramp_step = 20
    max_users = 500

