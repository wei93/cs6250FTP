import sys, socket, os, re, time

defAddr = '127.0.0.1'
defPort = 12111

class FTPClient():
    
    def __init__(self):
        self.bufferSize = 2048
        self.dataAddr = None
        self.controlSocket = None
        self.connected = False
        self.loggedIn = False
        self.dataMode = 'PORT'
        
    def getServRes(self):
        if self.controlSocket == None:
            return (5,"555 No control socket\r\n")
        try:
            res = self.controlSocket.recv(self.bufferSize).decode('ascii')
        except (socket.timeout):
            print('No response from the server before timeout')
            return (5,"555 Socket recv timed out\r\n")
        else:
            if 0 >= len(res): # Lost connection when in action
                self.controlSocket.close()
                self.controlSocket = None
                self.connected = False
                self.loggedIn = False
            else: 
                print('<< ' + res.strip().replace('\n','\n<< '))
                return (int(res[0]), res)
            
    def help(self):
        if not self.connected or not self.loggedIn:
            return
        self.controlSocket.send(b'HELP\r\n')
        self.getServRes()
                
    def connect(self, host, port):
        if self.controlSocket != None: # Only one client control socket at a time
            self.connected = False
            self.loggedIn = False
            self.controlSocket.close()
        self.controlSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.controlSocket.connect((host, port))
        if self.getServRes()[0] <= 3:
            self.connected = True
            self.controlSocket.settimeout(1)
        else:
            raise Exception('Control connection failed. Please try again.')
            
    def login(self, username, password):
        if not self.connected:
            raise Exception('Please connect first')
            return
        self.loggedIn = False
        self.controlSocket.send(('USER %s\r\n' % username).encode('ascii'))
        if self.getServRes()[0] <= 3:
            self.controlSocket.send(('PASS %s\r\n' % password).encode('ascii'))
            if self.getServRes()[0] <= 3:
                self.loggedIn = True
        if not self.loggedIn:
            raise Exception('Logged in failed. Please try again.')
        
    def pwd(self):
        if not self.connected or not self.loggedIn:
            raise Exception('Please log in first')
            return
        self.controlSocket.send(b'PWD\r\n')
        return self.getServRes()[1]
        
    def cwd(self, path):
        if not self.connected or not self.loggedIn:
            raise Exception('Please log in first')
            return
        self.controlSocket.send(('CWD %s\r\n' % path).encode('ascii'))
        return self.getServRes()[1]
        
    def type(self, t):
        if not self.connected or not self.loggedIn:
            raise Exception('Please log in first')
            return
        self.controlSocket.send(('TYPE %s\r\n' % t).encode('ascii'))
        return self.getServRes()[1]
        
    def pasv(self):
        if not self.connected or not self.loggedIn:
            raise Exception('Please log in first')
            return
        self.controlSocket.send(b'PASV\r\n')
        res = self.getServRes()
        if res[0] <= 3:
            daddr = re.search(r'(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)', res[1])
            self.dataAddr = (daddr.group(1) + '.' + daddr.group(2) + '.' + daddr.group(3) + '.' + daddr.group(4), int(daddr.group(5)) * 256 + int(daddr.group(6)))
            self.dataMode = 'PASV'
            
    def nlst(self):
        if not self.connected or not self.loggedIn:
            raise Exception('Please log in first')
            return
        if self.dataMode != 'PASV': 
            raise Exception('Please set to pasv first')
            return
        dataSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        dataSocket.connect(self.dataAddr)
        dataSocket.setblocking(False)
        self.controlSocket.send(b'NLST\r\n')
        time.sleep(1) # Wait for data to come in 
        out = ''
        while True:
            try:
                nlstdata = dataSocket.recv(self.bufferSize)
                if len(nlstdata) == 0: 
                    break
                print(nlstdata.decode('ascii').strip())
                out = out + nlstdata.decode('ascii').strip()
            except (socket.error): # Connection closed
                break
        dataSocket.close()
        self.getServRes()
        return out
        
    def retr(self, filename):
        if not self.connected or not self.loggedIn:
            raise Exception('Please log in first')
            return
        if self.dataMode != 'PASV': # Currently only PASV is supported
            raise Exception('Please set to pasv first')
            return
        dataSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        dataSocket.connect(self.dataAddr)
        dataSocket.setblocking(False) 
        self.controlSocket.send(('RETR %s\r\n' % filename).encode('ascii'))
        time.sleep(1.5) # Wait for data to come in
        fo = open(filename, 'wb')
        while True:
            try:
                retrdata = dataSocket.recv(self.bufferSize)
                if len(retrdata) == 0: 
                	break
                fo.write(retrdata)
            except (socket.error): # Connection closed
                break
        fo.close()
        dataSocket.close()
        self.getServRes()
        
    def stor(self, filePath): # Store files by file path
        if not self.connected or not self.loggedIn:
            raise Exception('Please log in first')
            return
        if self.dataMode != 'PASV': 
            return
        dataSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        dataSocket.connect(self.dataAddr)
        time.sleep(0.5) # Wait for data connection to set up
        filename = os.path.basename(filePath)
        self.controlSocket.send(('STOR %s\r\n' % filename).encode('ascii'))
        dataSocket.send(open(filePath, 'rb').read())
        dataSocket.close()
        self.getServRes()
                    
    def quit(self):
        if not self.connected:
            print('Already disconnected.')
            return
        self.controlSocket.send(b'QUIT\r\n')
        self.getServRes()
        self.loggedIn = False
        self.controlSocket.close()
        self.controlSocket = None
        self.connected = False
           
c = FTPClient()
c.connect(defAddr,defPort)
c.login("yaling","true")
c.pasv()
#print('PWD out: '+c.pwd())
print('CWD out: '+c.cwd("/home/yalingwu/Documents"))
#print('PWD out: '+c.pwd())
print('NLST out: '+c.nlst()) 
#c.stor("storeTest.txt")
#c.stor("/home/yalingwu/Documents/cs6250FTP/storeTest2.txt")
#print(open("/home/yalingwu/Documents/cs6250FTP/README.md", 'rb').read())
#c.retr("retrTest.txt")
c.quit()