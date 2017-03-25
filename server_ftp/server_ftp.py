import socket, sys, os, threading, time, argparse

defAddr = '127.0.0.1'
defPort = 12111
terminated = False
threadsPool = []

def log(msg, clientAddr = None):
    if clientAddr == None:
        print('\033[92m[%s]\033[0m %s' % (time.strftime(r'%H:%M:%S, %m.%d.%Y'), msg))
    else:
        print('\033[92m[%s] %s:%d\033[0m %s' % (time.strftime(r'%H:%M:%S, %m.%d.%Y'), clientAddr[0], clientAddr[1], msg))

class DataConnSockListener(threading.Thread):
    ''' Asynchronously accepts data connection per client '''
    def __init__(self, server, exitThreadFlag):
        super().__init__()
        self.daemon = True 
        self.server = server
        self.listenSocket = server.dataConnListenSocket
        self.exitThreadFlag = exitThreadFlag
    def run(self):
        self.listenSocket.settimeout(1.0) # Check for every 1 second
        while True:
            try:
                (dataSocket, clientAddr) = self.listenSocket.accept()
            except (socket.timeout):
                pass
            except (socket.error): 
            	log('Error with DataConnListenSocket')
            	break
            else:
                if self.server.dataSocket != None: # Existing data connection not closed, cannot accept
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
        self.controlSocket = controlSocket  # Control connection socket served by current server thread
        self.clientAddr = clientAddr        # Client address of control connection
        self.bufferSize = 1024				
        self.daemon = True 
        self.dataConnSockListener = None	# Data connection socket listener thread
        self.dataConnListenSocket = None	# The listening socket to accept data connection from the client
        self.dataSocket = None				# The accepted data connection socket from client
        self.dataAddr = '127.0.0.1'			# Data connection server address
        self.dataPort = None				# Data connection server port (along with address, tells client-DTP where to connect to)
        self.username = ''
        self.loggedIn = False
        self.cwd = os.getcwd()				# Record current working directory of FTP
        self.type = 'Binary'				# Data Type
        self.dataMode = 'PORT'				# Data connection mode, only PASV is supported
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
            if command == '': # Connection closed
                #self.controlSocket.close()
                #log('Client disconnected.', self.clientAddr)
                #break
                continue
            curuser = self.username if self.loggedIn else 'None'
            log('[user ' + curuser + '] ' + command.strip(), self.clientAddr)
            cmd = command.split()[0].upper()
            if cmd == 'HELP': 
                self.controlSocket.send(b'214 Commands supported: HELP USER PASS PASV TYPE PWD CWD NLST RETR STOR QUIT\r\n')         
            elif cmd == 'USER':
                if len(command.split()) < 2:
                    self.controlSocket.send(b'501 Syntax error in parameters or arguments.\r\n')
                else:
                    self.username = command.split()[1]
                    self.controlSocket.send(b'331 Username okay, need password.\r\n')
                    self.loggedIn = False
            elif cmd == 'PASS':
                if self.username == '':
                    self.controlSocket.send(b'503 Bad sequence of commands.\r\n')
                else:
                    if len(command.split()) < 2:
                        self.controlSocket.send(b'501 Syntax error in parameters or arguments.\r\n')
                    else:
                    	'''TODO: authenticate the user'''
                    	self.controlSocket.send(b'230 User logged in.\r\n')
                    	self.loggedIn = True
            elif cmd == 'PWD':
                if not self.loggedIn:
                    self.controlSocket.send(b'530 Not logged in.\r\n')
                else:
                	'''May change the format of msg here to accommodate the UI'''
                	self.controlSocket.send(('257 "%s" is the current directory.\r\n' % self.cwd).encode('ascii'))
            elif cmd == 'CWD':
                if not self.loggedIn:
                    self.controlSocket.send(b'530 Not logged in.\r\n')
                elif len(command.split()) < 2:
                    self.controlSocket.send(('250 "%s" is the current directory.\r\n' % self.cwd).encode('ascii'))
                else:
                    serverDir = os.getcwd()
                    os.chdir(self.cwd)
                    newDir = command.split()[1]
                    try:
                        os.chdir(newDir)
                    except (OSError):
                        self.controlSocket.send(b'550 Requested action not taken. File unavailable (e.g., file not found, no access).\r\n')
                    else:
                        self.cwd = os.getcwd()
                        self.controlSocket.send(('250 "%s" is the current directory now.\r\n' % self.cwd).encode('ascii'))
                    os.chdir(serverDir)
            elif cmd == 'TYPE': # currently only I is supported
                if not self.loggedIn:
                    self.controlSocket.send(b'530 Not logged in.\r\n')
                elif len(command.split()) < 2:
                    self.controlSocket.send(b'501 Syntax error in parameters or arguments.\r\n')
                elif command.split()[1] == 'I':
                    self.type = 'Binary'
                    self.controlSocket.send(b'200 Command OK. Type set to: Binary.\r\n')
                else:
                	'''support ascii'''
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
                    time.sleep(0.5) # Wait for connection to set up
                    daddr_split = self.dataAddr.split('.')
                    self.controlSocket.send(('227 Entering passive mode (%s,%s,%s,%s,%d,%d).\r\n' % (daddr_split[0], daddr_split[1], daddr_split[2], daddr_split[3], int(self.dataPort / 256), self.dataPort % 256)).encode('ascii'))
            elif cmd == 'NLST': 
                if not self.loggedIn:
                    self.controlSocket.send(b'530 Not logged in.\r\n')
                elif self.dataMode == 'PASV' and self.dataSocket != None: # Only PASV implemented
                    self.controlSocket.send(b'125 Data connection already open. Transfer starting.\r\n')
                    ls = '\r\n'.join(os.listdir(self.cwd)) + '\r\n'
                    self.dataSocket.send(ls.encode('ascii'))
                    self.controlSocket.send(b'226 Closing data connection. Requested file action successful (for example, file transfer or file abort).\r\n')
                    self.dataSocket.close()
                    self.dataSocket = None
                else:
                    self.controlSocket.send(b"425 Can't open data connection.\r\n")
            elif cmd == 'RETR':
                if not self.loggedIn:
                    self.controlSocket.send(b'530 Not logged in.\r\n')
                elif len(command.split()) < 2:
                    self.controlSocket.send(b'501 Syntax error in parameters or arguments.\r\n')
                elif self.dataMode == 'PASV' and self.dataSocket != None: # Only PASV implemented
                    serverDir = os.getcwd()
                    os.chdir(self.cwd)
                    self.controlSocket.send(b'125 Data connection already open; transfer starting.\r\n')
                    fileName = command.split()[1]
                    try:
                        #self.dataSocket.send(open(fileName, 'rb').read())
                        #print('Current working dir: %s' % os.getcwd())
                        #print('RETR file name: %s' % fileName)
                        #basepath = os.path.dirname(__file__)
                        #filepath = os.path.abspath(os.path.join(basepath, "..", "..", "test.txt"))
                        fu = open(fileName, 'r')
                        fdata = fu.read()
                        #print('RETR %s: file data is \r\n' % filepath)
                        #print(fdata)
                        if False == self.dataSocket.send(fdata.encode('ascii')):
                        	raise Exception("Buffer is full or over window size or connection is lost")
                    except (IOError):
                    	log("IOError: file unavailable")
                    	self.controlSocket.send(b'550 Requested action not taken. File unavailable (e.g., file not found, no access).\r\n')
                    self.controlSocket.send(b'225 Closing data connection. Requested file action successful (i.e. file retrieval).\r\n')
                    self.dataSocket.close()
                    self.dataSocket = None
                    os.chdir(serverDir)
                else:
                    self.controlSocket.send(b"425 Can't open data connection.\r\n")
            elif cmd == 'STOR':
                if not self.loggedIn:
                    self.controlSocket.send(b'530 Not logged in.\r\n')
                elif len(command.split()) < 2:
                    self.controlSocket.send(b'501 Syntax error in parameters or arguments.\r\n')
                elif self.dataMode == 'PASV' and self.dataSocket != None: # Only PASV implemented
                    serverDir = os.getcwd()
                    os.chdir(self.cwd)
                    self.controlSocket.send(b'125 Data connection already open; transfer starting.\r\n')
                    fileOut = open(command.split()[1], 'wb')
                    time.sleep(0.5) # Wait for connection to set up
                    self.dataSocket.setblocking(False) 
                    while True:
                        try:
                            data = self.dataSocket.recv(self.bufferSize)
                            if data == b'': # Connection closed
                            	log('Did not receive any data from data connection', self.clientAddr)
                            	break
                            fileOut.write(data)
                        except (socket.error): # Connection closed
                            break
                    fileOut.close()
                    self.controlSocket.send(b'225 Closing data connection. Requested file action successful (i.e. file uploading).\r\n')
                    self.dataSocket.close()
                    self.dataSocket = None
                    os.chdir(serverDir)
                else:
                    self.controlSocket.send(b"425 Can't open data connection.\r\n")
            elif cmd == 'QUIT': 
                	self.controlSocket.send(b'221 Control socket closed. Logged out.\r\n')
                	self.controlSocket.close()
                	self.dataConnSockListener.exitThreadFlag = True
                	log('Client logged out. Server and DataScoketListener instances stopped', self.clientAddr)
                	break

def check_command():
	while True:
		command = input("------------------------------------------------------------------------------------------\r\nYou need to enter 'q' to terminate all running server threads before quitting the program: \r\n------------------------------------------------------------------------------------------\r\n")
		if(command == 'q'):
			terminated = True
			break
	for t in threadsPool:
		t.exitThreadFlag = True
		t.join()
	log('Terminated all children threads. Now you can control-c the program')

if __name__ == '__main__': # main thread
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) #default socket to accept client control connections
    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serverSocket.bind((defAddr, defPort))
    serverSocket.listen(5)
    check = threading.Thread(target=check_command)
    check.start()
    log('Server started.')
    #serverSocket.setblocking(False)
    while True:
        (controlSocket, clientAddr) = serverSocket.accept()
        ftpsv = FTPServer(controlSocket, clientAddr, False)
        threadsPool.append(ftpsv)
        ftpsv.start() # starting one child thread of the server for this coming control sock
        log("Connection accepted.", clientAddr)
