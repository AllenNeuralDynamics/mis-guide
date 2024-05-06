"""
NoFilter serves as a pass-through component in a frame processing pipeline, 
employing a worker-thread model to asynchronously handle frames without modification, 
facilitating integration and optional processing steps.
"""

import logging
import time

import cv2
from PyQt5.QtCore import QObject, QThread, pyqtSignal

# Set logger name
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class AxisFilter(QObject):
    """Class representing no filter."""

    name = "None"
    frame_processed = pyqtSignal(object)

    class Worker(QObject):
        """Worker class for processing frames in a separate thread."""

        finished = pyqtSignal()
        frame_processed = pyqtSignal(object)

        def __init__(self, name):
            """Initialize the worker object."""
            QObject.__init__(self)
            self.name = name
            self.running = False
            self.new = False
            self.frame = None

        def update_frame(self, frame):
            """Update the frame to be processed.

            Args:
                frame: The frame to be processed.
            """
            self.frame = frame
            self.new = True

        def process(self, frame):
            """Process nothing (no filter) and emit the frame_processed signal.

            Args:
                frame: The frame to be processed.
            """
            cv2.circle(frame, (2000,1500), 10, (0, 255, 0), -1) # Test
            self.frame_processed.emit(frame)

        def stop_running(self):
            """Stop the worker from running."""
            self.running = False

        def start_running(self):
            """Start the worker running."""
            self.running = True

        def run(self):
            """Run the worker thread."""
            while self.running:
                if self.new:
                    self.process(self.frame)
                    self.new = False
                time.sleep(0.001)
            self.finished.emit()
            logger.debug(f"thread finished {self.name}")

        def set_name(self, name):
            """Set name as camera serial number."""
            self.name = name

    def __init__(self, camera_name):
        """Initialize the filter object."""
        logger.debug("Init axis filter manager")
        super().__init__()
        self.worker = None
        self.name = camera_name
        self.thread = None
        self.thread = None

    def init_thread(self):
        """Initialize or reinitialize the worker and thread"""
        if self.thread is not None:
            self.clean()  # Clean up existing thread and worker before reinitializing 
        self.thread = QThread()
        self.worker = self.Worker(self.name)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.destroyed.connect(self.onThreadDestroyed)
        self.threadDeleted = False

        #self.worker.frame_processed.connect(self.frame_processed)
        self.worker.frame_processed.connect(self.frame_processed.emit)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.thread.deleteLater)
        logger.debug(f"init camera name: {self.name}")

    def process(self, frame):
        """Process the frame using the worker.

        Args:
            frame: The frame to be processed.
        """
        if self.worker is not None:
            self.worker.update_frame(frame)

    def start(self):
        """Start the filter by reinitializing and starting the worker and thread."""
        self.init_thread()  # Reinitialize and start the worker and thread
        self.worker.start_running()
        self.thread.start()
        logger.debug(f"thread started {self.name}")

    def stop(self):
        """Stop the filter by stopping the worker."""
        if self.worker is not None:
            self.worker.stop_running()

    def set_name(self, camera_name):
        """Set camera name."""
        self.name = camera_name
        if self.worker is not None:
            self.worker.set_name(self.name)
        logger.debug(f"camera name: {self.name}")

    def clean(self):
        """Safely clean up the reticle detection manager."""
        logger.debug("Cleaning the thread")
        if self.worker is not None:
            self.worker.stop_running()  # Signal the worker to stop
        if not self.threadDeleted and self.thread.isRunning():
            self.thread.quit()  # Ask the thread to quit
            self.thread.wait()  # Wait for the thread to finish
        self.thread = None  # Clear the reference to the thread
        self.worker = None  # Clear the reference to the worker

    def onThreadDestroyed(self):
        """Flag if thread is deleted"""
        self.threadDeleted = True

    def __del__(self):
        """Destructor for the filter object."""
        self.clean()