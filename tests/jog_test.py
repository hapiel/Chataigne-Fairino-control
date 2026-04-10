from fairino import Robot
import time
# Establish a connection with the robot controller and return a robot object if the connection is successful
robot = Robot.RPC('192.168.58.2')
for i in range(6):
    robot.StartJOG(0, i + 1, 0, 20.0, 20.0, 30.0)
    time.sleep(1)
    robot.ImmStopJOG()
    time.sleep(1)
for i in range(6):
    robot.StartJOG(2, i + 1, 0, 20.0, 20.0, 30.0)
    time.sleep(1)
    robot.ImmStopJOG()
    time.sleep(1)
for i in range(6):
    robot.StartJOG(4, i + 1, 0, 20.0, 20.0, 30.0)
    time.sleep(1)
    robot.StopJOG(5)
    time.sleep(1)
for i in range(6):
    robot.StartJOG(8, i + 1, 0, 20.0, 20.0, 30.0)
    time.sleep(1)
    robot.StopJOG(9)
    time.sleep(1)
robot.CloseRPC()