# YourMove - Quick Start Guide

Get up and running with YourMove in 5 minutes!

## ⚡ Quick Installation

```bash
# 1. Navigate to the project
cd yourmove_optimized

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
python main.py

# 4. Open your browser
# http://localhost:8000
```

## 🎯 First Steps

### 1. Access the Landing Page
Visit: `http://localhost:8000`

### 2. Login to Dashboard
- Go to: `http://localhost:8000/login`
- **Username**: `admin`
- **Password**: `admin123`
- Click the demo credentials box to auto-fill

### 3. Explore the Dashboard
- View the **Live Session Monitor** tab
- Check out the **Body Stress Map**
- Navigate to **Patient Management** tab
- Add a test patient

### 4. Test API (Optional)
Visit API docs: `http://localhost:8000/docs`

## 🔌 Connect UE5 Client

To connect your Unreal Engine 5 VR application:

**WebSocket URL**: `ws://localhost:8000/ws/ue5`

**Example Python Client**:
```python
import asyncio
import websockets
import json

async def connect():
    uri = "ws://localhost:8000/ws/ue5"
    async with websockets.connect(uri) as ws:
        # Prepare sensor data
        data = {
            "session_id": "test_session",
            "patient_id": "patient_001",
            "global_metrics": {
                "hmd_eye_dot_product": 0.95
            },
            "sensors": {
                "head": {
                    "tremor_intensity": 1.5,
                    "stress_trend": 8.0,
                    "stress_timer": 2.0,
                    "rotation": {"pitch": 0, "yaw": 0, "roll": 0},
                    "delta_rotation": {"pitch": 0, "yaw": 0, "roll": 0},
                    "average_speed": 1.2
                },
                "chest": {
                    "tremor_intensity": 0.5,
                    "stress_trend": 3.0,
                    "stress_timer": 1.0,
                    "rotation": {"pitch": 0, "yaw": 0, "roll": 0},
                    "delta_rotation": {"pitch": 0, "yaw": 0, "roll": 0},
                    "average_speed": 0.8
                },
                # Add remaining 11 sensors...
                # hip, left_hand, right_hand, left_upper_arm, right_upper_arm,
                # left_lower_arm, right_lower_arm, left_upper_leg, right_upper_leg,
                # left_lower_leg, right_lower_leg
            }
        }
        
        # Send data
        await ws.send(json.dumps(data))
        
        # Receive AI command
        response = await ws.recv()
        print(f"AI Command: {response}")

asyncio.run(connect())
```

## 📊 Key Features Overview

### Landing Page
- Hero section with stats
- Feature showcase
- FAQ section
- Contact information

### Login Page
- Secure JWT authentication
- Demo credentials available
- Modern neon gradient design

### Dashboard
**Live Session Monitor**:
- Real-time body stress map (13 body parts)
- Global metrics (Focus, Stress, Tremor)
- AI recommendations
- Live charts (Focus & Stress over time)

**Patient Management**:
- Add/Edit/Delete patients
- Patient information (name, age, gender)
- Diagnosis levels (Level 1, 2, 3)
- Notes and history

## 🎨 UI Theme

The interface features a futuristic neon gradient theme:
- **Colors**: Cyan (#00f5ff) → Purple (#8b5cf6) → Pink (#ff006e)
- **Dark Background**: Professional dark mode
- **Glow Effects**: Subtle neon glows
- **Smooth Animations**: Gradient shifts and transitions

## 🔐 Security

- JWT token-based authentication
- 8-hour session expiration
- Bcrypt password hashing
- Protected API routes
- Input validation

## 📱 Supported Browsers

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 🚨 Troubleshooting

### Port Already in Use
```bash
# Kill process on port 8000
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

### Import Errors
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### Database Issues
```bash
# Reset database (WARNING: Deletes all data)
rm yourmove.db
python main.py
```

### WebSocket Connection Failed
- Check firewall settings
- Ensure port 8000 is open
- Try localhost instead of 127.0.0.1

## 📚 Next Steps

1. **Read the README**: Comprehensive feature documentation
2. **Check DEPLOYMENT_GUIDE**: Production deployment instructions
3. **Review API Docs**: Available at `/docs` endpoint
4. **Explore CHANGELOG**: See what's new in v2.0

## 🎓 Learning Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com
- **WebSocket Guide**: See `main.py` WebSocket endpoints
- **Chart.js Docs**: https://www.chartjs.org
- **Tailwind CSS**: https://tailwindcss.com

## 💡 Tips

1. **Auto-fill Login**: Click the demo credentials box
2. **Keyboard Shortcuts**: Tab to navigate forms
3. **Mobile Friendly**: Dashboard works on tablets
4. **API Testing**: Use `/docs` for interactive API testing
5. **Health Check**: Visit `/health` to verify server status

## 🆘 Need Help?

- Check the **README.md** for detailed information
- Review **DEPLOYMENT_GUIDE.md** for deployment help
- See **CHANGELOG.md** for version history
- Open an issue on GitHub

## 🎉 You're Ready!

Start building amazing AI-powered VR therapy experiences with YourMove!

---

**Version**: 2.0.0  
**Last Updated**: February 2024  
**Built with ❤️ for children with autism**
