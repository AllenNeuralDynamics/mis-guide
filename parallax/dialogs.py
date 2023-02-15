from PyQt5.QtWidgets import QPushButton, QLabel, QSpinBox
from PyQt5.QtWidgets import QGridLayout
from PyQt5.QtWidgets import QDialog, QLineEdit, QDialogButtonBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator
import pyqtgraph as pg
import numpy as np

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
        layout.addWidget(self.go_button, 4,0, 1,2)
        self.setLayout(layout)

        self.setWindowTitle("Calibration Routine Parameters")
        self.setMinimumWidth(300)

    def get_stage(self):
        return self.stage_dropdown.current_stage()

    def get_resolution(self):
        return self.resolution_box.value()

    def get_extent(self):
        return float(self.extent_edit.text())

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

        self.obj_point = None
        self.last_button = QPushButton('Last Reconstructed Point')
        self.last_button.clicked.connect(self.populate_last)
        if self.model.obj_point_last is None:
            self.last_button.setEnabled(False)

        self.random_button = QPushButton('Random Point')
        self.random_button.clicked.connect(self.populate_random)

        self.relative_label = QLabel('Relative Coordinates')
        self.abs_rel_toggle = ToggleSwitch(thumb_radius=11, track_radius=8)
        self.abs_rel_toggle.setChecked(True)

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

        self.xedit.textEdited.connect(self.input_changed)
        self.yedit.textEdited.connect(self.input_changed)
        self.zedit.textEdited.connect(self.input_changed)
        self.abs_rel_toggle.toggled.connect(self.input_changed)

        self.info_label = QLabel('')
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setFont(FONT_BOLD)
        self.update_info()

        self.dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.dialog_buttons.accepted.connect(self.accept)
        self.dialog_buttons.rejected.connect(self.reject)

        ####

        layout = QGridLayout()
        layout.addWidget(self.last_button, 0,0, 1,2)
        layout.addWidget(self.random_button, 1,0, 1,2)
        layout.addWidget(self.relative_label, 2,0, 1,1)
        layout.addWidget(self.abs_rel_toggle, 2,1, 1,1)
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

    def populate_last(self):
        op = self.model.obj_point_last
        self.xedit.setText('{0:.2f}'.format(op[0]))
        self.yedit.setText('{0:.2f}'.format(op[1]))
        self.zedit.setText('{0:.2f}'.format(op[2]))
        self.abs_rel_toggle.setChecked(False)
        self.obj_point = op
        self.update_info()

    def populate_random(self):
        self.obj_point = None
        self.xedit.setText('{0:.2f}'.format(np.random.uniform(-2000, 2000)))
        self.yedit.setText('{0:.2f}'.format(np.random.uniform(-2000, 2000)))
        self.zedit.setText('{0:.2f}'.format(np.random.uniform(-2000, 2000)))
        self.update_info()

    def get_params(self):
        params = {}
        if self.obj_point is None:
            params['point'] = np.array([float(self.xedit.text()), float(self.yedit.text()), float(self.zedit.text())])
            params['relative'] = self.abs_rel_toggle.isChecked()
        else:
            params['point'] = self.obj_point
            params['relative'] = False
        return params

    def update_info(self):
        info = "(units are μm)"
        if self.obj_point is not None:
            info = f'coord sys: {self.obj_point.system.name}\n{info}'
        self.info_label.setText(info)

    def input_changed(self):
        self.obj_point = None
        self.update_info()


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


class TrainingDataDialog(QDialog):

    def __init__(self, model):
        QDialog.__init__(self)
        self.model = model

        self.setWindowTitle('Training Data Generator')

        self.stage_label = QLabel('Select a Stage:')
        self.stage_label.setAlignment(Qt.AlignCenter)
        self.stage_label.setFont(FONT_BOLD)

        self.stage_dropdown = StageDropdown(self.model)
        self.stage_dropdown.activated.connect(self.update_status)

        self.img_count_label = QLabel('Image Count:')
        self.img_count_label.setAlignment(Qt.AlignCenter)
        self.img_count_box = QSpinBox()
        self.img_count_box.setMinimum(1)
        self.img_count_box.setValue(100)

        self.extent_label = QLabel('Extent:')
        self.extent_label.setAlignment(Qt.AlignCenter)
        self.extent_spin = pg.SpinBox(value=4e-3, suffix='m', siPrefix=True, bounds=[0.1e-3, 20e-3], dec=True, step=0.5, minStep=1e-6, compactHeight=False)

        self.go_button = QPushButton('Start Data Collection')
        self.go_button.setEnabled(False)
        self.go_button.clicked.connect(self.go)

        layout = QGridLayout()
        layout.addWidget(self.stage_label, 0,0, 1,1)
        layout.addWidget(self.stage_dropdown, 0,1, 1,1)
        layout.addWidget(self.img_count_label, 1,0, 1,1)
        layout.addWidget(self.img_count_box, 1,1, 1,1)
        layout.addWidget(self.extent_label, 2,0, 1,1)
        layout.addWidget(self.extent_spin, 2,1, 1,1)
        layout.addWidget(self.go_button, 4,0, 1,2)
        self.setLayout(layout)

        self.setMinimumWidth(300)

    def get_stage(self):
        return self.stage_dropdown.current_stage()

    def get_img_count(self):
        return self.img_count_box.value()

    def get_extent(self):
        return self.extent_spin.value() * 1e6

    def go(self):
        self.accept()

    def update_status(self):
        if self.stage_dropdown.is_selected():
            self.go_button.setEnabled(True)
