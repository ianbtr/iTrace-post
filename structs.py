class Rect:
    def __init__(self, left, right, top, bottom):
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom
    def as_dict(self):
        return {
            "L": int(self.left),
            "R": int(self.right),
            "T": int(self.top),
            "B": int(self.bottom)
        }
    def area(self):
        return (self.right - self.left) * (self.bottom - self.top)