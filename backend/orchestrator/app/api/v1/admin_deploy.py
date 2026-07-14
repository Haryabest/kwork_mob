"""Admin: export deploy JSON (§15.3 / §20)."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from app.core.security import require_admin
from app.core.vpn import require_vpn
from app.services import deploy_bundle as db


def _vpn(request: Request) -> None:
    require_vpn(request)


router = APIRouter(
    prefix="/admin/deploy",
    tags=["Deploy bundles"],
    dependencies=[Depends(_vpn), Depends(require_admin)],
)


@router.get("/bundle")
async def get_deploy_bundle(
    role: str = Query("worker", description="worker|storage|storage-replica|orchestrator|cloud|all"),
    worker_id: str | None = Query(None),
    _: dict = Depends(require_admin),
):
    """JSON bundle для CasaOS / docker compose / cloud bootstrap."""
    try:
        kwargs: dict = {}
        if worker_id:
            kwargs["worker_id"] = worker_id
        if role.startswith("storage"):
            node = "replica" if "replica" in role else "primary"
            kwargs["node"] = node
        return db.build_bundle(role, **kwargs)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/bundle/download")
async def download_deploy_bundle(
    role: str = Query("worker"),
    worker_id: str | None = Query(None),
    _: dict = Depends(require_admin),
):
    try:
        kwargs: dict = {}
        if worker_id:
            kwargs["worker_id"] = worker_id
        if role.startswith("storage"):
            node = "replica" if "replica" in role else "primary"
            kwargs["node"] = node
        data = db.build_bundle(role, **kwargs)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    body = json.dumps(data, ensure_ascii=False, indent=2)
    fname = f"deploy_{role.replace('-', '_')}.json"
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
