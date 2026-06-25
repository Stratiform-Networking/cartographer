#!/usr/bin/env python3
"""
Cartographer Load Test Runner

This script provides an easy way to run load tests against Cartographer microservices.
It can run tests against individual services or all services at once.

IMPORTANT: All endpoints require authentication. Provide credentials via:
    --username and --password arguments, OR
    LOADTEST_USERNAME and LOADTEST_PASSWORD environment variables
    Optional: --auth-host / LOADTEST_AUTH_HOST (default: http://localhost:8002)

Usage:
    python run_load_tests.py --service all -u 10 -r 2 -t 60 --username myuser --password mypass
    python run_load_tests.py --service health --users 10 --spawn-rate 2 --time 60
    python run_load_tests.py --service auth --users 20 --web  # Opens web UI
"""

import argparse
import subprocess
import sys
import os

DEFAULT_AUTH_HOST = "http://localhost:8002"

# Service configuration
SERVICES = {
    "health": {
        "file": "locustfile_health.py",
        "port": 8001,
        "description": "Health monitoring service (ping, ports, DNS, speed tests)",
    },
    "auth": {
        "file": "locustfile_auth.py",
        "port": 8002,
        "description": "Authentication service (login, users, invites)",
    },
    "metrics": {
        "file": "locustfile_metrics.py",
        "port": 8003,
        "description": "Metrics service (snapshots, Redis, WebSocket)",
    },
    "assistant": {
        "file": "locustfile_assistant.py",
        "port": 8004,
        "description": "AI Assistant service (chat, context, providers)",
    },
    "notifications": {
        "file": "locustfile_notification.py",
        "port": 8005,
        "description": "Notification service (preferences, Discord, ML)",
    },
    "all": {
        "file": "locustfile_all.py",
        "port": 8000,
        "description": "All services via main backend proxy",
    },
}


def run_locust(
    service: str,
    users: int,
    spawn_rate: float,
    run_time: int,
    host: str,
    web: bool,
    tags: list,
    headless: bool,
    html_report: str,
    username: str,
    password: str,
    auth_host: str,
):
    """Run locust with the specified configuration"""
    
    service_config = SERVICES[service]
    locustfile = os.path.join(os.path.dirname(__file__), service_config["file"])
    
    if not host:
        host = f"http://localhost:{service_config['port']}"
    
    # Set environment variables for authentication
    env = os.environ.copy()
    if username:
        env["LOADTEST_USERNAME"] = username
    if password:
        env["LOADTEST_PASSWORD"] = password
    resolved_auth_host = auth_host or env.get("LOADTEST_AUTH_HOST", DEFAULT_AUTH_HOST)
    env["LOADTEST_AUTH_HOST"] = resolved_auth_host
    
    cmd = ["locust", "-f", locustfile, "--host", host, "--exit-code-on-error", "1"]
    
    if web:
        # Web UI mode
        print(f"\n🌐 Starting Locust Web UI for {service} service")
        print(f"   Target: {host}")
        print(f"   Auth host: {resolved_auth_host}")
        print(f"   Username: {username or env.get('LOADTEST_USERNAME', 'loadtest')}")
        print(f"   Open http://localhost:8089 in your browser\n")
    else:
        # Headless mode
        cmd.extend([
            "--headless",
            "-u", str(users),
            "-r", str(spawn_rate),
            "-t", f"{run_time}s",
        ])
        
        if html_report:
            cmd.extend(["--html", html_report])
        
        print(f"\n🚀 Running load test for {service} service")
        print(f"   Target: {host}")
        print(f"   Auth host: {resolved_auth_host}")
        print(f"   Username: {username or env.get('LOADTEST_USERNAME', 'loadtest')}")
        print(f"   Users: {users}")
        print(f"   Spawn rate: {spawn_rate}/s")
        print(f"   Duration: {run_time}s")
        if tags:
            print(f"   Tags: {', '.join(tags)}")
        print()
    
    if tags:
        cmd.extend(["--tags", ",".join(tags)])
    
    try:
        result = subprocess.run(cmd, env=env, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n\n⏹️  Load test stopped by user")
        return 130
    except FileNotFoundError:
        print("\n❌ Error: locust is not installed.")
        print("   Install with: pip install -r requirements.txt")
        return 1


def list_services():
    """Print available services"""
    print("\n📋 Available services:\n")
    for name, config in SERVICES.items():
        print(f"   {name:15} - {config['description']}")
        print(f"                    Port: {config['port']}, File: {config['file']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Run load tests against Cartographer microservices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run quick test with credentials
  python run_load_tests.py -s all -u 10 -r 2 -t 30 --username myuser --password mypass

  # Run using environment variables (recommended for CI/CD)
  set LOADTEST_USERNAME=myuser && set LOADTEST_PASSWORD=mypass
  python run_load_tests.py -s all -u 10 -r 2 -t 30

  # Run comprehensive test on all services
  python run_load_tests.py -s all -u 100 -r 10 -t 300 --html report.html --username admin --password secret

  # Open web UI for interactive testing
  python run_load_tests.py -s metrics --web --username myuser --password mypass

  # Test only read operations
  python run_load_tests.py -s health -u 50 -r 5 -t 60 --tags read

  # Direct service test with explicit auth host
  python run_load_tests.py -s metrics --host http://localhost:8003 --auth-host http://localhost:8002

  # List available services
  python run_load_tests.py --list
        """
    )
    
    parser.add_argument(
        "-s", "--service",
        choices=list(SERVICES.keys()),
        default="all",
        help="Service to test (default: all)"
    )
    
    parser.add_argument(
        "-u", "--users",
        type=int,
        default=10,
        help="Number of concurrent users (default: 10)"
    )
    
    parser.add_argument(
        "-r", "--spawn-rate",
        type=float,
        default=1,
        help="User spawn rate per second (default: 1)"
    )
    
    parser.add_argument(
        "-t", "--time",
        type=int,
        default=60,
        help="Test duration in seconds (default: 60)"
    )
    
    parser.add_argument(
        "--host",
        help="Target host URL (default: localhost with service port)"
    )
    
    parser.add_argument(
        "--web",
        action="store_true",
        help="Open Locust web UI instead of running headless"
    )
    
    parser.add_argument(
        "--tags",
        nargs="+",
        help="Only run tasks with specified tags"
    )
    
    parser.add_argument(
        "--html",
        help="Generate HTML report to specified file"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available services and exit"
    )
    
    parser.add_argument(
        "--username",
        help="Username for authentication (or set LOADTEST_USERNAME env var)"
    )
    
    parser.add_argument(
        "--password",
        help="Password for authentication (or set LOADTEST_PASSWORD env var)"
    )

    parser.add_argument(
        "--auth-host",
        default=os.environ.get("LOADTEST_AUTH_HOST", DEFAULT_AUTH_HOST),
        help=f"Auth service base URL for login requests (default: {DEFAULT_AUTH_HOST})",
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_services()
        return
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║           Cartographer Load Test Runner                       ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    rc = run_locust(
        service=args.service,
        users=args.users,
        spawn_rate=args.spawn_rate,
        run_time=args.time,
        host=args.host,
        web=args.web,
        tags=args.tags or [],
        headless=not args.web,
        html_report=args.html,
        username=args.username,
        password=args.password,
        auth_host=args.auth_host,
    )
    sys.exit(rc)


if __name__ == "__main__":
    main()
