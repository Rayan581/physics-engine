import pygame
from config import *


class Body:
    def __init__(self, x, y, mass=1, velocity=(0, 0)):
        self.x = x
        self.y = y
        self.mass = mass
        self.velocity = velocity


class RectBody(Body):
    def __init__(self, x, y, width, height, mass=1, velocity=(0, 0)):
        super().__init__(x, y, mass, velocity)
        self.width = width
        self.height = height

    def draw(self, screen):
        pygame.draw.rect(screen, Colors.WHITE,
                         (self.x, self.y, self.width, self.height))


class CircleBody(Body):
    def __init__(self, x, y, radius, mass=1, velocity=(0, 0)):
        super().__init__(x, y, mass, velocity)
        self.radius = radius

    def draw(self, screen):
        pygame.draw.circle(screen, Colors.WHITE,
                           (int(self.x), int(self.y)), self.radius)


class PolygonBody(Body):
    def __init__(self, points, mass=1, velocity=(0, 0)):
        x, y = self._centroid(points)
        super().__init__(x, y, mass, velocity)
        self.points = points

    @staticmethod
    def _centroid(points):
        if not points:
            raise ValueError("Polygon must have at least one point")
        if len(points) < 3:
            x = sum(p[0] for p in points) / len(points)
            y = sum(p[1] for p in points) / len(points)
            return x, y

        area = 0.0
        cx = 0.0
        cy = 0.0
        count = len(points)
        for i in range(count):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % count]
            cross = x0 * y1 - x1 * y0
            area += cross
            cx += (x0 + x1) * cross
            cy += (y0 + y1) * cross

        area *= 0.5
        if area == 0.0:
            x = sum(p[0] for p in points) / len(points)
            y = sum(p[1] for p in points) / len(points)
            return x, y

        cx /= (6.0 * area)
        cy /= (6.0 * area)
        return cx, cy

    def draw(self, screen):
        pygame.draw.polygon(screen, Colors.WHITE, [
                            (int(p[0]), int(p[1])) for p in self.points])
