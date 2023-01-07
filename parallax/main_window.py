from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QMainWindow, QAction
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon

from .message_log import MessageLog
from .screen_widget import ScreenWidget
from .control_panel import ControlPanel
from .triangulation_panel import TriangulationPanel
from .dialogs import AboutDialog
from .rigid_body_transform_tool import RigidBodyTransformTool
from .stage_manager import StageManager


class MainWindow(QMainWindow):

    def __init__(self, model):
        QMainWindow.__init__(self)
        self.model = model

        self.widget = MainWidget(model)
        self.setCentralWidget(self.widget)

        # menubar actions
        self.save_frames_action = QAction("Save Camera Frames")
        self.save_frames_action.triggered.connect(self.widget.save_camera_frames)
        self.save_frames_action.setShortcut("Ctrl+F")
        self.save_cal_action = QAction("Save Calibration")
        self.save_cal_action.triggered.connect(self.widget.tri_panel.save)
        self.save_cal_action.setShortcut("Ctrl+S")
        self.load_cal_action = QAction("Load Calibration")
        self.load_cal_action.triggered.connect(self.widget.tri_panel.load)
        self.load_cal_action.setShortcut("Ctrl+O")
        self.edit_prefs_action = QAction("Preferences")
        self.edit_prefs_action.setEnabled(False)
        self.refresh_cameras_action = QAction("Refresh Camera List")
        self.refresh_cameras_action.triggered.connect(self.refresh_cameras)
        self.manage_stages_action = QAction("Manage Stages")
        self.manage_stages_action.triggered.connect(self.launch_stage_manager)
        self.refresh_focos_action = QAction("Refresh Focus Controllers")
        self.refresh_focos_action.triggered.connect(self.refresh_focus_controllers)
        self.rbt_action = QAction("Rigid Body Transform Tool")
        self.rbt_action.triggered.connect(self.launch_rbt)
        self.about_action = QAction("About")
        self.about_action.triggered.connect(self.launch_about)

        # build the menubar
        self.file_menu = self.menuBar().addMenu("File")
        self.file_menu.addAction(self.save_frames_action)
        self.file_menu.addSeparator()    # not visible on linuxmint?
        self.file_menu.addAction(self.save_cal_action)
        self.file_menu.addAction(self.load_cal_action)

        self.edit_menu = self.menuBar().addMenu("Edit")
        self.edit_menu.addAction(self.edit_prefs_action)

        self.device_menu = self.menuBar().addMenu("Devices")
        self.device_menu.addAction(self.refresh_cameras_action)
        self.device_menu.addAction(self.manage_stages_action)
        self.device_menu.addAction(self.refresh_focos_action)

        self.tools_menu = self.menuBar().addMenu("Tools")
        self.tools_menu.addAction(self.rbt_action)

        self.help_menu = self.menuBar().addMenu("Help")
        self.help_menu.addAction(self.about_action)

        self.setWindowTitle('Parallax')
        self.setWindowIcon(QIcon('../img/sextant.png'))

        self.refresh_cameras()
        self.refresh_focus_controllers()

    def launch_stage_manager(self):
        self.stage_manager = StageManager(self.model)
        self.stage_manager.show()

    def launch_about(self):
        dlg = AboutDialog()
        dlg.exec_()

    def launch_rbt(self):
        self.rbt = RigidBodyTransformTool(self.model)
        self.rbt.show()

    def screens(self):
        return self.widget.lscreen, self.widget.rscreen

    def refresh_cameras(self):
        self.model.scan_for_cameras()
        for screen in self.screens():
            screen.update_camera_menu()

    def refresh_focus_controllers(self):
        self.model.scan_for_focus_controllers()
        for screen in self.screens():
            screen.update_focus_control_menu()


class MainWidget(QWidget):

    def __init__(self, model):
        QWidget.__init__(self) 
        self.model = model

        self.screens = QWidget()
        hlayout = QHBoxLayout()
        self.lscreen = ScreenWidget(model=self.model)
        self.rscreen = ScreenWidget(model=self.model)
        hlayout.addWidget(self.lscreen)
        hlayout.addWidget(self.rscreen)
        self.screens.setLayout(hlayout)

        self.controls = QWidget()
        self.control_panel1 = ControlPanel(self.model)
        self.control_panel2 = ControlPanel(self.model)
        self.tri_panel = TriangulationPanel(self.model)
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.control_panel1)
        hlayout.addWidget(self.tri_panel)
        hlayout.addWidget(self.control_panel2)
        self.controls.setLayout(hlayout)

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(32)

        # connections
        self.msg_log = MessageLog()
        self.control_panel1.msg_posted.connect(self.msg_log.post)
        self.control_panel2.msg_posted.connect(self.msg_log.post)
        self.control_panel1.target_reached.connect(self.zoom_out)
        self.control_panel2.target_reached.connect(self.zoom_out)
        self.tri_panel.msg_posted.connect(self.msg_log.post)
        self.model.cal_point_reached.connect(self.clear_selected)
        self.model.cal_point_reached.connect(self.zoom_out)
        self.model.msg_posted.connect(self.msg_log.post)
        self.lscreen.selected.connect(self.model.set_lcorr)
        self.lscreen.cleared.connect(self.model.clear_lcorr)
        self.rscreen.selected.connect(self.model.set_rcorr)
        self.rscreen.cleared.connect(self.model.clear_rcorr)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.screens)
        main_layout.addWidget(self.controls)
        main_layout.addWidget(self.msg_log)
        self.setLayout(main_layout)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_R:
            if (e.modifiers() & Qt.ControlModifier):
                self.clear_selected()
                self.zoom_out()
                e.accept()
        elif e.key() == Qt.Key_C:
            self.model.register_corr_points_cal()
        elif e.key() == Qt.Key_Escape:
            self.model.halt_all_stages()

    def refresh(self):
        self.lscreen.refresh()
        self.rscreen.refresh()

    def clear_selected(self):
        self.lscreen.clear_selected()
        self.rscreen.clear_selected()

    def zoom_out(self):
        self.lscreen.zoom_out()
        self.rscreen.zoom_out()

    def save_camera_frames(self):
        for i,camera in enumerate(self.model.cameras):
            if camera.last_image:
                filename = 'camera%d_%s.png' % (i, camera.get_last_capture_time())
                camera.save_last_image(filename)
                self.msg_log.post('Saved camera frame: %s' % filename)


