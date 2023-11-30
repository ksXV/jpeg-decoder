import struct
import idct
import stream
import sys
import huffman

"""
Marker Identifier 	2 bytes 	0xff, 0xc4 to identify DHT marker
Length 	2 bytes 	This specifies the length of Huffman table
Huffman Table information 	1 byte 	bit 0..3: number of HT (0..3, otherwise error)
                        bit 4: type of HT, 0 = DC table, 1 = AC table
                        bit 5..7: not used, must be 0

Number of Symbols 	16 bytes 	Number of symbols with codes of length 1..16, the sum(n) of these bytes is the total number of codes, which must be <= 256
Symbols 	n bytes 	Table containing the symbols in order of increasing code length ( n = total number of codes ).
"""


def PrintMatrix(m):
    """
    A convenience function for printing matrices
    """
    for j in range(8):
        print("|", end="")
        for i in range(8):
            print("%d  |" % m[i + j * 8], end="\t")
        print()
    print()


def Clamp(col):
    """
    Makes sure col is between 0 and 255.
    """
    col = 255 if col > 255 else col
    col = 0 if col < 0 else col
    return int(col)


def ColorConversion(Y, Cr, Cb):
    """
    Converts Y, Cr and Cb to RGB color space
    """
    R = Cr * (2 - 2 * 0.299) + Y
    B = Cb * (2 - 2 * 0.114) + Y
    G = (Y - 0.114 * B - 0.299 * R) / 0.587
    return (Clamp(R + 128), Clamp(G + 128), Clamp(B + 128))


def DrawMatrix(x, y, matL, matCb, matCr):
    """
    Loops over a single 8x8 MCU and draws it on Tkinter canvas
    """
    for yy in range(8):
        for xx in range(8):
            c = "#%02x%02x%02x" % ColorConversion(
                matL[yy][xx], matCb[yy][xx], matCr[yy][xx]
            )
            x1, y1 = (x * 8 + xx) * 2, (y * 8 + yy) * 2
            x2, y2 = (x * 8 + (xx + 1)) * 2, (y * 8 + (yy + 1)) * 2
            w.create_rectangle(x1, y1, x2, y2, fill=c, outline=c)


def removeFF00(data):
    """
    Removes 0x00 after 0xff in the image scan section of JPEG
    """
    datapro = []
    i = 0
    while True:
        b, bnext = struct.unpack("BB", data[i:i + 2])
        if b == 0xFF:
            if bnext != 0:
                break
            datapro.append(data[i])
            i += 2
        else:
            datapro.append(data[i])
            i += 1
    return datapro, i


def GetArray(type, l, length):
    """
    A convenience function for unpacking an array from bitstream
    """
    s = ""
    for i in range(length):
        s = s + type
    return list(struct.unpack(s, l[:length]))


def DecodeNumber(code, bits):
    l = 2 ** (code - 1)
    if bits >= l:
        return bits
    else:
        return bits - (2 * l - 1)


class JPEG:
    def __init__(self, image_file: str):
        self.huffman_tables = {}
        self.quant = {}
        self.quantMapping = []
        with open(image_file, "rb") as f:
            self.img_data = f.read()

    @property
    def getWidth(self):
        return self.width

    @property
    def getHeigth(self):
        return self.height

    def BuildMatrix(self, stream: stream.Stream, index: int, quant: dict, oldccoeff):
        IDCT = idct.IDCT()

        code = self.huffman_tables[0 + index].GetCode(stream)
        bits = stream.GetBitN(code)
        dccoeff = DecodeNumber(code, bits) + oldccoeff

        IDCT.base[0] = (dccoeff) * quant[0]

        l = 1

        while l < 64:
            code = self.huffman_tables[16 + index].GetCode(stream)
            if code == 0:
                break

            if code > 15:
                l += code >> 4
                code = code & 0x0f

            bits = stream.GetBitN(code)

            if l < 64:
                coeff = DecodeNumber(code, bits)
                IDCT.base[l] = coeff * quant[l]
                l += 1

        IDCT.rearrange_using_zigzag()
        IDCT.perform_IDCT()

        return IDCT, dccoeff

    def StartScan(self, data: list, hdrlen: int):
        data, lenchunk = removeFF00(data[hdrlen:])

        st = stream.Stream(data)
        oldlumdccoeff, oldCbdccoeff, oldCrdccoeff = 0, 0, 0
        for y in range(self.height // 8):
            for x in range(self.width // 8):
                matL, oldlumdccoeff = self.BuildMatrix(
                    st, 0, self.quant[self.quantMapping[0]], oldlumdccoeff
                )
                matCr, oldCrdccoeff = self.BuildMatrix(
                    st, 1, self.quant[self.quantMapping[1]], oldCrdccoeff
                )
                matCb, oldCbdccoeff = self.BuildMatrix(
                    st, 1, self.quant[self.quantMapping[2]], oldCbdccoeff
                )
                DrawMatrix(x, y, matL.base, matCb.base, matCr.base)

        return lenchunk + hdrlen

    def DefineQuantizationTable(self, data: list[int]):
        (hdr,) = struct.unpack("B", data[0:1])
        self.quant[hdr] = GetArray("B", data[1:1+64], 64)
        data = data[65:]

    def BaselineDCT(self, data: list):
        hdr, self.height, self.width, components = struct.unpack(
            ">BHHB", data[0:6])
        print("size {width}x{height}".format(
            width=self.width, height=self.height))

        for i in range(components):
            id, samp, QtbId = struct.unpack("BBB", data[6+i*3:9+i*3])
            self.quantMapping.append(QtbId)

    def decode(self):
        data = self.img_data

        while True:
            (marker,) = struct.unpack(">H", data[0:2])

            if marker == 0xFFD8:
                data = data[2:]
            elif marker == 0xFFD9:
                return
            else:
                (len_chunk,) = struct.unpack(">H", data[2:4])
                len_chunk += 2
                chunk = data[4:len_chunk]
                if marker == 0xFFC4:
                    self.decodeHuffman(chunk)
                elif marker == 0xFFDB:
                    self.DefineQuantizationTable(chunk)
                elif marker == 0xFFC0:
                    self.BaselineDCT(chunk)
                elif marker == 0xFFDA:
                    len_chunk = self.StartScan(data, len_chunk)
                data = data[len_chunk:]
            if len(data) == 0:
                break

    def decodeHuffman(self, data):
        offset = 0
        (header,) = struct.unpack("B", data[offset:offset+1])
        offset += 1

        lengths = GetArray("B", data[offset:offset + 16], 16)
        offset += 16

        # Extracting the elements after 16 bytes
        elements = []
        for i in lengths:
            elements += (GetArray("B", data[offset:offset + i], i))
            offset += i

        hf = huffman.HuffmanTable()
        hf.GetHuffmanBits(lengths, elements)
        self.huffman_tables[header] = hf
        data = data[offset:]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("You must provide an image!")
        exit(1)
    import tkinter
    master = tkinter.Tk()
    w = tkinter.Canvas(master, width=1920, height=1200)
    w.pack()

    img_path = sys.argv[1]

    img = JPEG(img_path)
    print("Showing the image, hang tight")
    img.decode()

    tkinter.mainloop()
