#!/usr/bin/python2

# certbot/certbot is python 2 :(

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import SocketServer
import sys


PORT = 8080

path, content = sys.argv[1], sys.argv[2]


class ACMEHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global content
        if self.path != path:
            content = "invalid path"
            self.send_response(404)
        else:
            self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(content)


httpd = SocketServer.TCPServer(("0.0.0.0", PORT), ACMEHandler)

httpd.serve_forever()
