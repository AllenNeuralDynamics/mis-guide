import cv2
import numpy as np
import time
import logging

from PyQt5.QtCore import pyqtSignal, Qt, QObject, QThread
from .reticle_detection import ReticleDetection
from .mask_generator import MaskGenerator
from .reticle_detection_coords_interests import ReticleDetectCoordsInterest
# Set logger name
logger = logging.getLogger(__name__)
# Set the logging level for PyQt5.uic.uiparser/properties to WARNING, to ignore DEBUG messages
logging.getLogger("PyQt5.uic.uiparser").setLevel(logging.DEBUG)
logging.getLogger("PyQt5.uic.properties").setLevel(logging.DEBUG)

class ReticleDetectManager(QObject):

    name = "None"
    frame_processed = pyqtSignal(object)

    class Worker(QObject):
        finished = pyqtSignal()
        frame_processed = pyqtSignal(object)
        found_coords = pyqtSignal(str, tuple)

        def __init__(self, name):
            QObject.__init__(self)
            self.name = name
            self.running = False
            self.is_detection_on = False
            self.new = False
            self.frame = None
            self.IMG_SIZE_ORIGINAL = (4000, 3000) # TODO

            self.mask_detect = MaskGenerator()
            self.reticleDetector = ReticleDetection(self.IMG_SIZE_ORIGINAL, self.mask_detect)
            self.coordsInterests = ReticleDetectCoordsInterest()
                
        def update_frame(self, frame):
            self.frame = frame
            self.new = True

        def draw(self, frame, x_axis_coords, y_axis_coords):
            if x_axis_coords is None or y_axis_coords is None:
                return frame
            
            for pixel in x_axis_coords:
                pt = tuple(pixel)
                cv2.circle(frame, pt, 7, (255, 0, 0), -1)
            for pixel in y_axis_coords:
                pt = tuple(pixel)
                cv2.circle(frame, pt, 7, (0, 255, 0), -1)
            
            print(x_axis_coords[0], y_axis_coords[0])
            return frame
        
        def process(self, frame):
            #cv2.circle(frame, (2000,1500), 10, (255, 0, 0), -1)
            ret, frame, _, inliner_lines_pixels = self.reticleDetector.get_coords(frame)
            if ret:
                ret, x_axis_coords, y_axis_coords = self.coordsInterests.get_coords_interest(inliner_lines_pixels)
            if ret:
                frame = self.draw(frame, x_axis_coords, y_axis_coords)
                self.found_coords.emit()
            return frame

        def stop_running(self):
            self.running = False

        def start_running(self):
            self.running = True

        def start_detection(self):
            self.is_detection_on = True

        def stop_detection(self):
            self.is_detection_on = False

        def run(self):
            print("reticle detection run ", self.running)
            while self.running:
                if self.new:
                    self.frame = self.process(self.frame)
                self.frame_processed.emit(self.frame)
                self.new = False
                time.sleep(0.001)
            print("reticle detection run finished ", self.running)
            self.finished.emit()

    def __init__(self):
        super().__init__()
        self.worker = None
        self.thread = None
        self.init_thread()
    
    def init_thread(self):
        #if self.thread is not None:
        #    self.clean()  # Clean up existing thread and worker before reinitializing
    
        self.thread = QThread()
        self.worker = self.Worker(self.name)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.frame_processed.connect(self.frame_processed)
        self.worker.found_coords.connect(self.found_coords)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

    def process(self, frame):
        if self.worker is not None:
            self.worker.update_frame(frame)

    def found_coords(self):
        pass
    
    def start(self):
        self.init_thread()  # Reinitialize and start the worker and thread
        self.worker.start_running()
        self.thread.start()
    
    def stop(self):
        if self.worker is not None:
            self.worker.stop_running()

    def clean(self):
        if self.worker is not None:
            self.worker.stop_running()
        if self.thread is not None:
            self.thread.quit()
            self.thread.wait()

    def __del__(self):
        self.clean()