import sys, socket, os, re, time, hashlib,datetime

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
        self.port = None
        
    def hash(self, username, password, challenge):
        m = hashlib.md5()
        m.update((username + password + challenge).encode('ascii'));
        temp_username = ' '*(15-len(username)) + username
        #self.print_debug_message("Sending username:" + self.username + " and hash:" + m.digest())
        #self.client_socket.send('2'+temp_username+m.digest()+"\\end")
        return temp_username+m.digest().decode('ascii')
    
    def log(self,msg, port = 0):
        if port == None:
            print('\033[92m[%s]\033[0m %s' % (time.strftime(r'%H:%M:%S, %m.%d.%Y'), msg))
        else:
            print('\033[92m[%s] %d\033[0m %s' % (datetime.datetime.now().strftime("%H:%M:%S.%f"), port, msg))
    
    def isConnected(self):
        return self.connected
        
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
            self.port = self.controlSocket.getsockname()[1]
        else:
            raise Exception('Control connection failed. Please try again.')
            
    def login(self, username, password):
        if not self.connected:
            raise Exception('Please connect first')
            return
        self.loggedIn = False
        self.controlSocket.send(('USER %s\r\n' % username).encode('ascii'))
        (res, msg) = self.getServRes()
        if res <= 3:
            #challenge = msg.split('\r\n')[1]
            #print("challenge: "+challenge)
            #hashedPassword = self.hash(username,password,challenge)
            self.controlSocket.send(('PASS %s\r\n' % password).encode('ascii'))
            if self.getServRes()[0] <= 3:
                self.loggedIn = True
        if not self.loggedIn:
            #raise Exception('Login failed. Please try again.')
            return False
        else:
            return True
        
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
    
    def mkd(self,dirname):
        if not self.connected or not self.loggedIn:
            raise Exception('Please log in first')
            return
        self.controlSocket.send(('MKD %s\r\n' % dirname).encode('ascii'))
        return self.getServRes()[1]
    
    def rmd(self,dirname):
        if not self.connected or not self.loggedIn:
            raise Exception('Please log in first')
            return
        self.controlSocket.send(('RMD %s\r\n' % dirname).encode('ascii'))
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
            return True
        return False
            
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
        #time.sleep(1)
        self.getServRes()
        return out
        
    def retr(self, filename):
        #self.log('RETR START: '+filename, self.port)
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
        time.sleep(2) # Wait for file data to come in
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
        #time.sleep(1)
        (res, msg) = self.getServRes()
        #self.log('RETR FINISH: '+filename, self.port)
        '''TODO: return'''
        if(res<=3):
            return True
        else:
            return False
        
    def stor(self, filePath): # Store files by file path
        filename = os.path.basename(filePath)
        #self.log('STOR START: '+filename, self.port)
        if not self.connected or not self.loggedIn:
            raise Exception('Please log in first')
            return
        if self.dataMode != 'PASV': 
            return
        dataSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        dataSocket.connect(self.dataAddr)
        time.sleep(1) # Wait for data connection to set up at server
        #self.log('pre sending: '+filename, self.port)
        self.controlSocket.send(('STOR %s\r\n' % filename).encode('ascii'))
        #self.log('post sending: '+filename, self.port)
        dataSocket.send(open(filePath, 'rb').read())
        dataSocket.close()
        time.sleep(1) # wait for data connection to close at server
        (res, msg) = self.getServRes()
        #self.log('STOR FINISH: '+filename, self.port)
        if(res<=3):
            return True
        else:
            return False
                    
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
           
if __name__ == '__main__':
    c = FTPClient()
    c.connect(defAddr,defPort)
    # c.login("yaling22", "true")
    # c.login('a','b')
    c.login("yaling","true")
    c.pasv()
    # #print('PWD out: '+c.pwd())
    # #c.nlst()
    #c.cwd("/home/yalingwu/Documents")
    # c.cwd("/home/yalingwu/Documents/cs6250FTP/server_ftp/test")
    #print('MKD out: '+c.mkd("mkdtest"))
    #print('RMD out: '+c.rmd("mkdtest"))
    #print('PWD out: '+c.pwd())
    # print('NLST out: '+c.nlst()) 
    #c.stor("/home/yalingwu/Documents/cs6250FTP/client_ftp/97stor.mp4")
    c.stor("/home/yalingwu/Documents/cs6250FTP/client_ftp/490stor.rmvb")
    # #time.sleep(1)
    # print(c.stor("/home/yalingwu/Documents/cs6250FTP/storeTest2.txt"))
    # #print(open("/home/yalingwu/Documents/cs6250FTP/README.md", 'rb').read())
    # time.sleep(1)
    #    
    #c.nlst()
    #c.nlst()
    #c.retr("retrTest.txt")
    #c.retr("207retr.mp4")
    c.retr("490retr.rmvb")
    c.quit()
