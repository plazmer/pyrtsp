# -*- coding: utf-8 -*-
# RTCP Datagram Module
from struct import unpack, pack

debug = 0

# Receiver Reports included in Sender Report
class Report:
    SSRC = 0
    FractionLost = 0
    CumulativeNumberOfPacketsLostH = 0
    CumulativeNumberOfPacketsLostL = 0
    ExtendedHighestSequenceNumberReceived = 0
    InterarrivalJitter = 0
    LastSR = 0
    DelaySinceLastSR = 0

# Source Description
class SDES:
    SSRC = 0
    CNAME = ''
    NAME = ''
    EMAIL = ''
    PHONE = ''
    LOC = ''
    TOOL = ''
    NOTE = ''
    PRIV = ''

class RTCPDatagram(object):
    'RTCP packet parser end generator'
    def __init__(self):
        self.Datagram = ''
        # SR specific
        self.SSRC_sender = 0
        self.NTP_TimestampH = 0
        self.NTP_TimestampL = 0
        self.RTP_Timestamp = 0
        self.SenderPacketCount = 0
        self.SenderOctetCount = 0
        self.Reports = []
        self.ProfileSpecificExtension = ''
        # SDES specific
        self.SourceDescriptions = []

    def loadDatagram(self, DatagramIn):
        self.Datagram = DatagramIn
    
    def parse(self):
        # RTCP parsing is complete
        # including SDES, BYE and APP
        # RTCP Header
        (Ver_P_RC,
        PacketType,
        Length) = unpack('!BBH', self.Datagram[:4])
        Version = (Ver_P_RC & 0b11000000) >> 6
        Padding = (Ver_P_RC & 0b00100000) >> 5
        # Byte offset
        off = 4
        # Sender's Report
        if PacketType == 200:
            # Sender's information
            (self.SSRC_sender,
            self.NTP_TimestampH,
            self.NTP_TimestampL,
            self.RTP_Timestamp,
            self.SenderPacketCount,
            self.SenderOctetCount) = unpack('!IIIIII', self.Datagram[off: off + 24])
            off += 24
            ReceptionCount = Ver_P_RC & 0b00011111
            if debug:
                print 'SDES: SR from', str(self.SSRC_sender)
            # Included Receiver Reports
            self.Reports = []
            i = 0
            for i in range(ReceptionCount):
                self.Reports.append(Report())
                self.Reports[i].SSRC,
                self.Reports[i].FractionLost,
                self.Reports[i].CumulativeNumberOfPacketsLostH,
                self.Reports[i].CumulativeNumberOfPacketsLostL,
                self.Reports[i].ExtendedHighestSequenceNumberReceived,
                self.Reports[i].InterarrivalJitter,
                self.Reports[i].LastSR,
                self.Reports[i].DelaySinceLastSR = unpack('!IBBHIIII', self.Datagram[off: off + 24])
                off += 24
        # Source Description (SDES)
        elif PacketType == 202:
            # RC now is SC
            SSRCCount = Ver_P_RC & 0b00011111
            self.SourceDescriptions = []
            i = 0
            for i in range(SSRCCount):
                self.SourceDescriptions.append(SDES())
                SSRC, = unpack('!I', self.Datagram[off: off + 4])
                off += 4
                self.SourceDescriptions[i].SSRC = SSRC
                SDES_Item = -1
                # Go on the list of descriptions
                while SDES_Item != 0:
                    SDES_Item, = unpack('!B', self.Datagram[off])
                    off += 1
                    if SDES_Item != 0:
                        SDES_Length, = unpack('!B', self.Datagram[off])
                        off += 1
                        Value = self.Datagram[off: off + SDES_Length]
                        off += SDES_Length
                        if debug:
                            print 'SDES:', SDES_Item, Value
                    if SDES_Item == 1:
                        self.SourceDescriptions[i].CNAME = Value
                    elif SDES_Item == 2:
                        self.SourceDescriptions[i].NAME = Value
                    elif SDES_Item == 3:
                        self.SourceDescriptions[i].EMAIL = Value
                    elif SDES_Item == 4:
                        self.SourceDescriptions[i].PHONE = Value
                    elif SDES_Item == 5:
                        self.SourceDescriptions[i].LOC = Value
                    elif SDES_Item == 6:
                        self.SourceDescriptions[i].TOOL = Value
                    elif SDES_Item == 7:
                        self.SourceDescriptions[i].NOTE = Value
                    elif SDES_Item == 8:
                        self.SourceDescriptions[i].PRIV = Value
                        # Extra parsing for PRIV is needed
                    elif SDES_Item == 0:
                        # End of list. Padding to 32 bits
                        while (off % 4):
                            off += 1
        # BYE Packet
        elif PacketType == 203:
            SSRCCount = Ver_P_RC & 0b00011111
            i = 0
            for i in range(SSRCCount):
                SSRC, = unpack('!I', self.Datagram[off: off + 4])
                off += 4
                print 'SDES: SSRC ' + str(SSRC) + ' is saying goodbye.'
        # Application specific packet
        elif PacketType == 204:
            Subtype = Ver_P_RC & 0b00011111
            SSRC, = unpack('!I', self.Datagram[off: off + 4])
            Name = self.Datagram[off + 4: off + 8]
            AppData = self.Datagram[off + 8: off + Length]
            print 'SDES: APP Packet "' + Name + '" from SSRC ' + str(SSRC) + '.'
            off += Length
        # Check if there is something else in the datagram        
        if self.Datagram[off:]:
            self.Datagram = self.Datagram[off:]
            self.parse()
    
    def generateRR(self):
        # Ver 2, Pad 0, RC 1
        Ver_P_RC = 0b10000001
        # PT 201, Length 7, SSRC 0xF00F - let it be our ID
        Header = pack('!BBHI', Ver_P_RC, 201, 7, 0x0000F00F)
        NTP_32 = (self.NTP_TimestampH & 0x0000FFFF) + ((self.NTP_TimestampL & 0xFFFF0000) >> 16)
        # No lost packets, no delay in receiving data, RR sent right after receiving SR
        # Instead of self.SenderPacketCount should be proper value
        ReceiverReport = pack('!IBBHIIII', self.SSRC_sender, 0, 0, 0, self.SenderPacketCount, 1, NTP_32, 1)
        return Header + ReceiverReport