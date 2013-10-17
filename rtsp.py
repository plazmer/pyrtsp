#http://habrahabr.ru/post/149077/
#http://heim.ifi.uio.no/~meccano/reflector/smallclient.html

import socket, sys, time, select, rtp_datagram, rfc2435jpeg
from base64 import b64encode

def recv_timeout2(the_socket):
    the_socket.setblocking(0)
    total_data=[];data=''
    while True:
        r,w,x = select.select([the_socket],[],[],0.1)
        if len(r)>0:
            data = r[0].recv(4096)
            total_data.append(data)
        else:
            break
    return ''.join(total_data)

#UDP RECEIVER
class RTP():
    port = None
    stream = None
    jpeg = None
    prevSeq = -1
    lostPacket = 0
    save_to = ''

    def __init__(self,port,save_to):
        self.port = port
        self.save_to = save_to
        # Object that deals with JPEGs
        self.jpeg = rfc2435jpeg.RFC2435JPEG()

    def log(self,msg):
        print(msg+'\r\n');

    def start(self):
        self.stream = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.stream .bind(('',self.port))
        self.stream .setblocking(False)
        self.stream .setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def recv(self):
        if not self.stream:
            self.start()

        rlist,wlist,xlist = select.select([self.stream],[],[],0) #data available?
        if len(rlist)>0:
            buf, addr = rlist[0].recvfrom(4096)
            if len(buf)>0:
                self.parse(buf)

    def parse(self,buf):
        rtpdata = rtp_datagram.RTPDatagram()
        rtpdata.parse(buf)

        # Check for lost packets
        if self.prevSeq != -1:
            if (rtpdata.SequenceNumber != self.prevSeq + 1) and rtpdata.SequenceNumber != 0:
                self.lostPacket = 1
        self.prevSeq = rtpdata.SequenceNumber

        self.log('RECV RTP: seq=%d, len=%d type=%d' % (rtpdata.SequenceNumber, len(rtpdata.Payload),rtpdata.PayloadType))
        # Handle Payload
        if rtpdata.PayloadType == 26: # JPEG compressed video
            self.jpeg.Datagram = rtpdata.Payload
            self.jpeg.parse()
            # Marker = 1 if we just recieved the last fragment
            if rtpdata.Marker:
                if not self.lostPacket:
                    self.jpeg.makeJpeg()
                    self.save(self.save_to+str(time.time())+'.jpg', self.jpeg.JpegImage)
                else:
                    print "RTP packet lost"
                    self.lostPacket = 0
                    self.jpeg.JpegPayload = ""

    def save(self,filepath, content):
        self.log('SAVE: %s' % filepath)
        f = open(filepath,'wb')
        f.write(content)
        f.close()


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

    def send_query(self,command,params={},track='',post=''):
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
        if post:
            s += "Content-length: %d\r\n" % len(post)

        s += "\r\n"

        if post:
            s += post

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
        response = recv_timeout2(self.stream)
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

    def send_set_parameter(self,parameter = ''):
        pass

    def send_get_parameter(self,parameter = ''):
        self.send_query('GET_PARAMETER',{},'',parameter)

    def toHex(self,s):
        lst = []
        for ch in s:
            hv = hex(ord(ch)).replace('0x', '')
            if len(hv) == 1: hv = '0'+hv
            lst.append(hv)
        return reduce(lambda x,y:x+y, lst)

config = {'path': '/cam/realmonitor?channel=1&subtype=0',
      'login': 'admin',
      'passw': 'admin',
      'host': '172.16.8.140',
      'port': 554,
      'udp_port': 2001,
      'save_to':'/ramdisk/140.jpg'}

rtsp_client = RTSP(config)
rtsp_client.connect()

rtsp_client.send_options()
resp = rtsp_client.recv_response()

rtsp_client.send_describe()
rtsp_client.recv_response()
if 'content-type' in rtsp_client.response and rtsp_client.response['content-type'] == 'application/sdp':
    rtsp_client.parse_sdp()

rtsp_client.send_get_parameter('packetization-supported')
rtsp_client.recv_response()

rtsp_client.send_setup()
rtsp_client.recv_response()

rtsp_client.send_play()
rtsp_client.recv_response()

rtp_client = RTP(config['udp_port'],config['save_to'])
while True:
    rtp_client.recv()


rtsp_client.disconnect()
