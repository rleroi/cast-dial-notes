import socket, ssl, struct, os, json, sys
from pychromecast import cast_channel_pb2 as pb
from cast_sniffer import decode_deviceauth
host=sys.argv[1]
ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
s=ctx.wrap_socket(socket.create_connection((host,8009),timeout=8)); s.settimeout(8)
def send(ns,pb_=None,st=None):
    m=pb.CastMessage(); m.protocol_version=m.CASTV2_1_0; m.source_id="sender-0"; m.destination_id="receiver-0"; m.namespace=ns
    if pb_ is not None: m.payload_type=pb.CastMessage.BINARY; m.payload_binary=pb_
    else: m.payload_type=pb.CastMessage.STRING; m.payload_utf8=st
    b=m.SerializeToString(); s.sendall(struct.pack(">I",len(b))+b)
def recv():
    h=b""
    while len(h)<4: h+=s.recv(4-len(h))
    n=struct.unpack(">I",h)[0]; b=b""
    while len(b)<n: b+=s.recv(n-len(b))
    m=pb.CastMessage(); m.ParseFromString(b); return m
send("urn:x-cast:com.google.cast.tp.connection",st=json.dumps({"type":"CONNECT"}))
ch=pb.DeviceAuthMessage(); ch.challenge.sender_nonce=os.urandom(16); ch.challenge.signature_algorithm=1
send("urn:x-cast:com.google.cast.tp.deviceauth",pb_=ch.SerializeToString())
for _ in range(6):
    m=recv()
    if m.namespace.endswith("deviceauth"):
        d=decode_deviceauth(m.payload_binary); r=d.get("response",{})
        print(host, "sig_len=%s cert_b64_len=%s intermediates=%s crl_len=%s error=%s"%(r.get("signature_len"),len(r.get("client_auth_certificate_der_b64","")),r.get("intermediate_certificates"),r.get("crl_len"),d.get("error")))
        break
s.close()
