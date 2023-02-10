import time, queue, threading
import numpy as np
import coorx
from newscale.multistage import USBXYZStage, PoEXYZStage
from newscale.interfaces import USBInterface, NewScaleSerial
from .mock_sim import MockSim


def list_stages():
    stages = []
    stages.extend(NewScaleStage.scan_for_stages())
    if len(stages) == 0:
        tr1 = coorx.AffineTransform(dims=(3, 3))
        tr1.rotate(130, (1, 0, 0))
        tr1.rotate(30, (0, 0, 1))
        tr2 = tr1.copy()
        tr2.rotate(60, (0, 0, 1))

        stages.extend([
            MockStage(transform=tr1), 
            MockStage(transform=tr2),
        ])
    return stages


def close_stages():
    NewScaleStage.close_stages()
    MockStage.close_stages()


class NewScaleStage:

    stages = {}

    @classmethod
    def scan_for_stages(cls):
        instances = NewScaleSerial.get_instances()
        stages = []
        for serial in instances:
            if serial not in cls.stages:
                cls.stages[serial] = NewScaleStage(serial=serial)
            stages.append(cls.stages[serial])
        return stages

    @classmethod
    def close_stages(cls):
        for stage in cls.stages.values():
            stage.close()

    def __init__(self, ip=None, serial=None):
        super().__init__()
        if ip is not None:
            self.ip = ip
            self.name = ip
            self.device = PoEXYZStage(ip)
        elif serial is not None:
            self.serial = serial
            self.name = serial.get_serial_number()
            self.device = USBXYZStage(usb_interface=USBInterface(serial))

        self.initialize()

    def close(self):
        pass

    def calibrate_frequency(self):
        self.device.calibrate_all()

    def initialize(self):
        self.origin = [7500,7500,7500]

    def get_name(self):
        return self.name

    def set_origin(self, x, y, z):
        self.origin = [x,y,z]

    def get_origin(self):
        return self.origin

    def get_position(self, relative=False):
        pos = self.device.get_position('x', 'y', 'z')
        x,y,z = pos['x'], pos['y'], pos['z']
        if relative:
            x -= self.origin[0]
            y -= self.origin[1]
            z -= self.origin[2]
        return x,y,z

    def move_to_target_1d(self, axis, position, relative=False):
        if axis == 'x':
            self.device.move_absolute(x=position)
        elif axis == 'y':
            self.device.move_absolute(y=position)
        elif axis == 'z':
            self.device.move_absolute(z=position)

    def move_to_target_3d(self, x, y, z, relative=False, safe=True):
        # TODO implement safe parameter
        if relative:
            xo,yo,zo = self.get_origin()
            x += xo
            y += yo
            z += zo
        self.device.move_absolute(x=x, y=y, z=z)

    def move_distance_1d(self, axis, distance):
        if axis == 'x':
            self.device.move_relative(x=distance)
        elif axis == 'y':
            self.device.move_relative(y=distance)
        elif axis == 'z':
            self.device.move_relative(z=distance)

    def move_distance_3d(self, x, y, z):
        self.device.move_relative(x=x, y=y, z=z)

    def get_speed(self):
        d = self.device.get_closed_loop_speed_and_accel('x')
        speed = d['x'][0]
        return speed

    def set_speed(self, speed):
        accel = self.get_accel()
        self.device.set_closed_loop_speed_and_accel(global_setting=(speed, accel))

    def get_accel(self):
        d = self.device.get_closed_loop_speed_and_accel('x')
        accel = d['x'][1]
        return accel

    def halt(self):
        pass


class MockStage:

    n_mock_stages = 0

    def __init__(self, transform):
        self.transform = transform
        self.speed = 1000  # um/s
        self.accel = 5000  # um/s^2
        self.pos = np.array([0, 0, 0])
        self.name = f"mock_stage_{MockStage.n_mock_stages}"
        MockStage.n_mock_stages += 1

        self.move_callbacks = []

        self.move_queue = queue.Queue()
        self.move_thread = threading.Thread(target=self.thread_loop, daemon=True)
        self.move_thread.start()

        self.sim = MockSim.instance()
        self.sim.add_stage(self)

    def get_origin(self):
        return [0, 0, 0]

    @classmethod
    def close_stages(self):
        pass

    def get_name(self):
        return self.name

    def get_speed(self):
        return self.speed

    def set_speed(self, speed):
        self.speed = speed

    def get_accel(self):
        return self.accel

    def get_position(self):
        return self.pos.copy()

    def move_to_target_3d(self, x, y, z):
        move_cmd = {'pos': np.array([x, y, z]), 'speed': self.speed, 'accel': self.accel, 'finished': False, 'interrupted': False}
        self.move_queue.put(move_cmd)

    def move_distance_1d(self, axis, distance):
        ax_ind = 'xyz'.index(axis)
        pos = self.get_position()
        pos[ax_ind] += distance
        return self.move_to_target_3d(*pos)

    def thread_loop(self):
        current_move = None
        while True:
            try:
                next_move = self.move_queue.get(block=False)                
            except queue.Empty:
                next_move = None
    
            if next_move is not None:
                if current_move is not None:
                    current_move['interrupted'] = True
                    current_move['finished'] = True
                current_move = next_move
                last_update = time.perf_counter()

            if current_move is not None:
                now = time.perf_counter()
                dt = now = last_update
                last_update = now

                pos = self.get_position()
                target = current_move['pos']
                dx = target - pos
                dist_to_go = np.linalg.norm(dx)
                max_dist_per_step = current_move['speed'] * dt
                if dist_to_go > max_dist_per_step:
                    # take a step
                    direction = dx / dist_to_go
                    dist_this_step = min(dist_to_go, max_dist_per_step)
                    step = direction * dist_this_step
                    self.pos = pos + step
                else:
                    self.pos = target.copy()
                    current_move['interrupted'] = False
                    current_move['finished'] = True
                    current_move = None
                
                for cb in self.move_callbacks[:]:
                    cb(self)

            time.sleep(10e-3)

    def add_move_callback(self, cb):
        self.move_callbacks.append(cb)

    def orientation(self):
        p1 = self.transform.map([0, 0, 0])
        p2 = self.transform.map([0, 0, 1])
        axis = p1 - p2
        r = np.linalg.norm(axis[:2])
        phi = np.arctan2(r, axis[2]) * 180 / np.pi
        theta = np.arctan2(axis[1], axis[0]) * 180 / np.pi
        return theta, phi

    def get_tip_position(self):
        return self.transform.map(self.get_position())
