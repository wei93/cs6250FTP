import socket, sys, os, threading, time, argparse, random, string#, hashlib
from get_fileProperty import fileProperty

defAddr = '127.0.0.1'
defPort = 12111
terminated = False
threadsPool = []
USERS = {'yaling':'true'}

def hash(self, username, challenge):
        m = hashlib.md5()
        m.update(username + USERS[username] + challenge);
        return m.digest()

def log(msg, clientAddr = None):
    if clientAddr == None:
        print('\033[92m[%s]\033[0m %s' % (time.strftime(r'%H:%M:%S, %m.%d.%Y'), msg))
    else:
        print('\033[92m[%s] %s:%d\033[0m %s' % (time.strftime(r'%H:%M:%S, %m.%d.%Y'), clientAddr[0], clientAddr[1], msg))

class DataConnSockListener(threading.Thread):
    def __init__(self, server, exitThreadFlag):
        super().__init__()
        self.server = server
        self.listenSocket = server.dataConnListenSocket
        self.exitThreadFlag = exitThreadFlag
        self.daemon = True 
    def run(self):
        self.listenSocket.settimeout(1) 
        while True:
            try:
                (dataSocket, clientAddr) = self.listenSocket.accept()
            except (socket.timeout):
                pass
            except (socket.error): 
            	log('Error with DataConnListenSocket')
            	break
            else:
                if self.server.dataSocket != None: # Only one data connection at a time
                    dataSocket.close()
                    log('Data connection refused from client %s:%d.' % (clientAddr[0], clientAddr[1]), self.server.clientAddr)
                else:
                    self.server.dataSocket = dataSocket
                    log('Data connection accepted from client %s:%d.' % (clientAddr[0], clientAddr[1]), self.server.clientAddr)
            finally:
            	if self.exitThreadFlag:
            		log('Terminating current dataConnSockListener thread.', self.server.clientAddr)
            		break

class FTPServer(threading.Thread):
    def __init__(self, controlSocket, clientAddr, exitThreadFlag):
        super().__init__()
        global USERS                            # Stored usernames and passwords
        self.controlSocket = controlSocket      # Control connection socket served by current server thread
        self.clientAddr = clientAddr            # Client address of control connection
        self.bufferSize = 2048				
        self.daemon = True 
        self.dataConnSockListener = None	    # Data connection socket listener thread
        self.dataConnListenSocket = None	    # The listening socket to accept data connection from the client
        self.dataSocket = None				    # The accepted data connection socket from client
        self.dataAddr = '127.0.0.1'			    # Data connection server address
        self.dataPort = None				    # Data connection server port (along with address, tells client-DTP where to connect to)
        self.username = ''
        self.loggedIn = False
        self.cwd = os.getcwd()				    # Record current working directory of FTP
        self.type = 'Binary'				    # Data Type
        self.dataMode = 'PORT'				    # Data connection mode, only PASV is supported
        self.exitThreadFlag = exitThreadFlag
    def run(self):
        self.controlSocket.send(b'220 Service ready for new user.\r\n')
        while True:
            if self.exitThreadFlag:
                self.controlSocket.close()
                if self.dataConnSockListener != None:
                    self.dataConnSockListener.exitThreadFlag = True
                log('Terminating from keyboard interrupt for current control thread.', self.clientAddr)
                break
            command = self.controlSocket.recv(self.bufferSize).decode('ascii')
            if command == '': # Server standby
                continue
            curuser = self.username if self.loggedIn else 'None'
            log('[User ' + curuser + '] ' + command.strip(), self.clientAddr)
            command_len = len(command.split())
            cmd = command.split()[0].upper()
            if cmd == 'HELP': 
                self.controlSocket.send(b'214 Commands supported: HELP USER PASS PASV PWD CWD NLST RETR STOR QUIT\r\n')         
            elif cmd == 'USER':
                if command_len < 2:
                    self.controlSocket.send(b'USER: 501 Syntax error in parameters or arguments.\r\n')
                else:
                    if(None==USERS.get(command.split()[1])):
                        self.controlSocket.send(b'530 Not logged in. Username does not exist\r\n')
                    else:
                        #challenge = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(64))
                        self.username = command.split()[1]
                        self.controlSocket.send(('331 Username okay, need password.\r\n').encode('ascii'))
                        #self.controlSocket.send(.encode('ascii'))
                        self.loggedIn = False
            elif cmd == 'PASS':
                if self.username == '':
                    self.controlSocket.send(b'503 Bad sequence of commands. Need USER first.\r\n')
                else:
                    if command_len < 2:
                        self.controlSocket.send(b'501 PASS: Syntax error in parameters or arguments.\r\n')
                    else:
                    	if command.split()[1] != USERS[self.username]:
                            self.controlSocket.send(b'530 Not logged in. Password not correct.\r\n')
                    	else:
                            self.controlSocket.send(b'230 User logged in.\r\n')
                            self.loggedIn = True
            elif cmd == 'PWD':
                if not self.loggedIn:
                    self.controlSocket.send(b'530 Not logged in.\r\n')
                else:
                	'''May change the format of msg here to accommodate the UI'''
                	self.controlSocket.send(('250 "%s" is the current working directory.\r\n' % self.cwd).encode('ascii'))
            elif cmd == 'CWD':
                if not self.loggedIn:
                    self.controlSocket.send(b'530 Not logged in.\r\n')
                elif command_len < 2:
                    self.controlSocket.send(('250 "%s" is the current working directory.\r\n' % self.cwd).encode('ascii'))
                else:
                    serverDir = os.getcwd()
                    os.chdir(self.cwd)
                    newDir = command.split()[1]
                    try:
                        os.chdir(newDir) # Verify new directory is valid
                    except (OSError):
                        self.controlSocket.send(b'550 Requested action not taken. File unavailable (e.g., file not found, no access).\r\n')
                    else:
                        self.cwd = os.getcwd()
                        self.controlSocket.send(('250 "%s" is the current directory now.\r\n' % self.cwd).encode('ascii'))
                    os.chdir(serverDir)
            elif cmd == 'TYPE': 
                if not self.loggedIn:
                    self.controlSocket.send(b'530 Not logged in.\r\n')
                elif command_len < 2:
                    self.controlSocket.send(b'501 TYPE: Syntax error in parameters or arguments.\r\n')
                elif command.split()[1] == 'I':
                    self.type = 'Binary'
                    self.controlSocket.send(b'200 Command OK. Type set to: Binary.\r\n')
                else:
                	self.controlSocket.send(b'504 Command not implemented for that parameter.\r\n')
            elif cmd == 'PASV': # currently only support PASV
                if not self.loggedIn:
                    self.controlSocket.send(b'530 Not logged in.\r\n')
                else:
                    self.dataMode = 'PASV'
                    if self.dataConnListenSocket != None: # Close existing data connection listening socket
                        self.dataConnListenSocket.close()
                    self.dataConnListenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
                    self.dataConnListenSocket.bind((self.dataAddr, 0))
                    self.dataPort = self.dataConnListenSocket.getsockname()[1]
                    self.dataConnListenSocket.listen(5)
                    self.dataConnSockListener = DataConnSockListener(self,False)
                    threadsPool.append(self.dataConnSockListener)
                    self.dataConnSockListener.start()
                    #time.sleep(0.5)
                    daddr_split = self.dataAddr.split('.')
                    self.controlSocket.send(('227 Entering passive mode (%s,%s,%s,%s,%d,%d).\r\n' % (daddr_split[0], daddr_split[1], daddr_split[2], daddr_split[3], int(self.dataPort / 256), self.dataPort % 256)).encode('ascii'))
            elif cmd == 'NLST': 
                time.sleep(0.5) # Wait for connection to set up
                if not self.loggedIn:
                    self.controlSocket.send(b'530 NLST: Not logged in.\r\n')
                elif self.dataMode == 'PASV' and self.dataSocket != None: # Only PASV implemented
                    self.controlSocket.send(b'125 NLST: Data connection already open. Transfer starting.\r\n')
                    dirs = os.listdir(self.cwd)
                    finfo = []
                    for l in dirs:
                        fp = os.path.join(self.cwd,l)
                        finfo.append(fileProperty(fp))
                        #finfo.append(fp)
                        #log(fileProperty(fp), self.clientAddr)
                    lsla = '\r\n'.join(finfo) + '\r\n'
                    self.dataSocket.send(lsla.encode('ascii'))
                    self.controlSocket.send(b'226 NLST: Closing data connection. Requested file action successful (for example, file transfer or file abort).\r\n')
                    self.dataSocket.close() # Close data socket once current command is complete
                    self.dataSocket = None
                else:
                    self.controlSocket.send(b'425 NLST: Cant open data connection.\r\n')
            elif cmd == 'RETR':
                time.sleep(1) # Wait for connection to set up
                if not self.loggedIn:
                    self.controlSocket.send(b'530 RETR: Not logged in.\r\n')
                elif command_len < 2:
                    self.controlSocket.send(b'501 RETR: Syntax error in parameters or arguments.\r\n')
                elif self.dataMode == 'PASV' and self.dataSocket != None: # Only PASV implemented
                    self.controlSocket.send(b'125 RETR: Data connection already open; transfer starting.\r\n')
                    fName = command.split()[1]
                    serverDir = os.getcwd()
                    try:
                        os.chdir(self.cwd)
                        self.dataSocket.send(open(fName, 'rb').read())
                    except (IOError):
                    	log("RETR: IOError: file unavailable")
                    	self.controlSocket.send(b'550 RETR: Requested action not taken. File unavailable (e.g., file not found, no access).\r\n')
                    self.controlSocket.send(b'226 RETR: Closing data connection. Requested file action successful (i.e. file retrieval).\r\n')
                    self.dataSocket.close()
                    self.dataSocket = None
                    os.chdir(serverDir)
                else:
                    self.controlSocket.send(b'425 RETR: Cant open data connection.\r\n')
            elif cmd == 'STOR':
                #time.sleep(0.5) # Wait for connection to set up
                if not self.loggedIn:
                    self.controlSocket.send(b'530 STOR: Not logged in.\r\n')
                elif command_len < 2:
                    self.controlSocket.send(b'501 STOR: Syntax error in parameters or arguments.\r\n')
                elif self.dataMode == 'PASV' and self.dataSocket != None: 
                    self.controlSocket.send(b'125 STOR: Data connection already open; transfer starting.\r\n')
                    serverDir = os.getcwd()
                    os.chdir(self.cwd)
                    fName = command.split()[1]
                    storedFile = open(fName, 'wb')
                    time.sleep(0.5) # Wait for data to come
                    self.dataSocket.setblocking(False) 
                    while True:
                        try:
                            data = self.dataSocket.recv(self.bufferSize)
                            if data == b'': 
                            	break
                            storedFile.write(data)
                        except (socket.error): # Connection closed
                            break
                    storedFile.close()
                    self.controlSocket.send(b'226 STOR: Closing data connection. Requested file action successful (i.e. file uploading).\r\n')
                    self.dataSocket.close()
                    self.dataSocket = None
                    os.chdir(serverDir)
                else:
                    self.controlSocket.send(b'425 STOR: Cant open data connection.\r\n')
            elif cmd == 'QUIT': 
                	self.controlSocket.send(b'221 Control socket closed. Logged out.\r\n')
                	self.controlSocket.close()
                	self.dataConnSockListener.exitThreadFlag = True
                	log('Client logged out. Server and DataScoketListener instances stopping', self.clientAddr)
                	break
            else:
                    self.controlSocket.send(b'502 Command not implemented.\r\n')

def check_command():
    global terminated
    while True:
        command = input("------------------------------------------------------------------------------------------\r\nYou need to enter 'q' to terminate all running server threads and quit the program: \r\n------------------------------------------------------------------------------------------\r\n")
        if(command == 'q'):
            terminated = True
            break
    #log('Terminated all children threads. Now you can control-c the program')

if __name__ == '__main__': # main thread
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) #default socket to accept client control connections
    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serverSocket.bind((defAddr, defPort))
    serverSocket.listen(5)
    check = threading.Thread(target=check_command)
    check.start()
    log('Server started.')
    serverSocket.settimeout(1)
    while True:
        try:
            (controlSocket, clientAddr) = serverSocket.accept()
        except (socket.timeout):
            pass
        except (socket.error): 
            log('Error with DataConnListenSocket')
            break
        else:
            ftpsv = FTPServer(controlSocket, clientAddr, False)
            threadsPool.append(ftpsv)
            ftpsv.start() # starting one child thread of the server for this coming control sock
            log("Connection accepted.", clientAddr)
        finally:
            if(terminated):
                log("Terminating the entire program.")
                break
    for t in threadsPool:
        t.exitThreadFlag = True
        t.join()