import os
import pathlib
import subprocess
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from pydantic import BaseModel
import json


router = APIRouter()


class MapperResponse(BaseModel):
	content: str
	script_exit_code: int
	network_map_path: Optional[str] = None


def _project_root() -> pathlib.Path:
	# backend/app/routers -> repo root at ../../..
	return pathlib.Path(__file__).resolve().parents[3]


def _script_path() -> pathlib.Path:
	return _project_root() / "lan_mapper.sh"


def _network_map_candidates() -> list[pathlib.Path]:
	root = _project_root()
	return [
		root / "network_map.txt",
		root / "output" / "network_map.txt",
	]


@router.get("/config")
def get_config():
	# Frontend can use this to discover deployment base URL
	app_url = os.environ.get("APPLICATION_URL", "")
	return JSONResponse({"applicationUrl": app_url})


@router.post("/run-mapper", response_model=MapperResponse)
def run_mapper() -> MapperResponse:
	script = _script_path()
	if not script.exists():
		raise HTTPException(status_code=404, detail=f"lan_mapper.sh not found at {script}")
	if not os.access(script, os.X_OK):
		# Try to run with /bin/bash even if not executable
		cmd = ["/bin/bash", str(script)]
	else:
		cmd = [str(script)]

	try:
		# Run from repo root to keep relative paths consistent
		proc = subprocess.run(
			cmd,
			cwd=str(_project_root()),
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			text=True,
			timeout=300,
		)
	except subprocess.TimeoutExpired:
		raise HTTPException(status_code=504, detail="lan_mapper.sh timed out after 300s")
	except Exception as exc:  # pragma: no cover
		raise HTTPException(status_code=500, detail=f"Failed to run lan_mapper.sh: {exc}")

	# Prefer an actual file artifact if present
	content: Optional[str] = None
	map_path: Optional[str] = None
	for candidate in _network_map_candidates():
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
		# Provide stderr context for easier debugging
		raise HTTPException(
			status_code=500,
			detail=f"No network_map.txt content produced. stderr: {proc.stderr.strip()}",
		)

	return MapperResponse(
		content=content,
		script_exit_code=proc.returncode,
		network_map_path=map_path,
	)

def _sse_event(event: str, data: str) -> str:
	# Basic SSE formatting; split multi-line payloads
	lines = data.splitlines() or [""]
	chunks = [f"event: {event}"]
	for line in lines:
		chunks.append(f"data: {line}")
	chunks.append("")  # end of message
	return "\n".join(chunks) + "\n"


@router.get("/run-mapper/stream")
def run_mapper_stream():
	script = _script_path()
	if not script.exists():
		raise HTTPException(status_code=404, detail=f"lan_mapper.sh not found at {script}")

	def event_gen():
		# Try to execute with bash to avoid exec perm issues
		cmd = ["/bin/bash", str(script)] if not os.access(script, os.X_OK) else [str(script)]
		try:
			proc = subprocess.Popen(
				cmd,
				cwd=str(_project_root()),
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				text=True,
				bufsize=1,
				universal_newlines=True,
			)
		except Exception as exc:
			yield _sse_event("log", f"ERROR: failed to start lan_mapper.sh: {exc}")
			yield _sse_event("done", "exit=-1")
			return

		# Stream stdout
		if proc.stdout:
			for line in proc.stdout:
				yield _sse_event("log", line.rstrip("\n"))
		# Drain stderr afterwards (some scripts only write stderr)
		if proc.stderr:
			for line in proc.stderr:
				stripped = line.rstrip('\n')
				yield _sse_event("log", f"STDERR: {stripped}")

		exit_code = proc.wait()

		# Attempt to read produced file
		result_payload = {"content": "", "script_exit_code": exit_code, "network_map_path": None}
		for candidate in _network_map_candidates():
			if candidate.exists():
				try:
					result_payload["content"] = candidate.read_text()
					result_payload["network_map_path"] = str(candidate)
					break
				except Exception as exc:
					yield _sse_event("log", f"ERROR: could not read {candidate}: {exc}")

		# If no file, try to provide a minimal result from stdout (already streamed)
		if not result_payload["content"]:
			result_payload["content"] = ""

		yield _sse_event("result", json.dumps(result_payload))
		yield _sse_event("done", f"exit={exit_code}")

	return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get("/download-map")
def download_map():
	# Serve the latest produced network_map.txt as a download
	for candidate in _network_map_candidates():
		if candidate.exists():
			filename = candidate.name
			return FileResponse(
				path=str(candidate),
				filename=filename,
				media_type="text/plain",
			)
	raise HTTPException(status_code=404, detail="network_map.txt not found")


def _saved_layout_path() -> pathlib.Path:
	"""Path where the saved network layout JSON is stored"""
	# Use /app/data for Docker volume persistence
	data_dir = pathlib.Path("/app/data")
	if data_dir.exists():
		return data_dir / "saved_network_layout.json"
	# Fallback to project root for local development
	return _project_root() / "saved_network_layout.json"


@router.post("/save-layout")
def save_layout(layout: dict):
	"""Save the network layout to the server"""
	try:
		layout_path = _saved_layout_path()
		with open(layout_path, 'w') as f:
			json.dump(layout, f, indent=2)
		return JSONResponse({
			"success": True,
			"message": "Layout saved successfully",
			"path": str(layout_path)
		})
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Failed to save layout: {exc}")


@router.get("/load-layout")
def load_layout():
	"""Load the saved network layout from the server"""
	layout_path = _saved_layout_path()
	if not layout_path.exists():
		return JSONResponse({"exists": False, "layout": None})
	
	try:
		with open(layout_path, 'r') as f:
			layout = json.load(f)
		return JSONResponse({
			"exists": True,
			"layout": layout
		})
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Failed to load layout: {exc}")


@router.get("/embed-data")
def get_embed_data():
	"""Get the network map data for the embed view (read-only, no auth required)"""
	layout_path = _saved_layout_path()
	if not layout_path.exists():
		return JSONResponse({"exists": False, "root": None})
	
	try:
		with open(layout_path, 'r') as f:
			layout = json.load(f)
		
		# Return just the root tree node for the embed
		root = layout.get("root")
		if not root:
			return JSONResponse({"exists": False, "root": None})
		
		return JSONResponse({
			"exists": True,
			"root": root
		})
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Failed to load embed data: {exc}")


