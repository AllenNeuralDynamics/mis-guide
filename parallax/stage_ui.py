from PyQt5.QtWidgets import QWidget


class StageUI(QWidget):
    def __init__(self, model, parent=None):
        QWidget.__init__(self, parent)
        self.selected_stage = None
        self.model = model
        self.ui = parent
        self.update_stage_selector()
        self.updateStageSN()
        self.updateStageLocalCoords()
        self.updateStageGlobalCoords()

        self.ui.stage_selector.currentIndexChanged.connect(self.updateStageSN)
        self.ui.stage_selector.currentIndexChanged.connect(self.updateStageLocalCoords)
        self.ui.stage_selector.currentIndexChanged.connect(self.updateStageGlobalCoords)

    def get_selected_stage_sn(self):
        if self.selected_stage is not None:
            return self.selected_stage.sn
        return None

    def update_stage_selector(self):
        self.ui.stage_selector.clear()
        for stage in self.model.stages.keys():
            self.ui.stage_selector.addItem("Probe " + stage, stage)
            
    def _get_current_stage_id(self):
        currentIndex = self.ui.stage_selector.currentIndex()
        stage_id = self.ui.stage_selector.itemData(currentIndex)
        return stage_id
        
    def updateStageSN(self):
        stage_id = self._get_current_stage_id()
        if stage_id:
            self.selected_stage = self.model.stages.get(stage_id)
            if self.selected_stage:
                self.ui.stage_sn.setText(" "+self.selected_stage.sn)

    def updateStageLocalCoords(self):
        stage_id = self._get_current_stage_id()
        if stage_id:
            self.selected_stage = self.model.stages.get(stage_id)
            if self.selected_stage:
                self.ui.local_coords_x.setText(str(self.selected_stage.stage_x))
                self.ui.local_coords_y.setText(str(self.selected_stage.stage_y))
                self.ui.local_coords_z.setText(str(self.selected_stage.stage_z))

    def updateStageGlobalCoords(self):
        stage_id = self._get_current_stage_id()
        if stage_id:
            self.selected_stage = self.model.stages.get(stage_id)
            if self.selected_stage:
                if self.selected_stage.stage_x_global is not None \
                and self.selected_stage.stage_y_global is not None \
                and self.selected_stage.stage_z_global is not None:
                    self.ui.global_coords_x.setText(str(self.selected_stage.stage_x_global))
                    self.ui.global_coords_y.setText(str(self.selected_stage.stage_y_global))
                    self.ui.global_coords_z.setText(str(self.selected_stage.stage_z_global))
                else:
                    self.ui.global_coords_x.setText('-')
                    self.ui.global_coords_y.setText('-')
                    self.ui.global_coords_z.setText('-')                    