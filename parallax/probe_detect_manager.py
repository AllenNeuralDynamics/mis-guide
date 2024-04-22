"""
ProbeDetectManager coordinates probe detection in images, leveraging PyQt threading 
and signals for real-time processing. It handles frame updates, detection, 
and result communication, utilizing components like MaskGenerator and ProbeDetector.
"""
from PyQt5.QtCore import pyqtSignal, QObject, QThread
from .mask_generator import MaskGenerator
from .reticle_detection import ReticleDetection
from .probe_detector import ProbeDetector
from .curr_prev_cmp_processor import CurrPrevCmpProcessor
from .curr_bg_cmp_processor import CurrBgCmpProcessor
import cv2
import time
import logging

# Set logger name
logger = logging.getLogger(__name__)
# Set the logging level for PyQt5.uic.uiparser/properties to WARNING, to ignore DEBUG messages
logging.getLogger("PyQt5.uic.uiparser").setLevel(logging.WARNING)
logging.getLogger("PyQt5.uic.properties").setLevel(logging.WARNING)

class ProbeDetectManager(QObject):
    """Manager class for probe detection."""
    name = "None"
    frame_processed = pyqtSignal(object)
    found_coords = pyqtSignal(str, str, tuple, tuple)

    class Worker(QObject):
        """Worker class for probe detection."""
        finished = pyqtSignal()
        frame_processed = pyqtSignal(object)
        found_coords = pyqtSignal(str, str, tuple)

        def __init__(self, name, model):
            """ Initialize Worker object """
            QObject.__init__(self)
            self.model = model
            self.name = name
            self.running = False
            self.is_detection_on = False
            self.new = False
            self.frame = None
            self.reticle_coords = self.model.get_coords_axis(self.name)

            # TODO move to model structure
            self.prev_img = None
            self.reticle_zone = None
            self.is_probe_updated = True
            self.probes = {}
            self.sn = None

            self.IMG_SIZE = (1000, 750)
            self.IMG_SIZE_ORIGINAL = (4000, 3000) # TODO
            self.CROP_INIT = 50
            self.mask_detect = MaskGenerator()

        def update_sn(self, sn):
            """Update the serial number and initialize probe detectors.

            Args:
                sn (str): Serial number.
            """
            if sn not in self.probes.keys():
                self.sn = sn
                self.probeDetect = ProbeDetector(self.sn, self.IMG_SIZE)
                self.currPrevCmpProcess = CurrPrevCmpProcessor(self.probeDetect, self.IMG_SIZE_ORIGINAL, self.IMG_SIZE)
                self.currBgCmpProcess = CurrBgCmpProcessor(self.probeDetect, self.IMG_SIZE_ORIGINAL, self.IMG_SIZE)
                self.probes[self.sn] = {'probeDetector': self.probeDetect,
                              'currPrevCmpProcess': self.currPrevCmpProcess,
                              'currBgCmpProcess': self.currBgCmpProcess}
            else:
                if sn != self.sn:
                    self.sn = sn
                    self.probeDetect = self.probes[self.sn]['probeDetector']
                    self.currPrevCmpProcess = self.probes[self.sn]['currPrevCmpProcess']
                    self.currBgCmpProcess = self.probes[self.sn]['currBgCmpProcess']
                else: 
                    pass
                
        def update_frame(self, frame, timestamp):
            """Update the frame and timestamp.

            Args:
                frame (numpy.ndarray): Input frame.
                timestamp (str): Timestamp of the frame.
            """
            self.frame = frame
            self.new = True
            self.timestamp = timestamp

        def process(self, frame, timestamp):
            """ Process the frame for probe detection.
            1. First run currPrevCmpProcess 
            2. If it fails on 1, run currBgCmpProcess

            Args:
                frame (numpy.ndarray): Input frame.
                timestamp (str): Timestamp of the frame.

            Returns:
                tuple: Processed frame and timestamp.
            """
            if frame.ndim > 2:
                gray_img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray_img = frame
        
            resized_img = cv2.resize(gray_img, self.IMG_SIZE)
            self.curr_img = cv2.GaussianBlur(resized_img, (9, 9), 0)
            mask = self.mask_detect.process(resized_img)                # Generate Mask

            if self.mask_detect.is_reticle_exist and self.reticle_zone is None:
                reticle = ReticleDetection(self.IMG_SIZE, self.mask_detect, self.name)
                self.reticle_zone = reticle.get_reticle_zone(frame)     # Generate X and Y Coordinates zone
                self.currBgCmpProcess.update_reticle_zone(self.reticle_zone)
            
            if self.prev_img is not None:
                if self.probeDetect.angle is None:  # Detecting probe for the first time
                    ret = self.currPrevCmpProcess.first_cmp(self.curr_img, self.prev_img, mask, gray_img)
                    if ret is False:
                        ret = self.currBgCmpProcess.first_cmp(self.curr_img, mask, gray_img)
                    if ret:
                        logger.debug("First detect")
                        logger.debug(f"angle: {self.probeDetect.angle}, tip: {self.probeDetect.probe_tip}, \
                                                                base: {self.probeDetect.probe_base}")
                else:                               # Tracking for the known probe
                    ret = self.currPrevCmpProcess.update_cmp(self.curr_img, self.prev_img, mask, gray_img)
                    if ret is False:
                        ret = self.currBgCmpProcess.update_cmp(self.curr_img, mask, gray_img)
            
                    if ret:     # Found
                        self.found_coords.emit(timestamp, self.sn, self.probeDetect.probe_tip_org)
                        cv2.circle(frame, self.probeDetect.probe_tip_org, 5, (255, 255, 0), -1)

                if ret:
                    self.prev_img = self.curr_img
            else:
                self.prev_img = self.curr_img

            return frame, timestamp

        def stop_running(self):
            """Stop the worker from running."""
            self.running = False

        def start_running(self):
            """Start the worker running."""
            self.running = True

        def start_detection(self):
            """Start the probe detection."""
            self.is_detection_on = True

        def stop_detection(self):
            """Stop the probe detection."""
            self.is_detection_on = False

        def process_draw_reticle(self, frame):
            if self.reticle_coords is not None:
                for coords in self.reticle_coords:
                    for x, y in coords:
                        cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)
            return frame

        def run(self):
            """Run the worker thread."""
            print("probe_detect_manager running ")
            while self.running:
                if self.new:
                    if self.is_detection_on:
                        self.frame, self.timestamp = self.process(self.frame, self.timestamp)
                    self.frame = self.process_draw_reticle(self.frame)
                    self.frame_processed.emit(self.frame)
                    self.new = False
                time.sleep(0.001)
            print("probe_detect_manager running done")
            self.finished.emit()

    def __init__(self, model, camera_name):
        """ Initialize ProbeDetectManager object """
        super().__init__()
        self.model = model
        self.worker = None
        self.name = camera_name
        self.thread = None
        self.init_thread()

    def init_thread(self):
        """Initialize the worker thread."""
        self.thread = QThread()
        self.worker = self.Worker(self.name, self.model)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.frame_processed.connect(self.frame_processed)
        self.worker.found_coords.connect(self.found_coords_print)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

    def process(self, frame, timestamp):
        """Process the frame using the worker.

        Args:
            frame (numpy.ndarray): Input frame.
            timestamp (str): Timestamp of the frame.
        """
        if self.worker is not None:
            self.worker.update_frame(frame, timestamp)
    
    def found_coords_print(self, timestamp, sn, pixel_coords):
        """Emit the found coordinates signal.

        Args:
            timestamp (str): Timestamp of the frame.
            sn (str): Serial number.
            pixel_coords (tuple): Pixel coordinates of the probe tip.
        """
        moving_stage = self.model.get_stage(sn)
        if moving_stage is not None:
            stage_info = (moving_stage.stage_x, moving_stage.stage_y, moving_stage.stage_z)
        #print(timestamp, sn, stage_info, pixel_coords)
        self.found_coords.emit(timestamp, sn, stage_info, pixel_coords)

    def start(self):
        """Start the probe detection manager."""
        self.init_thread()  # Reinitialize and start the worker and thread
        self.worker.start_running()
        self.thread.start()

    def stop(self):
        """Stop the probe detection manager."""
        if self.worker is not None:
            self.worker.stop_running()

    def start_detection(self, sn):       # Call from stage listener.
        """Start the probe detection for a specific serial number.

        Args:
            sn (str): Serial number.
        """
        if self.worker is not None:
            self.worker.update_sn(sn)
            self.worker.start_detection()
    
    def stop_detection(self, sn):       # Call from stage listener.
        """Stop the probe detection for a specific serial number.

        Args:
            sn (str): Serial number.
        """
        if self.worker is not None:
            self.worker.stop_detection()

    def clean(self):
        """Clean up the probe detection manager."""
        if self.worker is not None:
            self.worker.stop_running()
        if self.thread is not None:
            self.thread.quit()
            self.thread.wait()

    def __del__(self):
        """Destructor for the probe detection manager."""
        self.clean()