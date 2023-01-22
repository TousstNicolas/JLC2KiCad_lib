import math
from KicadModTree import *


class Vector2(Vector2D):
    def __str__(self):
        return "Vector2({0}, {1})".format(self.x, self.y)

    def __repr__(self):
        return self.__str__()

    def __mul__(self, other):
        return Vector2(self.x * other, self.y * other)

    def __add__(self, other):
        return Vector2(self.x + other[0], self.y + other[1])

    def __sub__(self, other):
        return Vector2(self.x - other[0], self.y - other[1])

    def __getitem__(self, key):
        if key == 0:
            return self.x
        elif key == 1:
            return self.y
        else:
            raise Exception("Vector2 index out of range")

    def length(self):
        return math.sqrt(self.x * self.x + self.y * self.y)

    def perpendicularClockwise(self):
        return Vector2(-self.y, self.x)

    def perpendicularCounterClockwise(self):
        return Vector2(self.y, -self.x)

    def normalized(self):
        length = self.length()
        return Vector2(self.x / length, self.y / length)

    def angle(self, other):
        return math.acos(self.dot_product(other) / (self.length() * other.length())) * (
            180.0 / math.pi
        )

    def dot_product(self, other):
        return self.x * other.x + self.y * other.y
