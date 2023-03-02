import time

import rclpy  # ROS client library
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

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


# states
# 0: normal
# 1: on the front wall
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


        # allows packet loss
        self.state = 0
        self.go = True
        self.rot = False
        self.front_search = True
        self.back_search = True
        self.right_search = True
        self.left_search = True
        self.object_front = False
        self.object_back = False
        self.object_left = False
        self.object_right = False
        self.counter = 0
        self.ang_vel_percent = 0
        self.lin_vel_percent = 0
        self.image = None
        #TODO Add orientations
        self.orient_west = 180
        self.orient_back = -90
        self.VIEW = "up"
        self.rotate_direction = None

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
        pass
        # try:
        #     cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        # except CvBridgeError as e:
        #     print(e)
        #
        # self.image_received = True
        # self.image = cv_image
        #
        # detect_red(self)
        # start_video(self)

    def odom_callback(self, msg):
        pos = msg.pose.pose.position
        orient = quat2euler([msg.pose.pose.orientation.x, msg.pose.pose.orientation.y, msg.pose.pose.orientation.z, msg.pose.pose.orientation.w])
        if self.go:
            drive(self, 20)
            self.go = False

        if self.rot:
            if self.VIEW == "north":
                rotate(self, self.rotate_direction)
                if self.rotate_direction < 0:
                    if orient[0] > rad(self.orient_west):
                    self.VIEW = "west"
                elif self.rotate_direction > 0:
                    self.VIEW = "east"
                else:
                    return

            elif self.VIEW == "west":
                rotate(self, self.rotate_direction)
                if self.rotate_direction < 0:
                    self.VIEW = "south"
                elif self.rotate_direction > 0:
                    self.VIEW = "north"
                else:
                    return

            elif self.VIEW == "south":
                rotate(self, self.rotate_direction)
                if self.rotate_direction < 0:
                    self.VIEW = "east"
                elif self.rotate_direction > 0:
                    self.VIEW = "west"
                else:
                    return

            elif self.VIEW == "east":
                rotate(self, self.rotate_direction)
                if self.rotate_direction < 0:
                    self.VIEW = "north"
                elif self.rotate_direction > 0:
                    self.VIEW = "south"
                else:
                    return

        if self.VIEW == "west":
            rotate(self, self.rotate_direction)

            #print("RAD: ", rad(self.orient_back)
            print("Postion", pos)
            print("Orientation", orient)

        elif orient[0] == rad(self.orient_left) and orient[0] > rad(self.orient_back):
            print("Orientupdate: ", self.orient_back)
            start_search(self)
            drive(self, 20)
            self.rot = False

        if self.object_front and self.object_left:
            stop(self)
            self.rot = True
        elif self.object_front and self.object_right:
            stop(self)
            self.rot = True
        elif self.object_front:
            stop(self)
            self.rot = True
            self.rotate_direction = 10
        elif self.object_right:
            stop_nosearch(self)
            drive(self, 20)
        elif self.object_left:
            stop_nosearch(self)
            drive(self, 20)


    def scan_callback(self, msg):
        """
        is run whenever a LaserScan msg is received
        """
        #### Degrees of laser view
        # 60 - 120 right side
        # 150 -210 behind
        # 240 - 300 left
        # -30 - 30 front

        min_dist_front = 0.32
        min_dist_back = 0.32
        min_dist_left = 0.32
        min_dist_right = 0.32

        search_object(self, laser=msg.ranges, scan_range_front=min_dist_front, scan_range_back=min_dist_back,
                      scan_range_left=min_dist_left, scan_range_right=min_dist_right)


def main(args=None):
    rclpy.init(args=args)

    tb3 = Tb3()
    print('waiting for messages...')

    try:
        rclpy.spin(tb3)  # Execute tb3 node
        # Blocks until the executor (spin) cannot work
    except KeyboardInterrupt:
        pass

    tb3.destroy_node()
    rclpy.shutdown()

    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
