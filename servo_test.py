from fairino import Robot
import time
# Establish a connection with the robot controller and return a robot object if the connection is successful
robot = Robot.RPC('192.168.58.2')
j = [0.0] * 6
epos = [0.0] * 4
vel = 0.0
acc = 0.0
cmdT = 0.008
filterT = 0.0
gain = 0.0
flag = 0
count = 100
dt = 0.5
cmdID = 0
ret, j = robot.GetActualJointPosDegree(flag)
if ret == 0:
    cmdID += 1
    robot.ServoMoveStart()
    while count:
        robot.ServoJ(joint_pos=j,axisPos= epos,acc= acc,vel= vel, cmdT=cmdT, filterT=filterT, gain=gain, id=cmdID)
        j[4] += dt
        count -= 1
        time.sleep(cmdT)
        rtn,pkg = robot.GetRobotRealTimeState()
        print(f"Servoj Count {pkg.servoJCmdNum}; last pos is {pkg.lastServoTarget[0]},{pkg.lastServoTarget[1]},{pkg.lastServoTarget[2]},{pkg.lastServoTarget[3]},{pkg.lastServoTarget[4]},{pkg.lastServoTarget[5]}")

        if count < 50:
            robot.MotionQueueClear()
            print(f"After queue clear, Servoj Count {pkg.servoJCmdNum}; last pos is {pkg.lastServoTarget[0]},{pkg.lastServoTarget[1]},{pkg.lastServoTarget[2]},{pkg.lastServoTarget[3]},{pkg.lastServoTarget[4]},{pkg.lastServoTarget[5]}")
            break
    robot.ServoMoveEnd()
else:
    print(f"GetActualJointPosDegree errcode:{ret}")
robot.CloseRPC()