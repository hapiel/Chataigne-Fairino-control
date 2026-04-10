from fairino import Robot
import time
import os
# Establish a connection with the robot controller and return a robot object if the connection is successful


file_path = "C:\\FILES\\3projects\\cobot\\ai\\test_01\\data\\AI_test_base_only.txt"

if not os.path.isfile(file_path):
    raise FileNotFoundError(f"Trajectory file not found: {file_path}")

if os.path.getsize(file_path) == 0:
    raise ValueError(f"Trajectory file is empty: {file_path}")

robot = Robot.RPC('192.168.57.2')
rtn = robot.TrajectoryJUpLoad(file_path)
print(f"Upload TrajectoryJ A {rtn}")


traj_file_name = "/fruser/traj/AI_test_base_only.txt"

rtn = robot.LoadTrajectoryJ(traj_file_name, 100, 1)
print(f"LoadTrajectoryJ {traj_file_name}, rtn is: {rtn}")
rtn,traj_start_pose = robot.GetTrajectoryStartPose(traj_file_name)
print(f"GetTrajectoryStartPose is: {rtn}")
print(f"desc_pos:{traj_start_pose[0]},{traj_start_pose[1]},{traj_start_pose[2]},"
      f"{traj_start_pose[3]},{traj_start_pose[4]},{traj_start_pose[5]}")
time.sleep(1)
robot.SetSpeed(50)
robot.MoveCart(traj_start_pose, 0, 0, 50, 100, 100)
rtn,traj_num = robot.GetTrajectoryPointNum()
print(f"GetTrajectoryStartPose rtn is: {rtn}, traj num is: {traj_num}")
rtn = robot.SetTrajectoryJSpeed(50.0)
print(f"SetTrajectoryJSpeed is: {rtn}")
traj_force = [0.0,0.0,0.0,0.0,0.0,0.0]
traj_force[0] = 10  # fx = 10
rtn = robot.SetTrajectoryJForceTorque(traj_force)
print(f"SetTrajectoryJForceTorque rtn is: {rtn}")
rtn = robot.SetTrajectoryJForceFx(10.0)
print(f"SetTrajectoryJForceFx rtn is: {rtn}")
rtn = robot.SetTrajectoryJForceFy(0.0)
print(f"SetTrajectoryJForceFy rtn is: {rtn}")
rtn = robot.SetTrajectoryJForceFz(0.0)
print(f"SetTrajectoryJForceFz rtn is: {rtn}")
rtn = robot.SetTrajectoryJTorqueTx(10.0)
print(f"SetTrajectoryJTorqueTx rtn is: {rtn}")
rtn = robot.SetTrajectoryJTorqueTy(10.0)
print(f"SetTrajectoryJTorqueTy rtn is: {rtn}")
rtn = robot.SetTrajectoryJTorqueTz(10.0)
print(f"SetTrajectoryJTorqueTz rtn is: {rtn}")
rtn = robot.MoveTrajectoryJ()
print(f"MoveTrajectoryJ rtn is: {rtn}")
robot.CloseRPC()