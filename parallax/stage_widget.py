"""
This module contains the StageWidget class, which is a PyQt5 QWidget subclass for controlling 
and calibrating stages in microscopy instruments. It interacts with the application's model 
to manage calibration data and provides UI functionalities for reticle and probe detection, 
and camera calibration. The class integrates with PyQt5 for the UI, handling UI loading, 
initializing components, and linking user actions to calibration processes.
"""
from PyQt5.QtWidgets import QWidget, QMessageBox, QPushButton, QSpacerItem, QSizePolicy
from PyQt5.uic import loadUi
from PyQt5.QtCore import QTimer
from .stage_listener import StageListener
from .probe_calibration import ProbeCalibration
from .calibration_camera import CalibrationStereo
from .stage_ui import StageUI
import os
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class StageWidget(QWidget):
    """Widget for stage control and calibration."""
    def __init__(self, model, ui_dir, screen_widgets):
        """ Initializes the StageWidget instance. """
        super().__init__()
        self.model = model
        self.screen_widgets = screen_widgets
        loadUi(os.path.join(ui_dir, "stage_info.ui"), self)
        self.setMaximumWidth(400)
                
        # Load reticle_calib.ui into its placeholder
        self.reticle_calib_widget = QWidget()  # Create a new widget
        loadUi(os.path.join(ui_dir, "reticle_calib.ui"), self.reticle_calib_widget)
        # Assuming reticleCalibPlaceholder is the name of an empty widget designated as a placeholder in your stage_info.ui
        self.stage_status_ui.layout().addWidget(self.reticle_calib_widget)  # Add it to the placeholder's layout
        self.reticle_calib_widget.setMinimumSize(0, 150)

        # Load probe_calib.ui into its placeholder
        self.probe_calib_widget = QWidget()  # Create a new widget
        loadUi(os.path.join(ui_dir, "probe_calib.ui"), self.probe_calib_widget)
        # Assuming probeCalibPlaceholder is the name of an empty widget designated as a placeholder in your stage_info.ui
        self.stage_status_ui.layout().addWidget(self.probe_calib_widget)  # Add it to the placeholder's layout
        self.probe_calib_widget.setMinimumSize(0, 150) 
        
        # Create a vertical spacer with expanding policy
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        # Add the spacer to the layout
        self.stage_status_ui.addItem(spacer)

        # Access probe_calibration_btn
        self.probe_calibration_btn = self.probe_calib_widget.findChild(QPushButton, "probe_calibration_btn")
        self.reticle_calibration_btn = self.reticle_calib_widget.findChild(QPushButton, "reticle_calibration_btn")
        self.acceptButton = self.reticle_calib_widget.findChild(QPushButton, "acceptButton")
        self.rejectButton = self.reticle_calib_widget.findChild(QPushButton, "rejectButton")
        self.calib_x = self.probe_calib_widget.findChild(QPushButton, "calib_x")
        self.calib_y = self.probe_calib_widget.findChild(QPushButton, "calib_y")
        self.calib_z = self.probe_calib_widget.findChild(QPushButton, "calib_z")

        # Reticle Widget
        self.reticle_detection_status = None    # options: default, process, detected, accepted
        self.reticle_calibration_btn.clicked.connect(self.reticle_detection_button_handler)
        self.calibrationStereo = None
        # Hide Accept and Reject Button in Reticle Detection
        self.acceptButton.hide() 
        self.rejectButton.hide() 
        self.acceptButton.clicked.connect(self.reticle_detect_accept_detected_status)
        self.rejectButton.clicked.connect(self.reticle_detect_default_status)
        # Add a QTimer for delayed check
        self.reticle_calibration_timer = QTimer(self)
        self.reticle_calibration_timer.timeout.connect(self.reticle_detect_default_status)
        
        # Stage widget
        self.stageUI = StageUI(self.model, self)
        self.probe_calibration_btn.setEnabled(False)
        self.probe_calibration_btn.clicked.connect(self.probe_detection_button_handler)
        # Start refreshing stage info
        self.stageListener = StageListener(self.model, self.stageUI)
        self.stageListener.start()
        self.probeCalibration = ProbeCalibration(self.stageListener)
        # Hide X, Y, and Z Buttons in Probe Detection
        self.calib_x.hide() 
        self.calib_y.hide()
        self.calib_z.hide()
        self.probeCalibration.calib_complete_x.connect(self.calib_x_complete)
        self.probeCalibration.calib_complete_y.connect(self.calib_y_complete)
        self.probeCalibration.calib_complete_z.connect(self.calib_z_complete)
        self.calib_status_x, self.calib_status_y, self.calib_status_z = False, False, False
        self.probe_detection_status = None    # options: default, process, x_y_z_detected, accepted

        self.filter = "no_filter"

    def reticle_detection_button_handler(self):
        """Handle the reticle detection button click."""
        logger.debug(f"\n reticle_detection_button_handler {self.reticle_detection_status}")
        if self.reticle_calibration_btn.isChecked():
            # Run reticle detectoin
            self.reticle_detect_process_status()
        else:
            if self.reticle_detection_status == "accepted":
                response = self.overwrite_popup_window()
                if response:
                    # Overwrite the result
                    self.reticle_detect_default_status()    
                else:
                    # Keep the last calibration result
                    self.reticle_calibration_btn.setChecked(True)
    
    def reticle_detect_default_status(self):
        # Enable reticle_calibration_btn button
        if not self.reticle_calibration_btn.isEnabled():
            self.reticle_calibration_btn.setEnabled(True)

        if self.reticle_detection_status == "process":
            self.reticle_detect_fail_popup_window()
            
        # Stop reticle detectoin, and run no filter
        self.reticle_calibration_timer.stop()

        if self.reticle_detection_status != "accepted":
            for screen in self.screen_widgets:
                screen.reticle_coords_detected.disconnect(self.reticle_detect_all_screen)
                screen.run_no_filter()
            self.filter = "no_filter"

        # Hide Accept and Reject Button
        self.acceptButton.hide() 
        self.rejectButton.hide() 
        
        self.reticle_calibration_btn.setStyleSheet("""
            QPushButton {
                color: white;
                background-color: black;
            }
            QPushButton:hover {
                background-color: #641e1e;
            }
        """)
        self.reticle_detection_status = "default"
        if self.probe_calibration_btn.isEnabled():        
            # Disable probe calibration
            self.probe_detect_default_status()

    def overwrite_popup_window(self):
        message = f"Are you sure you want to overwrite the current reticle position?"
        response = QMessageBox.warning(self, "Reticle Detection Failed", message, 
                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        # Check which button was clicked
        if response == QMessageBox.Yes:
            logger.debug("User clicked Yes.")
            return True
        else:
            logger.debug("User clicked No.")
            return False
    
    def reticle_detect_fail_popup_window(self):
        coords_detect_fail_cameras = []
        for screen in self.screen_widgets:
            coords = screen.get_reticle_coords()
            if coords is None:
                camera_name = screen.get_camera_name()
                coords_detect_fail_cameras.append(camera_name)

        message = f"No reticle detected on cameras: {coords_detect_fail_cameras}"
        QMessageBox.warning(self, "Reticle Detection Failed", message)

    def reticle_detect_process_status(self):
        # Disable reticle_calibration_btn button
        if self.reticle_calibration_btn.isEnabled():
            self.reticle_calibration_btn.setEnabled(False)
        
        # Run reticle detectoin
        self.reticle_calibration_btn.setStyleSheet(
            "color: gray;"
            "background-color: #ffaaaa;"
        )
        for screen in self.screen_widgets:
            screen.reset_reticle_coords()  # screen.reticle_coords = None
            screen.reticle_coords_detected.connect(self.reticle_detect_all_screen)
            screen.run_reticle_detection()
        self.filter = "reticle_detection"

        # Hide Accept and Reject Button
        self.acceptButton.hide() 
        self.rejectButton.hide() 

        # Start the timer for 10 seconds to check the status later
        self.reticle_detection_status = "process"
        self.reticle_calibration_timer.start(10000)
        logger.debug(self.reticle_detection_status)


    def reticle_detect_detected_status(self):
        # Found the coords
        self.reticle_detection_status = "detected"
        self.reticle_calibration_timer.stop()

        # Show Accept and Reject Button
        self.acceptButton.show() 
        self.rejectButton.show() 

        # Change the button to brown.
        self.reticle_calibration_btn.setStyleSheet(
            "color: white;"
            "background-color: #bc9e44;"
        )

    def reticle_detect_accept_detected_status(self):
        self.reticle_detection_status = "accepted"
        
        # Change the button to green.
        self.reticle_calibration_btn.setStyleSheet(
            "color: white;"
            "background-color: #84c083;"
        )
        # Show Accept and Reject Button
        self.acceptButton.hide() 
        self.rejectButton.hide() 

        self.calibrate_stereo()

        for screen in self.screen_widgets:
            screen.reticle_coords_detected.disconnect(self.reticle_detect_all_screen)
            screen.run_no_filter()
        self.filter = "no_filter"

        # Enable reticle_calibration_btn button
        if not self.reticle_calibration_btn.isEnabled():
            self.reticle_calibration_btn.setEnabled(True)
        logger.debug(self.reticle_detection_status)

        # Enable probe calibration
        if not self.probe_calibration_btn.isEnabled():   
            self.probe_calibration_btn.setEnabled(True)

    def calibrate_stereo(self):
        # Streo Camera Calibration
        if len(self.model.coords_axis) >=2 and len(self.model.camera_intrinsic) >=2:
            img_coords = []
            intrinsics = []
            cam_names = []
            
            for screen in self.screen_widgets: 
                camera_name = screen.get_camera_name()
                cam_names.append(camera_name)
                img_coords.append(self.model.get_coords_axis(camera_name))
                intrinsics.append(self.model.get_camera_intrinsic(camera_name))

            if len(intrinsics) >= 2:
                print("\n== intrinsics ==")
                print(f" cam {cam_names[0]}:\n  {intrinsics[0]}")
                print(f" cam {cam_names[1]}:\n  {intrinsics[1]}")

            # TODO 
            self.calibrationStereo = CalibrationStereo(cam_names[0], img_coords[0], intrinsics[0], \
                                                    cam_names[1], img_coords[1], intrinsics[1])
            retval, R_AB, T_AB, E_AB, F_AB = self.calibrationStereo.calibrate_stereo()
            self.model.add_camera_extrinsic(cam_names[0], cam_names[1], retval, R_AB, T_AB, E_AB, F_AB)

            # Test
            self.calibrationStereo.test(cam_names[0], img_coords[0], cam_names[1], img_coords[1])

    def reticle_detect_all_screen(self):
        """Detect reticle coordinates on all screens."""
        for screen in self.screen_widgets:
            coords = screen.get_reticle_coords()
            if coords is None:
                return
        
        # Found the coords
        self.reticle_detect_detected_status()

        #self.reticle_calibration_btn.setText("Confirm ?")
        for screen in self.screen_widgets:
            coords = screen.get_reticle_coords()
            mtx, dist = screen.get_camera_intrinsic()
            camera_name = screen.get_camera_name()
            # Retister the reticle coords in the model
            self.model.add_coords_axis(camera_name, coords)
            self.model.add_camera_intrinsic(camera_name, mtx, dist)

    def probe_detect_all_screen(self):
        """Detect probe coordinates on all screens."""
        timestamp_cmp, sn_cmp = None, None
        cam_names = []
        tip_coords = []

        if self.calibrationStereo is None:
            print("Camera calibration has not done")
            return 

        for screen in self.screen_widgets:
            timestamp, sn, tip_coord = screen.get_last_detect_probe_info()
            
            if (sn is None) or (tip_coords is None) or (timestamp is None):
                return

            if timestamp_cmp is None:
                timestamp_cmp = timestamp    
            else: # if timestamp is different between screens, return
                if timestamp_cmp[:-2] != timestamp[:-2]:
                    return

            if sn_cmp is None:
                sn_cmp = sn
            else: # if sn is different between screens, return
                if sn_cmp != sn:
                    return
            
            camera_name = screen.get_camera_name()
            cam_names.append(camera_name)
            tip_coords.append(tip_coord)

        # All screen has the same timestamp. Proceed the triangulation
        global_coords = self.calibrationStereo.get_global_coords(cam_names[0], tip_coords[0], cam_names[1], tip_coords[1])
        self.stageListener.handleGlobalDataChange(sn, global_coords, timestamp)

    def probe_overwrite_popup_window(self):
        message = f"Are you sure you want to overwrite the current probe position?"
        response = QMessageBox.warning(self, "Reticle Detection Failed", message, 
                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        # Check which button was clicked
        if response == QMessageBox.Yes:
            logger.debug("User clicked Yes.")
            return True
        else:
            logger.debug("User clicked No.")
            return False

    def probe_detection_button_handler(self):
        """Handle the probe detection button click."""
        if self.probe_calibration_btn.isChecked():
            self.probe_detect_process_status()
        else:
            response = self.probe_overwrite_popup_window()
            if response:
                self.probe_detect_default_status()
            else:
                # Keep the last calibration result
                self.probe_calibration_btn.setChecked(True)

    def probe_detect_default_status(self):    
        self.probe_detection_status = "default"
        self.probe_calibration_btn.setStyleSheet("""
            QPushButton {
                color: white;
                background-color: black;
            }
            QPushButton:hover {
                background-color: #641e1e;
            }
        """)
        self.hide_x_y_z()
        self.probeCalibration.reset_calib()
        self.reset_calib_status()

        self.probe_calibration_btn.setChecked(False)
        if self.reticle_detection_status == "default":
            self.probe_calibration_btn.setEnabled(False)
        
        if self.filter == "probe_detection":
            for screen in self.screen_widgets:
                screen.probe_coords_detected.disconnect(self.probe_detect_all_screen)
                screen.run_no_filter()

            self.filter = "no_filter"
            self.probeCalibration.clear()
        
    def probe_detect_process_status(self):    
        self.probe_detection_status = "process"
        self.probe_calibration_btn.setStyleSheet(
            "color: white;"
            "background-color: #bc9e44;"
        )
        self.calib_x.show()
        self.calib_y.show()
        self.calib_z.show()

        for screen in self.screen_widgets:
            screen.probe_coords_detected.connect(self.probe_detect_all_screen)
            screen.run_probe_detection()
        self.filter = "probe_detection"

        # message
        message = f"Move probe at leas X mm along X, Y, and Z axes"
        QMessageBox.information(self, "Probe calibration info", message)

    def probe_detect_accepted_status(self):
        self.probe_detection_status = "accepted"
        self.probe_calibration_btn.setStyleSheet(
            "color: white;"
            "background-color: #84c083;"
        )
        self.hide_x_y_z()

    def hide_x_y_z(self):
        if self.calib_x.isVisible():
            self.calib_x.hide()
            # Change the button to green.
            self.calib_x.setStyleSheet(
            "color: white;"
            "background-color: black;"
        )
        if self.calib_y.isVisible():
            self.calib_y.hide()
            # Change the button to green.
            self.calib_y.setStyleSheet(
            "color: white;"
            "background-color: black;"
        )
        if self.calib_z.isVisible():
            self.calib_z.hide()
            # Change the button to green.
            self.calib_z.setStyleSheet(
            "color: white;"
            "background-color: black;"
        )
            
    def calib_x_complete(self):
        if self.calib_x.isVisible():
            # Change the button to green.
            self.calib_x.setStyleSheet(
            "color: white;"
            "background-color: #84c083;"
        )
        self.calib_status_x = True
        if self.is_calib_success():
            self.probe_detect_accepted_status()
    
    def calib_y_complete(self):
        if self.calib_y.isVisible():
            # Change the button to green.
            self.calib_y.setStyleSheet(
            "color: white;"
            "background-color: #84c083;"
        )
        self.calib_status_y = True
        if self.is_calib_success():
            self.probe_detect_accepted_status()
    
    def calib_z_complete(self):
        if self.calib_z.isVisible():
            # Change the button to green.
            self.calib_z.setStyleSheet(
            "color: white;"
            "background-color: #84c083;"
        )
        self.calib_status_z = True
        if self.is_calib_success():
            self.probe_detect_accepted_status()

    def is_calib_success(self):
        return self.calib_status_x and self.calib_status_y and self.calib_status_z

    def reset_calib_status(self):
        self.calib_status_x, self.calib_status_y, self.calib_status_z = False, False, False