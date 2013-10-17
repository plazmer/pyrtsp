# -*- coding: utf-8 -*-
'''
This module handles RTP payload for MJPEG codec as described in RFC2435.
JPEG header restoration code is taken from that RFC, but adapted to Python.
'''
#   The following code can be used to create a quantization table from a
#   Q factor:

# Tables with leading underscores are alternative, but not from the
# specification. I took them from a certain JPEG image.
_jpeg_luma_quantizer = [
        16, 11, 10, 16, 24, 40, 51, 61,
        12, 12, 14, 19, 26, 58, 60, 55,
        14, 13, 16, 24, 40, 57, 69, 56,
        14, 17, 22, 29, 51, 87, 80, 62,
        18, 22, 37, 56, 68, 109, 103, 77,
        24, 35, 55, 64, 81, 104, 113, 92,
        49, 64, 78, 87, 103, 121, 120, 101,
        72, 92, 95, 98, 112, 100, 103, 99]

_jpeg_chroma_quantizer = [
        17, 18, 24, 47, 99, 99, 99, 99,
        18, 21, 26, 66, 99, 99, 99, 99,
        24, 26, 56, 99, 99, 99, 99, 99,
        47, 66, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99]

jpeg_luma_quantizer = [
      16,   11,   12,   14,   12,   10,   16,   14,
      13,   14,   18,   17,   16,   19,   24,   40,
      26,   24,   22,   22,   24,   49,   35,   37,
      29,   40,   58,   51,   61,   60,   57,   51,
      56,   55,   64,   72,   92,   78,   64,   68,
      87,   69,   55,   56,   80,  109,   81,   87,
      95,   98,  103,  104,  103,   62,   77,  113,
     121,  112,  100,  120,   92,  101,  103,   99]

jpeg_chroma_quantizer = [
      17,   18,   18,   24,   21,   24,   47,   26,
      26,   47,   99,   66,   56,   66,   99,   99,
      99,   99,   99,   99,   99,   99,   99,   99,
      99,   99,   99,   99,   99,   99,   99,   99,
      99,   99,   99,   99,   99,   99,   99,   99,
      99,   99,   99,   99,   99,   99,   99,   99,
      99,   99,   99,   99,   99,   99,   99,   99,
      99,   99,   99,   99,   99,   99,   99,   99]

 # Call MakeTables with the Q factor and two u_char[64] return arrays
def MakeTables(q, lqt, cqt):
    i = 0
    factor = q
    if q < 1:
        factor = 1.0
    if q > 99:
        factor = 99.0
    if q < 50:
        _q = 5000.0 / factor
    else:
        _q = 200.0 - factor*2
        
    for i in range(64):
        lq = int((jpeg_luma_quantizer[i] * _q + 50.0) / 100.0)
        cq = int((jpeg_chroma_quantizer[i] * _q + 50.0) / 100.0)
        # Limit the quantizers to 1 <= q <= 255
        if lq < 1:
            lq = 1
        elif lq > 255:
            lq = 255
        lqt.append(lq)
        
        if cq < 1:
            cq = 1
        elif cq > 255:
            cq = 255
        cqt.append(cq)
  
# Reconstruct Header
lum_dc_codelens = [0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0]

lum_dc_symbols = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

lum_ac_codelens = [0, 2, 1, 3, 3, 2, 4, 3, 5, 5, 4, 4, 0, 0, 1, 0x7d]

lum_ac_symbols = [
        0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12,
        0x21, 0x31, 0x41, 0x06, 0x13, 0x51, 0x61, 0x07,
        0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xa1, 0x08,
        0x23, 0x42, 0xb1, 0xc1, 0x15, 0x52, 0xd1, 0xf0,
        0x24, 0x33, 0x62, 0x72, 0x82, 0x09, 0x0a, 0x16,
        0x17, 0x18, 0x19, 0x1a, 0x25, 0x26, 0x27, 0x28,
        0x29, 0x2a, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39,
        0x3a, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49,
        0x4a, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
        0x5a, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69,
        0x6a, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79,
        0x7a, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
        0x8a, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98,
        0x99, 0x9a, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7,
        0xa8, 0xa9, 0xaa, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6,
        0xb7, 0xb8, 0xb9, 0xba, 0xc2, 0xc3, 0xc4, 0xc5,
        0xc6, 0xc7, 0xc8, 0xc9, 0xca, 0xd2, 0xd3, 0xd4,
        0xd5, 0xd6, 0xd7, 0xd8, 0xd9, 0xda, 0xe1, 0xe2,
        0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0xe8, 0xe9, 0xea,
        0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8,
        0xf9, 0xfa]

chm_dc_codelens = [0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0]

chm_dc_symbols = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

chm_ac_codelens = [0, 2, 1, 2, 4, 4, 3, 4, 7, 5, 4, 4, 0, 1, 2, 0x77]

chm_ac_symbols = [
        0x00, 0x01, 0x02, 0x03, 0x11, 0x04, 0x05, 0x21,
        0x31, 0x06, 0x12, 0x41, 0x51, 0x07, 0x61, 0x71,
        0x13, 0x22, 0x32, 0x81, 0x08, 0x14, 0x42, 0x91,
        0xa1, 0xb1, 0xc1, 0x09, 0x23, 0x33, 0x52, 0xf0,
        0x15, 0x62, 0x72, 0xd1, 0x0a, 0x16, 0x24, 0x34,
        0xe1, 0x25, 0xf1, 0x17, 0x18, 0x19, 0x1a, 0x26,
        0x27, 0x28, 0x29, 0x2a, 0x35, 0x36, 0x37, 0x38,
        0x39, 0x3a, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48,
        0x49, 0x4a, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58,
        0x59, 0x5a, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68,
        0x69, 0x6a, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78,
        0x79, 0x7a, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87,
        0x88, 0x89, 0x8a, 0x92, 0x93, 0x94, 0x95, 0x96,
        0x97, 0x98, 0x99, 0x9a, 0xa2, 0xa3, 0xa4, 0xa5,
        0xa6, 0xa7, 0xa8, 0xa9, 0xaa, 0xb2, 0xb3, 0xb4,
        0xb5, 0xb6, 0xb7, 0xb8, 0xb9, 0xba, 0xc2, 0xc3,
        0xc4, 0xc5, 0xc6, 0xc7, 0xc8, 0xc9, 0xca, 0xd2,
        0xd3, 0xd4, 0xd5, 0xd6, 0xd7, 0xd8, 0xd9, 0xda,
        0xe2, 0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0xe8, 0xe9,
        0xea, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8,
        0xf9, 0xfa]

def MakeQuantHeader(p, qt, tableNo):
    p.append(0xff)
    p.append(0xdb)            # DQT
    p.append(0)               # length msb
    p.append(67)              # length lsb
    p.append(tableNo)
    p.extend(qt)


def MakeHuffmanHeader(p, codelens, ncodes, symbols, nsymbols, tableNo, tableClass):
    p.append(0xff)
    p.append(0xc4)            # DHT
    p.append(0)               # length msb
    p.append(3 + ncodes + nsymbols) # length lsb
    p.append((tableClass << 4) | tableNo)
    p.extend(codelens)
    p.extend(symbols)

def MakeDRIHeader(p, dri):
    p.append(0xff)
    p.append(0xdd)            # DRI
    p.append(0x0)             # length msb
    p.append(4)               # length lsb
    p.append(dri >> 8)        # dri msb
    p.append(dri & 0xff)      # dri lsb


#===============================================================================
#    Arguments:
#      type, width, height: as supplied in RTP/JPEG header
#      lqt, cqt: quantization tables as either derived from
#           the Q field using MakeTables() or as specified
#           in section 4.2.
#      dri: restart interval in MCUs, or 0 if no restarts.
#  
#      p: pointer to return area
#  
#    Return value:
#      The length of the generated headers.
#  
#      Generate a frame and scan headers that can be prepended to the
#      RTP/JPEG data payload to produce a JPEG compressed image in
#      interchange format (except for possible trailing garbage and
#      absence of an EOI marker to terminate the scan).
#===============================================================================
 
def MakeHeaders(p, type, w, h, lqt, cqt, dri):
    p.append(0xff)
    p.append(0xd8)            # SOI
    MakeQuantHeader(p, lqt, 0)
    MakeQuantHeader(p, cqt, 1)

    if dri != 0:
        MakeDRIHeader(p, dri)

    p.append(0xff)
    p.append(0xc0)            # SOF
    p.append(0)               # length msb
    p.append(17)              # length lsb
    p.append(8)               # 8-bit precision
    p.append(h >> 8)          # height msb
    p.append(h & 255)               # height lsb
    p.append(w >> 8)          # width msb
    p.append(w & 255)               # wudth lsb
    p.append(3)               # number of components
    p.append(0)               # comp 0
    if type == 0:
        p.append(0x21)        # hsamp = 2, vsamp = 1
    else:
        p.append(0x22)        # hsamp = 2, vsamp = 2
    p.append(0)               # quant table 0
    p.append(1)               # comp 1
    p.append(0x11)            # hsamp = 1, vsamp = 1
    p.append(1)               # quant table 1
    p.append(2)               # comp 2
    p.append(0x11)            # hsamp = 1, vsamp = 1
    p.append(1)               # quant table 1
    MakeHuffmanHeader(p, lum_dc_codelens,
                          len(lum_dc_codelens),
                          lum_dc_symbols,
                          len(lum_dc_symbols), 0, 0)
    MakeHuffmanHeader(p, lum_ac_codelens,
                          len(lum_ac_codelens),
                          lum_ac_symbols,
                          len(lum_ac_symbols), 0, 1)
    MakeHuffmanHeader(p, chm_dc_codelens,
                          len(chm_dc_codelens),
                          chm_dc_symbols,
                          len(chm_dc_symbols), 1, 0)
    MakeHuffmanHeader(p, chm_ac_codelens,
                          len(chm_ac_codelens),
                          chm_ac_symbols,
                          len(chm_ac_symbols), 1, 1)
    p.append(0xff)
    p.append(0xda)            # SOS
    p.append(0)               # length msb
    p.append(12)              # length lsb
    p.append(3)               # 3 components
    p.append(0)               # comp 0
    p.append(0)               # huffman table 0
    p.append(1)               # comp 1
    p.append(0x11)            # huffman table 1
    p.append(2)               # comp 2
    p.append(0x11)            # huffman table 1
    p.append(0)               # first DCT coeff
    p.append(63)              # last DCT coeff
    p.append(0)               # sucessive approx.
    

from struct import unpack

def list2string(l):
    s = ''
    for c in l:
        s += chr(c)
    return s

def string2list(s):
    l = []
    for c in s:
        l.append(ord(c))
    return l

class RFC2435JPEG(object):
    'JPEG image recreation from RTP payload'
    def __init__(self):
        # Main part of these are header fields
        self.TypeSpecific = 0
        self.Offset = 0
        self.Type = 0
        self.Q = 0
        self.Width = 0
        self.Height = 0
        self.Datagram = "" # Recieved datagram
        self.JpegHeader = "" # Reconstructed header
        self.JpegPayload = "" # Raw JPEG fragment
        self.JpegImage = "" # Complete JPEG Image
        self.QT_MBZ = 0 # Quantization Table header
        self.QT_Precision = 0
        self.QT_Length = 0
        # These tables are put inside the JPEG header
        self.QT_luma = [] # Luma table
        self.QT_chroma = [] # Chroma table
        self.RM_Header = '' # Restart Marker header

    def loadDatagram(self, DatagramIn):
        self.Datagram = DatagramIn
        
    def parse(self):
        HOffset = 0
        LOffset = 0
        # Straightforward parsing
        (self.TypeSpecific,
        HOffset, #3 byte offset
        LOffset,
        self.Type,
        self.Q,
        self.Width,
        self.Height) = unpack('!BBHBBBB', self.Datagram[:8])
        self.Offest = (HOffset << 16) + LOffset
        self.Width = self.Width << 3
        self.Height = self.Height << 3
        
        # Check if we have Restart Marker header
        if 64 <= self.Type <= 127:
            # TODO: make use of that header
            self.RM_Header = self.Datagram[8:12]
            rm_i = 4 # Make offset for JPEG Header
        else:
            rm_i = 0
        
        # Check if we have Quantinization Tables embedded into JPEG Header
        # Only the first fragment will have it
        if self.Q > 127 and not self.JpegPayload:
            self.JpegPayload = self.Datagram[rm_i+8+132:]
            QT_Header = self.Datagram[rm_i+8:rm_i+140]
            (self.QT_MBZ,
             self.QT_Precision,
             self.QT_Length) = unpack('!BBH', QT_Header[:4])
            self.QT_luma = string2list(QT_Header[4:68])
            self.QT_chroma = string2list(QT_Header[68:132])
        else:
            self.JpegPayload += self.Datagram[rm_i+8:]
        # Clear tables. Q might be dynamic.
        if self.Q <= 127:
            self.QT_luma = []
            self.QT_chroma = []
            
    def makeJpeg(self):
        lqt = []
        cqt = []
        dri = 0
        # Use exsisting tables or generate ours
        if self.QT_luma:
            lqt=self.QT_luma
            cqt=self.QT_chroma
        else:
            MakeTables(self.Q,lqt,cqt)        
        JPEGHdr = []
        # Make a complete JPEG header
        MakeHeaders(JPEGHdr, self.Type, int(self.Width), int(self.Height), lqt, cqt, dri)
        self.JpegHeader = list2string(JPEGHdr)
        # And a complete JPEG image
        self.JpegImage = self.JpegHeader + self.JpegPayload
        self.JpegPayload = ''
        self.JpegHeader = ''
        self.Datagram = ''
