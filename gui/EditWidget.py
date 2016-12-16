# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'EditWidget.ui'
#
# Created by: PyQt5 UI code generator 5.7
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtWidgets


class Ui_EditWidget(object):
    def setupUi(self, EditWidget):
        EditWidget.setObjectName("EditWidget")
        EditWidget.resize(400, 300)
        self.verticalLayout = QtWidgets.QVBoxLayout(EditWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(EditWidget)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.scrollArea = QtWidgets.QScrollArea(EditWidget)
        self.scrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.editWidgetsContainer = QtWidgets.QWidget()
        self.editWidgetsContainer.setGeometry(QtCore.QRect(0, 0, 382, 256))
        self.editWidgetsContainer.setObjectName("editWidgetsContainer")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.editWidgetsContainer)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.scrollArea.setWidget(self.editWidgetsContainer)
        self.verticalLayout.addWidget(self.scrollArea)

        self.retranslateUi(EditWidget)
        QtCore.QMetaObject.connectSlotsByName(EditWidget)

    def retranslateUi(self, EditWidget):
        _translate = QtCore.QCoreApplication.translate
        EditWidget.setWindowTitle(_translate("EditWidget", "Form"))
        self.label.setText(_translate("EditWidget", "TextLabel"))
