# CS6250 Spring 2017 Team Project
- Implementation of the RFC 959: File Transfer Protocol
- Useful doc links:
  1. [RFC 959](http://www.faqs.org/rfcs/rfc959.html)
  2. [FTP Brief Overview](http://enterprisedt.com/publications/FTP_Overview.html)

## Documentation on *server_ftp*
- FTP commands
  * ```HELP```
  * ```USER <username>```
  * ```PASS <password>``` 
  * ```PASV```
  * ```CWD <absolute file_path>``` 
  * ```PWD```
  * ```RETR <filename>``` 
  * ```STOR <filename>```
  * ```QUIT```  
  * ```NLST```
- How to use the ftp server:
  1. Set up a control connection socket to the server by ```connect()```
  2. ```login(<username>,<password>)``` raises exception if login fails, otherwise returns true
    * Send ```USER <username>``` via control connection sockets
    * Send ```PASS <password>``` (now logged in)
  3. ```pasv()```
    * Send ```PASV``` for server to listen to data connection sockets from client
  4. Now you can call other file-related commands: client functions same as command names except in lower cases
  5. **Remember to log out by calling ```quit()``` after the current client is done**
  6. To exit the server *program*, remember to type ```q``` on terminal to kill all existing children threads
- Important things to note:
  * All replies from the server are transmitted through the control socket, except for ```NLST, RETR, STOR```
    - those three responses are transmitted through the data connection socket 
  * If received server replies starting with 4, send current failed commands again
    - e.g. Get "425 Can't open data connection." after sending ```NLST``` command, it is probably because data connection with the server has not been set up -> should send this command again
