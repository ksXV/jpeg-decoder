class Stream:
    """
    A bit stream class with convenience methods
    """

    def __init__(self, data):
        self.data = data
        self.pos = 0

    def GetBit(self):
        b = self.data[self.pos >> 3]
        s = 7 - (self.pos & 0x7)
        self.pos += 1
        return (b >> s) & 1

    def GetBitN(self, l):
        val = 0
        for _ in range(l):
            val = val * 2 + self.GetBit()
        return val

    def len(self):
        return len(self.data)

