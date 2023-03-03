import rclpy  # ROS client library
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
import sys
import os
from itertools import islice

from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Point
from geometry_msgs.msg import Quaternion
from geometry_msgs.msg import Twist
from utils.tb3_motion import *
from transforms3d.euler import quat2euler
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge, CvBridgeError
import math


class Tb3(Node):
        def __init__(self):
                super().__init__('tb3')
                self.cmd_vel_pub = self.create_publisher(
                                Twist,  # message type
                                'cmd_vel',  # topic name
                                1)  # history depth

                self.odom_sub = self.create_subscription(
                                Odometry,
                                'odom',
                                self.odom_callback,
                                qos_profile_sensor_data)

                self.scan_sub = self.create_subscription(
                                LaserScan,
                                'scan',
                                self.scan_callback,  # function to run upon message arrival
                                qos_profile_sensor_data)  # allows packet loss

                self.bridge = CvBridge()
                self.image_received = False
                self.img_sub = self.create_subscription(
                                Image,
                                '/camera/image_raw',
                                self.img_callback,
                                qos_profile_sensor_data)

                self.state = 0
                self.ang_vel_percent = 0
                self.lin_vel_percent = 0
                self.image = None
                self.color = ""

                self.pos = None
                self.orient = [-1, -1, -1]
                self.front_beams = {}
                self.back_beams = {}
                self.left_beams = {}
                self.right_beams = {}
                self.op_beams = [(0,0)]
                self.groups = []
                self.pre_rotate = 9999
                self.rot_goal = 9999
                self.once = True

                self.state = 0

        def vel(self, lin_vel_percent, ang_vel_percent=0):
                """ publishes linear and angular velocities in percent
                """
                # for TB3 Waffle
                MAX_LIN_VEL = 0.26  # m/s
                MAX_ANG_VEL = 1.82  # rad/s

                cmd_vel_msg = Twist()
                cmd_vel_msg.linear.x = MAX_LIN_VEL * lin_vel_percent / 100
                cmd_vel_msg.angular.z = MAX_ANG_VEL * ang_vel_percent / 100

                self.cmd_vel_pub.publish(cmd_vel_msg)
                self.ang_vel_percent = ang_vel_percent
                self.lin_vel_percent = lin_vel_percent

        def img_callback(self, msg):
                return
                try:
                        cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
                        self.image = cv_image
                        self.image_received = True
                        detect_red(self)
                        # start_video(self)
                except CvBridgeError as e:
                        print(e)
                self.image_received = False

        def odom_callback(self, msg):
                self.pos = msg.pose.pose.position
                self.orient = quat2euler([msg.pose.pose.orientation.x, msg.pose.pose.orientation.y, msg.pose.pose.orientation.z, msg.pose.pose.orientation.w])

                if self.once:
                        self.rotate_degree(60, clockwise=False)

        def rotate_degree(self, deg, clockwise = False):
                if self.pre_rotate == 9999:
                        self.pre_rotate = self.orient[0]
                if clockwise:
                        rotate(self, -5)
                        self.rot_goal = rad(self.pre_rotate*(180/math.pi) - deg)
                        if self.orient[0] < self.rot_goal:
                                self.pre_rotate = 9999
                                stop(self)
                else:
                        rotate(self, 5)
                        self.rot_goal = rad(self.pre_rotate*(180/math.pi) + deg)
                        if self.orient[0] > self.rot_goal:
                                self.pre_rotate = 9999
                                stop(self)

        def scan_callback(self, msg):
                """
                is run whenever a LaserScan msg is received
                """
                # min_dist_front = 0.32
                # min_dist_back = 0.32
                # min_dist_left = 0.32
                # min_dist_right = 0.32

                self.beams = msg.ranges
                self.diagnostics()
                self.op_beams = [(x, self.beams[x]) for x in range(0, len(self.beams)) if self.beams[x] > 1]
                self.get_grouped_beams()
                
        def get_grouped_beams(self):
                if len(self.op_beams) == 0:
                        return
                self.groups = [[self.op_beams[0][0]]]
                idx = self.op_beams[0][0]
                for x in self.op_beams[1:]:
                        id = x[0]
                        ab = abs(idx - id)
                        if ab == 1:
                                idx = id
                                self.groups[-1].append(id)
                        else:
                                idx = id
                                self.groups.append([id])
                if len(self.groups) >= 2 and self.groups[0][0] == 0 and self.groups[-1][-1] == 359:
                        self.groups = [self.groups[-1] + self.groups[0]] + self.groups[1:-1]


        def diagnostics(self):
                if self.pos != None and self.orient != None:
                        try:
                                os.system("clear")
                                print(f"X{' ' * len(str(self.pos.x))}\tY{' ' * len(str(self.pos.y))}\tZ{' ' * len(str(self.pos.z))}\t|\tRotX{' ' * len(str(self.orient[0]))}\tRotY{' ' * (len(str(self.orient[1]))-3)}\tRotZ")
                                print(f"{self.pos.x}\t{self.pos.y}\t{self.pos.z}\t|\t{self.orient[0]}\t{self.orient[1]}\t{self.orient[2]}")
                                print("\n")
                                print(f"List of beam groups that extend the range of 1m")
                                print(f"#Beams\t|\t <\t>")
                                print(f"{'-' * 35}")
                                for g in self.groups:
                                        print(f"{len(g)}\t|\t{g[0]}\t{g[-1]}")
                                print(f"Rotation Logs (9999 is the default):\n\n")
                                print(f"\nRadian calculations")
                                print(f"Degree\tRadian")
                                rads = [0, 90, 180, 60, 195, 270, 359]
                                for r in rads:
                                        print(f"{r}\t{rad(r)}")
                                print(f"pre rotation value: {self.pre_rotate}")
                                print(f"rotation goal: {self.rot_goal}")
                        except:
                                pass

def rad(deg):
        if deg > 180:
                deg -= 360 
        return math.radians(deg)


def main(args=None):
        rclpy.init(args=args)
        tb3 = Tb3()
        print('waiting for messages...')

        try:
                rclpy.spin(tb3)  # Execute tb3 node
        # Blocks until the executor (spin) cannot work
        except KeyboardInterrupt:
                pass
                # os.system("clear")

        tb3.destroy_node()
        rclpy.shutdown()

        cv2.destroyAllWindows()

if __name__ == '__main__':
        main()
