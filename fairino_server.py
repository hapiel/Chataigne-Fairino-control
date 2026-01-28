from pythonosc import dispatcher, udp_client
from pythonosc.osc_server import ThreadingOSCUDPServer
import threading
import time
from fairino import Robot
import random

# --- CONFIG ---
ROBOT_IP = "192.168.58.2"
OSC_LISTEN_PORT = 9000
OSC_SEND_IP = "127.0.0.1" 
OSC_SEND_PORT = 8000

# Global telemetry control
telemetry_hz = 100.0  # Default 20 updates per second
telemetry_interval = 1.0 / telemetry_hz 

# --- INIT ROBOT ---
robot = Robot.RPC(ROBOT_IP)

# --- MOTION HANDLERS ---
def handle_movej(addr, *args):
    try:
        # Parse OSC arguments
        q = [float(x) for x in args[:6]]
        speed = float(args[6]) if len(args) > 6 else 20.0
        accel = float(args[7]) if len(args) > 7 else 50.0 # Default from your docs is 0.0
        ovl = float(args[8]) if len(args) > 8 else 100.0 # Default from your docs is 100.0
        
        tool = 1 # hand
        flag = 2 # 0 doesn't work on first run

        robot.MoveJ(q, tool, 0, vel=speed, acc=accel, ovl=ovl, offset_flag=flag)

    except Exception as e:
        print(f"MoveJ failed: {e}")

def handle_movel(addr, *args):
    try:
        # Parse OSC arguments (X, Y, Z, Rx, Ry, Rz)
        d_pos = [float(x) for x in args[:6]]
        speed = float(args[6]) if len(args) > 6 else 20.0
        accel = float(args[7]) if len(args) > 7 else 0.0
        ovl = float(args[8]) if len(args) > 8 else 100.0
        
        tool = 1 # hand
        flag = 2 # 0 doesn't work on first run

        # Linear motion using keyword arguments for simplicity
        robot.MoveL(d_pos, tool, 0, vel=speed, acc=accel, ovl=ovl, offset_flag=flag)

    except Exception as e:
        # Suppress the socket error if it's just a collision, otherwise print
        if "CannotSendRequest" not in str(e):
            print(f"MoveL failed: {e}")

def handle_servo(addr, *args):
    q = list(args[:6])
    robot.ServoJ(q, 0, 0, 0.008, 0.1, 400)

def handle_drag(addr, state):
    robot.DragTeachSwitch(int(state))

def handle_jog(addr, *args):
    mode, ref, direction = args
    robot.StartJog(mode, ref, direction, 20.0)

def handle_jog_stop(addr):
    robot.StopJog(1)


# --- SERVO CONTROL (Streamed Motion) ---

def handle_servo_start(addr):
    try:
        ret = robot.ServoMoveStart()
        print(f"ServoStart: {ret if ret == 0 else f'FAILED ({ret})'}")
    except Exception as e:
        print(f"ServoStart Error: {e}")

def handle_servo_stop(addr):
    try:
        ret = robot.ServoMoveEnd()
        print(f"ServoStop: {ret if ret == 0 else f'FAILED ({ret})'}")
    except Exception as e:
        print(f"ServoStop Error: {e}")

def handle_servoj(addr, *args):
    try:
        # Args: j1, j2, j3, j4, j5, j6
        q = [float(x) for x in args[:6]]
        # We use keyword args to handle the axisPos [0,0,0,0] requirement
        # acc and vel don't work in current version of library
        robot.ServoJ(joint_pos=q, axisPos=[0.0, 0.0, 0.0, 0.0], cmdT=0.01, acc=50, vel=50)
    except Exception: pass

def handle_servojt_start(addr):
    try:
        # Per documentation: usually used with DragTeachSwitch
        robot.DragTeachSwitch(1) 
        ret = robot.ServoJTStart()
        if ret == 0:
            print("ServoJT Mode: Started")
        else:
            print(f"ServoJT Start Failed: {ret}")
    except Exception:
        pass

def handle_servojt_stop(addr):
    try:
        robot.ServoJTEnd()
        robot.DragTeachSwitch(0)
        print("ServoJT Mode: Completed")
    except Exception:
        pass

    
def handle_servocart(addr, *args):
    try:
        
        d_pos = [float(x) for x in args[:6]]
        # interval: 0.001 to 0.008 (match your OSC rate)
        # mode:  [0]-absolute motion (base coordinate system), [1]-incremental motion (base coordinate system), [2]-incremental motion (tool coordinate system);
        robot.ServoCart(mode=0, desc_pos=d_pos, cmdT=0.01)
        
    except Exception:
        pass


def handle_servojt(addr, *args):
    try:
        # Args: t1, t2, t3, t4, t5, t6
        torques = [float(x) for x in args[:6]]
        # interval should match your OSC sender rate (e.g., 0.008)
        robot.ServoJT(torque=torques, interval=0.008)
    except Exception: pass
    
    
# --- STOP PAUSE RESUME ---
    
def handle_stop(addr):
    try:
        ret = robot.StopMotion()
        if ret == 0:
            print("Motion stopped")
        else:
            print(f"StopMotion failed with code: {ret}")
    except Exception as e:
        print(f"StopMotion never works on the first try... (weird error)")

def handle_pause(addr):
    ret = robot.PauseMotion()
    if ret == 0:
        print("Motion Paused")
    else:
        print(f"PauseMotion failed with code: {ret}")

def handle_resume(addr):
    ret = robot.ResumeMotion()
    if ret == 0:
        print("Motion Resumed")
    else:
        print(f"ResumeMotion failed with code: {ret}")

def handle_clear_error(addr):
    ret = robot.ResetAllError()
    if ret == 0:
        print("Errors cleared")
    else:
        print(f"ClearError failed with code: {ret}")
        
        
def handle_enable(addr, state):
    try:
        # state is 1 for ON, 0 for OFF
        s = int(state)
        ret = robot.RobotEnable(s)
        print(f"Robot Enable ({s}): {ret if ret == 0 else f'FAILED ({ret})'}")
    except Exception as e:
        print(f"Enable Error: {e}")

def handle_set_rate(addr, hz):
    global telemetry_interval
    # Ensure we don't divide by zero or go too fast
    safe_hz = max(0.1, min(hz, 1000)) 
    telemetry_interval = 1.0 / safe_hz
    print(f"Telemetry rate set to {safe_hz}Hz ({telemetry_interval:.4f}s)")

# --- TELEMETRY LOOP ---
def telemetry_loop(osc_client):
    global telemetry_interval
    
    # Track the last known good positions to prevent "zero-flicker"
    last_valid_joints = [0.0] * 6 
    
    # Initialize the next tick time
    next_tick = time.perf_counter()
    
    while True:
        now = time.perf_counter()
        
        if now >= next_tick:
            try:
                # 1. Get raw data from robot
                ret_j, raw_joints = robot.GetActualJointPosDegree()
                ret_t, torques = robot.GetJointTorques()
                ret_f, ext_force = robot.FT_GetForceTorqueOrigin()
                ret_t, tool_pos = robot.GetActualTCPPose()
                _, err_code = robot.GetRobotErrorCode()

                # 2. Filter Joint Data
                # If the return code is successful (usually 0) and we have data
                if ret_j == 0 and isinstance(raw_joints, list) and len(raw_joints) >= 6:
                    processed_joints = []
                    for i in range(6):
                        # Check if the value is 0.000
                        if raw_joints[i] == 0.0:
                            processed_joints.append(last_valid_joints[i])
                        else:
                            processed_joints.append(raw_joints[i])
                    
                    # Update our persistent storage
                    last_valid_joints = processed_joints
                else:
                    # If the RPC call failed entirely, use the last good set
                    processed_joints = last_valid_joints

                # 3. Send OSC messages
                if err_code != [0, 0]:
                    osc_client.send_message("/error", f"ID: {err_code}")
                    # print(f"Robot Error Code: {err_code}")

                # Send the "cleaned" joints
                osc_client.send_message("/j_pos", processed_joints)
                
                
                osc_client.send_message("/tcp_pos", tool_pos)
                osc_client.send_message("/j_torq", torques)
                osc_client.send_message("/sens_ft", ext_force)
                
            except Exception as e:
                print(f"Robot Communication Error: {e}")

            # 4. Schedule next tick
            next_tick += telemetry_interval
            if next_tick < now:
                next_tick = now + telemetry_interval
        
        else:
            time.sleep(0.001)

# --- SERVER START ---
disp = dispatcher.Dispatcher()
disp.map("/movej", handle_movej)
disp.map("/movel", handle_movel)
disp.map("/servo", handle_servo)
disp.map("/drag", handle_drag)
disp.map("/jog", handle_jog)
disp.map("/jog_stop", handle_jog_stop)
disp.map("/telemetry/hz", handle_set_rate)
disp.map("/stop", handle_stop)
disp.map("/pause", handle_pause)
disp.map("/resume", handle_resume)
disp.map("/clear_error", handle_clear_error)
disp.map("/enable", handle_enable)

# Position Servo
disp.map("/servo/start", handle_servo_start)
disp.map("/servo/stop", handle_servo_stop)
disp.map("/servoj", handle_servoj)
disp.map("/servocart", handle_servocart)

# Torque Servo
disp.map("/servojt/start", handle_servojt_start)
disp.map("/servojt/stop", handle_servojt_stop)
disp.map("/servojt", handle_servojt)

server = ThreadingOSCUDPServer(("0.0.0.0", OSC_LISTEN_PORT), disp)
client = udp_client.SimpleUDPClient(OSC_SEND_IP, OSC_SEND_PORT)

# Start telemetry in a background thread
threading.Thread(target=telemetry_loop, args=(client,), daemon=True).start()

print(f"Fairino Precision Bridge Active on port {OSC_LISTEN_PORT}")
print(f"Sending telemetry to {OSC_SEND_IP}:{OSC_SEND_PORT}")

server.serve_forever()