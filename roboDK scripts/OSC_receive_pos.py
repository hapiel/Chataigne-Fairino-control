from robodk import robolink
from pythonosc import udp_client
from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.dispatcher import Dispatcher

# --- Configuration ---
ROBOT_NAME = 'FAIRINO FR3 WML input'
OSC_IN_IP = "127.0.0.1"
OSC_IN_PORT = 8100

# Initialize RoboDK
RDK = robolink.Robolink()
robot = RDK.Item(ROBOT_NAME, robolink.ITEM_TYPE_ROBOT)

def handle_joints(address, *args):
    joints = [float(a) for a in args]
    robot.setJoints(joints)

# --- OSC Server Setup ---
dispatcher = Dispatcher()
dispatcher.map("/joints", handle_joints)

print(f"Listening on {OSC_IN_IP}:{OSC_IN_PORT}")
print(f"Mirroring joints to '{ROBOT_NAME}'...")

server = BlockingOSCUDPServer((OSC_IN_IP, OSC_IN_PORT), dispatcher)
server.serve_forever()