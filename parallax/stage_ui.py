"""
Defines StageUI, a PyQt5 QWidget for showing and updating stage information in the UI, 
including serial numbers and coordinates. It interacts with the model to reflect 
real-time data changes.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal
import numpy as np

class StageUI(QWidget):
    """User interface for stage control and display."""
    prev_curr_stages = pyqtSignal(str, str)

    def __init__(self, model, ui=None):
        """Initialize StageUI object"""
        QWidget.__init__(self, ui)
        self.selected_stage = None
        self.model = model
        self.ui = ui
    
        self.update_stage_selector()
        self.updateStageSN()
        self.updateStageLocalCoords()
        self.updateStageGlobalCoords()
        self.previous_stage_id = self.get_current_stage_id()
        self.setCurrentReticle()

        # Swtich stages
        self.ui.stage_selector.currentIndexChanged.connect(self.updateStageSN)
        self.ui.stage_selector.currentIndexChanged.connect(
            self.updateStageLocalCoords
        )
        self.ui.stage_selector.currentIndexChanged.connect(
            self.updateStageGlobalCoords
        )
        self.ui.stage_selector.currentIndexChanged.connect(self.sendInfoToStageWidget)

        # Swtich Reticle Coordinates (e.g Reticle + No Offset, Reticle + Offset..)
        self.ui.reticle_selector.currentIndexChanged.connect(self.updateCurrentReticle)


    def get_selected_stage_sn(self):
        """Get the serial number of the selected stage.

        Returns:
            str or None: The serial number of the selected stage, or None if no stage is selected.
        """
        if self.selected_stage is not None:
            return self.selected_stage.sn
        return None

    def update_stage_selector(self):
        """Update the stage selector with available stages."""
        self.ui.stage_selector.clear()
        for stage in self.model.stages.keys():
            self.ui.stage_selector.addItem("Probe " + stage, stage)

    def get_current_stage_id(self):
        """Get the ID of the currently selected stage.

        Returns:
            str or None: The ID of the currently selected stage, or None if no stage is selected.
        """
        currentIndex = self.ui.stage_selector.currentIndex()
        stage_id = self.ui.stage_selector.itemData(currentIndex)
        return stage_id

    def update_stage_widget(self, prev_stage_id, curr_stage_id):
        # signal
        self.prev_curr_stages.emit(prev_stage_id, curr_stage_id)
        
    def sendInfoToStageWidget(self):
        """Send the selected stage information to the stage widget."""    
        # Get updated stage_id
        stage_id = self.get_current_stage_id()
        self.update_stage_widget(self.previous_stage_id, stage_id)
        self.previous_stage_id = stage_id

    def updateStageSN(self):
        """Update the displayed stage serial number."""
        stage_id = self.get_current_stage_id()
        if stage_id:
            self.selected_stage = self.model.stages.get(stage_id)
            if self.selected_stage:
                self.ui.stage_sn.setText(" " + self.selected_stage.sn)

    def updateStageLocalCoords(self):
        """Update the displayed local coordinates of the selected stage."""
        stage_id = self.get_current_stage_id()
        if stage_id:
            self.selected_stage = self.model.stages.get(stage_id)
            if self.selected_stage:
                self.ui.local_coords_x.setText(str(self.selected_stage.stage_x))
                self.ui.local_coords_y.setText(str(self.selected_stage.stage_y))
                self.ui.local_coords_z.setText(str(self.selected_stage.stage_z))

    def updateCurrentReticle(self):
        self.setCurrentReticle()
        self.updateStageGlobalCoords()

    def setCurrentReticle(self):
        reticle_name = self.ui.reticle_selector.currentText()
        if not reticle_name:
            return
        
        # Extract the letter from reticle_name, assuming it has the format "Global coords (A)"
        self.reticle = reticle_name.split('(')[-1].strip(')')

    def updateStageGlobalCoords(self):
        """Update the displayed global coordinates of the selected stage."""
        stage_id = self.get_current_stage_id()
        if stage_id:
            self.selected_stage = self.model.get_stage(stage_id)
            if self.selected_stage:
                x = self.selected_stage.stage_x_global
                y = self.selected_stage.stage_y_global
                z = self.selected_stage.stage_z_global
                if x is not None and y is not None and z is not None:
                    # If reticle is with offset, get the global coordinates with offset
                    if self.reticle != "Global coords": 
                        if self.ui.reticle_metadata is not None:
                            global_pts = np.array([x, y, z])
                            x, y, z = self.ui.reticle_metadata.get_global_coords_with_offset(self.reticle, global_pts)
                    
                    # Update into UI
                    if x is not None and y is not None and z is not None:
                        self.ui.global_coords_x.setText(str(x))
                        self.ui.global_coords_y.setText(str(y))
                        self.ui.global_coords_z.setText(str(z))
                else:
                    self.updateStageGlobalCoords_default()

    def updateStageGlobalCoords_default(self):
        """
        Resets the global coordinates displayed in the UI to default placeholders.

        This method is used to clear the display of global coordinates in the user interface,
        setting them back to a default placeholder value ('-').
        """
        self.ui.global_coords_x.setText("-")
        self.ui.global_coords_y.setText("-")
        self.ui.global_coords_z.setText("-")
