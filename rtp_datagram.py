# -*- coding: utf-8 -*-
'RTP datagram parser. It should be complete.'
"""
sources from:
Name:       Python M-JPEG Over RSTP Client
Version:    0.1
Purpose:    This program connects to an MJPEG source and saves retrived images.
Author:     Sergey Lalov
Date:       2011-02-18
License:    GPL
Target:     Cross Platform
Require:    Python 2.6. Modules: zope.interface, twisted
"""

# RTP Datagram Module
from struct import unpack

class RTPDatagram(object):
    'An RTP protocol datagram parser'
    def __init__(self):
        self.Version = 0
        self.Padding = 0
        self.Extension = 0
        self.CSRCCount = 0
        self.Marker = 0
        self.PayloadType = 0
        self.SequenceNumber = 0
        self.Timestamp = 0
        self.SyncSourceIdentifier = 0
        self.CSRS = []
        self.ExtensionHeader = ''
        self.ExtensionHeaderID = 0
        self.ExtensionHeaderLength = 0
        self.Datagram = ''
        self.Payload = ''
    def parse(self,DatagramIn):
        self.Datagram = DatagramIn

        Ver_P_X_CC, M_PT, self.SequenceNumber, self.Timestamp, self.SyncSourceIdentifier = unpack('!BBHII', self.Datagram[:12])
        self.Version =      (Ver_P_X_CC & 0b11000000) >> 6
        self.Padding =      (Ver_P_X_CC & 0b00100000) >> 5
        self.Extension =    (Ver_P_X_CC & 0b00010000) >> 4
        self.CSRCCount =     Ver_P_X_CC & 0b00001111
        self.Marker =       (M_PT & 0b10000000) >> 7
        self.PayloadType =   M_PT & 0b01111111
        i = 0
        for i in range(0, self.CSRCCount, 4):
            self.CSRS.append(unpack('!I', self.Datagram[12+i:16+i]))
        if self.Extension:
            i = self.CSRCCount * 4
            (self.ExtensionHeaderID, self.ExtensionHeaderLength) = unpack('!HH', self.Datagram[12+i:16+i])
            self.ExtensionHeader = self.Datagram[16+i:16+i+self.ExtensionHeaderLength]
            i += 4 + self.ExtensionHeaderLength
        self.Payload = self.Datagram[12+i:]
