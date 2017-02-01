#!/usr/bin/env python

'''
 Copyright (c) 2016, Juan Jimeno

 All rights reserved.

 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions are met:

 * Redistributions of source code must retain the above copyright notice,
 this list of conditions and the following disclaimer.
 * Redistributions in binary form must reproduce the above copyright
 notice, this list of conditions and the following disclaimer in the
 documentation and/or other materials provided with the distribution.
 * Neither the name of  nor the names of its contributors may be used to
 endorse or promote products derived from this software without specific
 prior written permission.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
 LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 POSSIBILITY OF SUCH DAMAGE.
'''

import rospy
import tf
import localization as lx
import serial

def get_transform(id):
    try:
        (trans,rot) = listener.lookupTransform('/map', id, rospy.Time(0))
        return trans
    except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
        pass

def get_tag_location(anchors, ranges, transforms):
    P = lx.Project(mode="3D",solver="LSE")

    #define anchor locations
    for i in range(REQ_ANCHOR):
        P.add_anchor(anchors[i], transforms[i])
    t, label = P.add_target()

    #define anchor ranges
    for i in range(REQ_ANCHOR):
        t.add_measure(anchors[i], ranges[i])

    P.solve()
    B = t.loc
    return {'x':B.x, 'y':B.y, 'z':B.z}

def is_listed(anchors, id):
    for anchor in anchors:
        if anchor == id:
            return True
        else:
            pass

def get_serial_data():
    # ser.write('+')
    start = ser.read()
    return ser.readline().strip('$\r\n').split(',')
    # if start == '$':
    #     data_string = ser.readline().strip('\r\n').split(',')
    #     return data_string
    # else:
    #     return None

if __name__ == '__main__':

    rospy.init_node('lips')
    listener = tf.TransformListener()
    start_time = rospy.get_time()
    #create rosparameters
    MIN_RANGE = rospy.get_param('/ros_dwm1000/min_range', 0.5)
    MAX_RANGE = rospy.get_param('/ros_dwm1000/max_range', 10.0)
    REQ_ANCHOR = rospy.get_param('/ros_dwm1000/req_anchor', 3)
    FRAME_ID = rospy.get_param('/ros_dwm1000/frame_id', 'uwb_tag')
    SERIAL_PORT = rospy.get_param('/ros_dwm1000/serial_port', '/dev/ttyUSB0')

    #rosparam logs just to make sure parameters kicked in
    rospy.loginfo("%s is %s", rospy.resolve_name('/ros_dwm1000/min_range'), MIN_RANGE)
    rospy.loginfo("%s is %s", rospy.resolve_name('/ros_dwm1000/max_range'), MAX_RANGE)
    rospy.loginfo("%s is %s", rospy.resolve_name('/ros_dwm1000/req_anchor'), REQ_ANCHOR)
    rospy.loginfo("%s is %s", rospy.resolve_name('/ros_dwm1000/frame_id'), FRAME_ID)
    rospy.loginfo("%s is %s", rospy.resolve_name('/ros_dwm1000/serial_port'), SERIAL_PORT)

    ser = serial.Serial(SERIAL_PORT, 115200)
    ser.timeout = None
    rospy.loginfo("Connected to %s", ser.portstr)

    ranges = []
    anchors = []
    transforms = []
    beacon_count = 0

    while not rospy.is_shutdown():
        #just give some delay for serial
        rospy.sleep(0.1)
        data_string = get_serial_data()
        print data_string
        if 'None' != data_string:
            # print "hello"
            #check if current anchor has already been listed
            #check if the current range is within specified distance
            if (not is_listed(anchors, data_string[0])) and (MIN_RANGE < float(data_string[1]) < MAX_RANGE):
                anchors.append(data_string[0])
                ranges.append(data_string[1])
                transforms.append(get_transform(data_string[0]))
                beacon_count += 1

        #perform trilateration once enough anchors have been found
        if beacon_count == REQ_ANCHOR:
            #do trilateration
            print transforms
            pos = get_tag_location(anchors,ranges,transforms)

            #broadcast the transform
            br = tf.TransformBroadcaster()
            br.sendTransform((pos['x'], pos['y'], pos['z']),
                            tf.transformations.quaternion_from_euler(0, 0, 0),
                            rospy.Time.now(),
                            FRAME_ID,
                            "map")
            # print pos
            # reset all lists
            beacon_count = 0
            ranges = []
            transforms = []
            anchors = []