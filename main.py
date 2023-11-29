import struct
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

marker_mapping = {
    0xffd8: "Start of image",
    0xffe0: "Application Default Header",
    0xffdb: "Quantification Table",
    0xffc0: "Start of frame",
    0xffc4: "Define Huffman Table",
    0xffda: "Start of scan",
    0xffd9: "End of image",
}


class JPEG:
    def __init__(self, image_file):
        with open(image_file, "rb") as f:
            self.img_data = f.read()

    def decode(self):
        data = self.img_data

        while True:
            marker, = struct.unpack(">H", data[0:2])
            print(marker_mapping.get(marker)
                  if marker_mapping.get(marker) is not None else "")
            match marker:
                case 0xffd8:
                    data = data[2:]
                case 0xffd9:
                    return
                case 0xffda:
                    data = data[-2:]
                case _:
                    if len(data) == 0:
                        break
                    lenchuck, = struct.unpack(">H", data[2:4])
                    lenchuck += 2

                    chunck = data[4:lenchuck]
                    if marker == 0xffc4:
                        self.decodeHuffman(chunck)
                    data = data[lenchuck:]

    def decodeHuffman(self, data):
        offset = 0
        header, = struct.unpack("B", data[offset:offset+1])
        offset += 1

        # Extracting the elements after 16 bytes
        elements = []
        lengths = struct.unpack("BBBBBBBBBBBBBBBB", data[offset:offset+16])
        for i in lengths:
            elements += (struct.unpack("B"*i, data[offset:offset+i]))
            offset += i

        hf = huffman.HuffmanTable()
        hf.GetHuffmanBits(lengths, elements)
        data = data[offset:]

        print("Header:", header)
        print("lengths:", lengths)
        print("Elements:", len(elements))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("You must provide an image!")
        exit(1)
    img_path = sys.argv[1]
    img = JPEG(img_path)
    img.decode()
