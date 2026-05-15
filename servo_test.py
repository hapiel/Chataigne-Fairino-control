import gc
gc.disable()

from fairino import Robot
from pythonosc import udp_client
import time
import math

robot = Robot.RPC('192.168.58.2')


# OSC client setup
osc_client = udp_client.SimpleUDPClient("127.0.0.1", 9005)

j = [0.0] * 6
epos = [0.0] * 4
vel = 0.0
acc = 0.0
cmdT = 0.008
filterT = 0.0
gain = 0.0
flag = 0
cmdID = 0

AMPLITUDE = 160.0
FREQUENCY = 0.15
OMEGA = 2 * math.pi * FREQUENCY

ret, j = robot.GetActualJointPosDegree(flag)

if ret == 0:
    start_j1 = j[0]
    clamped = max(-AMPLITUDE, min(AMPLITUDE, start_j1))
    phase_offset = math.asin(clamped / AMPLITUDE)
    print(f"Starting J1 position: {start_j1:.2f} deg, phase offset: {math.degrees(phase_offset):.2f} deg")

    cmdID += 1
    robot.ServoMoveStart()
    print("Starting sinusoidal motion on J1. Press Ctrl+C to stop.")

    start_wall = time.perf_counter()
    last_loop_end = None

    try:
        while True:
            loop_start = time.perf_counter()

            if last_loop_end is not None:
                time_since_last = loop_start - last_loop_end
                osc_client.send_message("/robot/loop_interval", time_since_last)

            t = loop_start - start_wall
            j[0] = AMPLITUDE * math.sin(OMEGA * t + phase_offset)

            robot.ServoJ(
                joint_pos=j,
                axisPos=epos,
                acc=acc,
                vel=vel,
                cmdT=cmdT,
                filterT=filterT,
                gain=gain,
                id=cmdID,
                
            )
            cmdID += 1

            elapsed_in_loop = time.perf_counter() - loop_start
            sleep_time = cmdT - elapsed_in_loop
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                print(f"WARNING: loop overran by {-sleep_time*1000:.2f} ms at t={t:.3f}s")

            last_loop_end = time.perf_counter()

    except KeyboardInterrupt:
        print("\nCtrl+C detected - stopping motion.")
        robot.MotionQueueClear()

    finally:
        robot.ServoMoveEnd()

else:
    print(f"GetActualJointPosDegree errcode: {ret}")

robot.CloseRPC()