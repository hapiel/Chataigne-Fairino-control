from pythonosc import dispatcher, udp_client
from pythonosc.osc_server import ThreadingOSCUDPServer
import threading
import time
from fairino import Robot
import socket
import struct
import random

# --- CONFIG ---
ROBOT_IP = "192.168.57.2"
OSC_LISTEN_PORT = 9000
OSC_SEND_IP = "192.168.57.255" 
OSC_SEND_PORT = 8000

# Global telemetry control
telemetry_hz = 125.0  # Default 20 updates per second
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
    
def handle_servocart_rel(addr, *args):
    try:
        
        d_pos = [float(x) for x in args[:6]]
        # interval: 0.001 to 0.008 (match your OSC rate)
        # mode:  [0]-absolute motion (base coordinate system), [1]-incremental motion (base coordinate system), [2]-incremental motion (tool coordinate system);
        robot.ServoCart(mode=2, desc_pos=d_pos, cmdT=0.01)
        
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
    

class UniqueUpdateTracker:
    def __init__(self, report_interval=1.0):
        self.report_interval = report_interval
        self.last_report_time = time.perf_counter()
        self.last_joints = None
        self.unique_updates = 0
        self.total_reads = 0

    def update(self, current_joints):
        now = time.perf_counter()
        self.total_reads += 1
        
        # Check if joints have changed
        if self.last_joints is None or current_joints != self.last_joints:
            self.unique_updates += 1
            self.last_joints = current_joints.copy()

        # Periodic Report
        if now - self.last_report_time >= self.report_interval:
            elapsed = now - self.last_report_time
            rate = self.unique_updates / elapsed
            print(f"[Stats] Reads: {self.total_reads} | Unique: {self.unique_updates} | Rate: {rate:.2f} Hz")
            
            # Reset
            self.total_reads = 0
            self.unique_updates = 0
            self.last_report_time = now



# --- TELEMETRY LOOP ---
def telemetry_loop(osc_client):
    ROBOT_IP = "192.168.57.2"
    PORT = 8083
    
    # Initialize the tracker
    stats_tracker = UniqueUpdateTracker(report_interval=1.0)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((ROBOT_IP, PORT))
        print("Connected to Fairino High-Speed Stream (8083)")
    except Exception as e:
        print(f"Failed to connect to 8083: {e}")
        return

    buffer = b""

    while True:
        try:
            # Receive data chunk
            chunk = sock.recv(2048)
            if not chunk:
                break
            
            buffer += chunk

            # Process all complete frames in the buffer
            while len(buffer) >= 2:
                # Find the 0x5A5A header
                header_idx = buffer.find(b'\x5a\x5a')
                
                if header_idx == -1:
                    # No header found, keep the last byte in case it's part of a header
                    buffer = buffer[-1:]
                    break
                
                # If we found a header, discard everything before it
                if header_idx > 0:
                    buffer = buffer[header_idx:]

                # Check if we have enough data for a full header + count + length (5 bytes)
                if len(buffer) < 5:
                    break

                # Read the data length from the packet (Offset 3, uint16)
                data_len = struct.unpack_from('<H', buffer, 3)[0]
                total_packet_size = 5 + data_len + 2 # Header(5) + Data + Checksum(2)

                # Wait until the full packet is in the buffer
                if len(buffer) < total_packet_size:
                    break

                # Extract the full packet
                packet = buffer[:total_packet_size]
                buffer = buffer[total_packet_size:]

                # --- UNPACK DATA ---
                
                base_error = struct.unpack_from('<B', packet, 6)[0]
                
                # Offset 8: Start of jt_cur_pos[0] (6 joints * 8 bytes)
                joints = struct.unpack_from('<6d', packet, 8)
                
                # Offset 56: (8 meta + 48 joints)
                tcp_pose = struct.unpack_from('<6d', packet, 56)

                # Offset 108: (Skip toolNum int4)
                torques = struct.unpack_from('<6d', packet, 108)
                
                # Offset 188: Force/Torque Sensor (6 * 8 bytes)
                # (Serial 32 in manual)
                ft_sensor = struct.unpack_from('<6d', packet, 184)

                # --- UPDATE STATS ---
                stats_tracker.update(list(joints))

                # --- SEND OSC ---
                osc_client.send_message("/j_pos", list(joints))
                osc_client.send_message("/tcp_pos", list(tcp_pose))
                osc_client.send_message("/j_torq", list(torques))
                osc_client.send_message("/ft_sens", list(ft_sensor))
                
                # Offset 314: Fault Codes (Serial 67/68)
                # We calculate this based on the Serial 67 position in the table
                # Note: These are often 'int32' (4 bytes)
                main_err = struct.unpack_from('<i', packet, 314)[0]
                sub_err = struct.unpack_from('<i', packet, 318)[0]
                
                if base_error != 0 or main_err != 0:
                    osc_client.send_message("/error", [base_error, main_err, sub_err])

        except Exception as e:
            print(f"Stream Parse Error: {e}")
            break

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
disp.map("/servocart_rel", handle_servocart_rel)

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