import time
from fairino import Robot

# ---------------- CONFIG ----------------
ROBOT_IP = "192.168.57.2"

LOOP_HZ = 800.0          # polling frequency (Hz)
PRINT_EVERY = 1.0        # seconds between stats prints
# ----------------------------------------

loop_interval = 1.0 / LOOP_HZ

robot = Robot.RPC(ROBOT_IP)

print(f"Connected to robot at {ROBOT_IP}")
print(f"Polling at {LOOP_HZ} Hz\n")

last_joints = None
unique_updates = 0
total_reads = 0
valid_reads = 0

start_time = time.perf_counter()
last_report_time = start_time
next_tick = start_time

while True:
    now = time.perf_counter()

    if now >= next_tick:
        ret, joints = robot.GetActualJointPosDegree()
        total_reads += 1

        if ret == 0 and isinstance(joints, list) and len(joints) >= 6:

            # Ignore samples where joint 1, 2, or 3 is exactly 0.0
            if joints[0] != 0.0 and joints[1] != 0.0 and joints[2] != 0.0:
                valid_reads += 1

                if last_joints is None or joints != last_joints:
                    unique_updates += 1
                    last_joints = joints.copy()

        next_tick += loop_interval
        if next_tick < now:
            next_tick = now + loop_interval

    # Periodic statistics output
    if now - last_report_time >= PRINT_EVERY:
        elapsed = now - last_report_time
        unique_rate = unique_updates / elapsed

        print(
            f"\n--- Stats ---\n"
            f"Total reads: {total_reads}\n"
            f"Valid reads (J1-J3 != 0.0): {valid_reads}\n"
            f"Unique joint updates: {unique_updates}\n"
            f"Unique updates per second: {unique_rate:.2f} Hz\n"
            f"--------------\n"
        )

        total_reads = 0
        valid_reads = 0
        unique_updates = 0
        last_report_time = now

    time.sleep(0.0005)
