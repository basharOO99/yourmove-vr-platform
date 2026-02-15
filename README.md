# YourMove VR Therapy Platform - Optimized v2.0

A production-ready, full-stack web platform for VR-based autism therapy with real-time AI analysis, body tracking, and adaptive therapy sessions. **Fully redesigned with neon gradient UI (Cyan → Purple → Pink) and optimized for performance.**

## 🎨 What's New in v2.0

### Visual & UX Improvements
- ✨ **Futuristic Neon Gradient Theme** - Cyan → Purple → Pink color scheme
- 🌙 **Dark Mode by Default** - Optimized for medical/clinical environments
- 💫 **Subtle Glow Effects** - Professional AI/VR-style interface
- 🎯 **Gradient Animated Buttons** - Smooth, eye-catching interactions
- ⚡ **Optimized Performance** - Faster load times and smoother animations
- 📱 **Fully Responsive** - Perfect on all devices

### Technical Improvements
- 🔒 **Enhanced Security** - Improved JWT validation and error handling
- 🐛 **Fixed Dashboard Zoom Bug** - No more infinite scaling issues
- ⚡ **Performance Optimizations** - GZip compression, throttled updates
- 📊 **Improved Chart Rendering** - Fixed animation issues
- 🔧 **Better Error Handling** - Comprehensive logging system
- 🚀 **Production Ready** - Ready for GitHub and Koyeb deployment

## 🏗️ Architecture

### Technology Stack
- **Backend**: FastAPI (Python) - High-performance async WebSocket server
- **Frontend**: HTML5, JavaScript (ES6), Tailwind CSS
- **Database**: SQLite with SQLAlchemy ORM
- **Real-time**: WebSockets for bidirectional communication
- **Visualization**: Chart.js for live data streaming
- **Authentication**: JWT (JSON Web Tokens)
- **Typography**: Orbitron + Inter fonts

### Data Flow
```
UE5 Sensor Data → WebSocket → FastAPI → AI Analysis → Command Response
                             ↓
                      Dashboard (Live Updates)
```

## 📁 Project Structure

```
yourmove_optimized/
├── main.py              # FastAPI application (optimized)
├── models.py            # SQLAlchemy database models
├── schemas.py           # Pydantic validation schemas (NEW)
├── auth.py              # JWT authentication system (NEW)
├── ai_logic.py          # AI movement analysis engine
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── .gitignore          # Git ignore file
├── Procfile            # Koyeb deployment config
├── runtime.txt         # Python version
├── test_ue5_simulator.py  # UE5 testing tool ✨
│
├── 📄 Documentation
│   ├── README.md                  # Main documentation
│   ├── QUICKSTART.md             # 5-minute setup guide
│   ├── DEPLOYMENT_GUIDE.md       # Deploy to 7+ platforms
│   ├── CHANGELOG.md              # Version history
│   ├── IMPROVEMENTS_SUMMARY.md   # v2.0 changes
│   ├── DATABASE_MIGRATION.md     # Migration from v1.x (NEW)
│   └── VERSION_COMPATIBILITY.md  # Compatibility guide (NEW)
│
├── templates/
│   ├── index.html       # Landing page (redesigned)
│   ├── login.html       # Doctor login (redesigned)
│   └── dashboard.html   # Real-time monitoring (redesigned + fixed)
│
└── yourmove.db         # SQLite database (created on first run)
```

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Step 1: Install Dependencies
```bash
cd yourmove_optimized
pip install -r requirements.txt
```

### Step 2: Configure Environment (Optional)
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

### Step 3: Start the Server



**Option B - Direct Python:**
```bash
python main.py
```

**Option C - Using uvicorn:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Step 4: Access the Platform
- **Landing Page**: http://localhost:8000
- **Doctor Login**: http://localhost:8000/login
- **Dashboard**: http://localhost:8000/dashboard
- **API Docs**: http://localhost:8000/docs

### Default Login Credentials
```
Username: admin
Password: admin123
```

## 📡 WebSocket Endpoints

### 1. UE5 Connection (`/ws/ue5`)
Receives high-frequency sensor data from Unreal Engine 5.

**Input JSON Format**:
```json
{
  "session_id": "sess_123",
  "patient_id": "pt_55",
  "global_metrics": {
    "hmd_eye_dot_product": 0.95
  },
  "sensors": {
    "head": { "tremor_intensity": 0.0, "stress_trend": 0.0, ... },
    // ... (13 total sensors)
  }
}
```

**Output (AI Command)**:
```json
{
  "command": "calm_down",
  "target_sensor": "right_hand",
  "reason": "Critical stress detected",
  "severity": "critical"
}
```

### 2. Dashboard Connection (`/ws/dashboard`)
Streams real-time sensor data and AI analysis to doctor dashboard.

## 🧠 AI Analysis Logic

### Detection Rules

1. **Outburst Prediction** (CRITICAL)
   - `stress_trend > 15.0` AND `stress_timer > 3.0`
   - Action: "calm_down" command

2. **Tremor Detection** (HIGH)
   - `tremor_intensity > 5.0`
   - Action: "pause_and_breathe" command

3. **Focus Loss** (MEDIUM)
   - `hmd_eye_dot_product < 0.6`
   - Action: "refocus" command

4. **Elevated Stress** (MEDIUM - Preventive)
   - `stress_trend > 10.0`
   - Action: "slow_down" command

## 🎨 Dashboard Features

### Live Session Monitor
- **Body Stress Map**: 13-point visual tracking
  - 🔵 Cyan: Normal
  - 🟡 Yellow: Elevated stress
  - 🟠 Orange: Warning (tremors)
  - 🔴 Pink: Critical (high stress)
  
- **Global Metrics**: Focus, Max Stress, Max Tremor, Avg Stress
- **AI Recommendations**: Real-time commands with severity levels
- **Live Charts**: Focus and Stress over time (50-point window)

### Patient Management (CRUD)
- Add/Edit/Delete patients
- Diagnosis levels (Level 1, 2, 3)
- Patient notes and history

## 🔐 Security Features

- **JWT Authentication**: Secure token-based auth
- **Password Hashing**: Bcrypt encryption
- **Protected Routes**: All patient data requires auth
- **Session Management**: 8-hour token expiration
- **Input Validation**: Pydantic schemas
- **Error Handling**: Comprehensive logging

## 🧪 Testing the System

### Built-in UE5 Simulator

The project includes a comprehensive UE5 data simulator for testing without VR hardware:

```bash
python test_ue5_simulator.py
```

**Available Test Modes:**
1. **Normal Session** - 60 seconds of realistic therapy data
2. **Stress Scenario** - Focused AI detection testing with stress events
3. **Quick Test** - 10 second rapid test
4. **Custom Configuration** - Set your own duration and tick rate

The simulator generates realistic sensor data for all 13 body parts and triggers AI responses.

### Python WebSocket Client
```python
import asyncio
import websockets
import json

async def test_ue5_connection():
    uri = "ws://localhost:8000/ws/ue5"
    async with websockets.connect(uri) as ws:
        data = {
            "session_id": "test_001",
            "patient_id": "pt_123",
            "global_metrics": {"hmd_eye_dot_product": 0.85},
            "sensors": {
                "head": {
                    "tremor_intensity": 2.0,
                    "stress_trend": 5.0,
                    "stress_timer": 1.0,
                    "rotation": {"pitch": 0, "yaw": 0, "roll": 0},
                    "delta_rotation": {"pitch": 0, "yaw": 0, "roll": 0},
                    "average_speed": 0.5
                },
                # Include all 13 sensors...
            }
        }
        
        await ws.send(json.dumps(data))
        response = await ws.recv()
        print(f"AI Response: {response}")

asyncio.run(test_ue5_connection())
```

## 📊 API Endpoints

### Authentication
- `POST /api/auth/login` - Login and receive JWT token

### Patients (Protected)
- `GET /api/patients` - Get all patients
- `POST /api/patients` - Create new patient
- `PUT /api/patients/{id}` - Update patient
- `DELETE /api/patients/{id}` - Delete patient

### Session
- `GET /api/session/current` - Get current active session
- `GET /health` - Health check endpoint

## 🌐 Production Deployment

### Koyeb Deployment

1. **Push to GitHub**
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/yourmove.git
git push -u origin main
```

2. **Deploy to Koyeb**
- Create new service on [Koyeb](https://www.koyeb.com)
- Connect GitHub repository
- Set build command: `pip install -r requirements.txt`
- Set run command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Deploy!

### Environment Variables (Koyeb)
```
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///./yourmove.db
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t yourmove .
docker run -p 8000:8000 yourmove
```

## 🐛 Bug Fixes in v2.0

### Fixed Issues
✅ **Dark Theme Implementation** - Fully functional dark mode with neon gradients  
✅ **Dashboard Infinite Zoom** - Fixed chart resize issues with proper configuration  
✅ **Performance Optimization** - Added throttling to prevent render loops  
✅ **WebSocket Stability** - Improved connection handling and reconnection  
✅ **Chart Animation** - Disabled problematic animations causing flickering  
✅ **Error Handling** - Comprehensive try-catch blocks and logging  

## ⚡ Performance Optimizations

- GZip compression for responses
- Chart update throttling (100ms interval)
- Disabled chart animations (`animation: false`)
- Fixed chart container sizes
- Async database operations
- Connection pooling
- Efficient WebSocket broadcasts

## 📝 Configuration

### Change Server Port
Edit `main.py`:
```python
uvicorn.run(app, host="0.0.0.0", port=8080)  # Your port here
```

### Change JWT Secret
Edit `auth.py`:
```python
SECRET_KEY = "your-new-secret-key"  # Use environment variable in production
```

### Modify AI Thresholds
Edit `ai_logic.py`:
```python
STRESS_TREND_THRESHOLD = 15.0
STRESS_TIMER_THRESHOLD = 3.0
TREMOR_INTENSITY_THRESHOLD = 5.0
FOCUS_THRESHOLD = 0.6
```

## 🎯 Key Features

✅ Real-time AI Analysis (60+ fps)  
✅ 13-Point Body Tracking  
✅ Adaptive Therapy Sessions  
✅ Visual Body Stress Map  
✅ Live Charts with Chart.js  
✅ Patient Management (CRUD)  
✅ Secure JWT Authentication  
✅ Neon Gradient UI Design  
✅ Production-Ready Code  
✅ Comprehensive Error Handling  
✅ High Performance & Optimized  

## 🛠️ Troubleshooting

### WebSocket Connection Issues
- Check firewall allows port 8000
- Use `wss://` for HTTPS connections
- Verify CORS settings

### Database Errors
- Delete `yourmove.db` to reset
- Check file permissions

### Import Errors
- Reinstall dependencies: `pip install -r requirements.txt`
- Verify Python 3.8+

### Chart Display Issues
- Clear browser cache
- Check browser console for errors
- Ensure Chart.js CDN is accessible

## 📄 License

This project is built for the YourMove VR Therapy System. All rights reserved.

## 🤝 Contributing

For questions or contributions, please contact the development team.

---

**Built with ❤️ for children with autism**

Version 2.0 - Optimized & Redesigned
