from PyQt5.QtWidgets import QPushButton, QLabel, QWidget, QInputDialog
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QFileDialog
from PyQt5.QtCore import pyqtSignal, QTimer, Qt
from PyQt5.QtGui import QIcon

import cv2
import numpy as np
import time
import datetime
import os
import pickle

from . import get_image_file, data_dir
from .screen_widget import ScreenWidget
from .filters import CheckerboardFilter
from .calibration import Calibration, CalibrationMono

CB_ROWS = 19 #number of checkerboard rows.
CB_COLS = 19 #number of checkerboard columns.
WORLD_SCALE = 500 # 500 um per square

#coordinates of squares in the checkerboard world space
OBJPOINTS_CB = np.zeros((CB_ROWS*CB_COLS,3), np.float32)
OBJPOINTS_CB[:,:2] = np.mgrid[0:CB_ROWS,0:CB_COLS].T.reshape(-1,2)
OBJPOINTS_CB = WORLD_SCALE * OBJPOINTS_CB


class CheckerboardToolMono(QWidget):
    msg_posted = pyqtSignal(str)
    cal_generated = pyqtSignal()

    def __init__(self, model):
        QWidget.__init__(self, parent=None)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.model = model

        self.lscreen = ScreenWidget(model=self.model)
        self.grab_button = QPushButton('Grab Corners')
        self.grab_button.clicked.connect(self.grab_corners)
        self.calibrate_button = QPushButton('Calibrate')
        self.calibrate_button.setEnabled(False)
        self.calibrate_button.clicked.connect(self.calibrate)
        self.save_corners_button = QPushButton('Save Corners (None)')
        self.save_corners_button.clicked.connect(self.save_corners)
        self.load_corners_button = QPushButton('Load Corners')
        self.load_corners_button.clicked.connect(self.load_corners)
        self.save_cal_button = QPushButton('Save Calibration')
        self.save_cal_button.setEnabled(False)
        self.save_cal_button.clicked.connect(self.save_cal)

        self.screens_layout = QHBoxLayout()
        self.screens_layout.addWidget(self.lscreen)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.lscreen)
        self.layout.addWidget(self.grab_button)
        self.layout.addWidget(self.calibrate_button)
        self.layout.addWidget(self.save_corners_button)
        self.layout.addWidget(self.load_corners_button)
        self.layout.addWidget(self.save_cal_button)
        self.setLayout(self.layout)

        self.setWindowTitle('Checkerboard Calibration Tool')
        self.setWindowIcon(QIcon(get_image_file('sextant.png')))

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.lscreen.refresh)
        self.refresh_timer.start(250)

        self.opts = []  # object points
        self.lipts = [] # left image points

        self.last_cal = None

    def save_cal(self):
        if (self.last_cal is not None):
            name, ret = QInputDialog.getText(self, 'Calibration Name', 'Name:')
            if ret:
                self.last_cal.set_name(name)
            else:
                return
            self.model.add_calibration(self.last_cal)
            self.cal_generated.emit()
            suggested_filename = os.path.join(data_dir, self.last_cal.name + '.pkl')
            filename = QFileDialog.getSaveFileName(self, 'Save calibration file',
                                                    suggested_filename,
                                                    'Pickle files (*.pkl)')[0]
            if filename:
                with open(filename, 'wb') as f:
                    pickle.dump(self.last_cal, f)
                self.msg_posted.emit('Saved calibration %s to: %s' % (self.last_cal.name, filename))


    def grab_corners(self):
        lfilter = self.lscreen.filter
        if isinstance(lfilter, CheckerboardFilter):
            if (lfilter.worker.corners is not None):
                self.lipts.append(lfilter.worker.corners)
                self.opts.append(OBJPOINTS_CB)
                self.update_gui()

    def update_gui(self):
        self.save_corners_button.setText('Save Corners (%d)' % len(self.opts))
        if len(self.opts) >= 2:
            self.calibrate_button.setEnabled(True)

    def save_corners(self):
        ts = time.time()
        dt = datetime.datetime.fromtimestamp(ts)
        suggested_basename = 'corners_mono_%04d%02d%02d-%02d%02d%02d.npz' % (dt.year,
                                        dt.month, dt.day, dt.hour, dt.minute, dt.second)
        suggested_filename = os.path.join(data_dir, suggested_basename)
        filename = QFileDialog.getSaveFileName(self, 'Save Corners File',
                                                suggested_filename,
                                                'Numpy files (*.npz)')[0]
        if filename:
            np.savez(filename, opts=self.opts, lipts=self.lipts)
            self.msg_posted.emit('Exported corners to %s' % filename)

    def calibrate(self):
        cal = CalibrationMono('checkerCalMono', 'checkerboard') # temp
        opts = np.array(self.opts, dtype=np.float32)
        lipts = np.array(self.lipts, dtype=np.float32).squeeze()
        cal.calibrate(lipts, opts)
        if (self.last_cal is not None):
            dparams = self.calculate_last_change(cal)
            self.msg_posted.emit('Largest fractional change = %.2E' % np.max(np.abs(dparams)))
        self.last_cal = cal
        self.save_cal_button.setEnabled(True)

    def calculate_last_change(self, cal):
        dparams = np.zeros(9)
        dparams[0] = (cal.mtx1[0,0] - self.last_cal.mtx1[0,0]) / self.last_cal.mtx1[0,0] # fx
        dparams[1] = (cal.mtx1[1,1] - self.last_cal.mtx1[1,1]) / self.last_cal.mtx1[1,1] # fy
        dparams[2] = (cal.mtx1[0,2] - self.last_cal.mtx1[0,2]) / self.last_cal.mtx1[0,2] # cx
        dparams[3] = (cal.mtx1[1,2] - self.last_cal.mtx1[1,2]) / self.last_cal.mtx1[1,2] # cy
        dparams[4] = (cal.dist1[0,0] - self.last_cal.dist1[0,0]) / self.last_cal.dist1[0,0] # k1
        dparams[5] = (cal.dist1[0,1] - self.last_cal.dist1[0,1]) / self.last_cal.dist1[0,1] # k2
        dparams[6] = (cal.dist1[0,2] - self.last_cal.dist1[0,2]) / self.last_cal.dist1[0,2] # p1
        dparams[7] = (cal.dist1[0,3] - self.last_cal.dist1[0,3]) / self.last_cal.dist1[0,3] # p2
        dparams[8] = (cal.dist1[0,4] - self.last_cal.dist1[0,4]) / self.last_cal.dist1[0,4] # k3
        return dparams

    def load_corners(self):
        filename = QFileDialog.getOpenFileName(self, 'Load corners file', data_dir,
                                                    'Numpy files (*.npz)')[0]
        corners = np.load(filename)
        self.opts = corners['opts']
        self.lipts = corners['lipts'].squeeze() # temp for legacy file
        self.update_gui()


class CheckerboardToolStereo(QWidget):
    msg_posted = pyqtSignal(str)
    cal_generated = pyqtSignal()

    def __init__(self, model):
        QWidget.__init__(self, parent=None)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.model = model

        self.lscreen = ScreenWidget(model=self.model)
        self.rscreen = ScreenWidget(model=self.model)
        self.save_button = QPushButton('Save Corners')
        self.save_button.clicked.connect(self.save_corners)
        self.export_button = QPushButton('Save Corners (None)')
        self.export_button.clicked.connect(self.exportCorners)
        self.import_button = QPushButton('Load Corners')
        self.import_button.clicked.connect(self.import_corners)
        self.generate_button = QPushButton('Generate Calibration from Corners')
        self.generate_button.clicked.connect(self.generate)

        self.screens_layout = QHBoxLayout()
        self.screens_layout.addWidget(self.lscreen)
        self.screens_layout.addWidget(self.rscreen)

        self.layout = QVBoxLayout()
        self.layout.addLayout(self.screens_layout)
        self.layout.addWidget(self.save_button)
        self.layout.addWidget(self.export_button)
        self.layout.addWidget(self.import_button)
        self.layout.addWidget(self.generate_button)
        self.setLayout(self.layout)

        self.setWindowTitle('Checkerboard Calibration Tool')
        self.setWindowIcon(QIcon(get_image_file('sextant.png')))

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.lscreen.refresh)
        self.refresh_timer.timeout.connect(self.rscreen.refresh)
        self.refresh_timer.start(250)

        self.opts = []  # object points
        self.lipts = [] # left image points
        self.ripts = [] # right image points

    def save_corners(self):
        lfilter = self.lscreen.filter
        rfilter = self.rscreen.filter
        if isinstance(lfilter, CheckerboardFilter) and \
            isinstance(rfilter, CheckerboardFilter):
            lfilter.lock()
            rfilter.lock()
            if (lfilter.worker.corners is not None) and (rfilter.worker.corners is not None):
                self.lipts.append(lfilter.worker.corners)
                self.ripts.append(rfilter.worker.corners)
                self.opts.append(OBJPOINTS_CB)
                self.update_text()
            lfilter.unlock()
            rfilter.unlock()

    def update_text(self):
        self.export_button.setText('Save Corners (%d)' % len(self.opts))

    def exportCorners(self):
        ts = time.time()
        dt = datetime.datetime.fromtimestamp(ts)
        suggested_basename = 'corners_%04d%02d%02d-%02d%02d%02d.npz' % (dt.year,
                                        dt.month, dt.day, dt.hour, dt.minute, dt.second)
        suggested_filename = os.path.join(data_dir, suggested_basename)
        filename = QFileDialog.getSaveFileName(self, 'Save corners',
                                                suggested_filename,
                                                'Numpy files (*.npz)')[0]
        if filename:
            np.savez(filename, opts=self.opts, lipts=self.lipts, ripts=self.ripts)
            self.msg_posted.emit('Exported corners to %s' % filename)

    def generate(self):
        cal = Calibration('checkerCal', 'checkerboard') # temp
        opts = np.array(self.opts, dtype=np.float32)
        lipts = np.array(self.lipts, dtype=np.float32).squeeze()
        ripts = np.array(self.ripts, dtype=np.float32).squeeze()
        cal.calibrate(lipts, ripts, opts)
        self.model.add_calibration(cal)
        self.msg_posted.emit('Added calibration "%s"' % cal.name)
        self.cal_generated.emit()

    def import_corners(self):
        filename = QFileDialog.getOpenFileName(self, 'Load corners file', data_dir,
                                                    'Numpy files (*.npz)')[0]
        corners = np.load(filename)
        self.opts = corners['opts']
        self.lipts = corners['lipts'].squeeze() # temp for legacy file
        self.ripts = corners['ripts'].squeeze() # temp for legacy file
        self.update_text()

