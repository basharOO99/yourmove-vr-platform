# YourMove — VR Rehabilitation System for Children with ASD and ADHD

## Description

YourMove is a graduation project developed to explore how virtual reality can support therapy for children diagnosed with Autism Spectrum Disorder (ASD) and Attention Deficit Hyperactivity Disorder (ADHD).

The system lets a child wear a set of small motion sensors and interact with a VR environment during a therapy session. While the session is running, a separate web dashboard gives the therapist a live view of the child's movement patterns, stress indicators, and engagement level. The idea is to give therapists more objective data to work with, rather than relying entirely on observation.

This is an academic prototype. It is not a medical product and has not been clinically validated.

---

## Motivation

Children with ASD and ADHD often struggle in traditional therapy settings. Group sessions can cause anxiety, and it can be difficult for a therapist to measure whether a child is actually making progress over time, since assessment is largely based on observation and notes.

We wanted to build something that could make sessions more engaging for the child and give the therapist better information. VR environments can be controlled and adjusted in ways a physical room cannot, and motion data can show things that are hard to notice just by watching.

There are existing tools in this space, but most are expensive or not designed with therapists in mind. This project is an attempt to build something practical that a clinic could realistically use.

---

## System Overview

The system has three main parts that work together during a session.

The first is the VR environment itself, built in Unreal Engine. The child wears a headset and interacts with scenes designed to encourage movement and attention. The environment can adjust its difficulty based on what the AI layer is detecting.

The second part is the wearable setup. The child wears small motion-tracking units at several points on the body. These capture movement data and send it to the backend in real time. Nothing is invasive — the units attach with straps.

The third part is the clinician dashboard, a web application the therapist uses during and after the session. It shows live metrics, highlights unusual patterns, and stores session data for later review. The therapist can also compare sessions to track progress over time.

The backend is written in Python using FastAPI and handles everything between the sensors, the VR environment, and the dashboard.

---

## Main Features

- Live body movement monitoring displayed on a visual body map
- Automatic detection of stress patterns and loss of focus during sessions
- A stability score and risk level updated in real time
- Predictive estimates of where stress levels are heading, up to two minutes ahead
- A session summary generated at the end of each session
- Historical session comparison so therapists can track changes over time
- PDF export of session reports
- Secure login for therapists with session management

---

## How to Run the Project

These steps cover running the backend server. The VR environment and the hardware setup have separate requirements not covered here.

**Requirements**

- Python 3.10 or later
- pip

**Setup**

```bash
git clone https://github.com/your-repo/yourmove.git
cd yourmove
pip install -r requirements.txt
```

**Start the server**

```bash
uvicorn main:app --reload
```

The dashboard will be available at `http://localhost:8000`.

Default login credentials for testing: username `admin`, password `admin123`.

**Environment variables (optional)**

You can set `SECRET_KEY` in your environment to override the default signing key. For any deployment outside a local machine, this should be changed.

---

## Project Structure

```
yourmove/
├── main.py                 Entry point. Handles routing, authentication, and WebSocket connections.
├── ai_logic.py             Coordinates the analysis pipeline and produces session analytics.
├── data_processing.py      Handles the statistical processing of incoming sensor data.
├── anomaly_detection.py    Identifies unusual patterns in the data during a session.
├── predictive_model.py     Estimates where stress levels are heading over the next few minutes.
├── models.py               Database table definitions.
├── schemas.py              Data validation models.
├── auth.py                 Login and token handling.
├── requirements.txt        Python dependencies.
└── templates/
    ├── dashboard.html      The main clinician dashboard.
    ├── index.html          Project landing page.
    └── login.html          Login screen.
```

---

## Future Improvements

There are several things we would have liked to do given more time.

The session comparison feature works, but it would be more useful with longer-term trend graphs across many sessions rather than just two at a time. Adding a proper patient profile system so therapists can track multiple children separately would also make the dashboard more practical in a real clinic.

On the VR side, the environment currently has a limited number of scenes. Expanding the variety of activities, and making the difficulty adaptation smoother, would improve the therapy experience.

The motion analysis is based on statistical methods we implemented ourselves to keep the system transparent and auditable. In the future it would be worth comparing these against established clinical screening tools to see how well the patterns we detect correlate with known indicators.

Finally, the system has not been tested with actual patients. Any real-world use would require ethics approval and involvement from qualified clinicians, which is beyond the scope of a graduation project.

---

## Team Members

- Ahmed Mujahed Al-Tamimi
- Bashar Mokadam
- Maen Al-Sabah

---

## Academic Information

**Department:** Software Engineering  
**Supervisor:** Dr. Wael Al-Zayadat  
**Academic Year:** 2025 – 2026
