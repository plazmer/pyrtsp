#Thanx to author of: http://habrahabr.ru/post/117735/,
#http://heim.ifi.uio.no/~meccano/reflector/smallclient.html

import socket, sys, time, select, rtcp_datagram, rtp_datagram, rfc2435jpeg
from base64 import b64encode

config = {'path': '/cam/realmonitor?channel=1&subtype=1',
      'login': 'admin',
      'passw': 'admin',
      'host': '172.16.8.140',
      'port': 554,
      'udp_port': 17654,
      'save_to':'/ramdisk/cam8.jpg'}

#RTCP by UDP RECEIVER / REPLY

class RTCP_client:
    port = None
    server_port = None
    server_address = None
    stream = None
    rtcp = None

    def __init__(self,port,server_address,server_port):
      self.port = port
      self.server_address = server_address
      self.server_port = server_port
      self.rtcp = rtcp_datagram.RTCPDatagram()

    def __del__(self):
        del self.rtcp
        self.stream.close()

    def log(self,msg):
        print(msg);

    def start(self):
        self.stream = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.stream.bind(('',self.port))
        self.stream.setblocking(False)
        self.stream.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.log('RTCP SERVER STARTED ON %d' % (self.port))

    def recv(self):
        if not self.stream:
            self.start()
        rlist,wlist,xlist = select.select([self.stream],[],[],0) #data available? pls recommend better non-blocking way
        if len(rlist)>0:
            buf, addr = rlist[0].recvfrom(4096)
            if len(buf)>0:
                self.log('RTCP recv: Len=%d' % (len(buf)))
                self.parse(buf)

    def parse(self,datagram):
        self.rtcp.Datagram = datagram
        self.rtcp.parse()
        # Send back our Reciever Report
        # saying that everything is fine
        RR = self.rtcp.generateRR()
        self.stream.sendto(RR, (self.server_address, self.server_port))

#RTP by UDP RECEIVER
class RTP_client():
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

    def __del__(self):
        del self.jpeg
        self.stream.close()

    def log(self,msg):
        print(msg);

    def start(self):
        self.stream = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.stream.bind(('',self.port))
        self.stream.setblocking(False)
        self.stream.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.log('RTP SERVER STARTED ON %d' % (self.port))

    def recv(self):
        if not self.stream:
            self.start()
        rlist,wlist,xlist = select.select([self.stream],[],[],0) #data available? wait 1/100 of s
        if len(rlist)>0:
            buf, addr = rlist[0].recvfrom(4096)
            if len(buf)>0:
                #self.log('RTP recv: Len=%d' % (len(buf)))
                self.parse(buf)

    def parse(self,buf):
        rtpdata = rtp_datagram.RTPDatagram()
        rtpdata.parse(buf)

        # Check for lost packets
        if self.prevSeq != -1:
            if (rtpdata.SequenceNumber != self.prevSeq + 1) and rtpdata.SequenceNumber != 0:
                self.lostPacket = 1
        self.prevSeq = rtpdata.SequenceNumber

        #self.log('RECV RTP: seq=%d, len=%d type=%d' % (rtpdata.SequenceNumber, len(rtpdata.Payload),rtpdata.PayloadType))
        # Handle Payload
        if rtpdata.PayloadType == 26: # JPEG compressed video
            self.jpeg.Datagram = rtpdata.Payload
            self.jpeg.parse()
            # Marker = 1 if we just recieved the last fragment
            if rtpdata.Marker:
                if not self.lostPacket:
                    self.jpeg.makeJpeg()
                    self.save(self.save_to, self.jpeg.JpegImage)
                else:
                    print "RTP packet lost"
                    self.lostPacket = 0
                    self.jpeg.JpegPayload = ""

    def save(self,filepath, content):
        self.log('SAVE: %s' % filepath)
        f = open(filepath,'wb')
        f.write(content)
        f.close()


class RTSP_client:
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
    rtcp_server_port = 0
    rtcp_client_port = 0
    rtp_client_port = 0

    #state is not implemented
    state = 0 #0 - not connected, 1 - connected rtsp, 2 - rtsp init, 4 - rtsp ready, 8 - rtsp playing

    def __init__(self,config):
        self.host = config['host']
        self.port = config['port']
        self.path = config['path']
        self.udp_port = config['udp_port']
        if config['login']:
            self.login = config['login']
            self.passw = config['passw']
        self.cseq = 0
    def __del__(self):
        if self.stream:
            self.stream.close()

    def log(self,msg):
        print(msg);

    def recv_timeout(self):
        #the_socket.setblocking(0)
        total_data=[];data=''
        while True:
            r,w,x = select.select([self.stream],[],[],0.05)
            if len(r)>0:
                data = r[0].recv(4096)
                total_data.append(data)
            else:
                break
        return ''.join(total_data)

    def connect(self):
        self.stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn = self.stream.connect_ex((self.host,self.port))
        if conn != 0:
            self.log('ERROR CONNECT %d'%(conn))
            return -1
        self.state = 1
        self.log('CONNECT: ok')
        return 0

    def parse_sdp(self):
        data = None
        if self.response and 'content' in self.response:
            data = self.response['content'].strip()

        if not data:
            self.sdp = None
            self.log('PARSE_SDP: NO SDP RESPONSE')
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

        self.log('SENDING QUERY: %s Len:%d' % (command,len(s)))

        totalsent = 0
        while totalsent < len(s):
            sent = self.stream.send(s[totalsent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent
        if totalsent == len(s):
            self.log('SENDING QUERY: %s Len:%d Sent:%d' % (command,len(s),totalsent))
            return 0

    def recv_response(self):
        self.response = None
        response = self.recv_timeout()
        r = {}
        if not response:
            self.log('NO RESPONSE')
            return -1

        tmp = response.split('\r\n\r\n',1)
        header = tmp[0].strip().split('\n')
        if len(tmp)>0:
            r['content'] = tmp[1]

        r['code'] = 0 #default error
        if len(header)>0:
            r['code'] = int( header[0].split(' ')[1] ) #RTSP/1.0 200 OK

        for row in header[1:]:
            tmp = row.strip().split(':',1)
            if len(tmp)>0:
                r[tmp[0].lower()]=tmp[1].strip()

        if 'session' in r:
            self.session = r['session'].split(';')[0]
            self.log('SESSION found:%s' % (self.session))

        if 'transport' in r:
            tr = r['transport'].split(';')
            for row in tr:
                ttmp = row.split('=')
                if len(ttmp)>1: # sample: client_port=5000-5001 server_port=20008-20009
                    r[ttmp[0]] = ttmp[1].split('-')
            self.rtp_client_port = int(r['client_port'][0])
            self.rtcp_client_port = int(r['client_port'][1])
            self.rtcp_server_port = int(r['server_port'][1])

        if 'cseq' in r:
            self.cseq = int(r['cseq'])

        self.log('RECV RESPONSE: code=%d Len:%d' % (r['code'], len(response)))
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

    def send_teardown(self):
        self.send_query('TEARDOWN');

    def send_set_parameter(self,parameter = ''):
        self.send_query('SET_PARAMETER',{},'',parameter)

    def send_get_parameter(self,parameter = ''):
        self.send_query('GET_PARAMETER',{},'',parameter)

    def rtsp_start(self):
        if not self.stream:
            self.connect()

        self.send_options()
        resp = self.recv_response()

        self.send_describe()
        self.recv_response()
        if 'content-type' in self.response and \
            self.response['content-type'] == 'application/sdp':
            self.parse_sdp()

        self.send_setup()
        self.recv_response()

        self.send_play()
        self.recv_response()
        if self.response['code'] == 200:
            return True
        else:
            return False

#main loop
while True:
    try:
        start_time = time.time()
        current_time = time.time()

        rtsp_client = RTSP_client(config)
        rtsp_client.rtsp_start()

        if rtsp_client.rtp_client_port: #if setup rtsp command and responsse - ok
            print('PORTS: rtp %d, rtsp client %d, rtsp server %d' % (\
                    rtsp_client.rtp_client_port,\
                    rtsp_client.rtcp_client_port,\
                    rtsp_client.rtcp_server_port ))
            rtp_client = RTP_client(rtsp_client.rtp_client_port, config['save_to'])
            rtcp_client = RTCP_client(rtsp_client.rtcp_client_port, config['host'], rtsp_client.rtcp_server_port)

            while current_time - start_time < 60: #60 sec, then reconnect by rtsp
                rtp_client.recv() #and save jpeg
                rtcp_client.recv() #and send reply
                current_time = time.time()

            del rtp_client
            del rtcp_client

        del rtsp_client
        start_time = time.time()
    except KeyboardInterrupt as e:
        print >>sys.stderr, e.message
        sys.exit(0)
    except Exception as e:
        print >>sys.stderr, e.message
        pass

