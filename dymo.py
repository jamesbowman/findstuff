#!/usr/bin/env python3
import time
import struct

# http://sites.dymo.com/Documents/LW450_Series_Technical_Reference.pdf

class Dymo:
    def __init__(self, f):
        self.f = f

    def cmd(self, s):
        self.f.write(bytes([0x1b]) + s)

    def reset(self):
        # self.f.write(bytes([0x1b]) * 85) # finish any partial line
        self.cmd(b'@')
        return

        for i in range(3):
            self.cmd(b'A')
            self.f.flush()
            status = self.f.read(1)[0]
            print(hex(status))
        time.sleep(.1)
        self.cmd('G')
        self.f.flush()
        time.sleep(.1)
        self.f.close()
        time.sleep(.1)
        assert 0

        pass
    def setlabellength(self, h):
        self.cmd(b'L' + struct.pack(">H", h))
    def setbytesperline(self, w):
        self.cmd(b'D' + bytes([w]))
    def formfeed(self):
        self.cmd(b'E')
    def shortformfeed(self):
        self.cmd(b'G')
    def feed(self, n):
        self.cmd(b"f1" + bytes([n]))
    def line(self, s):
        self.f.write(bytes([0x16]) + s)
    def image(self, pim, ff = True):
        assert pim.mode == "1"
        im = pim.point([255] + [0] * 255, "1")
        # im.save("x.png")
        bpl = (im.size[0] + 7) // 8
        self.setbytesperline(bpl)
        for y in range(im.size[1]):
            slice = im.crop((0, y, im.size[0], y + 1))
            s = slice.tobytes()
            assert len(s) == bpl, "%d bytes per line, but line length is %d" % (bpl, len(s))
            self.line(s)
        if ff:
            self.formfeed()
        self.f.flush()

if __name__ == "__main__":
    import sys
    from PIL import Image
    d = Dymo(open("/dev/usb/lp1", "wb"))
    d.reset()
    for a in sys.argv[1:]:
        s = Image.open(a).convert("1")
        (w, h) = s.size
        if w > h:
            s = s.transpose(Image.Transpose.ROTATE_270)
        (w, h) = s.size
        if h <= 1800:
            d.image(s)
        else:
            for y in range(0, h, 1800):
                t = s.crop((0, y, 1200, y + 1800))
                d.image(t)
