#!/usr/bin/python3

from MotorStatus import MotorStatus

import time

JOG_STEPS = 10000   # 5 mm
# steps are 0.5 um by default

class Stage():

    def __init__(self, sock):
        self.sock = sock
        self.status = None
        self.center = [0., 0., 0.]

    def close(self):
        self.sock.close()

    def getIP(self):
        return self.sock.getpeername()[0]

    #################################

    """
    all commands list in Section 8 of the Command and Control Reference Guide
    """

    # 01
    def readFirmwareVersion(self):
        """
        This command retrieves the version of the controller firmware.
        """
        cmd = "TR<01>\r"
        cmd_bytes = bytes(cmd, 'utf-8')
        self.sock.sendall(cmd_bytes)
        resp = self.sock.recv(1024).decode('utf-8').strip('<>\r')
        version = resp.split()[3]
        info = resp.split()[4]
        fw_version = '%s (%s)' % (version, info)
        return fw_version

    # 03
    def halt(self):
        """
        This command halts motor motion regardless of where the movement command
        was issued. If in closed-loop mode, the current position is now the target
        position.
        """
        cmd = "<03>\r"
        cmd_bytes = bytes(cmd, 'utf-8')
        self.sock.sendall(cmd_bytes)
        resp = self.sock.recv(1024) # no response after halt command?

    # 04
    def run(self, direction, duration_ds=None):
        """
        This command runs the motor. The motor will continue to move until command
        <03> is received or until an optional time value elapses. In closed-loop
        mode the motor will run according to PID, speed and acceleration settings.
        """
        if direction == 'forward':
            D = 1
        elif direction == 'backward':
            D = 0
        else:
            print('unrecognized direction')
            return
        TTTT = '' if duration_ds is None else '{0:04x}'.format(duration_ds)
        cmd = "<04 {0} {1}>\r".format(D, TTTT)
        cmd_bytes = bytes(cmd, 'utf-8')
        self.sock.sendall(cmd_bytes)
        resp = self.sock.recv(1024)

    # 05
    def moveTimedOpenLoopSteps(self, direction, SPT=None):
        """
        This command sends one or more bursts of resonant pulses to the motor at
        100 Hz (10 ms period) or at the period indicated by the PPPP parameter.
        By default, SPT=None means runs until halt. Otherwise,
            SPT = [nsteps, period, timeDuration]
        with period and timeDuration in units of 3.2us, and timeDuration < period
        """
        if direction == 'forward':
            D = 1
        elif direction == 'backward':
            D = 0
        else:
            print('unrecognized direction')
            return
        SSSS = '' if SPT is None else '{0:04x}'.format(SPT[0])
        PPPP = '' if SPT is None else '{0:04x}'.format(SPT[1])
        TTTT = '' if SPT is None else '{0:04x}'.format(SPT[2])
        cmd = "<05 {0} {1} {2} {3}>\r".format(D, SSSS, PPPP, TTTT)
        cmd_bytes = bytes(cmd, 'utf-8')
        self.sock.sendall(cmd_bytes)
        resp = self.sock.recv(1024)

    # 06
    def moveClosedLoopStep(self, direction, stepSize_counts=None):
        """
        This command adds or subtracts the specified step size (in encoder counts)
        to the current target position, and then moves the motor to the new target
        at the previously defined speed.
        ONLY VALID IN CLOSED LOOP MODE.
        """
        if direction == 'forward':
            D = 1
        elif direction == 'backward':
            D = 0
        else:
            print('unrecognized direction')
            return
        SSSSSSSS = '' if stepSize_counts is None else '{0:08x}'.format(int(stepSize_counts))
        cmd = "<06 {0} {1}>\r".format(D, SSSSSSSS)
        cmd_bytes = bytes(cmd, 'utf-8')
        self.sock.sendall(cmd_bytes)
        resp = self.sock.recv(1024)

    # 07
    def toggleAbsoluteRelative(self):
        """
        This command toggles the relative or absolute position modes. If the M3
        is currently in Absolute position mode, then the current reported position
        is set to 0.
        """
        cmd = "<07>\r"
        cmd_bytes = bytes(cmd, 'utf-8')
        self.sock.sendall(cmd_bytes)
        resp = self.sock.recv(1024)

    # 08
    def moveToTarget(self, targetValue):
        """
        This command sets a target position and moves the motor to that target
        position at the speed defined by command <40>.
        ONLY VALID IN CLOSED-LOOP MODE.
        """
        targetValue = int(targetValue)
        cmd = "<08 {0:08x}>\r".format(targetValue)
        cmd_bytes = bytes(cmd, 'utf-8')
        self.sock.sendall(cmd_bytes)
        resp = self.sock.recv(1024)

    # 09
    def setOpenLoopSpeed(self, speed_255):
        """
        This command sets the open-loop speed of the motor, as a range from 0-255,
        with 255 representing 100% speed. This value is not saved to internal EEPROM.
        """
        speed_255 = int(speed_255)
        cmd = "<09 {0:02x}>\r".format(speed_255)
        cmd_bytes = bytes(cmd, 'utf-8')
        self.sock.sendall(cmd_bytes)
        resp = self.sock.recv(1024)

    # 10
    def viewClosedLoopStatus(self):
        """
        This command is used to view the motor status and position.
        """
        cmd = b"<10>\r"
        cmd_bytes = bytes(cmd, 'utf-8')
        self.sock.sendall(cmd_bytes)
        resp = self.sock.recv(1024).decode('utf-8').strip('<>\r')
        SSSSSS = int(resp.split()[1], 16)
        PPPPPPPP = int(resp.split()[2], 16)
        EEEEEEEE = int(resp.split()[3], 16)
        # self.status = MotorStatus(status_bitfield, position)
        return SSSSSS, PPPPPPPP, EEEEEEEE
        
    # 19
    def readMotorFlags(self):
        """
        This command reports internal flags used by the controller to monitor
        motor conditions.
        """
        cmd = "<19>\r"
        cmd_bytes = bytes(cmd, 'utf-8')
        self.sock.sendall(cmd_bytes)
        resp = self.sock.recv(1024).decode('utf-8').strip('<>\r')
        # TODO parse response
        
    # 20
    def setOrQueryDriveMode(self, mode, interval=None):
        """
        This command sets the drive mode for the M3. The M3 will always default
        to closed-loop mode on power up.
        """
        if mode == 'open':
            X = '0'
        elif mode == 'closed':
            X = '1'
        elif mode == 'query':
            X = 'R'
        else:
            print('unrecognized drive mode')
            return
        IIII = '' if interval is None else '0:04x'.format(int(interval))
        cmd = "<20 {0} {1}>\r".format(X, IIII)
        cmd_bytes = bytes(cmd, 'utf-8')
        self.sock.sendall(cmd_bytes)
        resp = self.sock.recv(1024).decode('utf-8').strip('<>\r')

    # 40
    # TODO set the closed-loop mode speed

    # 41
    # TODO set the position error thresholds and stall detection

    # 43
    # TODO view and set closed-loop PID coefficients

    # 46
    # TODO view and set forward and reverse soft limit values

    # 47
    # TODO view activate/deactivate soft limits

    # 52
    # TODO view time interval units

    # 54
    # TODO get/set baud rate

    # 58
    # TODO supress/enable writes to eeprom

    # 74
    # TODO save closed-loop speed parameters to eeprom

    # 87
    def runFrequencyCalibration(self, direction, incremental=False, automatic=True,
                                frequncy_offset=None, ):
        """
        This command is used to optimize the Squiggle motor resonant drive frequency
        by, on command, sweeping over a range of frequencies, centered at the
        specified period, and settling on the frequency at which the best motor
        performance was detected. This command needs to be run at every power-up or
        more often in environments where the temperature is changing. When issuing
        an automatic frequency-calibration sweep command, the carriage may typically
        move 250 microns during the frequency sweep. If in closed-loop mode, the
        smart stage will return to the current target position automatically.
        It is best to run this command when system is idle and in the forward
        direction for the M3-LS-3.4 Linear Smart Stage.
        """
        if direction == 'forward':
            b0 = 1
        elif direction == 'backward':
            b0 = 0
        else:
            print('unrecognized direction')
            return
        b1 = 1 if incremental else 0
        b2 = 1 if automatic else 0
        D = (b2 << 2) | (b1 << 1) | (b0 << 0)
        XX = '' if frequency_offset is None else '0:02x'.format(int(frequency_offset))
        cmd = "<87 {0} {1}>\r".format(D, XX)
        cmd_bytes = bytes(cmd, 'utf-8')
        self.sock.sendall(cmd_bytes)
        resp = self.sock.recv(1024)


    #################################

    """
    debug commands
    """

    def setCenter(self, x, y, z):
        self.center = [x,y,z]

    def getPosition(self):
        cmd = b"<10>\r"

        self.selectAxis('x')
        self.sock.sendall(cmd)
        time.sleep(0.1)
        resp = self.sock.recv(1024).decode('utf-8').strip('<>\r')
        x = int(resp.split()[2], 16)

        self.selectAxis('y')
        self.sock.sendall(cmd)
        time.sleep(0.1)
        resp = self.sock.recv(1024).decode('utf-8').strip('<>\r')
        y = int(resp.split()[2], 16)

        self.selectAxis('z')
        self.sock.sendall(cmd)
        time.sleep(0.1)
        resp = self.sock.recv(1024).decode('utf-8').strip('<>\r')
        z = int(resp.split()[2], 16)

        return x, y, z

    #################################

    """
    setup commands
    """

    def selectAxis(self, axis):
        if (axis=='x') or (axis=='X'):
            cmd = b"TR<A0 01>\r"
        elif (axis=='y') or (axis=='Y'):
            cmd = b"TR<A0 02>\r"
        elif (axis=='z') or (axis=='Z'):
            cmd = b"TR<A0 03>\r"
        else:
            print('Error: axis not recognized')
            return
        self.sock.sendall(cmd)
        resp = self.sock.recv(1024)

    def querySelectedAxis(self):
        cmd = b"TR<A0>\r"
        self.sock.sendall(cmd)
        resp = self.sock.recv(1024)

    #################################

    """
    per-axis motion commands
    """

    #################################

    """
    higher level motion commands
    """

    def moveToTarget_mm3d(self, x, y, z):
        self.selectAxis('x')
        self.moveToTarget(15000 + 15000*x/7.5)
        self.selectAxis('y')
        self.moveToTarget(15000 + 15000*y/7.5)
        self.selectAxis('z')
        self.moveToTarget(15000 + 15000*z/7.5)

    def center(self):
        self.moveToTarget_mm3d(0, 0, 0)


if __name__ == '__main__':

    import socket
    IP = '10.128.49.22'
    PORT = 23
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((IP, PORT))
    stage = Stage(sock)

    stage.moveTimedOpenLoopSteps('forward', [100, 5, 2])

    stage.close()

