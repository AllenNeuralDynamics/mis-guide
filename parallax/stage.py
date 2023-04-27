import queue
import time

from PyQt5.QtCore import QObject, pyqtSignal, QThread

from newscale.multistage import USBXYZStage, PoEXYZStage
from newscale.interfaces import USBInterface

from . import io_commands as io

TIME_SLEEP = 0.03


class IOWorker(QObject):
    finished = pyqtSignal()

    def __init__(self, device):
        QObject.__init__(self)
        self.device = device
        self.qslow = queue.Queue()
        self.qfast = queue.Queue()
        self.halt_requested = False

    def run(self):
        while True:
            while not self.qslow.empty() and not self.halt_requested:
                cmd = self.qslow.get()
                cmd.execute()
                if not cmd.blocking:
                    while not cmd.done() and not self.halt_requested:
                        while not self.qfast.empty() and not self.halt_requested:
                            fc = self.qfast.get()
                            fc.execute()
                        time.sleep(TIME_SLEEP)
            while not self.qfast.empty() and not self.halt_requested:
                fc = self.qfast.get()
                fc.execute()
            if self.halt_requested:
                self.device.halt()
                self.clear_queues()
                self.halt_requested = False
            time.sleep(TIME_SLEEP)
        self.finished.emit()

    def queue_command(self, cmd):
        if cmd.fast:
            self.qfast.put(cmd)
        else:
            self.qslow.put(cmd)

    def clear_queues(self):
        while not self.qslow.empty():
            cmd = self.qslow.get()
        while not self.qfast.empty():
            gcmd = self.qfast.get()

    def halt(self):
        self.halt_requested = True


class Stage:

    def __init__(self, ip=None, serial=None):

        if ip is not None:
            self.ip = ip
            self.name = ip
            self.device = PoEXYZStage(ip)
        elif serial is not None:
            self.serial = serial
            self.name = serial.get_serial_number()
            self.device = USBXYZStage(usb_interface=USBInterface(serial))

        self.thread = QThread()
        self.worker = IOWorker(self.device)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def get_name(self):
        return self.name

    def calibrate_frequency(self):
        cmd = io.CalibrateFrequencyCommand(self.device)
        self.worker.queue_command(cmd)

    def get_position(self):
        cmd = io.GetPositionCommand(self.device)
        self.worker.queue_command(cmd)
        while not cmd.done():
            time.sleep(TIME_SLEEP)
        return cmd.result()

    def get_speed(self):
        cmd = io.GetSpeedCommand(self.device)
        self.worker.queue_command(cmd)
        while not cmd.done():
            time.sleep(TIME_SLEEP)
        return cmd.result() # vx, vy, vz

    def set_speed(self, speed):
        cmd = io.SetSpeedCommand(self.device, speed)
        self.worker.queue_command(cmd)

    def move_absolute_3d(self, x, y, z, safe=False):
        pos = (x,y,z)
        cmd = io.MoveAbsolute3dCommand(self.device, pos)
        self.worker.queue_command(cmd)

    def move_absolute_1d(self, axis, position):
        cmd = io.MoveAbsolute1dCommand(self.device, axis, position)
        self.worker.queue_command(cmd)

    def move_relative_3d(self, dx, dy, dz):
        cmd = io.MoveRelative3dCommand(self.device, (dx,dy,dz))
        self.worker.queue_command(cmd)

    def move_relative_1d(self, axis, distance):
        cmd = io.MoveRelative1dCommand(self.device, axis, distance)
        self.worker.queue_command(cmd)

    def halt(self):
        self.worker.halt()

