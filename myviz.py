#!/usr/bin/env python

import roslib; roslib.load_manifest('rviz_python_tutorial');
roslib.load_manifest('gazebo')
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image
from gazebo.srv import GetModelState
from tf.transformations import euler_from_quaternion
import rospy
from math import atan, degrees

import sys

from python_qt_binding.QtGui import *
from python_qt_binding.QtCore import *

import rviz

## The MyViz class is the main container widget.
class MyViz( QWidget ):

    ## MyViz Constructor
    ## ^^^^^^^^^^^^^^^^^
    ##
    ## Its constructor creates and configures all the component widgets:
    def __init__(self):
        self.image = 0
        self.image_height = 0
        self.image_width = 0
        self.image_step = 0
        self.rotating = False

        self.take_action = True
        QWidget.__init__(self)

        self.frame = rviz.VisualizationFrame()
        self.frame.setSplashPath( "" )
        self.frame.initialize()

        reader = rviz.YamlConfigReader()
        config = rviz.Config()
        reader.readFile( config, "config.rviz" )
        self.frame.load( config )

        self.setWindowTitle( config.mapGetChild( "Title" ).getValue() )

        # self.frame.setMenuBar( None )
        self.frame.setStatusBar( None )
        self.frame.setHideButtonVisibility( False )

        self.manager = self.frame.getManager()

        ## Since the config file is part of the source code for this
        ## example, we know that the first display in the list is the
        ## grid we want to control.
        self.image_display = self.manager.getRootDisplayGroup().getDisplayAt( 0 )
        # self.image_display.eventFilter = self.eventFilter
        
        ## Here we create the layout and other widgets in the usual Qt way.
        layout = QVBoxLayout()
        layout.addWidget( self.frame )
        
        self.setLayout( layout )

        self.publisher = rospy.Publisher('cmd_vel', Twist)
        rospy.init_node('Controller_Interface', anonymous=True)
        self.listen()

    def find_average_color(self, image, click_x, click_y):
        average_color = [0, 0, 0]
        count = 0
        for i in xrange(4):
            for j in xrange(4):
                x = click_x-2+i
                y = click_y-2+j
                if (x)*(y) > 0:
                    count += 1
                    average_color[0] += ord(image[self.image_step*y + x*3])
                    average_color[1] += ord(image[self.image_step*y + x*3 + 1])
                    average_color[2] += ord(image[self.image_step*y + x*3 + 2])
        if count > 0:
            return [x/count for x in average_color]
        else:
            print "ERRRORRRR"
            return [-1, -1, -1]


    def calculate_direction(self, event):
        # Do some image processing and then 
        # decide where to go.

        found_object = 0
        print event.x(), event.y()
        print self.image_height
        print self.image_width
        print self.image_step

        image_temp = self.image

        print type(self.image[self.image_step*event.y() + event.x()*3])
        average_color = self.find_average_color(image_temp, event.x(), event.y())

        # Find position of your bot.
        rospy.wait_for_service('/gazebo/get_model_state')
        bot_orientation = [-1, -1, -1]
        try:
            gms = rospy.ServiceProxy('/gazebo/get_model_state', GetModelState)
            resp1 = gms('quadrotor', 'world')
            print resp1.pose
            orientation = resp1.pose.orientation
            quaternion = [orientation.x, orientation.y, orientation.z, orientation.w]
            bot_orientation = euler_from_quaternion(quaternion)
        except rospy.ServiceException, e:
            print "Service call failed: %s"%e

        # Find the direction you are facing

        print "bot orientation is ", bot_orientation
        print average_color
        yaw = bot_orientation[2]
        if yaw < 0:
            yaw += 6.28

        target_orientation = -1
        target_x = 0
        target_y = 0

        # if(average_color == red):
        #     # go to red object
        # -7.5, 0, 0.63
        if(average_color[0] > 60 and average_color[1] < 30 and average_color[2] < 30):
            print "Turning towards red object"
            target_x = -7.5
            target_y = 0
            found_object = 1

        # if(average_color == green):
        #     # go to green object
        # -6.5, 6, 0.63
        if(average_color[0] < 60 and average_color[1] > 60 and average_color[2] < 30):
            print "Turning towards green object"
            target_x = -6.5
            target_y = 6
            found_object = 1

        #     # go to blue object
        # -3.5, -3, 0.63
        if(average_color[0] == 0 and average_color[1] < 60 and average_color[2] > 60):
            print "Turning towards blue object"
            target_x = -3.5
            target_y = -3
            found_object = 1

        if found_object == 1:
            if resp1.pose.position.x == target_x:
                if resp1.pose.position.y > target_y:
                    target_orientation = 3.14/2.0
                else:
                    target_orientation = -3.14/2.0
            else:
                target_orientation = atan( (target_y-resp1.pose.position.y)/(target_x-resp1.pose.position.x) )
                if target_orientation < 0 and (target_y > resp1.pose.position.y):
                    target_orientation += 3.14
                elif target_orientation < 0 and (target_y < resp1.pose.position.y):
                    target_orientation += 6.28
                elif target_orientation > 0 and (target_y < resp1.pose.position.y):
                    target_orientation += 3.14

            print target_orientation
            print degrees(target_orientation)

            while abs(yaw - target_orientation) > 0.1:
                twist = Twist()
                if target_orientation < yaw:
                    twist.angular.z = -1.2
                    self.publisher.publish(twist)

                    rospy.sleep(0.04)

                    twist.angular.z = 0.0
                    self.publisher.publish(twist)
                else:
                    twist.angular.z = 1.2
                    self.publisher.publish(twist)

                    rospy.sleep(0.04)

                    twist.angular.z = 0.0
                    self.publisher.publish(twist)

                try:
                    resp1 = gms('quadrotor', 'world')
                    orientation = resp1.pose.orientation
                    quaternion = [orientation.x, orientation.y, orientation.z, orientation.w]
                    bot_orientation = euler_from_quaternion(quaternion)
                    yaw = bot_orientation[2]
                    if yaw < 0:
                        yaw += 6.28
                    print "Yaw is", yaw, "and target is", target_orientation
                except rospy.ServiceException, e:
                    print "Service call failed: %s"%e

            twist = Twist()

            twist.linear.x = 1.4
            self.publisher.publish(twist)
        return found_object

    ## Handle GUI events
    ## ^^^^^^^^^^^^^^^^^
    def eventFilter(self, source, event):
        if (event.type() == QEvent.MouseButtonDblClick):
            print "double click"
            if self.take_action:
                if self.calculate_direction(event) == 0:
                    twist = Twist()

                    twist.linear.x = 0.9
                    self.publisher.publish(twist)

                    # rospy.sleep(0.15)
                self.take_action = False
            else:
                self.take_action = True

        elif (event.type() == QEvent.MouseButtonPress and
            event.button() == Qt.LeftButton):
            if self.take_action:
                if self.calculate_direction(event) == 0:
                    if self.rotating:
                        twist = Twist()
                        twist.angular.z = 0.0
                        self.publisher.publish(twist)
                        self.rotating = False
                    else:
                        twist = Twist()
                        twist.angular.z = 0.4
                        self.publisher.publish(twist)
                        self.rotating = True
                self.take_action = False
            else:
                self.take_action = True

        elif (event.type() == QEvent.MouseButtonPress and
            event.button() == Qt.RightButton):
            if self.take_action:
                print "1"
                twist = Twist()

                twist.angular.z = -0.4
                self.publisher.publish(twist)
                self.rotating = True

                self.take_action = False
            else:
                print "2"
                self.take_action = True
        return QWidget.eventFilter(self, source, event)

    def callback(self, data):
        self.image = data.data
        self.image_height = data.height
        self.image_width = data.width
        self.image_step = data.step

    def listen(self):
        rospy.Subscriber("/ardrone/image_raw", Image, self.callback)
        # rospy.spin()

## Start the Application
## ^^^^^^^^^^^^^^^^^^^^^
##
## That is just about it.  All that's left is the standard Qt
## top-level application code: create a QApplication, instantiate our
## class, and start Qt's main event loop (app.exec_()).
if __name__ == '__main__':
    print "entered main"
    app = QApplication( sys.argv )

    myviz = MyViz()
    app.installEventFilter(myviz)
    print 'created myviz'
    # myviz.resize( 823, 518 )
    myviz.show()

    app.exec_()
