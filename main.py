"""
YourMove VR Therapy Platform — Production Backend  v4.0
═══════════════════════════════════════════════════════════════════════════════
Enterprise-grade FastAPI server with:
  • In-process token-bucket rate limiter (no external dependency)
  • CORS restricted via environment variable
  • GZip compression
  • Structured JSON logging for AI decisions
  • Full v4 analytics pipeline integrated
  • Database-indexed queries
  • /api/session/export  — session data export for PDF generation
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketState

from ai_logic import MovementAnalyzer
from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_doctor,
    create_access_token,
    decode_access_token,
    get_current_doctor,
)
from models import (
    Doctor,
    Patient,
    SessionDataLog,
    SessionLocal,
    get_db,
    init_database,
)
from schemas import AICommand, DoctorLogin, PatientCreate, PatientResponse, Token, VRSensorInput


# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":%(message)s}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("yourmove.api")


# ── In-process token-bucket rate limiter ─────────────────────────────────────

class _RateLimiter:
    """
    Sliding-window rate limiter (no external dependency).
    Tracks request timestamps per IP key in-memory.
    Not suitable for multi-process deployments — use Redis for that.
    """

    def __init__(self) -> None:
        self._windows: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str, limit: int, window_s: float = 60.0) -> bool:
        now   = time.monotonic()
        cutoff = now - window_s
        w = self._windows[key]
        # Evict expired entries
        self._windows[key] = [t for t in w if t > cutoff]
        if len(self._windows[key]) >= limit:
            return False
        self._windows[key].append(now)
        return True


_limiter = _RateLimiter()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate(request: Request, limit: int = 60, window_s: float = 60.0) -> None:
    """FastAPI dependency: raises 429 if rate limit exceeded."""
    ip = _client_ip(request)
    if not _limiter.is_allowed(ip, limit, window_s):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded ({limit} requests/{int(window_s)}s). Please slow down.",
            headers={"Retry-After": str(int(window_s))},
        )


# ── CORS configuration ────────────────────────────────────────────────────────

def _get_allowed_origins() -> List[str]:
    """
    In production, set ALLOWED_ORIGINS env var to a comma-separated list.
    Default is localhost-only for local development.
    """
    raw = os.environ.get("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if "*" in origins:
        logger.warning('{"msg":"CORS wildcard (*) enabled — restrict in production"}')
    return origins


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_database()
        logger.info('"Database initialized"')
        from auth import SECRET_KEY
        if "CHANGE-ME" in SECRET_KEY or len(SECRET_KEY) < 32:
            logger.warning('"Insecure SECRET_KEY detected — set SECRET_KEY env var"')
        logger.info('"YourMove v4.0 ready"')
    except Exception as exc:
        logger.error(f'"Startup failed: {exc}"')
        raise
    yield
    logger.info('"YourMove shutting down"')


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="YourMove Clinical Platform",
    description="Evidence-based real-time VR therapy analytics for ASD/ADHD.",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

templates = Jinja2Templates(directory="templates")


# ── WebSocket Connection Manager ──────────────────────────────────────────────

class ConnectionManager:
    _LOG_EVERY_N = 5

    def __init__(self) -> None:
        self.active_ue5:       List[WebSocket] = []
        self.active_dashboards: List[WebSocket] = []
        self.current_data:      Dict            = {}
        self.ai_buffer:         List[Dict]      = []
        self.analyzer           = MovementAnalyzer()
        self._lock              = asyncio.Lock()
        self._frame_counter:    int             = 0

    async def connect_ue5(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self.active_ue5.append(ws)
        logger.info(f'"UE5 connected total={len(self.active_ue5)}"')

    async def connect_dashboard(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self.active_dashboards.append(ws)

    async def disconnect_ue5(self, ws: WebSocket) -> None:
        async with self._lock:
            if ws in self.active_ue5:
                self.active_ue5.remove(ws)
        logger.info(f'"UE5 disconnected remaining={len(self.active_ue5)}"')

    async def disconnect_dashboard(self, ws: WebSocket) -> None:
        async with self._lock:
            if ws in self.active_dashboards:
                self.active_dashboards.remove(ws)

    @staticmethod
    def _is_open(ws: WebSocket) -> bool:
        try:
            return ws.client_state == WebSocketState.CONNECTED
        except Exception:
            return False

    def _push_ai(self, ai: Dict) -> None:
        last = self.ai_buffer[-1] if self.ai_buffer else {}
        if last.get("command") == ai.get("command") and last.get("severity") == ai.get("severity"):
            return
        self.ai_buffer.append({**ai, "timestamp": datetime.utcnow().strftime("%H:%M:%S")})
        if len(self.ai_buffer) > 25:
            self.ai_buffer.pop(0)

    async def broadcast(self, message: dict) -> None:
        dead: List[WebSocket] = []
        for ws in list(self.active_dashboards):
            if not self._is_open(ws):
                dead.append(ws)
                continue
            try:
                await asyncio.wait_for(ws.send_json(message), timeout=5.0)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    if ws in self.active_dashboards:
                        self.active_dashboards.remove(ws)

    @staticmethod
    def _db_write(
        session_id: str, patient_id: str,
        focus_pct: int, stress_pct: int,
        max_tremor: float, avg_stress: float,
        ai_cmd: str, ai_sev: str,
    ) -> None:
        db = SessionLocal()
        try:
            db.add(SessionDataLog(
                session_id=session_id, patient_id=patient_id,
                focus_level=focus_pct, stress_level=stress_pct,
                max_tremor=round(max_tremor, 2), avg_stress=round(avg_stress, 2),
                ai_command=ai_cmd, ai_severity=ai_sev,
            ))
            db.commit()
        except Exception as exc:
            logger.error(f'"DB write error: {exc}"')
            db.rollback()
        finally:
            db.close()


manager = ConnectionManager()


# ── WebSocket: UE5 ────────────────────────────────────────────────────────────

@app.websocket("/ws/ue5")
async def ws_ue5(websocket: WebSocket) -> None:
    await manager.connect_ue5(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                sensor_data  = VRSensorInput.model_validate_json(raw)
                ai_command   = manager.analyzer.analyze_movement(sensor_data)
                body_status  = manager.analyzer.get_body_part_status(sensor_data)
                global_stats = manager.analyzer.get_global_stats(sensor_data)
                advanced     = manager.analyzer.get_advanced_analytics(sensor_data)

                ai_dict   = ai_command.model_dump()
                manager._push_ai(ai_dict)

                focus_pct  = int(round(sensor_data.global_metrics.hmd_eye_dot_product * 100))
                stress_pct = min(100, int(round(global_stats["max_stress"] * 5)))

                manager.current_data = {
                    "session_id":    sensor_data.session_id,
                    "patient_id":    sensor_data.patient_id,
                    "timestamp":     datetime.utcnow().isoformat(),
                    "body_status":   body_status,
                    "global_stats":  global_stats,
                    "advanced":      advanced,
                    "ai_command":    ai_dict,
                    "ai_buffer":     list(reversed(manager.ai_buffer)),
                    "focus_pct":     focus_pct,
                    "stress_pct":    stress_pct,
                }

                async with manager._lock:
                    manager._frame_counter += 1
                    do_log = (manager._frame_counter % manager._LOG_EVERY_N == 0)

                if do_log:
                    loop = asyncio.get_running_loop()
                    loop.run_in_executor(
                        None, manager._db_write,
                        sensor_data.session_id, sensor_data.patient_id,
                        focus_pct, stress_pct,
                        global_stats["max_tremor"], global_stats["avg_stress"],
                        ai_dict["command"], ai_dict["severity"],
                    )

                await manager.broadcast({"type": "sensor_update", "data": manager.current_data})
                await websocket.send_json(ai_dict)

            except ValueError as exc:
                logger.error(f'"Validation error: {exc}"')
                await websocket.send_json({"command": "error", "reason": "Invalid data", "severity": "low", "target_sensor": None})
            except Exception as exc:
                logger.error(f'"Processing error: {exc}"')
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error(f'"UE5 WS error: {exc}"')
    finally:
        await manager.disconnect_ue5(websocket)


# ── WebSocket: Dashboard ──────────────────────────────────────────────────────

@app.websocket("/ws/dashboard")
async def ws_dashboard(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None),
) -> None:
    if token is not None and decode_access_token(token) is None:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect_dashboard(websocket)
    try:
        if manager.current_data and manager._is_open(websocket):
            await websocket.send_json({"type": "sensor_update", "data": manager.current_data})

        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=25.0)
            except asyncio.TimeoutError:
                if manager._is_open(websocket):
                    await websocket.send_json({"type": "ping"})
                else:
                    break
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error(f'"Dashboard WS error: {exc}"')
    finally:
        await manager.disconnect_dashboard(websocket)


# ── HTML pages ────────────────────────────────────────────────────────────────

@app.get("/",          response_class=HTMLResponse)
async def page_index(request: Request):
    return templates.TemplateResponse("index.html",    {"request": request})

@app.get("/login",     response_class=HTMLResponse)
async def page_login(request: Request):
    return templates.TemplateResponse("login.html",    {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def page_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/api/auth/login", response_model=Token)
async def api_login(
    body:    DoctorLogin,
    request: Request,
    db:      Session = Depends(get_db),
) -> Token:
    # Strict rate limit on login endpoint (5 attempts / 60s per IP)
    _check_rate(request, limit=5, window_s=60.0)
    doctor = authenticate_doctor(body.username, body.password, db)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": doctor.username}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    logger.info(f'"Login OK user={doctor.username}"')
    return Token(
        access_token=token,
        token_type="bearer",
)


# ── Me ────────────────────────────────────────────────────────────────────────

@app.get("/api/me")
async def api_me(doctor: Doctor = Depends(get_current_doctor)):
    return {"username": doctor.username, "full_name": doctor.full_name, "email": doctor.email}


# ── Patients ──────────────────────────────────────────────────────────────────

@app.get("/api/patients", response_model=List[PatientResponse])
async def api_get_patients(
    doctor: Doctor = Depends(get_current_doctor),
    db:     Session = Depends(get_db),
):
    return db.query(Patient).order_by(Patient.created_at.desc()).all()


@app.post("/api/patients", response_model=PatientResponse, status_code=201)
async def api_create_patient(
    body:    PatientCreate,
    request: Request,
    doctor:  Doctor  = Depends(get_current_doctor),
    db:      Session = Depends(get_db),
):
    _check_rate(request, limit=30, window_s=60.0)
    try:
        p = Patient(name=body.name, age=body.age, gender=body.gender,
                    diagnosis_level=body.diagnosis_level, notes=body.notes)
        db.add(p); db.commit(); db.refresh(p)
        return p
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error creating patient")


@app.put("/api/patients/{patient_id}", response_model=PatientResponse)
async def api_update_patient(
    patient_id: int,
    body:        PatientCreate,
    doctor:      Doctor  = Depends(get_current_doctor),
    db:          Session = Depends(get_db),
):
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    try:
        p.name = body.name; p.age = body.age; p.gender = body.gender
        p.diagnosis_level = body.diagnosis_level; p.notes = body.notes
        db.commit(); db.refresh(p)
        return p
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error updating patient")


@app.delete("/api/patients/{patient_id}")
async def api_delete_patient(
    patient_id: int,
    doctor:     Doctor  = Depends(get_current_doctor),
    db:         Session = Depends(get_db),
):
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    db.delete(p); db.commit()
    return {"message": "Deleted"}


# ── Session history ───────────────────────────────────────────────────────────

@app.get("/api/session/current")
async def api_current(doctor: Doctor = Depends(get_current_doctor)):
    if not manager.current_data:
        return {"active": False}
    return {"active": True, "data": manager.current_data}


@app.get("/api/session/history")
async def api_history(
    session_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    date_from:  Optional[str] = None,
    date_to:    Optional[str] = None,
    limit:      int            = 500,
    doctor:     Doctor         = Depends(get_current_doctor),
    db:         Session        = Depends(get_db),
):
    try:
        q = db.query(SessionDataLog)
        if session_id: q = q.filter(SessionDataLog.session_id == session_id)
        if patient_id: q = q.filter(SessionDataLog.patient_id == patient_id)
        if date_from:  q = q.filter(SessionDataLog.recorded_at >= datetime.fromisoformat(date_from))
        if date_to:    q = q.filter(SessionDataLog.recorded_at <= datetime.fromisoformat(date_to))
        rows = q.order_by(SessionDataLog.recorded_at.desc()).limit(min(limit, 2000)).all()
        return [
            {
                "id": r.id, "session_id": r.session_id, "patient_id": r.patient_id,
                "focus_level": r.focus_level, "stress_level": r.stress_level,
                "max_tremor": r.max_tremor, "avg_stress": r.avg_stress,
                "ai_command": r.ai_command, "ai_severity": r.ai_severity,
                "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
            }
            for r in rows
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Error fetching history")


@app.get("/api/session/export")
async def api_export(
    session_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    doctor:     Doctor         = Depends(get_current_doctor),
    db:         Session        = Depends(get_db),
):
    """
    Returns a structured JSON export payload for PDF generation.
    The dashboard JS uses this to populate the print template.
    """
    try:
        q = db.query(SessionDataLog)
        if session_id: q = q.filter(SessionDataLog.session_id == session_id)
        if patient_id: q = q.filter(SessionDataLog.patient_id == patient_id)
        rows = q.order_by(SessionDataLog.recorded_at.asc()).limit(2000).all()

        if not rows:
            return {"rows": [], "summary": None}

        focus_vals  = [r.focus_level  for r in rows]
        stress_vals = [r.stress_level for r in rows]
        tremor_vals = [r.max_tremor   for r in rows if r.max_tremor is not None]

        summary = {
            "session_id":      session_id or patient_id or "N/A",
            "patient_id":      patient_id or "N/A",
            "doctor":          doctor.full_name or doctor.username,
            "start_time":      rows[0].recorded_at.isoformat() if rows[0].recorded_at else None,
            "end_time":        rows[-1].recorded_at.isoformat() if rows[-1].recorded_at else None,
            "total_records":   len(rows),
            "avg_focus":       round(sum(focus_vals)  / len(focus_vals),  1) if focus_vals  else 0,
            "avg_stress":      round(sum(stress_vals) / len(stress_vals), 1) if stress_vals else 0,
            "avg_tremor":      round(sum(tremor_vals) / len(tremor_vals), 2) if tremor_vals else 0,
            "peak_stress":     max(stress_vals) if stress_vals else 0,
            "peak_tremor":     max(tremor_vals) if tremor_vals else 0,
            "min_focus":       min(focus_vals)  if focus_vals  else 0,
            "critical_events": sum(1 for r in rows if r.ai_severity == "critical"),
            "high_events":     sum(1 for r in rows if r.ai_severity == "high"),
        }
        return {"rows": [
            {"ts": r.recorded_at.isoformat() if r.recorded_at else "", "f": r.focus_level,
             "s": r.stress_level, "t": r.max_tremor, "cmd": r.ai_command, "sev": r.ai_severity}
            for r in rows
        ], "summary": summary}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Export failed")


@app.get("/api/stats")
async def api_stats(doctor: Doctor = Depends(get_current_doctor), db: Session = Depends(get_db)):
    try:
        from sqlalchemy import func
        total_patients = db.query(func.count(Patient.id)).scalar() or 0
        total_sessions = db.query(func.count(func.distinct(SessionDataLog.session_id))).scalar() or 0
        total_logs     = db.query(func.count(SessionDataLog.id)).scalar() or 0
        return {
            "total_patients":    total_patients,
            "total_sessions":    total_sessions,
            "total_data_points": total_logs,
            "active_ue5":        len(manager.active_ue5),
            "active_dashboards": len(manager.active_dashboards),
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Stats error")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status":    "healthy",
        "version":   "4.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "ue5":       len(manager.active_ue5),
        "dashboards": len(manager.active_dashboards),
        "session_active": bool(manager.current_data),
    }


@app.exception_handler(500)
async def err500(request: Request, exc: Exception):
    logger.error(f'"Unhandled 500: {exc}"')
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info", access_log=True)
