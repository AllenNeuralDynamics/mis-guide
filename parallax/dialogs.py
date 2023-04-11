from PyQt5.QtWidgets import QPushButton, QLabel, QRadioButton, QSpinBox
from PyQt5.QtWidgets import QGridLayout
from PyQt5.QtWidgets import QDialog, QLineEdit, QDialogButtonBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator

import numpy as np
import time
import datetime

from .toggle_switch import ToggleSwitch
from .helper import FONT_BOLD
from .stage_dropdown import StageDropdown
from .calibration_worker import CalibrationWorker as cw

from parallax import __version__ as VERSION


class StageSettingsDialog(QDialog):

    def __init__(self, stage, jog_um_current, cjog_um_current):
        QDialog.__init__(self)
        self.stage = stage

        self.current_label = QLabel('Current Value')
        self.current_label.setAlignment(Qt.AlignCenter)
        self.desired_label = QLabel('Desired Value')
        self.desired_label.setAlignment(Qt.AlignCenter)

        self.speed_label = QLabel('Closed-Loop Speed')
        self.speed_current = QLineEdit(str(self.stage.get_speed()))
        self.speed_current.setEnabled(False)
        self.speed_desired = QLineEdit()

        self.jog_label = QLabel('Jog Increment (um)')
        self.jog_current = QLineEdit(str(jog_um_current))
        self.jog_current.setEnabled(False)
        self.jog_desired = QLineEdit()

        self.cjog_label = QLabel('Control-Jog Increment (um)')
        self.cjog_current = QLineEdit(str(cjog_um_current))
        self.cjog_current.setEnabled(False)
        self.cjog_desired = QLineEdit()

        self.dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.dialog_buttons.accepted.connect(self.accept)
        self.dialog_buttons.rejected.connect(self.reject)

        self.freqcal_button = QPushButton('Calibrate PID Frequency')
        self.freqcal_button.clicked.connect(self.calibrate_frequency)

        layout = QGridLayout()
        layout.addWidget(self.current_label, 0,1, 1,1)
        layout.addWidget(self.desired_label, 0,2, 1,1)
        layout.addWidget(self.speed_label, 1,0, 1,1)
        layout.addWidget(self.speed_current, 1,1, 1,1)
        layout.addWidget(self.speed_desired, 1,2, 1,1)
        layout.addWidget(self.jog_label, 2,0, 1,1)
        layout.addWidget(self.jog_current, 2,1, 1,1)
        layout.addWidget(self.jog_desired, 2,2, 1,1)
        layout.addWidget(self.cjog_label, 3,0, 1,1)
        layout.addWidget(self.cjog_current, 3,1, 1,1)
        layout.addWidget(self.cjog_desired, 3,2, 1,1)
        layout.addWidget(self.dialog_buttons, 4,0, 1,3)
        layout.addWidget(self.freqcal_button, 5,0, 1,3)
        self.setLayout(layout)

    def calibrate_frequency(self):
        self.stage.calibrate_frequency()

    def speed_changed(self):
        dtext = self.speed_desired.text()
        ctext = self.speed_current.text()
        return bool(dtext) and (dtext != ctext)

    def get_speed(self):
        return int(self.speed_desired.text())

    def jog_changed(self):
        dtext = self.jog_desired.text()
        ctext = self.jog_current.text()
        return bool(dtext) and (dtext != ctext)

    def get_jog_um(self):
        return float(self.jog_desired.text())

    def cjog_changed(self):
        dtext = self.cjog_desired.text()
        ctext = self.cjog_current.text()
        return bool(dtext) and (dtext != ctext)

    def get_cjog_um(self):
        return float(self.cjog_desired.text())


class CalibrationDialog(QDialog):

    def __init__(self, model, parent=None):
        QDialog.__init__(self, parent)
        self.model = model

        self.stage_label = QLabel('Select a Stage:')
        self.stage_label.setAlignment(Qt.AlignCenter)
        self.stage_label.setFont(FONT_BOLD)

        self.stage_dropdown = StageDropdown(self.model)
        self.stage_dropdown.activated.connect(self.update_status)

        self.resolution_label = QLabel('Resolution:')
        self.resolution_label.setAlignment(Qt.AlignCenter)
        self.resolution_box = QSpinBox()
        self.resolution_box.setMinimum(2)
        self.resolution_box.setValue(cw.RESOLUTION_DEFAULT)

        self.extent_label = QLabel('Extent (um):')
        self.extent_label.setAlignment(Qt.AlignCenter)
        self.extent_edit = QLineEdit(str(cw.EXTENT_UM_DEFAULT))

        self.name_label = QLabel('Name')
        ts = time.time()
        dt = datetime.datetime.fromtimestamp(ts)
        cal_default_name = 'cal_%04d%02d%02d-%02d%02d%02d' % (dt.year,
                                        dt.month, dt.day, dt.hour, dt.minute, dt.second)
        self.name_edit = QLineEdit(cal_default_name)

        self.go_button = QPushButton('Start Calibration Routine')
        self.go_button.setEnabled(False)
        self.go_button.clicked.connect(self.go)

        layout = QGridLayout()
        layout.addWidget(self.stage_label, 0,0, 1,1)
        layout.addWidget(self.stage_dropdown, 0,1, 1,1)
        layout.addWidget(self.resolution_label, 1,0, 1,1)
        layout.addWidget(self.resolution_box, 1,1, 1,1)
        layout.addWidget(self.extent_label, 2,0, 1,1)
        layout.addWidget(self.extent_edit, 2,1, 1,1)
        layout.addWidget(self.name_label, 3,0, 1,1)
        layout.addWidget(self.name_edit, 3,1, 1,1)
        layout.addWidget(self.go_button, 4,0, 1,2)
        self.setLayout(layout)

        self.setWindowTitle("Calibration Routine Parameters")
        self.setMinimumWidth(300)

    def get_stage(self):
        ip = self.stage_dropdown.currentText()
        stage = self.model.stages[ip]
        return stage

    def get_resolution(self):
        return self.resolution_box.value()

    def get_extent(self):
        return float(self.extent_edit.text())

    def get_name(self):
        return self.name_edit.text()

    def go(self):
        self.accept()

    def handle_radio(self, button):
        print('TODO handleRadio')

    def update_status(self):
        if self.stage_dropdown.is_selected():
            self.go_button.setEnabled(True)


class TargetDialog(QDialog):

    def __init__(self, model):
        QDialog.__init__(self)
        self.model = model

        self.last_button = QPushButton('Last Reconstructed Point')
        self.last_button.clicked.connect(self.populate_last)
        if self.model.obj_point_last is None:
            self.last_button.setEnabled(False)

        self.random_button = QPushButton('Random Point')
        self.random_button.clicked.connect(self.populate_random)

        self.xlabel = QLabel('X = ')
        self.xlabel.setAlignment(Qt.AlignCenter)
        self.ylabel = QLabel('Y = ')
        self.ylabel.setAlignment(Qt.AlignCenter)
        self.zlabel = QLabel('Z = ')
        self.zlabel.setAlignment(Qt.AlignCenter)

        self.xedit = QLineEdit()
        self.yedit = QLineEdit()
        self.zedit = QLineEdit()

        self.validator = QDoubleValidator(-15000,15000,-1)
        self.validator.setNotation(QDoubleValidator.StandardNotation)
        self.xedit.setValidator(self.validator)
        self.yedit.setValidator(self.validator)
        self.zedit.setValidator(self.validator)

        self.xedit.textChanged.connect(self.validate)
        self.yedit.textChanged.connect(self.validate)
        self.zedit.textChanged.connect(self.validate)

        self.info_label = QLabel('(units are microns)')
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setFont(FONT_BOLD)

        self.cancel_button = QPushButton('Cancel')
        self.cancel_button.clicked.connect(self.reject)

        self.ok_button = QPushButton('Move')
        self.ok_button.setFont(FONT_BOLD)
        self.ok_button.setEnabled(False)
        self.ok_button.clicked.connect(self.accept)

        self.xedit.returnPressed.connect(self.ok_button.animateClick)
        self.yedit.returnPressed.connect(self.ok_button.animateClick)
        self.zedit.returnPressed.connect(self.ok_button.animateClick)

        ####

        layout = QGridLayout()
        layout.addWidget(self.last_button, 0,0, 1,2)
        layout.addWidget(self.random_button, 1,0, 1,2)
        layout.addWidget(self.xlabel, 3,0)
        layout.addWidget(self.ylabel, 4,0)
        layout.addWidget(self.zlabel, 5,0)
        layout.addWidget(self.xedit, 3,1)
        layout.addWidget(self.yedit, 4,1)
        layout.addWidget(self.zedit, 5,1)
        layout.addWidget(self.info_label, 6,0, 1,2)
        layout.addWidget(self.cancel_button, 7,0, 1,1)
        layout.addWidget(self.ok_button, 7,1, 1,1)
        self.setLayout(layout)
        self.setWindowTitle('Set Target Coordinates')

    def validate(self):
        valid =     self.xedit.hasAcceptableInput() \
                and self.yedit.hasAcceptableInput() \
                and self.zedit.hasAcceptableInput()
        self.ok_button.setEnabled(valid)

    def populate_last(self):
        self.xedit.setText('{0:.2f}'.format(self.model.obj_point_last[0]))
        self.yedit.setText('{0:.2f}'.format(self.model.obj_point_last[1]))
        self.zedit.setText('{0:.2f}'.format(self.model.obj_point_last[2]))

    def populate_random(self):
        self.xedit.setText('{0:.2f}'.format(np.random.uniform(-2000, 2000)))
        self.yedit.setText('{0:.2f}'.format(np.random.uniform(-2000, 2000)))
        self.zedit.setText('{0:.2f}'.format(np.random.uniform(-2000, 2000)))

    def get_params(self):
        params = {}
        params['x'] = float(self.xedit.text())
        params['y'] = float(self.yedit.text())
        params['z'] = float(self.zedit.text())
        return params


class CsvDialog(QDialog):

    def __init__(self, model, parent=None):
        QDialog.__init__(self, parent)
        self.model = model

        self.last_label = QLabel('Last Reconstructed Point:')
        self.last_label.setAlignment(Qt.AlignCenter)

        if self.model.objPoint_last is None:
            x,y,z = 1,2,3
        else:
            x,y,z = self.model.objPoint_last
        self.last_coords_label = QLabel('[{0:.2f}, {1:.2f}, {2:.2f}]'.format(x, y, z))
        self.last_coords_label.setAlignment(Qt.AlignCenter)

        self.lab_coords_label = QLabel('Lab Coordinates:')
        self.lab_coords_label.setAlignment(Qt.AlignCenter)

        self.xlabel = QLabel('X = ')
        self.xlabel.setAlignment(Qt.AlignCenter)
        self.ylabel = QLabel('Y = ')
        self.ylabel.setAlignment(Qt.AlignCenter)
        self.zlabel = QLabel('Z = ')
        self.zlabel.setAlignment(Qt.AlignCenter)
        validator = QDoubleValidator(-15000,15000,-1)
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.xedit = QLineEdit()
        self.xedit.setValidator(validator)
        self.yedit = QLineEdit()
        self.yedit.setValidator(validator)
        self.zedit = QLineEdit()
        self.zedit.setValidator(validator)

        self.info_label = QLabel('(units are microns)')
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setFont(FONT_BOLD)


        self.dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.dialog_buttons.accepted.connect(self.accept)
        self.dialog_buttons.rejected.connect(self.reject)

        ####

        layout = QGridLayout()
        layout.addWidget(self.last_label, 0,0, 1,2)
        layout.addWidget(self.last_coords_label, 1,0, 1,2)
        layout.addWidget(self.lab_coords_label, 2,0, 1,2)
        layout.addWidget(self.xlabel, 3,0)
        layout.addWidget(self.ylabel, 4,0)
        layout.addWidget(self.zlabel, 5,0)
        layout.addWidget(self.xedit, 3,1)
        layout.addWidget(self.yedit, 4,1)
        layout.addWidget(self.zedit, 5,1)
        layout.addWidget(self.info_label, 6,0, 1,2)
        layout.addWidget(self.dialog_buttons, 7,0, 1,2)
        self.setLayout(layout)
        self.setWindowTitle('Set Target Coordinates')

    def get_params(self):
        params = {}
        params['x'] = float(self.xedit.text())
        params['y'] = float(self.yedit.text())
        params['z'] = float(self.zedit.text())
        return params


class AboutDialog(QDialog):

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)

        self.main_label = QLabel('Parallax')
        self.main_label.setAlignment(Qt.AlignCenter)
        self.main_label.setFont(FONT_BOLD)
        self.version_label = QLabel('version %s' % VERSION)
        self.version_label.setAlignment(Qt.AlignCenter)
        self.repo_label = QLabel('<a href="https://github.com/AllenNeuralDynamics/parallax">'
                                    'github.com/AllenNeuralDynamics/parallax</a>')
        self.repo_label.setOpenExternalLinks(True)

        layout = QGridLayout()
        layout.addWidget(self.main_label)
        layout.addWidget(self.version_label)
        layout.addWidget(self.repo_label)
        self.setLayout(layout)
        self.setWindowTitle('About')

    def get_params(self):
        x = float(self.xedit.text())
        y = float(self.yedit.text())
        z = float(self.zedit.text())
        return x,y,z
