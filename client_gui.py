#!/usr/bin/env python
#--*--encoding:utf8--*--

from PyQt5 import QtGui
from PyQt5.QtCore import *
from PyQt5 import QtWidgets
from get_fileProperty import fileProperty
from dialog import loginDialog, ProgressDialog, DownloadProgressWidget, UploadProgressWidget, disconnectDialog, loginInSuccess, failLogin
from client_ftp import client_ftp
import atexit
import time
import os
import sys
import threading

app_icon_path = os.path.join(os.path.dirname(__file__), 'icons')

defAddr = '127.0.0.1'
defPort = 12111

class BaseGuiWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(BaseGuiWidget, self).__init__(parent)
        self.resize(600, 600)
        self.createFileListWidget( )
        self.createGroupboxWidget( )

        # setting column width
        for pos, width in enumerate((150, 70, 70, 70, 90, 90)):
            self.fileList.setColumnWidth(pos, width)

        self.mainLayout = QtWidgets.QVBoxLayout( )
        self.mainLayout.addWidget(self.groupBox)
        self.mainLayout.addWidget(self.fileList)
        #self.mainLayout.setMargin(5)
        self.setLayout(self.mainLayout)

        # completer for path edit
        completer      = QtWidgets.QCompleter( )
        self.completerModel = QStringListModel( )
        completer.setModel(self.completerModel)
        self.pathEdit.setCompleter(completer)


    def createGroupboxWidget(self):
        self.pathEdit   = QtWidgets.QLineEdit( )
        self.homeButton = QtWidgets.QPushButton( )
        self.backButton = QtWidgets.QPushButton( )
        self.nextButton = QtWidgets.QPushButton( )
        self.hideButton = QtWidgets.QPushButton( )
        self.refreshButton = QtWidgets.QPushButton()
        self.homeButton.setIcon(QtGui.QIcon(os.path.join(app_icon_path, 'home.png')))
        self.backButton.setIcon(QtGui.QIcon(os.path.join(app_icon_path, 'back.png')))
        self.nextButton.setIcon(QtGui.QIcon(os.path.join(app_icon_path, 'next.png')))
        self.hideButton.setIcon(QtGui.QIcon(os.path.join(app_icon_path, 'hide.png')))
        self.refreshButton.setIcon(QtGui.QIcon(os.path.join(app_icon_path, 'refresh.png')))
        self.homeButton.setIconSize(QSize(20, 20))
        self.pathEdit.setEnabled(False)
        self.homeButton.setEnabled(False)
        self.backButton.setEnabled(False)
        self.nextButton.setEnabled(False)
        self.hbox1 = QtWidgets.QHBoxLayout( )
        self.hbox2 = QtWidgets.QHBoxLayout( )
        self.hbox1.addWidget(self.homeButton)
        self.hbox1.addWidget(self.pathEdit)
        self.hbox2.addWidget(self.backButton)
        self.hbox2.addWidget(self.nextButton)
        self.hbox2.addWidget(self.hideButton)
        self.hbox2.addWidget(self.refreshButton)
        self.hbox2.addSpacerItem(QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))

        self.gLayout = QtWidgets.QVBoxLayout( )
        self.gLayout.addLayout(self.hbox1)
        self.gLayout.addLayout(self.hbox2)
        self.gLayout.setSpacing(5)
        #self.gLayout.setMargin(5)
        self.groupBox = QtWidgets.QGroupBox('Widgets')
        self.groupBox.setLayout(self.gLayout)

    def createFileListWidget(self):
        self.fileList = QtWidgets.QTreeWidget()
        self.fileList.setIconSize(QSize(20, 20))
        self.fileList.setRootIsDecorated(False)
        self.fileList.setHeaderLabels(('Name', 'Size', 'Owner', 'Group', 'Time', 'Mode'))
        self.fileList.header().setStretchLastSection(False)


class LocalGuiWidget(BaseGuiWidget):
    def __init__(self, parent=None):
        BaseGuiWidget.__init__(self, parent)
        self.uploadButton  = QtWidgets.QPushButton( )
        self.connectButton = QtWidgets.QPushButton( )
        self.disconnectButton = QtWidgets.QPushButton()
        self.uploadButton.setIcon(QtGui.QIcon(os.path.join(app_icon_path, 'upload.png')))
        self.connectButton.setIcon(QtGui.QIcon(os.path.join(app_icon_path, 'connect.png')))
        self.disconnectButton.setIcon(QtGui.QIcon(os.path.join(app_icon_path, 'disconnect.png')))
        self.uploadButton.setEnabled(False)
        self.hbox2.addWidget(self.uploadButton)
        self.hbox2.addWidget(self.connectButton)
        self.hbox2.addWidget(self.disconnectButton)
        self.groupBox.setTitle('Local')


class RemoteGuiWidget(BaseGuiWidget):
    def __init__(self, parent=None):
        BaseGuiWidget.__init__(self, parent)
        self.downloadButton = QtWidgets.QPushButton( )
        self.downloadButton.setIcon(QtGui.QIcon(os.path.join(app_icon_path, 'download.png')))
        self.homeButton.setIcon(QtGui.QIcon(os.path.join(app_icon_path, 'internet.png')))
        self.downloadButton.setEnabled(False)
        self.hbox2.addWidget(self.downloadButton)
        self.groupBox.setTitle('Remote')


class FtpClient(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(FtpClient, self).__init__(parent)
        self.ftp_client = client_ftp.FTPClient()
        self.hidden = True
        self.hiddenRemote = True
        self.setupGui( )
        #self.initialize()
        self.downloads=[ ]
        atexit.register(self.ftp_client.quit)

        self.remote.homeButton.clicked.connect(self.cdToRemoteHomeDirectory)
        self.remote.fileList.itemDoubleClicked.connect(self.cdToRemoteDirectory)
        self.remote.fileList.itemClicked.connect(lambda: self.remote.downloadButton.setEnabled(True))
        self.remote.backButton.clicked.connect(self.cdToRemoteBackDirectory)
        self.remote.nextButton.clicked.connect(self.cdToRemoteNextDirectory)
        self.remote.downloadButton.clicked.connect(self.download)
        self.remote.hideButton.clicked.connect(self.hideFileRemote)
        self.remote.refreshButton.clicked.connect(self.updateRemoteFileList)

        #QObject.connect(self.remote.pathEdit, pyqtSignal('returnPressed( )'), self.cdToRemotePath)

        self.local.homeButton.clicked.connect(self.cdToLocalHomeDirectory)
        self.local.fileList.itemDoubleClicked.connect(self.cdToLocalDirectory)
        self.local.fileList.itemClicked.connect(lambda: self.local.uploadButton.setEnabled(True))
        self.local.backButton.clicked.connect(self.cdToLocalBackDirectory)
        self.local.nextButton.clicked.connect(self.cdToLocalNextDirectory)
        self.local.uploadButton.clicked.connect(self.upload)
        self.local.connectButton.clicked.connect(self.connect)
        self.local.hideButton.clicked.connect(self.hideFile)
        self.local.disconnectButton.clicked.connect(self.disconnectRemote)
        self.local.disconnectButton.setEnabled(False)
        self.local.refreshButton.clicked.connect(self.updateLocalFileList)
        #QObject.connect(self.local.pathEdit, pyqtSignal('returnPressed( )'), self.cdToLocalPath)

        self.progressDialog = ProgressDialog(self)

    def setupGui(self):
        self.resize(1200, 650)
        self.local  = LocalGuiWidget(self)
        self.remote = RemoteGuiWidget(self)
        mainLayout = QtWidgets.QHBoxLayout( )
        mainLayout.addWidget(self.local)
        mainLayout.addWidget(self.remote)
        mainLayout.setSpacing(0)
        #mainLayout.setMargin(5)
        self.setLayout(mainLayout)

    def initialize(self):
        # self.ftp_client.connect(defAddr, defPort)
        # self.ftp_client.login("yaling", "true")
        # self.ftp_client.pasv()

        self.localBrowseRec    = [ ]
        self.remoteBrowseRec   = [ ]
        remoteOriginPath = self.ftp_client.pwd().strip()
        self.remotePwd               = remoteOriginPath[5:remoteOriginPath.index('" ')]
        self.local_pwd         = os.getenv('HOME')
        self.remoteOriginPath  = self.remotePwd
        self.localOriginPath   = self.local_pwd
        self.localBrowseRec.append(self.local_pwd)
        self.remoteBrowseRec.append(self.remotePwd)
        self.downloadToRemoteFileList( )
        self.loadToLocaFileList( )
        self.local.pathEdit.setText(self.localOriginPath)

    def connect(self):
        username_password = loginDialog()
        print(username_password[0])
        print(username_password[1])
        if not username_password:
            pass
        else:
            if not self.ftp_client.isConnected():
                self.ftp_client.connect(defAddr, defPort)
            try:
                #self.ftp_client.login("yaling", "true")
                self.ftp_client.login(username_password[0], username_password[1])
                self.ftp_client.pasv()
                self.local.connectButton.setEnabled(False)
                self.local.uploadButton.setEnabled(True)
                self.local.disconnectButton.setEnabled(True)
                self.initialize()
            except :
                msgBox = QtWidgets.QMessageBox();
                msgBox.setIcon(QtWidgets.QMessageBox.Warning)
                msgBox.setText("Something Wrong with your password or username");
                msgBox.exec_();
                #failLogin()


    def disconnectRemote(self):
        self.local.uploadButton.setEnabled(False)
        self.remote.fileList.clear()
        self.ftp_client.quit()
        self.local.disconnectButton.setEnabled(False)
        self.local.connectButton.setEnabled(True)
        msgBox = QtWidgets.QMessageBox();
        msgBox.setIcon(QtWidgets.QMessageBox.Information)
        msgBox.setText("You have disconnected with server");
        msgBox.exec_();

    #---------------------------------------------------------------------------------#
    ## the downloadToRemoteFileList with loadToLocalFileList is doing the same thing ##
    #---------------------------------------------------------------------------------#
    def downloadToRemoteFileList(self):
        """
        download file and directory list from FTP Server
        """
        self.remoteWordList = [ ]
        self.remoteDir      = { }
        remoteFileList = self.ftp_client.nlst().split("\r\n")
        for f in remoteFileList:
            self.addItemToRemoteFileList(f)
        self.remote.completerModel.setStringList(self.remoteWordList)

    def loadToLocaFileList(self):
        """
        load file and directory list from local computer
        """
        self.localWordList = [ ]
        self.localDir      = { }
        for f in os.listdir(self.local_pwd):
            if (f.startswith('~') or f.startswith('.') or f.startswith('$')) and self.hidden:
                continue
            pathname = os.path.join(self.local_pwd, f)
            self.addItemToLocalFileList(fileProperty(pathname))
        self.local.completerModel.setStringList(self.localWordList)

    def addItemToRemoteFileList(self, content):
        if content:
            mode, num, owner, group, size, date, filename = self.parseFileInfo(content)
            if (filename.startswith('~') or filename.startswith('.') or filename.startswith('$')) and self.hiddenRemote:
                return
            if content.startswith('d'):
                icon     = QtGui.QIcon(os.path.join(app_icon_path, 'folder.png'))
                pathname = os.path.join(self.remotePwd, filename)
                self.remoteDir[ pathname] = True
                self.remoteWordList.append(filename)

            else:
                icon = QtGui.QIcon(os.path.join(app_icon_path, 'file.png'))

            item = QtWidgets.QTreeWidgetItem( )
            item.setIcon(0, icon)
            for n, i in enumerate((filename, size, owner, group, date, mode)):
                item.setText(n, i)

            self.remote.fileList.addTopLevelItem(item)
        if not self.remote.fileList.currentItem():
            self.remote.fileList.setCurrentItem(self.remote.fileList.topLevelItem(0))
            self.remote.fileList.setEnabled(True)

    def addItemToLocalFileList(self, content):
        if content:
            mode, num, owner, group, size, date, filename = self.parseFileInfo(content)
            if content.startswith('d'):
                icon     = QtGui.QIcon(os.path.join(app_icon_path, 'folder.png'))
                pathname = os.path.join(self.local_pwd, filename)
                self.localDir[ pathname ] = True
                self.localWordList.append(filename)

            else:
                icon = QtGui.QIcon(os.path.join(app_icon_path, 'file.png'))

            item  = QtWidgets.QTreeWidgetItem( )
            item.setIcon(0, icon)
            for n, i in enumerate((filename, size, owner, group, date, mode)):
                #print((filename, size, owner, group, date, mode))
                item.setText(n, i)
            self.local.fileList.addTopLevelItem(item)
        if not self.local.fileList.currentItem():
            self.local.fileList.setCurrentItem(self.local.fileList.topLevelItem(0))
            self.local.fileList.setEnabled(True)

    def parseFileInfo(self, file):
        """
        parse files information "drwxr-xr-x 2 root wheel 1024 Nov 17 1993 lib" result like follower
                                "drwxr-xr-x", "2", "root", "wheel", "1024 Nov 17 1993", "lib"
        """
        item = [f for f in file.split(' ') if f != '']
        if not item:
            return (None, None, None, None, None, None, None)
        mode, num, owner, group, size, date, filename = (
            item[0], item[1], item[2], item[3], item[4], ' '.join(item[5:8]), ' '.join(item[8:]))
        return (mode, num, owner, group, size, date, filename)

    #--------------------------#
    ## for remote file system ##
    #--------------------------#
    # def cdToRemotePath(self):
    #     pathname = str(self.remote.pathEdit.text( ).toUtf8( ))
    #     try:
    #         self.ftp.cwd(pathname)
    #     except:
    #         return
    #     self.cwd = pathname.startswith(os.path.sep) and pathname or os.path.join(self.remotePwd, pathname)
    #     self.updateRemoteFileList( )
    #     self.remote.backButton.setEnabled(True)
    #     if os.path.abspath(pathname) != self.remoteOriginPath:
    #         self.remote.homeButton.setEnabled(True)
    #     else:
    #         self.remote.homeButton.setEnabled(False)

    def cdToRemoteDirectory(self, item, column):
        self.remote.nextButton.setEnabled(False)
        pathname = os.path.join(self.remotePwd, str(item.text(0)))
        if not self.isRemoteDir(pathname):
            return
        self.remoteBrowseRec.append(pathname)
        print(pathname)
        self.ftp_client.cwd(pathname)
        print(self.ftp_client.pwd())
        self.remotePwd= pathname
        #print(self.pwd())
        #remoteOriginPath = self.pwd().strip()
        #self.pwd = remoteOriginPath[5:remoteOriginPath.index('" ')]


        self.updateRemoteFileList( )
        self.remote.backButton.setEnabled(True)
        if pathname != self.remoteOriginPath:
            self.remote.homeButton.setEnabled(True)

    def cdToRemoteBackDirectory(self):
        pathname = self.remoteBrowseRec[ self.remoteBrowseRec.index(self.remotePwd)-1 ]
        if pathname != self.remoteBrowseRec[0]:
            self.remote.backButton.setEnabled(True)
        else:
            self.remote.backButton.setEnabled(False)

        if pathname != self.remoteOriginPath:
            self.remote.homeButton.setEnabled(True)
        else:
            self.remote.homeButton.setEnabled(False)
        self.remote.nextButton.setEnabled(True)
        self.remotePwd = pathname
        self.ftp_client.cwd(pathname)
        self.updateRemoteFileList( )

    def cdToRemoteNextDirectory(self):
        pathname = self.remoteBrowseRec[self.remoteBrowseRec.index(self.remotePwd)+1]
        if pathname != self.remoteBrowseRec[-1]:
            self.remote.nextButton.setEnabled(True)
        else:
            self.remote.nextButton.setEnabled(False)
        self.remote.backButton.setEnabled(True)
        if pathname != self.remoteOriginPath:
            self.remote.homeButton.setEnabled(True)
        else:
            self.remote.homeButton.setEnabled(False)
        self.remote.backButton.setEnabled(True)
        self.remotePwd = pathname
        self.ftp_client.cwd(pathname)
        self.updateRemoteFileList( )

    def cdToRemoteHomeDirectory(self):
        self.ftp_client.cwd(self.remoteOriginPath)
        self.remotePwd = self.remoteOriginPath
        self.updateRemoteFileList( )
        self.remote.homeButton.setEnabled(False)

    #-------------------------#
    ## for local file system ##
    #-------------------------#
    def hideFile(self):
        self.hidden = not self.hidden
        self.updateLocalFileList()
    def hideFileRemote(self):
        self.hiddenRemote = not self.hiddenRemote
        self.updateRemoteFileList()

    def cdToLocalPath(self):
        pathname = str(self.local.pathEdit.text( ).toUtf8( ))
        pathname = pathname.endswith(os.path.sep) and pathname or os.path.join(self.local_pwd, pathname)
        if not os.path.exists(pathname) and not os.path.isdir(pathname):
            return

        else:
            self.localBrowseRec.append(pathname)
            self.local_pwd = pathname
            self.updateLocalFileList( )
            self.local.backButton.setEnabled(True)
            print(pathname, self.localOriginPath)
            if os.path.abspath(pathname) != self.localOriginPath:
                self.local.homeButton.setEnabled(True)
            else:
                self.local.homeButton.setEnabled(False)

    def cdToLocalDirectory(self, item, column):
        self.local.nextButton.setEnabled(False)
        pathname = os.path.join(self.local_pwd, str(item.text(0)))
        if not self.isLocalDir(pathname):
            return
        self.localBrowseRec.append(pathname)
        self.local_pwd = pathname
        self.updateLocalFileList( )
        self.local.backButton.setEnabled(True)
        if pathname != self.localOriginPath:
            self.local.homeButton.setEnabled(True)

    def cdToLocalBackDirectory(self):
        pathname = self.localBrowseRec[ self.localBrowseRec.index(self.local_pwd)-1 ]
        if pathname != self.localBrowseRec[0]:
            self.local.backButton.setEnabled(True)
        else:
            self.local.backButton.setEnabled(False)
        if pathname != self.localOriginPath:
            self.local.homeButton.setEnabled(True)
        else:
            self.local.homeButton.setEnabled(False)
        self.local.nextButton.setEnabled(True)
        self.local_pwd = pathname
        self.updateLocalFileList( )

    def cdToLocalNextDirectory(self):
        pathname = self.localBrowseRec[self.localBrowseRec.index(self.local_pwd)+1]
        if pathname != self.localBrowseRec[-1]:
            self.local.nextButton.setEnabled(True)
        else:
            self.local.nextButton.setEnabled(False)
        if pathname != self.localOriginPath:
            self.local.homeButton.setEnabled(True)
        else:
            self.local.homeButton.setEnabled(False)
        self.local.backButton.setEnabled(True)
        self.local_pwd = pathname
        self.updateLocalFileList( )

    def cdToLocalHomeDirectory(self):
        self.local_pwd = self.localOriginPath
        self.updateLocalFileList( )
        self.local.homeButton.setEnabled(False)

    def updateLocalFileList(self):
        self.local.pathEdit.setText(self.local_pwd)
        self.local.fileList.clear( )
        self.loadToLocaFileList( )

    def updateRemoteFileList(self):
        self.remote.pathEdit.setText(self.remotePwd)
        self.remote.fileList.clear( )
        self.downloadToRemoteFileList( )

    def isLocalDir(self, dirname):
        return self.localDir.get(dirname, None)

    def isRemoteDir(self, dirname):
        return self.remoteDir.get(dirname, None)

    def download(self):
        item     = self.remote.fileList.currentItem( )
        #srcfile  = os.path.join(self.remotePwd, str(item.text(0)))
        filesize = int(item.text(1))
        dstfile  = os.path.join(self.local_pwd, str(item.text(0)))
        print(item.text(0))
        self.ftp_client.retr(item.text(0))

        time.sleep(5)
        
        curr_directory_path = self.local_pwd
        commend_line = "mv " + str(item.text(0)) + " " + curr_directory_path
        os.system(commend_line)

        self.updateLocalFileList()
        pb = DownloadProgressWidget(text=dstfile)
        pb.set_max(filesize)
        self.progressDialog.addProgressbar(pb)
        self.progressDialog.show( )

        # file = open(dstfile, 'wb')
        #
        # def __callback(data):
        #     pb.set_value(data)
        #     file.write(data)
        #
        # # create a new ftp connection
        # def __download( ):
        #     fp = ftp( )
        #     fp.connect(host=self.ftp.host, port=self.ftp.port, timeout=self.ftp.timeout)
        #     fp.login(user=self.ftp.user, passwd=self.ftp.passwd)
        #     fp.retrbinary(cmd='RETR '+srcfile, callback=__callback)
        # threading.Thread(target=__download).start( )

    def upload(self):
        item     = self.local.fileList.currentItem( )
        srcfile  = os.path.join(self.local_pwd, str(item.text(0)))
        self.ftp_client.stor(srcfile)
        time.sleep(5)
        self.updateRemoteFileList()
        filesize = int(item.text(1))
        #dstfile  = os.path.join(self.remotePwd, str(item.text(0)))

        pb = UploadProgressWidget(text=srcfile)
        pb.set_max(filesize)
        pb.set_max(100)
        self.progressDialog.addProgressbar(pb)
        self.progressDialog.show( )

        def _upload_test():
            pb.set_value(10)
            time.sleep(2)
            pb.set_value(50)
            time.sleep(3)
            pb.set_value(40)
            if pb.get_totalValue() == pb.get_maxValue():
                pb.remove_all()
                self.progressDialog.removeProgressbar(pb)

        threading.Thread(target=_upload_test).start()

        # file = open(srcfile, 'rb')
        #
        # def __callback(buf):
        #     pb.set_value(buf)
        #
        # def __upload( ):
        #     fp = ftp( )
        #     fp.connect(host=self.ftp.host, port=self.ftp.port, timeout=self.ftp.timeout)
        #     fp.login(user=self.ftp.user, passwd=self.ftp.passwd)
        #     fp.storbinary(cmd='STOR '+dstfile, fp=file, callback=__callback)
        # threading.Thread(target=__upload).start( )


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    client = FtpClient( )
    client.show( )
    app.exec_( )
