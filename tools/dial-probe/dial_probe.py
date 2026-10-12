#!/usr/bin/env python3
"""Minimal DIAL receiver probe for the YouTube app.

Advertises a DIAL device on the LAN (SSDP + UPnP device description + DIAL "YouTube" app) and logs every request
the phone makes. On POST /apps/YouTube it registers the received pairing code with the YouTube Lounge service for a
freshly generated screen, which is the step a TV app (SmartTube) has to perform.

Only the Python standard library is used. Run: python3 dial_probe.py [--name "DIAL test (Mac)"] [--port 8060]
"""
from __future__ import annotations

import argparse
import json
import socket
import struct
import threading
import time
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900
DIAL_ST = "urn:dial-multiscreen-org:service:dial:1"
LOUNGE = "https://www.youtube.com/api/lounge/pairing"
LOUNGE_APP = "lb-v4"  # same app id SmartTube uses for its screen


def log(*parts):
    print(time.strftime("%H:%M:%S"), *parts, flush=True)


def local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 9))
    ip = s.getsockname()[0]
    s.close()
    return ip


class Receiver:
    def __init__(self, name: str, port: int):
        self.name = name
        self.port = port
        self.ip = local_ip()
        self.udn = "uuid:" + str(uuid.uuid4())
        self.device_id = str(uuid.uuid4())
        self.state = "stopped"
        self.screen_id: str | None = None

    @property
    def base(self) -> str:
        return f"http://{self.ip}:{self.port}"

    # ---------------------------------------------------------------- Lounge
    def ensure_screen(self) -> str:
        if self.screen_id is None:
            with urllib.request.urlopen(f"{LOUNGE}/generate_screen_id", timeout=10) as r:
                self.screen_id = r.read().decode().strip()
            log("lounge: generated screen_id", self.screen_id[:8] + "…")
        return self.screen_id

    def register_pairing_code(self, code: str) -> None:
        data = urllib.parse.urlencode({
            "access_type": "permanent",
            "app": LOUNGE_APP,
            "pairing_code": code,
            "screen_id": self.ensure_screen(),
            "screen_name": self.name,
            "device_id": self.device_id,
        }).encode()
        req = urllib.request.Request(f"{LOUNGE}/register_pairing_code", data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                log("lounge: register_pairing_code ->", r.status, r.read()[:200])
        except urllib.error.HTTPError as e:
            log("lounge: register_pairing_code FAILED ->", e.code, e.read()[:200])

    # ---------------------------------------------------------------- XML
    def device_description(self) -> bytes:
        return f"""<?xml version="1.0"?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
  <specVersion><major>1</major><minor>0</minor></specVersion>
  <device>
    <deviceType>urn:dial-multiscreen-org:device:dial:1</deviceType>
    <friendlyName>{self.name}</friendlyName>
    <manufacturer>gms-cast</manufacturer>
    <modelName>DIAL probe</modelName>
    <UDN>{self.udn}</UDN>
  </device>
</root>""".encode()

    def app_status(self) -> bytes:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<service xmlns="urn:dial-multiscreen-org:schemas:dial" dialVer="1.7">
  <name>YouTube</name>
  <options allowStop="false"/>
  <state>{self.state}</state>
</service>""".encode()


def make_handler(rx: Receiver):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # quiet default logging, we log ourselves
            pass

        def _send(self, code, body=b"", ctype="text/xml; charset=utf-8", headers=None):
            self.send_response(code)
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            if body:
                self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def do_GET(self):
            log("HTTP GET", self.path, "from", self.client_address[0], "UA:", self.headers.get("User-Agent"),
                "Origin:", self.headers.get("Origin"))
            if self.path.startswith("/ssdp/device-desc.xml"):
                self._send(200, rx.device_description(), headers={"Application-URL": f"{rx.base}/apps/"})
            elif self.path.rstrip("/") == "/apps/YouTube":
                self._send(200, rx.app_status())
            else:
                self._send(404)

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length).decode(errors="replace")
            log("HTTP POST", self.path, "from", self.client_address[0], "Origin:", self.headers.get("Origin"),
                "Content-Type:", self.headers.get("Content-Type"))
            log("  body:", body)
            if self.path.rstrip("/") == "/apps/YouTube":
                params = urllib.parse.parse_qs(body)
                code = (params.get("pairingCode") or [None])[0]
                rx.state = "running"
                self._send(201, headers={"Location": f"{rx.base}/apps/YouTube/run"})
                if code:
                    threading.Thread(target=rx.register_pairing_code, args=(code,), daemon=True).start()
            else:
                self._send(404)

        def do_DELETE(self):
            log("HTTP DELETE", self.path)
            rx.state = "stopped"
            self._send(200)

    return Handler


def ssdp_loop(rx: Receiver):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.bind(("", SSDP_PORT))
    mreq = struct.pack("4s4s", socket.inet_aton(SSDP_ADDR), socket.inet_aton(rx.ip))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    log(f"SSDP listening on {SSDP_ADDR}:{SSDP_PORT} via {rx.ip}")
    while True:
        data, addr = sock.recvfrom(4096)
        text = data.decode(errors="replace")
        if not text.startswith("M-SEARCH"):
            continue
        st = next((l.split(":", 1)[1].strip() for l in text.split("\r\n") if l.upper().startswith("ST:")), "")
        if st not in (DIAL_ST, "ssdp:all"):
            continue
        log("SSDP M-SEARCH from", addr[0], "ST:", st)
        resp = ("HTTP/1.1 200 OK\r\n"
                "CACHE-CONTROL: max-age=1800\r\n"
                "EXT:\r\n"
                f"LOCATION: {rx.base}/ssdp/device-desc.xml\r\n"
                "SERVER: Linux/4.9 UPnP/1.0 gms-cast-dial-probe/0.1\r\n"
                f"ST: {DIAL_ST}\r\n"
                f"USN: {rx.udn}::{DIAL_ST}\r\n"
                "BOOTID.UPNP.ORG: 1\r\n\r\n").encode()
        reply = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        reply.sendto(resp, addr)
        reply.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--name", default="DIAL test (Mac)")
    p.add_argument("--port", type=int, default=8060)
    a = p.parse_args()
    rx = Receiver(a.name, a.port)
    threading.Thread(target=ssdp_loop, args=(rx,), daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", a.port), make_handler(rx))
    log(f"HTTP on {rx.base}  name={a.name!r}  udn={rx.udn}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
