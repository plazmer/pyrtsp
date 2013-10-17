# -*- coding: utf-8 -*-
"""
This module handles RTCP source reports
"""
import rtcp_datagram

from twisted.internet.protocol import DatagramProtocol

class RTCP_Client(DatagramProtocol):
    def __init__(self):
        # Object that deals with RTCP datagrams
        self.rtcp = rtcp_datagram.RTCPDatagram()
    def datagramReceived(self, datagram, address):
        # SSRC Report recieved
        self.rtcp.Datagram = datagram
        self.rtcp.parse()
        # Send back our Reciever Report
        # saying that everything is fine
        RR = self.rtcp.generateRR()
        self.transport.write(RR, address)
