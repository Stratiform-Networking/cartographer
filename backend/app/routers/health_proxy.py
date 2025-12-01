"""
Proxy router for health service requests.
Forwards /api/health/* requests to the health microservice.
"""
import os
import httpx
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from typing import Optional

router = APIRouter(prefix="/health", tags=["health"])

# Health service URL - defaults to localhost:8001 for host network mode
HEALTH_SERVICE_URL = os.environ.get("HEALTH_SERVICE_URL", "http://localhost:8001")


async def proxy_request(method: str, path: str, params: dict = None, json_body: dict = None):
    """Forward a request to the health service"""
    url = f"{HEALTH_SERVICE_URL}/api/health{path}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if method == "GET":
                response = await client.get(url, params=params)
            elif method == "POST":
                response = await client.post(url, params=params, json=json_body)
            elif method == "DELETE":
                response = await client.delete(url, params=params)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Health service unavailable"
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Health service timeout"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Health service error: {str(e)}"
            )


@router.get("/check/{ip}")
async def check_device(
    ip: str,
    include_ports: bool = Query(False),
    include_dns: bool = Query(True)
):
    """Proxy health check for a single device"""
    return await proxy_request(
        "GET",
        f"/check/{ip}",
        params={"include_ports": include_ports, "include_dns": include_dns}
    )


@router.post("/check/batch")
async def check_batch(request: Request):
    """Proxy batch health check"""
    body = await request.json()
    return await proxy_request("POST", "/check/batch", json_body=body)


@router.get("/cached/{ip}")
async def get_cached(ip: str):
    """Proxy get cached metrics"""
    return await proxy_request("GET", f"/cached/{ip}")


@router.get("/cached")
async def get_all_cached():
    """Proxy get all cached metrics"""
    return await proxy_request("GET", "/cached")


@router.delete("/cache")
async def clear_cache():
    """Proxy clear cache"""
    return await proxy_request("DELETE", "/cache")


@router.get("/ping/{ip}")
async def ping(ip: str, count: int = Query(3, ge=1, le=10)):
    """Proxy quick ping"""
    return await proxy_request("GET", f"/ping/{ip}", params={"count": count})


@router.get("/ports/{ip}")
async def scan_ports(ip: str):
    """Proxy port scan"""
    return await proxy_request("GET", f"/ports/{ip}")


@router.get("/dns/{ip}")
async def check_dns(ip: str):
    """Proxy DNS check"""
    return await proxy_request("GET", f"/dns/{ip}")

