from pythonosc import dispatcher, udp_client
from pythonosc.osc_server import ThreadingOSCUDPServer
import threading
import time
from fairino import Robot

# --- CONFIG ---
ROBOT_IP = "192.168.58.2"
OSC_LISTEN_PORT = 9000
OSC_SEND_IP = "127.0.0.1" 
OSC_SEND_PORT = 8000

# Global telemetry control
telemetry_rate = 0.05 

# --- INIT ROBOT ---
# The modern SDK handles the RPC connection internally
robot = Robot.RPC(ROBOT_IP)

# --- MOTION HANDLERS ---
def handle_move(addr, *args):
    # /movej j1 j2 j3 j4 j5 j6 speed accel overlap
    q = list(args[:6])
    v = args[6] if len(args) > 6 else 20.0
    a = args[7] if len(args) > 7 else 50.0
    ovl = args[8] if len(args) > 8 else 0.0
    # Clean call: joints, tool, wobj, speed, accel, ovl...
    robot.MoveJ(q, 0, 0, v, a, ovl)

def handle_servo(addr, *args):
    # /servoj j1 j2 j3 j4 j5 j6
    q = list(args[:6])
    # time=0.008 (8ms), lookahead=0.1, gain=400
    robot.ServoJ(q, 0, 0, 0.008, 0.1, 400)

def handle_drag(addr, state):
    # 1 to enable, 0 to disable
    robot.DragTeachSwitch(int(state))

def handle_jog(addr, *args):
    # ref_type(0:joint, 1:cartesian), index, direction(1/-1)
    mode, ref, direction = args
    robot.StartJog(mode, ref, direction, 20.0)

def handle_jog_stop(addr):
    robot.StopJog(1)

def handle_set_rate(addr, hz):
    global telemetry_rate
    telemetry_rate = 1.0 / max(1, hz)

# --- TELEMETRY LOOP ---
def telemetry_loop(osc_client):
    while True:
        # Get data - modern SDK returns standard lists
        _, joints = robot.GetActualJointPosDegree()
        _, torques = robot.GetActualJointTorque()
        _, ext_force = robot.GetForceSensorRaw() 
        
        # Error check
        _, err_code = robot.GetRobotErrorCode()
        if err_code != 0:
            osc_client.send_message("/error", f"ID: {err_code}")

        # Send to Chataigne
        osc_client.send_message("/joints", joints)
        osc_client.send_message("/torques", torques)
        osc_client.send_message("/ext_force", ext_force)
        
        time.sleep(telemetry_rate)

# --- SERVER START ---
disp = dispatcher.Dispatcher()
disp.map("/movej", handle_move)
disp.map("/servo", handle_servo)
disp.map("/drag", handle_drag)
disp.map("/jog", handle_jog)
disp.map("/jog_stop", handle_jog_stop)
disp.map("/telemetry/hz", handle_set_rate)

server = ThreadingOSCUDPServer(("0.0.0.0", OSC_LISTEN_PORT), disp)
client = udp_client.SimpleUDPClient(OSC_SEND_IP, OSC_SEND_PORT)

threading.Thread(target=telemetry_loop, args=(client,), daemon=True).start()
print(f"Fairino Modern Bridge Active on port {OSC_LISTEN_PORT}")
server.serve_forever()