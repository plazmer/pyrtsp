#http://habrahabr.ru/post/149077/
#http://heim.ifi.uio.no/~meccano/reflector/smallclient.html

import socket, sys, errno, time
from base64 import b64encode
from select import select

class rtsp_utils:
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

    def toHex(self,s):
        lst = []
        for ch in s:
            hv = hex(ord(ch)).replace('0x', '')
            if len(hv) == 1: hv = '0'+hv
            lst.append(hv)
        return reduce(lambda x,y:x+y, lst)
