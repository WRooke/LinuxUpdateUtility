# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'PopUp.ui'
#
# Created by: PyQt5 UI code generator 5.14.1
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_PopUpDialog(object):
    def setupUi(self, PopUpDialog):
        PopUpDialog.setObjectName("PopUpDialog")
        PopUpDialog.resize(395, 263)
        self.buttonBox = QtWidgets.QDialogButtonBox(PopUpDialog)
        self.buttonBox.setGeometry(QtCore.QRect(160, 230, 81, 21))
        self.buttonBox.setOrientation(QtCore.Qt.Vertical)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.popupimage = QtWidgets.QLabel(PopUpDialog)
        self.popupimage.setGeometry(QtCore.QRect(130, 10, 131, 121))
        self.popupimage.setText("")
        self.popupimage.setPixmap(QtGui.QPixmap("warning-icon-11552769738dqsq0g82mv.png"))
        self.popupimage.setScaledContents(True)
        self.popupimage.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.popupimage.setObjectName("popupimage")
        self.popuptext = QtWidgets.QLabel(PopUpDialog)
        self.popuptext.setGeometry(QtCore.QRect(0, 160, 391, 41))
        self.popuptext.setAlignment(QtCore.Qt.AlignCenter)
        self.popuptext.setObjectName("popuptext")

        self.retranslateUi(PopUpDialog)
        self.buttonBox.clicked['QAbstractButton*'].connect(PopUpDialog.close)
        QtCore.QMetaObject.connectSlotsByName(PopUpDialog)

    def retranslateUi(self, PopUpDialog):
        _translate = QtCore.QCoreApplication.translate
        PopUpDialog.setWindowTitle(_translate("PopUpDialog", "Dialog"))
        self.popuptext.setText(_translate("PopUpDialog", "DUMMY TEXT"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    PopUpDialog = QtWidgets.QDialog()
    ui = Ui_PopUpDialog()
    ui.setupUi(PopUpDialog)
    PopUpDialog.show()
    sys.exit(app.exec_())
