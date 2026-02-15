"""
YourMove VR Therapy Platform - Optimized Main Application
FastAPI server with WebSocket for real-time sensor data processing
Enhanced with security, performance optimizations, and error handling
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict
from datetime import timedelta, datetime
import json
import asyncio
import logging

# Import local modules
from models import init_database, get_db, Patient, Doctor
from schemas import (
    VRSensorInput, AICommand, PatientCreate, PatientResponse, 
    DoctorLogin, Token
)
from auth import (
    authenticate_doctor, create_access_token, get_current_doctor,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from ai_logic import MovementAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="YourMove VR Therapy Platform",
    description="AI-powered VR therapy system for children with autism",
    version="2.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
)

# Add middleware for security and performance
app.add_middleware(GZipMiddleware, minimum_size=1000)  # Compress responses
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates for HTML rendering
templates = Jinja2Templates(directory="templates")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    try:
        init_database()
        logger.info("✓ Database initialized successfully")
        logger.info("✓ YourMove server started")
        logger.info("→ Access landing page: http://localhost:8000")
        logger.info("→ Doctor login: http://localhost:8000/login")
        logger.info("→ API docs: http://localhost:8000/docs")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise


# WebSocket connection manager with improved error handling
class ConnectionManager:
    """Manages active WebSocket connections for real-time data streaming"""
    
    def __init__(self):
        self.active_ue5_connections: List[WebSocket] = []
        self.active_dashboard_connections: List[WebSocket] = []
        self.current_session_data: Dict = {}
        self.analyzer = MovementAnalyzer()
        self._lock = asyncio.Lock()  # Thread-safe operations
    
    async def connect_ue5(self, websocket: WebSocket):
        """Connect UE5 client"""
        await websocket.accept()
        async with self._lock:
            self.active_ue5_connections.append(websocket)
        logger.info(f"✓ UE5 connected - Total: {len(self.active_ue5_connections)}")
    
    async def connect_dashboard(self, websocket: WebSocket):
        """Connect dashboard client"""
        await websocket.accept()
        async with self._lock:
            self.active_dashboard_connections.append(websocket)
        logger.info(f"✓ Dashboard connected - Total: {len(self.active_dashboard_connections)}")
    
    async def disconnect_ue5(self, websocket: WebSocket):
        """Disconnect UE5 client"""
        async with self._lock:
            if websocket in self.active_ue5_connections:
                self.active_ue5_connections.remove(websocket)
        logger.info(f"✗ UE5 disconnected - Remaining: {len(self.active_ue5_connections)}")
    
    async def disconnect_dashboard(self, websocket: WebSocket):
        """Disconnect dashboard client"""
        async with self._lock:
            if websocket in self.active_dashboard_connections:
                self.active_dashboard_connections.remove(websocket)
        logger.info(f"✗ Dashboard disconnected - Remaining: {len(self.active_dashboard_connections)}")
    
    async def broadcast_to_dashboards(self, message: dict):
        """Send data to all connected dashboards with error handling"""
        disconnected = []
        for connection in self.active_dashboard_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to dashboard: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                for conn in disconnected:
                    if conn in self.active_dashboard_connections:
                        self.active_dashboard_connections.remove(conn)


manager = ConnectionManager()


# ==================== WebSocket Endpoints ====================

@app.websocket("/ws/ue5")
async def websocket_ue5_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for Unreal Engine 5
    Receives high-frequency sensor data, processes with AI, returns commands
    """
    await manager.connect_ue5(websocket)
    
    try:
        while True:
            # Receive sensor data from UE5
            data = await websocket.receive_text()
            
            try:
                # Parse and validate incoming data
                sensor_data = VRSensorInput.parse_raw(data)
                
                # Run AI analysis
                ai_command = manager.analyzer.analyze_movement(sensor_data)
                
                # Get body part status for dashboard
                body_status = manager.analyzer.get_body_part_status(sensor_data)
                global_stats = manager.analyzer.get_global_stats(sensor_data)
                
                # Store current session data
                manager.current_session_data = {
                    "session_id": sensor_data.session_id,
                    "patient_id": sensor_data.patient_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "body_status": body_status,
                    "global_stats": global_stats,
                    "ai_command": ai_command.dict(),
                    "focus": sensor_data.global_metrics.hmd_eye_dot_product
                }
                
                # Broadcast to all connected dashboards
                await manager.broadcast_to_dashboards({
                    "type": "sensor_update",
                    "data": manager.current_session_data
                })
                
                # Send AI command back to UE5
                await websocket.send_json(ai_command.dict())
                
            except ValueError as e:
                logger.error(f"Data validation error: {e}")
                await websocket.send_json({
                    "command": "error",
                    "reason": "Invalid data format",
                    "severity": "low"
                })
            except Exception as e:
                logger.error(f"Error processing sensor data: {e}")
                await websocket.send_json({
                    "command": "error",
                    "reason": str(e),
                    "severity": "low"
                })
    
    except WebSocketDisconnect:
        await manager.disconnect_ue5(websocket)
    except Exception as e:
        logger.error(f"WebSocket UE5 error: {e}")
        await manager.disconnect_ue5(websocket)


@app.websocket("/ws/dashboard")
async def websocket_dashboard_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for doctor dashboard
    Streams real-time sensor data and AI analysis
    """
    await manager.connect_dashboard(websocket)
    
    try:
        # Send current session data immediately if available
        if manager.current_session_data:
            await websocket.send_json({
                "type": "sensor_update",
                "data": manager.current_session_data
            })
        
        # Keep connection alive
        while True:
            try:
                # Wait for potential messages from dashboard
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Dashboard can send commands if needed
                logger.debug(f"Dashboard message: {message}")
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "ping"})
            except:
                break
    
    except WebSocketDisconnect:
        await manager.disconnect_dashboard(websocket)
    except Exception as e:
        logger.error(f"WebSocket dashboard error: {e}")
        await manager.disconnect_dashboard(websocket)


# ==================== HTML Page Routes ====================

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page - public facing"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Doctor login page"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Doctor dashboard - requires authentication (handled in frontend)"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


# ==================== API Routes ====================

@app.post("/api/auth/login", response_model=Token)
async def login(login_data: DoctorLogin, db: Session = Depends(get_db)):
    """
    Authenticate doctor and return JWT token
    
    - **username**: Doctor's username
    - **password**: Doctor's password
    """
    try:
        doctor = authenticate_doctor(login_data.username, login_data.password, db)
        
        if not doctor:
            logger.warning(f"Failed login attempt for username: {login_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": doctor.username}, 
            expires_delta=access_token_expires
        )
        
        logger.info(f"Successful login: {doctor.username}")
        return {"access_token": access_token, "token_type": "bearer"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/api/patients", response_model=List[PatientResponse])
async def get_patients(
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """Get all patients (protected route)"""
    try:
        patients = db.query(Patient).all()
        return patients
    except Exception as e:
        logger.error(f"Error fetching patients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching patients"
        )


@app.post("/api/patients", response_model=PatientResponse)
async def create_patient(
    patient: PatientCreate,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """Create a new patient (protected route)"""
    try:
        db_patient = Patient(
            name=patient.name,
            age=patient.age,
            gender=patient.gender,
            diagnosis_level=patient.diagnosis_level,
            notes=patient.notes
        )
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)
        logger.info(f"Patient created: {db_patient.id} by {doctor.username}")
        return db_patient
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating patient: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating patient"
        )


@app.put("/api/patients/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    patient: PatientCreate,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """Update a patient (protected route)"""
    try:
        db_patient = db.query(Patient).filter(Patient.id == patient_id).first()
        
        if not db_patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Patient not found"
            )
        
        db_patient.name = patient.name
        db_patient.age = patient.age
        db_patient.gender = patient.gender
        db_patient.diagnosis_level = patient.diagnosis_level
        db_patient.notes = patient.notes
        
        db.commit()
        db.refresh(db_patient)
        logger.info(f"Patient updated: {patient_id} by {doctor.username}")
        return db_patient
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating patient: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating patient"
        )


@app.delete("/api/patients/{patient_id}")
async def delete_patient(
    patient_id: int,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """Delete a patient (protected route)"""
    try:
        db_patient = db.query(Patient).filter(Patient.id == patient_id).first()
        
        if not db_patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Patient not found"
            )
        
        db.delete(db_patient)
        db.commit()
        logger.info(f"Patient deleted: {patient_id} by {doctor.username}")
        return {"message": "Patient deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting patient: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting patient"
        )


@app.get("/api/session/current")
async def get_current_session(doctor: Doctor = Depends(get_current_doctor)):
    """Get current active session data (protected route)"""
    if not manager.current_session_data:
        return {"active": False}
    
    return {
        "active": True,
        "data": manager.current_session_data
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "ue5_connections": len(manager.active_ue5_connections),
        "dashboard_connections": len(manager.active_dashboard_connections),
        "active_session": bool(manager.current_session_data)
    }


# Error handlers
@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    logger.error(f"Internal server error: {exc}")
    return {"detail": "Internal server error"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info",
        access_log=True
    )
