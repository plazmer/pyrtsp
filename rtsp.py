
#http://habrahabr.ru/post/149077/
#http://heim.ifi.uio.no/~meccano/reflector/smallclient.html

import socket, sys, errno, time, SocketServer
from base64 import b64encode
from select import select

def processImage(img):
    'This function is invoked by the MJPEG Client protocol'
    # Process image
    # Just save it as a file in this example
    f = open('frame.jpg', 'wb')
    f.write(img)
    f.close()

def recv_timeout(the_socket,timeout=0.3):
    the_socket.setblocking(0)
    total_data=[];data='';begin=time.time()
    while 1:
        #if you got some data, then break after wait sec
        if total_data and time.time()-begin>timeout:
            break

        elif time.time()-begin>timeout*2:
            break
        try:
            data=the_socket.recv(8192)
            if data:
                total_data.append(data)
                begin=time.time()
            else:
                time.sleep(0.1)
        except:
            pass
    return ''.join(total_data)

class RTP(SocketServer.BaseRequestHandler):
    port = None
    stream = None

    def handle(self):
        data = self.request[0].strip()
        socket = self.request[1]
        print "{} wrote:".format(self.client_address[0])
        print data

    def __init__(self,port):
        self.port = port

class RTSP:
    stream = None
    host = None
    port = None
    path = None
    cseq = None
    session = None
    login = None
    passw = None
    response = None
    sdp = None
    udp_port = 0
    rtp = None

    state = 0 #0 - not connected, 1 - connected rtsp, 2 - rtsp init, 4 - rtsp ready, 8 - rtsp playing
    debug = 1

    def __init__(self,config):
        self.host = config['host']
        self.port = config['port']
        self.path = config['path']
        self.udp_port = config['udp_port']
        if config['login']:
            self.login = config['login']
            self.passw = config['passw']
        self.cseq = 0

    def log(self,msg):
        print(msg+'\r\n');

    def connect(self):
        self.stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn = self.stream.connect_ex((self.host,self.port))
        if conn != 0:
            self.log('ERROR CONNECT %d'%(conn))
            return -1
        self.state = 1
        self.log('CONNECT: ok')
        return 0

    def disconnect(self):
        if self.stream:
            self.stream.close()
        self.state = 0
        return 0

    def parse_sdp(self):
        data = None
        if self.response and 'content' in self.response:
            data = self.response['content'].strip()

        if not data:
            self.sdp = None
            self.log('NO SDP RESPONSE')
            return -1

        data_arr = data.split('\r\n')
        params = []
        for row in data_arr:
            tmp = row.split('=',1)
            if len(tmp)>0:
                params.append([tmp[0],tmp[1]])
        self.sdp = {}
        self.sdp['params'] = params
        self.sdp['tracks'] = ['/trackID=0'] #dumb hack
        return 0

    def next_cseq(self):
        self.cseq += 1
        return self.cseq

    def send_query(self,command,params={},track=''):
        s = "%s rtsp://%s%s%s RTSP/1.0\r\n" % (command, self.host,self.path,track)
        s += 'CSeq: %u\r\n' % (self.next_cseq())
        if self.login: s += "Authorization: Basic %s\r\n" % ( b64encode(self.login+':'+self.passw) )
        if self.session: s += "Session: %s\r\n" % (self.session)
        if 'accept' in params:
            s += "Accept: %s\r\n" % (params['accept'])
        if 'transport' in params:
            s += "Transport: %s\r\n" % (params['transport'])
        if 'range' in params:
            s += "Range: %s\r\n" % (params['range'])
        s += "User-Agent: Plazmer Rtsp Client\r\n"
        s += "\r\n"
        self.log('SENDING QUERY:\r\n%sLen:%d' % (s,len(s)))

        totalsent = 0
        while totalsent < len(s):
            sent = self.stream.send(s[totalsent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent
        if totalsent == len(s):
            self.log('SEND %d OK' %(totalsent))
            return 0

    def recv_response(self):
        self.response = None
        response = recv_timeout(self.stream)
        r = {}
        if not response:
            self.log('NO RESPONSE')
            return -1

        tmp = response.split('\r\n\r\n',1)
        header = tmp[0].strip().split('\n')
        if len(tmp)>0:
            r['content'] = tmp[1]

        if len(header)>0:
            r['code'] = int( header[0].split(' ')[1] ) #RTSP/1.0 200 OK

        for row in header[1:]:
            tmp = row.strip().split(':',1)
            if len(tmp)>0:
                r[tmp[0].lower()]=tmp[1].strip()

        if 'session' in r:
            self.session = r['session'].split(';')[0]
            self.log('SESSION found:%s' % (self.session))

        if 'cseq' in r:
            self.cseq = int(r['cseq'])

        self.log('RECV RESPONSE:\r\n%sLEN:%d' % (response,len(response)))
        self.response = r
        return r

    def send_options(self):
        self.send_query('OPTIONS')

    def send_describe(self):
        self.send_query('DESCRIBE',{'accept': 'application/sdp'})

    def send_setup(self):
        headers = {'transport': 'RTP/AVP;unicast;client_port=%d-%d' % (self.udp_port,self.udp_port+1)}
        self.send_query('SETUP',headers,self.sdp['tracks'][0])

    def send_play(self):
        self.send_query('PLAY',{'range':'npt=0-'})

    def toHex(self,s):
        lst = []
        for ch in s:
            hv = hex(ord(ch)).replace('0x', '')
            if len(hv) == 1: hv = '0'+hv
            lst.append(hv)
        return reduce(lambda x,y:x+y, lst)

    def start_rtp(self):
        server1 = SocketServer.UDPServer(('', self.port), RTP)
        server1.serve_forever()
        server2 = SocketServer.UDPServer(('', self.port+1), RTP)
        server2.serve_forever()

config = {'path': '/cam/realmonitor?channel=1&subtype=1',
      'login': 'admin',
      'passw': 'admin',
      'host': '172.16.8.140',
      'port': 554,
      'udp_port': 2001}

rtsp_client = RTSP(config)
rtsp_client.connect()

rtsp_client.send_options()
resp = rtsp_client.recv_response()

rtsp_client.send_describe()
rtsp_client.recv_response()
if 'content-type' in rtsp_client.response and rtsp_client.response['content-type'] == 'application/sdp':
    rtsp_client.parse_sdp()

rtsp_client.send_setup()
rtsp_client.recv_response()

rtsp_client.send_play()
rtsp_client.recv_response()

#rtsp_client.start_rtp()

rtsp_client.disconnect()
