#!/usr/bin/python3

from http.server import BaseHTTPRequestHandler, HTTPServer
import sys


path, content = sys.argv[1], sys.argv[2]


class ACMEHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global content
        if self.path != path:
            content = "invalid path"
            self.send_response(404)
        else:
            self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(content.encode())


httpd = HTTPServer(("0.0.0.0", 8080), ACMEHandler)

try:
    httpd.serve_forever()
except KeyboardInterrupt:
    pass

httpd.server_close()
