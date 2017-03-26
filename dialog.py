#!/usr/bin/env python
# --*--codig: utf8 --*--

from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import QtWidgets

class LoginDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        import os, pwd
        self.setFixedSize(400, 250)
        self.nameLabel   = QtWidgets.QLabel('Name:')
        self.passwdLabel = QtWidgets.QLabel('Password:')
        self.nameEdit    = QtWidgets.QLineEdit( )
        self.passwdEdit  = QtWidgets.QLineEdit( )
        self.nameEdit.setText(pwd.getpwuid(os.getuid()).pw_name)
        self.passwdEdit.setEchoMode(QtWidgets.QLineEdit.Password)

        self.buttonBox = QtWidgets.QDialogButtonBox( )
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)


        self.groupBox = QtWidgets.QGroupBox('Login')
        self.groupBox.setStyleSheet('''
        QGroupBox
        {
            font-size: 18px;
            font-weight: bold;
            font-family: Monaco
        }
        ''')
        self.layout = QtWidgets.QGridLayout( )
        self.layout.addWidget(self.nameLabel,     3, 0, 3, 1)
        self.layout.addWidget(self.nameEdit,      3, 1, 3, 1)
        self.layout.addWidget(self.passwdLabel,   4, 0, 6, 1)
        self.layout.addWidget(self.passwdEdit,    4, 1, 6, 1)
        self.groupBox.setLayout(self.layout)
        self.mainLayout = QtWidgets.QVBoxLayout( )
        self.mainLayout.addWidget(self.groupBox)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)


        self.nameEdit.textEdited.connect(self.checkEdit)
        self.passwdEdit.textEdited.connect(self.checkEdit)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.show( )
        self.isAccepted = self.exec_( )

    def checkEdit(self):
        if self.nameEdit.text( ) and self.passwdEdit.text():
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)



class DisconnectDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        import os, pwd
        self.setFixedSize(300, 150)
        self.label = QtWidgets.QLabel()
        self.label.setText("You have diconnected with server")
        self.buttonBox = QtWidgets.QDialogButtonBox( )
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)

        self.groupBox = QtWidgets.QGroupBox('Disconnect')
        self.groupBox.setStyleSheet('''
        QGroupBox
        {
            font-size: 18px;
            font-weight: bold;
            font-family: Monaco
        }
        ''')
        self.layout = QtWidgets.QGridLayout( )
        self.layout.addWidget(self.label)
        self.groupBox.setLayout(self.layout)
        self.mainLayout = QtWidgets.QVBoxLayout( )
        self.mainLayout.addWidget(self.groupBox)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)


        self.buttonBox.accepted.connect(self.accept)
        self.show( )
        self.isAccepted = self.exec_( )

class ConnectSuccessDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.setFixedSize(300, 150)
        self.label = QtWidgets.QLabel()
        self.label.setText("You have connected to server")
        self.buttonBox = QtWidgets.QDialogButtonBox( )
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)

        self.groupBox = QtWidgets.QGroupBox('Connect Successfully')
        self.groupBox.setStyleSheet('''
        QGroupBox
        {
            font-size: 18px;
            font-weight: bold;
            font-family: Monaco
        }
        ''')
        self.layout = QtWidgets.QGridLayout( )
        self.layout.addWidget(self.label)
        self.groupBox.setLayout(self.layout)
        self.mainLayout = QtWidgets.QVBoxLayout( )
        self.mainLayout.addWidget(self.groupBox)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)

        # self.buttonBox.accepted.connect(self.accept)
        # self.isAccepted = self.exec_( )

    def accept(self):
        super(ConnectSuccessDialog, self).accept()

class ConnectFailDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        import os, pwd
        self.setFixedSize(300, 150)
        self.label = QtWidgets.QLabel()
        self.label.setText("Something wrong with your username or password")
        self.buttonBox = QtWidgets.QDialogButtonBox( )
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)

        self.groupBox = QtWidgets.QGroupBox('Connect Fail')
        self.groupBox.setStyleSheet('''
        QGroupBox
        {
            font-size: 18px;
            font-weight: bold;
            font-family: Monaco
        }
        ''')
        self.layout = QtWidgets.QGridLayout( )
        self.layout.addWidget(self.label)
        self.groupBox.setLayout(self.layout)
        self.mainLayout = QtWidgets.QVBoxLayout( )
        self.mainLayout.addWidget(self.groupBox)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)


        self.buttonBox.accepted.connect(self.accept)
        self.show( )


class BaseProgressWidget(QtWidgets.QWidget):
    updateProgress = QtCore.pyqtSignal(str)
    def __init__(self, text='', parent=None):
        super(BaseProgressWidget, self).__init__(parent)
        self.maxValue = 0
        self.setFixedHeight(50)
        self.text  = text
        self.progressbar = QtWidgets.QProgressBar( )
        self.progressbar.setTextVisible(True)
        self.updateProgress.connect(self.set_value)

        self.bottomBorder = QtWidgets.QWidget( )
        self.bottomBorder.setStyleSheet("""
            background: palette(shadow);
        """)
        self.bottomBorder.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed))
        self.bottomBorder.setMinimumHeight(1)

        self.label  = QtWidgets.QLabel(self.text)
        self.label.setStyleSheet("""
            font-weight: bold;
        """)
        self.layout = QtWidgets.QVBoxLayout( )
        self.layout.setContentsMargins(10,0,10,0)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.progressbar)

        self.mainLayout = QtWidgets.QVBoxLayout( )
        self.mainLayout.setContentsMargins(0,0,0,0)
        self.mainLayout.addLayout(self.layout)
        self.mainLayout.addWidget(self.bottomBorder)
        self.setLayout(self.mainLayout)
        self.totalValue = 0

    def set_value(self, value):
        self.totalValue += int(value)
        self.progressbar.setValue(self.totalValue)

    def set_max(self, value):
        self.maxValue = value
        self.progressbar.setMaximum(value)

    def get_maxValue(self):
        return self.maxValue

    def get_totalValue(self):
        return self.totalValue

    def remove_all(self):
        for i in reversed(range(self.layout.count())):
            self.layout.itemAt(i).widget().setParent(None)
        self.mainLayout.removeWidget(self.bottomBorder)


class DownloadProgressWidget(BaseProgressWidget):
    def __init__(self, text='Downloading', parent=None):
        super(self.__class__, self).__init__(text, parent)
        style ="""
        QProgressBar {
            border: 2px solid grey;
            border-radius: 5px;
            text-align: center;
        }

        QProgressBar::chunk {
            background-color: #37DA7E;
            width: 20px;
        }"""
        self.progressbar.setStyleSheet(style)


class UploadProgressWidget(BaseProgressWidget):
    def __init__(self, text='Uploading', parent=None):
        super(self.__class__, self).__init__(text, parent)
        style ="""
        QProgressBar {
            border: 2px solid grey;
            border-radius: 5px;
            text-align: center;
        }

        QProgressBar::chunk {
            background-color: #88B0EB;
            width: 20px;
        }"""
        self.progressbar.setStyleSheet(style)

class ProgressDialog(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.resize(500, 250)
        self.scrollArea = QtWidgets.QScrollArea( )
        self.scrollArea.setWidgetResizable(True)
        self.setCentralWidget(self.scrollArea)

        self.centralWidget = QtWidgets.QWidget( )
        self.scrollArea.setWidget(self.centralWidget)

        self.layout = QtWidgets.QVBoxLayout( )
        self.layout.setAlignment(QtCore.Qt.AlignTop)
        self.layout.setContentsMargins(0,10,0,0)
        self.centralWidget.setLayout(self.layout)

    def addProgressbar(self, progressbar):
        self.layout.addWidget(progressbar)

    def removeProgressbar(self, progressbar):
        self.layout.removeWidget(progressbar)

def loginDialog(parent=None):
    login = LoginDialog(parent)
    if not login.isAccepted:
        return False
    else:
        return (str(login.nameEdit.text( )), str(login.passwdEdit.text( )), True)

def disconnectDialog(parent=None):
    DisconnectDialog(parent)

def failLogin(parent=None):
    ConnectFailDialog(parent)

def loginInSuccess(parent=None):
    ConnectSuccessDialog(parent)






if __name__ == '__main__':
    def testLoinDialog( ):
        app = QtWidgets.QApplication([])
        print(loginDialog( ))

    def testDisconnectDialog( ):
        app = QtWidgets.QApplication([])
        print(disconnectDialog( ))

    def testProgressDialog( ):
        p = ProgressDialog( )

    def testProgressDialog( ):
        import random
        number = [x for x in range(1, 101)]
        progresses = [ ]
        while len(progresses) <= 20: progresses.append(random.choice(number))
        app = QtWidgets.QApplication([])
        w = ProgressDialog( )
        for i in progresses:
            pb = DownloadProgressWidget(text='download')
            pb.set_max(100)
            pb.set_value(i)
            w.addProgressbar(pb)

        for i in progresses:
            pb = UploadProgressWidget(text='upload')
            pb.set_max(100)
            pb.set_value(i)
            w.addProgressbar(pb)
        w.show( )
        app.exec_( )

    # testProgressDialog( )
    testLoinDialog( )
    testDisconnectDialog()
