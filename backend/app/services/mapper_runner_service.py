"""
Mapper script execution service.

Handles:
- Network mapper script execution (sync and streaming)
- Network map file discovery
- Layout file persistence
- SSE event formatting
"""

import json
import os
import pathlib
import platform
import shutil
import subprocess
from dataclasses import dataclass
from typing import Generator


@dataclass
class MapperResult:
    """Result from running the mapper script."""

    content: str
    exit_code: int
    map_path: str | None = None


def project_root() -> pathlib.Path:
    """Get the project root directory.

    Returns:
        Path to the repository root
    """
    # services -> app -> backend -> repo root
    return pathlib.Path(__file__).resolve().parents[3]


def script_path() -> pathlib.Path:
    """Get the path to the mapper script.

    Returns:
        Path to lan_mapper.sh
    """
    return project_root() / "lan_mapper.sh"


def network_map_candidates() -> list[pathlib.Path]:
    """Get candidate paths where network map file might be located.

    Returns:
        List of paths to check for network_map.txt
    """
    root = project_root()
    return [
        root / "network_map.txt",
        root / "output" / "network_map.txt",
    ]


def saved_layout_path() -> pathlib.Path:
    """Get the path where the saved network layout JSON is stored.

    Returns:
        Path to saved_network_layout.json
    """
    # Use /app/data for Docker volume persistence
    data_dir = pathlib.Path("/app/data")
    if data_dir.exists():
        return data_dir / "saved_network_layout.json"
    # Fallback to project root for local development
    return project_root() / "saved_network_layout.json"


def sse_event(event: str, data: str) -> str:
    """Format data as a Server-Sent Event.

    Args:
        event: Event type name
        data: Event data (can be multi-line)

    Returns:
        SSE-formatted string
    """
    lines = data.splitlines() or [""]
    chunks = [f"event: {event}"]
    for line in lines:
        chunks.append(f"data: {line}")
    chunks.append("")  # end of message
    return "\n".join(chunks) + "\n"


def get_script_command() -> list[str]:
    """Get the command to run the mapper script.

    Returns:
        Command list for subprocess
    """
    script = script_path()
    system = platform.system().lower()

    if system.startswith("win"):
        ps1 = project_root() / "lan_mapper.ps1"
        if ps1.exists():
            for candidate in ("pwsh", "powershell.exe", "powershell"):
                resolved = shutil.which(candidate)
                if resolved:
                    return [
                        resolved,
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(ps1),
                    ]
        bash = shutil.which("bash")
        if bash:
            return [bash, str(script)]

    if not os.access(script, os.X_OK):
        if system.startswith("win"):
            return [str(script)]
        # Try to run with /bin/bash if not executable
        return ["/bin/bash", str(script)]
    return [str(script)]


def run_mapper_sync(timeout: int = 300) -> MapperResult:
    """Run the mapper script synchronously.

    Args:
        timeout: Maximum execution time in seconds

    Returns:
        MapperResult with content, exit code, and optional map path

    Raises:
        FileNotFoundError: If script doesn't exist
        TimeoutError: If script times out
        RuntimeError: If script fails to run
    """
    script = script_path()
    if not script.exists():
        raise FileNotFoundError(f"lan_mapper.sh not found at {script}")

    cmd = get_script_command()

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(project_root()),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"lan_mapper.sh timed out after {timeout}s")
    except Exception as exc:
        raise RuntimeError(f"Failed to run lan_mapper.sh: {exc}")

    # Prefer an actual file artifact if present
    content: str | None = None
    map_path: str | None = None

    for candidate in network_map_candidates():
        if candidate.exists():
            try:
                content = candidate.read_text()
                map_path = str(candidate)
                break
            except Exception:
                pass

    # Fallback to stdout
    if content is None:
        content = proc.stdout.strip()

    if not content:
        stderr_msg = proc.stderr.strip() if proc.stderr else "No output"
        raise RuntimeError(f"No network_map.txt content produced. stderr: {stderr_msg}")

    return MapperResult(content=content, exit_code=proc.returncode, map_path=map_path)


def run_mapper_streaming() -> Generator[str, None, None]:
    """Run the mapper script with streaming output.

    Yields:
        SSE-formatted event strings

    Raises:
        FileNotFoundError: If script doesn't exist
    """
    script = script_path()
    if not script.exists():
        raise FileNotFoundError(f"lan_mapper.sh not found at {script}")

    cmd = get_script_command()

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(project_root()),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
    except Exception as exc:
        yield sse_event("log", f"ERROR: failed to start lan_mapper.sh: {exc}")
        yield sse_event("done", "exit=-1")
        return

    # Stream stdout
    if proc.stdout:
        for line in proc.stdout:
            yield sse_event("log", line.rstrip("\n"))

    # Drain stderr afterwards
    if proc.stderr:
        for line in proc.stderr:
            stripped = line.rstrip("\n")
            yield sse_event("log", f"STDERR: {stripped}")

    exit_code = proc.wait()

    # Attempt to read produced file
    result_payload = {"content": "", "script_exit_code": exit_code, "network_map_path": None}

    for candidate in network_map_candidates():
        if candidate.exists():
            try:
                result_payload["content"] = candidate.read_text()
                result_payload["network_map_path"] = str(candidate)
                break
            except Exception as exc:
                yield sse_event("log", f"ERROR: could not read {candidate}: {exc}")

    yield sse_event("result", json.dumps(result_payload))
    yield sse_event("done", f"exit={exit_code}")


def find_network_map() -> pathlib.Path | None:
    """Find the network map file.

    Returns:
        Path to network_map.txt if found, None otherwise
    """
    for candidate in network_map_candidates():
        if candidate.exists():
            return candidate
    return None


def save_layout(layout: dict) -> str:
    """Save network layout to file.

    Args:
        layout: Layout data to save

    Returns:
        Path where layout was saved

    Raises:
        RuntimeError: If save fails
    """
    try:
        layout_path = saved_layout_path()
        with open(layout_path, "w") as f:
            json.dump(layout, f, indent=2)
        return str(layout_path)
    except Exception as exc:
        raise RuntimeError(f"Failed to save layout: {exc}")


def load_layout() -> dict | None:
    """Load saved network layout from file.

    Returns:
        Layout dict if exists, None otherwise

    Raises:
        RuntimeError: If load fails
    """
    layout_path = saved_layout_path()
    if not layout_path.exists():
        return None

    try:
        with open(layout_path, "r") as f:
            return json.load(f)
    except Exception as exc:
        raise RuntimeError(f"Failed to load layout: {exc}")
