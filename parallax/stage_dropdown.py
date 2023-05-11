from PyQt5.QtWidgets import QComboBox
from PyQt5.QtCore import Qt


class StageDropdown(QComboBox):

    def __init__(self, model):
        QComboBox.__init__(self)
        self.model = model

        self.selected = False
        self.setFocusPolicy(Qt.NoFocus)
        self.activated.connect(self.set_selected)

        self.setToolTip('Select a stage')

    def set_selected(self):
        self.selected = True

    def is_selected(self):
        return self.selected

    def showPopup(self):
        self.populate()
        QComboBox.showPopup(self)

    def get_current_stage(self):
        return self.model.stages[self.currentText()]

    def populate(self):
        self.clear()
        for sn in self.model.stages.keys():
            self.addItem(sn)


