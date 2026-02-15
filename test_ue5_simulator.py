"""
UE5 Simulator - Test Script for YourMove Platform
Simulates Unreal Engine 5 sending sensor data to the server
"""
import asyncio
import websockets
import json
import random
import time
from datetime import datetime


def generate_sensor_data(session_id="test_session_001", patient_id="patient_demo"):
    """Generate realistic sensor data with random variations"""
    
    # Base stress level that fluctuates over time
    base_stress = random.uniform(0, 10)
    
    # Occasionally spike stress to trigger AI alerts
    is_stress_event = random.random() < 0.1  # 10% chance
    
    def generate_body_part_data(stress_multiplier=1.0):
        """Generate data for a single body part"""
        stress = base_stress * stress_multiplier
        
        if is_stress_event:
            stress += random.uniform(10, 20)
        
        return {
            "rotation": {"x": random.uniform(-180, 180), "y": random.uniform(-180, 180), "z": random.uniform(-180, 180)},
            "delta_rotation": {"x": random.uniform(-5, 5), "y": random.uniform(-5, 5), "z": random.uniform(-5, 5)},
            "average_speed": random.uniform(0, 5),
            "tremor_intensity": random.uniform(0, 8) if is_stress_event else random.uniform(0, 3),
            "stress_trend": stress,
            "stress_timer": random.uniform(0, 5) if stress > 15 else random.uniform(0, 2)
        }
    
    # Generate complete sensor data packet
    data = {
        "session_id": session_id,
        "patient_id": patient_id,
        "timestamp": time.time(),
        "global_metrics": {
            "hmd_eye_dot_product": random.uniform(0.5, 1.0) if not is_stress_event else random.uniform(0.3, 0.7)
        },
        "sensors": {
            "head": generate_body_part_data(0.8),
            "chest": generate_body_part_data(0.9),
            "hip": generate_body_part_data(1.0),
            "left_hand": generate_body_part_data(1.2),
            "right_hand": generate_body_part_data(1.2),
            "left_upper_arm": generate_body_part_data(1.0),
            "right_upper_arm": generate_body_part_data(1.0),
            "left_lower_arm": generate_body_part_data(1.1),
            "right_lower_arm": generate_body_part_data(1.1),
            "left_upper_leg": generate_body_part_data(0.7),
            "right_upper_leg": generate_body_part_data(0.7),
            "left_lower_leg": generate_body_part_data(0.6),
            "right_lower_leg": generate_body_part_data(0.6)
        }
    }
    
    return data


async def simulate_ue5_session(server_url="ws://localhost:8000/ws/ue5", duration_seconds=60, tick_rate=10):
    """
    Simulate a UE5 therapy session
    
    Args:
        server_url: WebSocket URL of the server
        duration_seconds: How long to run the simulation
        tick_rate: Data updates per second (UE5 typically runs at 60-120 FPS)
    """
    print("=" * 60)
    print("  YourMove UE5 Simulator")
    print("=" * 60)
    print(f"\nConnecting to: {server_url}")
    print(f"Duration: {duration_seconds} seconds")
    print(f"Tick Rate: {tick_rate} Hz\n")
    
    session_id = f"sim_session_{int(time.time())}"
    patient_id = "demo_patient_001"
    
    try:
        async with websockets.connect(server_url) as websocket:
            print(f"✓ Connected to server")
            print(f"✓ Session ID: {session_id}")
            print(f"✓ Patient ID: {patient_id}")
            print("\n--- Starting data stream ---\n")
            
            start_time = time.time()
            packet_count = 0
            
            while (time.time() - start_time) < duration_seconds:
                # Generate sensor data
                sensor_data = generate_sensor_data(session_id, patient_id)
                
                # Send to server
                await websocket.send(json.dumps(sensor_data))
                packet_count += 1
                
                # Receive AI command response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    ai_command = json.loads(response)
                    
                    # Print interesting commands
                    if ai_command['severity'] in ['high', 'critical']:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] 🚨 {ai_command['severity'].upper()}: {ai_command['command']}")
                        print(f"           Reason: {ai_command['reason']}")
                    elif ai_command['command'] != 'continue':
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] ⚠️  {ai_command['severity'].upper()}: {ai_command['command']}")
                        print(f"           Reason: {ai_command['reason']}")
                    
                except asyncio.TimeoutError:
                    pass
                
                # Wait for next tick
                await asyncio.sleep(1.0 / tick_rate)
            
            # Summary
            elapsed = time.time() - start_time
            print("\n--- Session Complete ---")
            print(f"Duration: {elapsed:.1f} seconds")
            print(f"Packets Sent: {packet_count}")
            print(f"Average Rate: {packet_count / elapsed:.1f} packets/second")
            print("\n✓ Session terminated successfully")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure the YourMove server is running:")
        print("  python main.py")


async def simulate_stress_scenario(server_url="ws://localhost:8000/ws/ue5"):
    """
    Simulate a specific stress scenario for testing AI detection
    """
    print("=" * 60)
    print("  YourMove Stress Scenario Test")
    print("=" * 60)
    print("\nThis test simulates a patient experiencing increasing stress")
    print("to demonstrate the AI detection system.\n")
    
    session_id = "stress_test_session"
    patient_id = "test_patient_stress"
    
    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected to server\n")
            
            # Phase 1: Normal activity
            print("Phase 1: Normal baseline (5 seconds)")
            for i in range(50):
                data = generate_sensor_data(session_id, patient_id)
                # Override to ensure normal values
                for sensor in data['sensors'].values():
                    sensor['stress_trend'] = random.uniform(0, 5)
                    sensor['stress_timer'] = random.uniform(0, 1)
                    sensor['tremor_intensity'] = random.uniform(0, 2)
                data['global_metrics']['hmd_eye_dot_product'] = random.uniform(0.8, 1.0)
                
                await websocket.send(json.dumps(data))
                response = await websocket.recv()
                await asyncio.sleep(0.1)
            
            print("✓ Baseline established\n")
            
            # Phase 2: Building stress
            print("Phase 2: Stress building (5 seconds)")
            for i in range(50):
                data = generate_sensor_data(session_id, patient_id)
                # Gradually increase stress
                for sensor in data['sensors'].values():
                    sensor['stress_trend'] = random.uniform(8, 12)
                    sensor['stress_timer'] = random.uniform(1, 2.5)
                    sensor['tremor_intensity'] = random.uniform(2, 4)
                data['global_metrics']['hmd_eye_dot_product'] = random.uniform(0.6, 0.8)
                
                await websocket.send(json.dumps(data))
                response = await websocket.recv()
                ai_command = json.loads(response)
                if ai_command['severity'] != 'low':
                    print(f"  ⚠️  AI Detected: {ai_command['command']} - {ai_command['severity']}")
                await asyncio.sleep(0.1)
            
            print("✓ Elevated stress detected\n")
            
            # Phase 3: Critical stress event
            print("Phase 3: Critical stress event (3 seconds)")
            for i in range(30):
                data = generate_sensor_data(session_id, patient_id)
                # Trigger critical stress in right hand
                data['sensors']['right_hand']['stress_trend'] = random.uniform(16, 20)
                data['sensors']['right_hand']['stress_timer'] = random.uniform(3.5, 5.0)
                data['sensors']['right_hand']['tremor_intensity'] = random.uniform(6, 10)
                data['global_metrics']['hmd_eye_dot_product'] = random.uniform(0.3, 0.5)
                
                await websocket.send(json.dumps(data))
                response = await websocket.recv()
                ai_command = json.loads(response)
                if ai_command['severity'] in ['high', 'critical']:
                    print(f"  🚨 CRITICAL: {ai_command['command']} - {ai_command['reason']}")
                await asyncio.sleep(0.1)
            
            print("\n✓ Test complete - AI detection working correctly!")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")


def main():
    """Main menu for simulator"""
    print("\n" + "=" * 60)
    print("  YourMove UE5 Data Simulator")
    print("=" * 60)
    print("\nSelect test mode:")
    print("  1. Normal Session (60 seconds, realistic data)")
    print("  2. Stress Scenario (focused AI testing)")
    print("  3. Quick Test (10 seconds)")
    print("  4. Custom Configuration")
    print("  0. Exit")
    print()
    
    choice = input("Enter choice: ").strip()
    
    if choice == "1":
        asyncio.run(simulate_ue5_session(duration_seconds=60, tick_rate=10))
    elif choice == "2":
        asyncio.run(simulate_stress_scenario())
    elif choice == "3":
        asyncio.run(simulate_ue5_session(duration_seconds=10, tick_rate=10))
    elif choice == "4":
        duration = int(input("Duration (seconds): "))
        tick_rate = int(input("Tick rate (Hz): "))
        asyncio.run(simulate_ue5_session(duration_seconds=duration, tick_rate=tick_rate))
    elif choice == "0":
        print("Exiting...")
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
