"""
This module contains the StageWidget class, which is a PyQt5 QWidget subclass for controlling 
and calibrating stages in microscopy instruments. It interacts with the application's model 
to manage calibration data and provides UI functionalities for reticle and probe detection, 
and camera calibration. The class integrates with PyQt5 for the UI, handling UI loading, 
initializing components, and linking user actions to calibration processes.
"""
from PyQt5.QtWidgets import QWidget, QMessageBox, QPushButton, QLabel, QSpacerItem, QSizePolicy
from PyQt5.uic import loadUi
from PyQt5.QtCore import QTimer
from .stage_listener import StageListener
from .probe_calibration import ProbeCalibration
from .calibration_camera import CalibrationStereo
from .stage_ui import StageUI
import os
import logging
import  numpy as np

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class StageWidget(QWidget):
    """Widget for stage control and calibration."""
    def __init__(self, model, ui_dir, screen_widgets):
        """ Initializes the StageWidget instance. 

        Parameters:
            model: The data model used for storing calibration and stage information.
            ui_dir (str): The directory path where UI files are located.
            screen_widgets (list): A list of ScreenWidget instances for reticle and probe detection.
        """
        super().__init__()
        self.model = model
        self.screen_widgets = screen_widgets
        loadUi(os.path.join(ui_dir, "stage_info.ui"), self)
        self.setMaximumWidth(380)
                
        # Load reticle_calib.ui into its placeholder
        self.reticle_calib_widget = QWidget()  # Create a new widget
        loadUi(os.path.join(ui_dir, "reticle_calib.ui"), self.reticle_calib_widget)
        # Assuming reticleCalibPlaceholder is the name of an empty widget designated as a placeholder in your stage_info.ui
        self.stage_status_ui.layout().addWidget(self.reticle_calib_widget)  # Add it to the placeholder's layout
        self.reticle_calib_widget.setMinimumSize(0, 160)

        # Load probe_calib.ui into its placeholder
        self.probe_calib_widget = QWidget()  # Create a new widget
        loadUi(os.path.join(ui_dir, "probe_calib.ui"), self.probe_calib_widget)
        # Assuming probeCalibPlaceholder is the name of an empty widget designated as a placeholder in your stage_info.ui
        self.stage_status_ui.layout().addWidget(self.probe_calib_widget)  # Add it to the placeholder's layout
        self.probe_calib_widget.setMinimumSize(0, 450) 
        
        # Create a vertical spacer with expanding policy
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        # Add the spacer to the layout
        self.stage_status_ui.addItem(spacer)

        # Access probe_calibration_btn
        self.probe_calibration_btn = self.probe_calib_widget.findChild(QPushButton, "probe_calibration_btn")
        self.reticle_calibration_btn = self.reticle_calib_widget.findChild(QPushButton, "reticle_calibration_btn")
        self.acceptButton = self.reticle_calib_widget.findChild(QPushButton, "acceptButton")
        self.rejectButton = self.reticle_calib_widget.findChild(QPushButton, "rejectButton")
        self.reticleCalibrationLabel = self.reticle_calib_widget.findChild(QLabel, "reticleCalibResultLabel")
        self.calib_x = self.probe_calib_widget.findChild(QPushButton, "calib_x")
        self.calib_y = self.probe_calib_widget.findChild(QPushButton, "calib_y")
        self.calib_z = self.probe_calib_widget.findChild(QPushButton, "calib_z")
        self.probeCalibrationLabel = self.probe_calib_widget.findChild(QLabel, "probeCalibrationLabel")

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
        self.probeCalibration.calib_complete.connect(self.probe_detect_accepted_status)
        self.probeCalibration.transM_info.connect(self.update_probe_calib_status)
        self.calib_status_x, self.calib_status_y, self.calib_status_z = False, False, False
        self.probe_detection_status = None    # options: default, process, x_y_z_detected, accepted

        self.filter = "no_filter"

    def reticle_detection_button_handler(self):
        """
        Handles clicks on the reticle detection button, initiating or canceling reticle detection.
        """
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
        """
        Resets the reticle detection process to its default state and updates the UI accordingly.
        """
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
        self.reticleCalibrationLabel.setText("")
        if self.probe_calibration_btn.isEnabled():        
            # Disable probe calibration
            self.probe_detect_default_status()

    def overwrite_popup_window(self):
        """
        Displays a confirmation dialog to decide whether to overwrite the current reticle position.
        
        Returns:
            bool: True if the user chooses to overwrite, False otherwise.
        """
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
        """
        Displays a warning dialog indicating the failure of reticle detection on one or more cameras.
        """
        coords_detect_fail_cameras = []
        for screen in self.screen_widgets:
            coords = screen.get_reticle_coords()
            if coords is None:
                camera_name = screen.get_camera_name()
                coords_detect_fail_cameras.append(camera_name)

        message = f"No reticle detected on cameras: {coords_detect_fail_cameras}"
        QMessageBox.warning(self, "Reticle Detection Failed", message)

    def reticle_detect_process_status(self):
        """
        Updates the UI and internal state to reflect that the reticle detection process is underway.
        """
        # Disable reticle_calibration_btn button
        if self.reticle_calibration_btn.isEnabled():
            self.reticle_calibration_btn.setEnabled(False)
        
        # Run reticle detectoin
        self.reticle_calibration_btn.setStyleSheet(
            "color: gray;"
            "background-color: #ffaaaa;"
        )
        for screen in self.screen_widgets:
            screen.reset_reticle_coords()  
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
        """
        Updates the UI and internal state to reflect that the reticle has been detected.
        """
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
        """
        Finalizes the reticle detection process, accepting the detected reticle position and updating the UI accordingly.
        """
        self.reticle_detection_status = "accepted"
        
        # Change the button to green.
        self.reticle_calibration_btn.setStyleSheet(
            "color: white;"
            "background-color: #84c083;"
        )
        # Show Accept and Reject Button
        self.acceptButton.hide() 
        self.rejectButton.hide() 

        result = self.calibrate_stereo()
        if result:
            self.reticleCalibrationLabel.setText(
                f"<span style='color:green;'><small>Coords Reproj RMSE:<br></small>"
                f"<span style='color:green;'>{result*1000:.1f} µm³</span>"
            )

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
        """
        Performs stereo calibration using the detected reticle positions and updates the model with the calibration data.
        """
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
            err = self.calibrationStereo.test_performance(cam_names[0], img_coords[0], cam_names[1], img_coords[1])
            return err
        else:
            return None

         
    def reticle_detect_all_screen(self):
        """
        Checks all screens for reticle detection results and updates the status based on whether the reticle
        has been detected on all screens.
        """
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
        """
        Displays a confirmation dialog asking the user if they want to overwrite the current probe position.

        Returns:
            bool: True if the user confirms the overwrite, False otherwise.
        """
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
        """
        Resets the probe detection status to its default state and updates the UI to reflect this change.
        This method is called after completing or aborting the probe detection process.
        """
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
        self.probeCalibrationLabel.setText("")
        self.probeCalibration.reset_calib()
        #self.reset_calib_status()

        self.probe_calibration_btn.setChecked(False)
        if self.reticle_detection_status == "default":
            self.probe_calibration_btn.setEnabled(False)
        
        if self.filter == "probe_detection":
            for screen in self.screen_widgets:
                screen.probe_coords_detected.disconnect(self.probe_detect_all_screen)
                screen.run_no_filter()

            self.filter = "no_filter"
            self.probeCalibration.clear()

        # update global coords
        self.stageListener.requestClearGlobalDataTransformM()
        
    def probe_detect_process_status(self): 
        """
        Updates the UI and internal state to reflect that the probe detection process is underway.
        """   
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
        message = f"Move probe at least 2mm along X, Y, and Z axes"
        QMessageBox.information(self, "Probe calibration info", message)

    def probe_detect_accepted_status(self, stage_sn, transformation_matrix):
        """
        Finalizes the probe detection process, accepting the detected probe position and updating the UI accordingly.
        Additionally, it updates the model with the transformation matrix obtained from the calibration.

        Parameters:
            stage_sn (str): The serial number of the stage for which the probe position is accepted.
            transformation_matrix (np.ndarray): The transformation matrix obtained from the probe calibration process.
        """
        self.probe_detection_status = "accepted"
        self.probe_calibration_btn.setStyleSheet(
            "color: white;"
            "background-color: #84c083;"
        )
        self.hide_x_y_z()
        if self.filter == "probe_detection":
            for screen in self.screen_widgets:
                screen.probe_coords_detected.disconnect(self.probe_detect_all_screen)
                screen.run_no_filter()

            self.filter = "no_filter"

        # update global coords
        self.stageListener.requestUpdateGlobalDataTransformM(stage_sn, transformation_matrix)
        
    def hide_x_y_z(self):
        """
        Hides the X, Y, and Z calibration buttons and updates their styles to indicate that the calibration for
        each axis has been completed.
        """
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
        """
        Updates the UI to indicate that the calibration for the X-axis is complete.
        """
        if self.calib_x.isVisible():
            # Change the button to green.
            self.calib_x.setStyleSheet(
            "color: white;"
            "background-color: #84c083;"
        )
    
    def calib_y_complete(self):
        """
        Updates the UI to indicate that the calibration for the Y-axis is complete.
        """
        if self.calib_y.isVisible():
            # Change the button to green.
            self.calib_y.setStyleSheet(
            "color: white;"
            "background-color: #84c083;"
        )
            
    def calib_z_complete(self):
        """
        Updates the UI to indicate that the calibration for the Z-axis is complete.
        """
        if self.calib_z.isVisible():
            # Change the button to green.
            self.calib_z.setStyleSheet(
            "color: white;"
            "background-color: #84c083;"
        )
    def update_probe_calib_status_transM(self, transformation_matrix):
        # Extract the rotation matrix (top-left 3x3)
        R = transformation_matrix[:3, :3]
        # Extract the translation vector (top 3 elements of the last column)
        T = transformation_matrix[:3, 3]
                
        # Set the formatted string as the label's text
        content = (
            f"<span style='color:yellow;'><small>"
            f"[Transformation Matrix]<br></small></span>"
            f"<span style='color:green;'><small><b>R:</b><br>"
            f" {R[0][0]:.5f}, {R[0][1]:.5f}, {R[0][2]:.5f},<br>"
            f" {R[1][0]:.5f}, {R[1][1]:.5f}, {R[1][2]:.5f},<br>"
            f" {R[2][0]:.5f}, {R[2][1]:.5f}, {R[2][2]:.5f},<br>"
            f"<b>T:</b><br>"
            f" {T[0]:.0f}, {T[1]:.0f}, {T[2]:.0f}<br>"
            f"</small></span>"
        )
        return content

    def update_probe_calib_status_L2(self, L2_err):
        content = (
            f"<span style='color:yellow;'><small>[L2 distance]<br></small></span>"
            f"<span style='color:green;'><small> {L2_err:.3f}<br>"
            f"</small></span>"
        )
        return content

    def update_probe_calib_status_distance_traveled(self, dist_traveled):
        x, y, z = dist_traveled[0], dist_traveled[1], dist_traveled[2]
        content = (
            f"<span style='color:yellow;'><small>[Distance traveled (µm)]<br></small></span>"
            f"<span style='color:green;'><small>"
            f"x: {x} y: {y} z: {z}<br>"
            f"</small></span>"
        )
        return content

    def update_probe_calib_status(self, transformation_matrix, L2_err, dist_traveled):
        content_transM = self.update_probe_calib_status_transM(transformation_matrix)
        content_L2 = self.update_probe_calib_status_L2(L2_err)
        content_L2_travel = self.update_probe_calib_status_distance_traveled(dist_traveled)
        # Ensure HTML content is properly combined
        full_content = content_transM + content_L2 + content_L2_travel

        self.probeCalibrationLabel.setText(full_content)


        
