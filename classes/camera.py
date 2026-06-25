from config import CAMERA_MIN_ZOOM, CAMERA_MAX_ZOOM

class Camera:

    def __init__(self, view_w: int, view_h: int):
        self.view_w = view_w
        self.view_h = view_h
        self.cam_x  = 0.0   # world point at view centre
        self.cam_y  = 0.0
        self.zoom   = 1.0

    def w2s(self, wx, wy):
        """World → screen (canvas) coords."""
        sx = (wx - self.cam_x) * self.zoom + self.view_w / 2
        sy = (wy - self.cam_y) * self.zoom + self.view_h / 2
        return sx, sy

    def s2w(self, sx, sy):
        """Screen (canvas) → world coords."""
        wx = (sx - self.view_w / 2) / self.zoom + self.cam_x
        wy = (sy - self.view_h / 2) / self.zoom + self.cam_y
        return wx, wy

    def zoom_at(self, sx, sy, factor):
        wx, wy = self.s2w(sx, sy)
        self.zoom = max(CAMERA_MIN_ZOOM, min(CAMERA_MAX_ZOOM, self.zoom * factor))
        self.cam_x = wx - (sx - self.view_w / 2) / self.zoom
        self.cam_y = wy - (sy - self.view_h / 2) / self.zoom

    def pan(self, dx, dy):
        """Pan by a screen-space delta."""
        self.cam_x -= dx / self.zoom
        self.cam_y -= dy / self.zoom

    def reset(self):
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.zoom  = 1.0
