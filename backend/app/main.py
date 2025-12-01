import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .routers.mapper import router as mapper_router
from .routers.health_proxy import router as health_proxy_router


def create_app() -> FastAPI:
	app = FastAPI(title="Cartographer Backend", version="0.1.0")

	# Allow local dev UIs
	app.add_middleware(
		CORSMiddleware,
		allow_origins=["*"],
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

	app.include_router(mapper_router, prefix="/api")
	app.include_router(health_proxy_router, prefix="/api")

	# Serve built frontend if present (for production) with SPA fallback
	# FRONTEND_DIST can override default location
	default_dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"
	dist_path = Path(os.environ.get("FRONTEND_DIST", str(default_dist)))
	if dist_path.exists():
		assets_dir = dist_path / "assets"
		if assets_dir.exists():
			app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

		index_file = dist_path / "index.html"
		if index_file.exists():
			@app.get("/", include_in_schema=False)
			def index():
				return FileResponse(str(index_file))

			# SPA fallback - keep /api routes working, everything else serves index.html
			@app.get("/{full_path:path}", include_in_schema=False)
			def spa_fallback(full_path: str):
				# Avoid catching API explicitly (redundant due to route order, but defensive)
				if full_path.startswith("api"):
					return {"detail": "Not Found"}
				return FileResponse(str(index_file))

	return app


app = create_app()


