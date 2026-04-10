from fairino import Robot
# Establish a connection with the robot controller and return a robot object if the connection is successful
robot = Robot.RPC('192.168.58.2')
j = [67.957, -81.482, 87.595, -95.691, -94.899, -9.727]
desc_pos = [-123.142, -551.735, 430.549, 178.753, -4.757, 167.754]
offset_pos1 = [50.0, 0.0, 0.0, -30.0, 0.0, 0.0]
offset_pos2 = [50.0, 0.0, 0.0, -30.0, 0.0, 0.0]
epos = [0.0] * 4
sp = [2, 30.0, 50.0, 10.0, 10.0, 0, 1]  # [circle_num, circle_angle, rad_init, rad_add, rotaxis_add, rot_direction, velAccMode]
tool = 0
user = 0
vel = 30.0
acc = 60.0
ovl = 100.0
blendT = -1.0
flag = 2
robot.SetSpeed(20)
rtn = robot.MoveJ(joint_pos=j, tool=tool, user=user, vel=vel, acc=acc, ovl=ovl, exaxis_pos=epos, blendT=blendT, offset_flag=flag, offset_pos=offset_pos1)
print(f"movej errcode:{rtn}")
# rtn = robot.NewSpiral(desc_pos=desc_pos, tool=tool, user=user, vel=vel, acc=acc, exaxis_pos=epos, ovl=ovl, offset_flag=flag, offset_pos=offset_pos2, param=sp)
print(f"newspiral errcode:{rtn}")
robot.CloseRPC()