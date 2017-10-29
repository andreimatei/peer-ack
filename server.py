#!/usr/bin/env python

from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib
from os import curdir, sep
import functools
import datetime
from enum import Enum
from urllib.parse import urlparse
import traceback
import configparser
import os

from config import Config
from common import Page
from ack import Ack
from my_acks import MyAcks
from report import Report
from config import Config

class Verb(Enum):
    GET = 1
    POST = 2

class PeerAckHTTPHandler(BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server):
        self.routing = {
            "/": "/ack",
            "/ack": Ack(),
            "/myacks": MyAcks(),
            "/report": Report(),
            "/favicon.ico": functools.partial(self.serve_file, "image/x-icon", "favicon.ico"),
            "/site.css": functools.partial(self.serve_file, "text/css", "site.css"),
            "/test.html": functools.partial(self.serve_file, "text/html", "test.html"),
            "/auth.js": functools.partial(self.serve_file, "application/javascript", "auth.js"),
            "/common.js": functools.partial(self.serve_file, "application/javascript", "common.js"),
            "/del.png": functools.partial(self.serve_file, "image/png", "del.png"),
        }
        super(BaseHTTPRequestHandler, self).__init__(request, client_address, server)


    def do_GET(self):
        self.route_request(Verb.GET)

    def route_request(self, verb):
        route = urlparse(self.path).path
        while type(route) == str:
            route = self.routing[route]
        if isinstance(route, Page):
            try:
                if verb == Verb.GET:
                    route.do_get(self)
                    return
                else:
                    route.do_post(self)
                    return
            except Exception as e:
                route.send_error(self, traceback.format_exc())
                raise
        if not callable(route):
            raise Exception("bad route %r" % route)
        route(verb)

    def do_POST(self):
        self.route_request(Verb.POST)

    def serve_file(self, content_type, file, verb):
        if verb != Verb.GET:
            raise Exception("required GET, got: %s" % verb)
        f = open(curdir + sep + file, "rb")
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.end_headers()
        self.wfile.write(f.read())
        f.close()
        return


def run():
  config = configparser.ConfigParser()
  dir = os.path.dirname(__file__)
  cfg_path = os.path.join(dir, 'config.ini')
  print('reading config from {0}'.format(cfg_path))
  config.read(cfg_path)
  if 'config' in config.sections():
    if 'conn_string' in config['config']:
        Config.conn_string = config['config']['conn_string']
    if 'superusers' in config['config']:
        s = config['config']['superusers']
        Config.superusers = [x.strip() for x in s.split(',')]

  # Server settings
  print('starting server on port 8081...')
  server_address = ('127.0.0.1', 8081)
  httpd = HTTPServer(server_address, PeerAckHTTPHandler)
  print('running server...')
  httpd.serve_forever()

run()
