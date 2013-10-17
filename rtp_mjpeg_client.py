# -*- coding: utf-8 -*-

import rtp_datagram
import rfc2435jpeg

from twisted.internet.protocol import DatagramProtocol

class RTP_MJPEG_Client(DatagramProtocol):
    def __init__(self, config):
        self.config = config
        # Previous fragment sequence number
        self.prevSeq = -1
        self.lost_packet = 0
        # Object that deals with JPEGs
        self.jpeg = rfc2435jpeg.RFC2435JPEG()

    def datagramReceived(self, datagram, address):
        # When we get a datagram, parse it
        rtp_dg = rtp_datagram.RTPDatagram()
        rtp_dg.Datagram = datagram
        rtp_dg.parse()
        # Check for lost packets
        if self.prevSeq != -1:
            if (rtp_dg.SequenceNumber != self.prevSeq + 1) and rtp_dg.SequenceNumber != 0:
                self.lost_packet = 1
        self.prevSeq = rtp_dg.SequenceNumber
        # Handle Payload
        if rtp_dg.PayloadType == 26: # JPEG compressed video
            self.jpeg.Datagram = rtp_dg.Payload
            self.jpeg.parse()
            # Marker = 1 if we just recieved the last fragment
            if rtp_dg.Marker:
                if not self.lost_packet:
                    # Obtain complete JPEG image and give it to the
                    # callback function
                    self.jpeg.makeJpeg()
                    self.config['callback'](self.jpeg.JpegImage)
                else:
                    #print "RTP packet lost"
                    self.lost_packet = 0
                    self.jpeg.JpegPayload = ""
