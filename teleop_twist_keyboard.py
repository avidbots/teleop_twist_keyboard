# Copyright 2011 Brown University Robotics.
# Copyright 2017 Open Source Robotics Foundation, Inc.
# All rights reserved.
#
# Software License Agreement (BSD License 2.0)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of the Willow Garage nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import sys
import threading
import time

import geometry_msgs.msg
from pynput import keyboard
import rcl_interfaces.msg
import rclpy

if sys.platform == 'win32':
    import ctypes
else:
    import termios
    import tty

moveBindings = {
    'i': (1, 0, 0, 0),
    'o': (1, 0, 0, -1),
    'j': (0, 0, 0, 1),
    'l': (0, 0, 0, -1),
    'u': (1, 0, 0, 1),
    ',': (-1, 0, 0, 0),
    '.': (-1, 0, 0, 1),
    'm': (-1, 0, 0, -1),
    'O': (1, -1, 0, 0),
    'I': (1, 0, 0, 0),
    'J': (0, 1, 0, 0),
    'L': (0, -1, 0, 0),
    'U': (1, 1, 0, 0),
    '<': (-1, 0, 0, 0),
    '>': (-1, -1, 0, 0),
    'M': (-1, 1, 0, 0),
    't': (0, 0, 1, 0),
    'b': (0, 0, -1, 0),
}

speedBindings = {
    'q': (1.1, 1.1),
    'z': (.9, .9),
    'w': (1.1, 1),
    'x': (.9, 1),
    'e': (1, 1.1),
    'c': (1, .9),
}


class KeyboardListener:
    """Thread-based keyboard listener for key press/release detection."""

    def __init__(self):
        self.pressed_keys = set()
        self.ctrl_pressed = False
        self.lock = threading.Lock()
        self.listener = None

    def _on_press(self, key):
        """Handle a key press."""
        try:
            # Try to get the character
            char = key.char
            if char:  # Only process actual characters
                with self.lock:
                    self.pressed_keys.add(char)
        except AttributeError:
            # Special keys
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                with self.lock:
                    self.ctrl_pressed = True

    def _on_release(self, key):
        """Handle a key release."""
        try:
            char = key.char
            if char:
                with self.lock:
                    self.pressed_keys.discard(char)
        except AttributeError:
            # Special keys
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                with self.lock:
                    self.ctrl_pressed = False

    def start(self):
        """Start the keyboard listener thread."""
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()

    def stop(self):
        """Stop the keyboard listener thread."""
        if self.listener:
            self.listener.stop()

    def get_pressed_keys(self):
        """
        Get the set of currently pressed keys.

        Returns
        -------
            set: Set of character strings currently pressed.

        """
        with self.lock:
            return self.pressed_keys.copy()

    def ctrl_c_is_pressed(self):
        """
        Check if Ctrl+C was pressed.

        Returns
        -------
            bool: True if Ctrl+C combination is currently pressed.

        """
        with self.lock:
            return self.ctrl_pressed and 'c' in self.pressed_keys


def saveTerminalSettings():
    if sys.platform == 'win32':
        # On Windows, save the console mode
        kernel32 = ctypes.windll.kernel32
        stdin_handle = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(stdin_handle, ctypes.byref(mode))
        return (stdin_handle, mode.value)
    return termios.tcgetattr(sys.stdin)


def restoreTerminalSettings(old_settings):
    if sys.platform == 'win32':
        if old_settings is not None:
            kernel32 = ctypes.windll.kernel32
            stdin_handle, old_mode = old_settings
            kernel32.SetConsoleMode(stdin_handle, old_mode)
        return
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def vels(speed, turn):
    return 'currently:\tspeed %.2f\tturn %.2f ' % (speed, turn)


def safe_print(text):
    """Print text with proper line endings for raw terminal mode."""
    # In raw mode (both Unix and Windows), we need \r\n instead of just \n
    text = text.replace('\n', '\r\n')
    print(text, end='')
    sys.stdout.flush()


def main():
    settings = saveTerminalSettings()

    rclpy.init()

    node = rclpy.create_node('teleop_twist_keyboard')

    # parameters
    read_only_descriptor = rcl_interfaces.msg.ParameterDescriptor(read_only=True)
    stamped = node.declare_parameter('stamped', True, read_only_descriptor).value
    frame_id = node.declare_parameter('frame_id', '', read_only_descriptor).value
    speed = node.declare_parameter('speed', 0.5, read_only_descriptor).value
    turn = node.declare_parameter('turn', 1.0, read_only_descriptor).value
    deadman_timeout = node.declare_parameter(
        'deadman_timeout', 0.1, read_only_descriptor
    ).value

    msg = (
        """This node takes keypresses from the keyboard and publishes them\n"""
        """as Twist/TwistStamped messages. It works best with a US keyboard layout.\n"""
        """---------------------------\n"""
        """Moving around:\n"""
        """u    i    o\n"""
        """j    k    l\n"""
        """m    ,    .\n"""
        """\n"""
        """For Holonomic mode (strafing), hold down the shift key:\n"""
        """---------------------------\n"""
        """U    I    O\n"""
        """J    K    L\n"""
        """M    <    >\n"""
        """\n"""
        """t : up (+z)\n"""
        """b : down (-z)\n"""
        """\n"""
        """anything else : stop\n"""
        """\n"""
    )
    if deadman_timeout > 0:
        msg += (
            """DEADMAN: hold a movement or speed key to maintain motion. If no valid key is\n"""
            """pressed within the timeout the node will publish zero velocities.\n"""
            """\n"""
            """NOTE: The deadman timeout is evaluated at 20Hz (every 0.05s). Timeout values\n"""
            """less than 0.05s will effectively become 0.05s, and non-integer multiples of\n"""
            """0.05s may trigger up to 0.05s late. For precise deadman behavior, use timeout\n"""
            """values that are integer multiples of 0.05s (e.g., 0.05, 0.1, 0.15, etc.).\n"""
            """\n"""
        )
    msg += (
        """q/z : increase/decrease max speeds by 10%\n"""
        """w/x : increase/decrease only linear speed by 10%\n"""
        """e/c : increase/decrease only angular speed by 10%\n"""
        """\n"""
        """CTRL-C to quit\n"""
    )

    if not stamped and frame_id:
        raise Exception("'frame_id' can only be set when 'stamped' is True")

    if stamped:
        TwistMsg = geometry_msgs.msg.TwistStamped
    else:
        TwistMsg = geometry_msgs.msg.Twist

    pub = node.create_publisher(TwistMsg, 'cmd_vel', 10)

    spinner = threading.Thread(target=rclpy.spin, args=(node,))
    spinner.start()

    x = 0.0
    y = 0.0
    z = 0.0
    th = 0.0
    status = 0.0
    last_motion_key_time = 0.0

    twist_msg = TwistMsg()

    if stamped:
        twist = twist_msg.twist
        twist_msg.header.stamp = node.get_clock().now().to_msg()
        twist_msg.header.frame_id = frame_id
    else:
        twist = twist_msg

    # Put terminal in raw mode to suppress key echo
    if sys.platform != 'win32':
        tty.setraw(sys.stdin.fileno())
    else:
        # On Windows, disable echo and line input mode
        kernel32 = ctypes.windll.kernel32
        stdin_handle = settings[0]
        # Disable ENABLE_ECHO_INPUT (0x0004) and ENABLE_LINE_INPUT (0x0002)
        new_mode = settings[1] & ~0x0006
        kernel32.SetConsoleMode(stdin_handle, new_mode)

    # Start pynput keyboard listener
    listener = KeyboardListener()
    listener.start()

    try:
        safe_print(msg + '\n')
        safe_print(vels(speed, turn) + '\n')
        rate = node.create_rate(20)
        while True:
            rate.sleep()

            if listener.ctrl_c_is_pressed():
                break

            # Get key presses
            pressed_keys = listener.get_pressed_keys()
            key = pressed_keys.pop() if len(pressed_keys) == 1 else ''
            now = time.time()

            # Keep previous twist command if deadman is disabled
            if key == '' and deadman_timeout <= 0:
                continue

            # Keep previous twist command if deadman hasn't timed out
            if key == '' and now <= last_motion_key_time + deadman_timeout:
                continue

            if key in moveBindings.keys():
                x = moveBindings[key][0]
                y = moveBindings[key][1]
                z = moveBindings[key][2]
                th = moveBindings[key][3]
                last_motion_key_time = now
            elif key in speedBindings.keys():
                speed = speed * speedBindings[key][0]
                turn = turn * speedBindings[key][1]

                safe_print(vels(speed, turn) + '\n')
                if (status == 14):
                    safe_print(msg + '\n')
                status = (status + 1) % 15
            else:
                x = 0.0
                y = 0.0
                z = 0.0
                th = 0.0
                if (key == '\x03'):
                    break

            if stamped:
                twist_msg.header.stamp = node.get_clock().now().to_msg()

            twist.linear.x = x * speed
            twist.linear.y = y * speed
            twist.linear.z = z * speed
            twist.angular.x = 0.0
            twist.angular.y = 0.0
            twist.angular.z = th * turn
            pub.publish(twist_msg)

    except Exception as e:
        safe_print(str(e) + '\n')

    finally:
        if stamped:
            twist_msg.header.stamp = node.get_clock().now().to_msg()

        twist.linear.x = 0.0
        twist.linear.y = 0.0
        twist.linear.z = 0.0
        twist.angular.x = 0.0
        twist.angular.y = 0.0
        twist.angular.z = 0.0
        pub.publish(twist_msg)
        rclpy.shutdown()
        spinner.join()

        listener.stop()

        # Flush any buffered input before restoring terminal settings
        if sys.platform != 'win32':
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        else:
            # On Windows, flush console input buffer
            kernel32 = ctypes.windll.kernel32
            stdin_handle = settings[0]
            kernel32.FlushConsoleInputBuffer(stdin_handle)
        restoreTerminalSettings(settings)


if __name__ == '__main__':
    main()
