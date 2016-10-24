from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import ssl
import logging
import gpiozero
import time
import signal
import os
import sys
from SocketServer import ThreadingMixIn

PORT_NUMBER = 443
doorRemote = gpiozero.OutputDevice(2, active_high=False)
indexPath = os.path.join(sys.path[0], 'index.html')
tokensPath = os.path.join(sys.path[0], 'tokens')
certPath = os.path.join(sys.path[0], 'cert.pem')
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
indexFile = tokens = None

def main():
    readIndexFile()
    readTokens()
    signal.signal(signal.SIGUSR1, readTokens)
    logging.info('Started http server on https://localhost:%s' % PORT_NUMBER)
    httpd = ThreadedHTTPServer(('', PORT_NUMBER), MyHandler)
    httpd.socket = ssl.wrap_socket (httpd.socket, certfile=certPath, server_side=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info('^C received, shutting down the web server')
        httpd.socket.close()

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

def readIndexFile():
    global indexFile
    with open(indexPath, 'r') as f:
        indexFile = f.read()

def readTokens(*args):
    global tokens
    with open(tokensPath, 'r') as f:
        tokens = {}
        for line in f.read().splitlines():
            token, user = line.split(' ', 1)
            tokens[token] = user


class MyHandler(BaseHTTPRequestHandler):
    def do_GET(req):
        token = getTokenFromUrl(req.path)
        if token:
            if openDoor(token):
                send(req, 200, 'OPEN')
            else:
                send(req, 401, 'Unauthorized!')
        else:
            send(req, 200, indexFile)

    def do_POST(req):
        token = req.headers.get('token')
        if openDoor(token):
            send(req, 200, 'OPEN')
        else:
            send(req, 401, 'Unauthorized!')

def send(req, status, text):
    req.send_response(status)
    req.send_header('Content-type', 'text/html')
    req.end_headers()
    if text: req.wfile.write(text)

def openDoor(token):
    if tokens.has_key(token):
        logging.debug('Starting to open door for %s' % tokens[token])
        doorRemote.on()
        time.sleep(2)
        doorRemote.off()
        logging.info('Opened door for %s' % tokens[token])
        return True
    else:
        return False

def getTokenFromUrl(url):
    parts = url.split('/')
    if len(parts) == 3 and parts[1] == 'token':
        return parts[2]

if __name__ == '__main__': main()
