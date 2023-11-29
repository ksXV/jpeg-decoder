class Stream:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def GetBit(self) -> int:
        b = self.data[self.pos >> 3]
        s = 7-(self.pos & 0x7)
        self.pos += 1
        return (b >> s) & 1

    def GetBitN(self, length: int) -> int:
        val = 0
        for i in range(length):
            val = val * 2 + self.GetBit
        return val
