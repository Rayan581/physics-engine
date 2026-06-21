import math
import pygame
from config import *


def _rot(lx, ly, ca, sa, ox, oy):
    return ox + lx*ca - ly*sa, oy + lx*sa + ly*ca

def _draw_ghost_poly(surface, pts):
    min_x = min(p[0] for p in pts); max_x = max(p[0] for p in pts)
    min_y = min(p[1] for p in pts); max_y = max(p[1] for p in pts)
    w = max_x - min_x; h = max_y - min_y
    if w > 0 and h > 0:
        g = pygame.Surface((int(w), int(h)), pygame.SRCALPHA)
        local_pts = [(p[0] - min_x, p[1] - min_y) for p in pts]
        pygame.draw.polygon(g, (80, 180, 255, 40), local_pts)
        surface.blit(g, (int(min_x), int(min_y)))
    pygame.draw.polygon(surface, Colors.WHITE, pts, 2)


class Body:
    def __init__(self, x, y, mass=1.0, restitution=0.5):
        self.x = float(x);  self.y = float(y)
        self.mass = float(mass)
        self.restitution = float(restitution)
        self.vx = 0.0;  self.vy = 0.0
        self.angle = 0.0
        self.angular_velocity = 0.0
        self.fixed = False
        self.layers = {"Default"}
        self.color = BODY_COLOR
        self._snap()

    def _snap(self):
        self._init = dict(x=self.x, y=self.y, vx=0.0, vy=0.0, angle=0.0, av=0.0)

    def reset(self):
        s = self._init
        self.x = s['x'];  self.y = s['y']
        self.vx = s['vx']; self.vy = s['vy']
        self.angle = s['angle'];  self.angular_velocity = s['av']

    def integrate(self, dt):
        if self.fixed: return
        self.vy += GRAVITY * dt
        self.x  += self.vx * dt;  self.y  += self.vy * dt
        self.angular_velocity *= (1.0 - 0.015 * dt * 60)   # angular damping
        self.angle += self.angular_velocity * dt

    @property
    def inv_mass(self):    return 0.0 if self.fixed else 1.0 / self.mass
    @property
    def inv_inertia(self):
        if self.fixed: return 0.0
        I = self.moment_of_inertia()
        return 0.0 if I <= 0 else 1.0 / I

    def moment_of_inertia(self): raise NotImplementedError
    def get_vertices(self):       raise NotImplementedError
    def get_axes(self):           raise NotImplementedError
    def project(self, ax, ay):    raise NotImplementedError
    def hit_test(self, px, py):   raise NotImplementedError

    def get_handles(self):
        return []

    def resize(self, handle_id, wp_x, wp_y):
        pass

    def draw(self, surface, cam, ghost=False):         raise NotImplementedError
    def draw_outline(self, surface, cam, color, width=2): raise NotImplementedError

    def to_dict(self):
        return {
            "type": type(self).__name__,
            "x": self.x, "y": self.y,
            "vx": self.vx, "vy": self.vy,
            "angle": self.angle, "angular_velocity": self.angular_velocity,
            "mass": self.mass, "restitution": self.restitution,
            "fixed": self.fixed,
            "layers": list(self.layers),
            "color": list(self.color),
            "_init": self._init
        }

    def _load_base_dict(self, d):
        self.vx = d.get("vx", 0.0)
        self.vy = d.get("vy", 0.0)
        self.angle = d.get("angle", 0.0)
        self.angular_velocity = d.get("angular_velocity", 0.0)
        self.fixed = d.get("fixed", False)
        self.layers = set(d.get("layers", ["Default"]))
        self.color = tuple(d.get("color", BODY_COLOR))
        self._init = d.get("_init", dict(x=self.x, y=self.y, vx=0.0, vy=0.0, angle=0.0, av=0.0))

    @staticmethod
    def from_dict(d: dict):
        typ = d.get("type")
        if typ == "RectBody":
            b = RectBody(d["x"], d["y"], d["width"], d["height"], d["mass"], d["restitution"])
        elif typ == "CircleBody":
            b = CircleBody(d["x"], d["y"], d["radius"], d["mass"], d["restitution"])
        elif typ == "PolygonBody":
            b = PolygonBody(d["points"], d["mass"], d["restitution"])
        else:
            return None
        b._load_base_dict(d)
        return b


class RectBody(Body):
    def __init__(self, cx, cy, w, h, mass=1.0, restitution=0.5):
        super().__init__(cx, cy, mass, restitution)
        self.width = float(w);  self.height = float(h)

    def to_dict(self):
        d = super().to_dict()
        d["width"] = self.width
        d["height"] = self.height
        return d

    def moment_of_inertia(self):
        return self.mass * (self.width**2 + self.height**2) / 12.0

    def get_vertices(self):
        hw, hh = self.width*.5, self.height*.5
        ca, sa = math.cos(self.angle), math.sin(self.angle)
        return [_rot(lx,ly,ca,sa,self.x,self.y)
                for lx,ly in [(-hw,-hh),(hw,-hh),(hw,hh),(-hw,hh)]]

    def get_axes(self):
        v = self.get_vertices(); axes = []
        for i in range(4):
            ex=v[(i+1)%4][0]-v[i][0]; ey=v[(i+1)%4][1]-v[i][1]
            l=math.hypot(ex,ey)
            if l: axes.append((-ey/l, ex/l))
        return axes

    def project(self, ax, ay):
        d=[vx*ax+vy*ay for vx,vy in self.get_vertices()]
        return min(d), max(d)

    def hit_test(self, px, py):
        dx,dy=px-self.x,py-self.y
        ca,sa=math.cos(-self.angle),math.sin(-self.angle)
        lx=dx*ca-dy*sa; ly=dx*sa+dy*ca
        return abs(lx)<=self.width*.5 and abs(ly)<=self.height*.5

    def _screen_pts(self, cam):
        return [(int(x),int(y)) for x,y in
                [cam.w2s(vx,vy) for vx,vy in self.get_vertices()]]

    def draw(self, surface, cam, ghost=False):
        pts = self._screen_pts(cam)
        if ghost:
            _draw_ghost_poly(surface, pts)
            return
            
        col = tuple(min(255, max(0, int(c * 0.7))) for c in self.color) if self.fixed else self.color
        pygame.draw.polygon(surface, col, pts)
        pygame.draw.polygon(surface, Colors.BLACK, pts, 1)
        # Centre-of-mass dot
        sx, sy = cam.w2s(self.x, self.y)
        pygame.draw.circle(surface, (220, 60, 60), (int(sx), int(sy)), max(3, int(3*cam.zoom)))

    def draw_outline(self, surface, cam, color, width=2):
        pygame.draw.polygon(surface, color, self._screen_pts(cam), width)

    def get_handles(self):
        return self.get_vertices()

    def resize(self, handle_id, wp_x, wp_y):
        v = self.get_vertices()
        fixed = v[(handle_id + 2) % 4]
        self.x = (fixed[0] + wp_x) / 2.0
        self.y = (fixed[1] + wp_y) / 2.0
        dx = wp_x - fixed[0]
        dy = wp_y - fixed[1]
        ca, sa = math.cos(-self.angle), math.sin(-self.angle)
        self.width = max(1.0, abs(dx * ca - dy * sa))
        self.height = max(1.0, abs(dx * sa + dy * ca))


class CircleBody(Body):
    def __init__(self, cx, cy, radius, mass=1.0, restitution=0.5):
        super().__init__(cx, cy, mass, restitution)
        self.radius = float(radius)

    def to_dict(self):
        d = super().to_dict()
        d["radius"] = self.radius
        return d

    def moment_of_inertia(self):  return .5*self.mass*self.radius**2
    def get_vertices(self):        return [(self.x, self.y)]
    def get_axes(self):            return []

    def project(self, ax, ay):
        c=self.x*ax+self.y*ay; return c-self.radius, c+self.radius

    def hit_test(self, px, py):
        return math.hypot(px-self.x, py-self.y) <= self.radius

    def draw(self, surface, cam, ghost=False):
        sx, sy = cam.w2s(self.x, self.y)
        r = max(1, int(self.radius * cam.zoom))
        
        if ghost:
            g = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(g, (80, 180, 255, 40), (r, r), r)
            surface.blit(g, (int(sx)-r, int(sy)-r))
            pygame.draw.circle(surface, Colors.WHITE, (int(sx), int(sy)), r, 2)
            return

        col = tuple(min(255, max(0, int(c * 0.7))) for c in self.color) if self.fixed else self.color
        lw = max(1, int(cam.zoom))
        pygame.draw.circle(surface, col, (int(sx), int(sy)), r)
        pygame.draw.circle(surface, Colors.BLACK, (int(sx), int(sy)), r, lw)
        ex = int(sx + r*math.cos(self.angle))
        ey = int(sy + r*math.sin(self.angle))
        pygame.draw.line(surface, Colors.BLACK, (int(sx), int(sy)), (ex, ey), lw)

    def draw_outline(self, surface, cam, color, width=2):
        sx, sy = cam.w2s(self.x, self.y)
        r = max(1, int(self.radius * cam.zoom))
        pygame.draw.circle(surface, color, (int(sx), int(sy)), r + width, width)

    def get_handles(self):
        hx = self.x + self.radius * math.cos(self.angle)
        hy = self.y + self.radius * math.sin(self.angle)
        return [(hx, hy)]

    def resize(self, handle_id, wp_x, wp_y):
        self.radius = max(1.0, math.hypot(wp_x - self.x, wp_y - self.y))


class PolygonBody(Body):
    def __init__(self, points, mass=1.0, restitution=0.5):
        cx, cy = self._centroid(points)
        super().__init__(cx, cy, mass, restitution)
        self.local_points = [(p[0]-cx, p[1]-cy) for p in points]

    def to_dict(self):
        d = super().to_dict()
        # Restore absolute points for saving (though they will be offset from 0,0 since we pass them to constructor)
        # Actually, PolygonBody expects absolute points, but our constructor centers them.
        # If we just pass `self.local_points` shifted by `self.x, self.y`, it will reconstruct correctly.
        d["points"] = [[px + self.x, py + self.y] for px, py in self.local_points]
        return d

    @staticmethod
    def _centroid(pts):
        n=len(pts)
        if n<3: return sum(p[0]for p in pts)/n, sum(p[1]for p in pts)/n
        area=cx=cy=0.0
        for i in range(n):
            x0,y0=pts[i]; x1,y1=pts[(i+1)%n]
            c=x0*y1-x1*y0; area+=c; cx+=(x0+x1)*c; cy+=(y0+y1)*c
        area*=.5
        if abs(area)<1e-9: return sum(p[0]for p in pts)/n, sum(p[1]for p in pts)/n
        return cx/(6*area), cy/(6*area)

    def moment_of_inertia(self):
        num=den=0.0; pts=self.local_points; n=len(pts)
        for i in range(n):
            p0,p1=pts[i],pts[(i+1)%n]
            c=abs(p0[0]*p1[1]-p1[0]*p0[1])
            d=p0[0]**2+p0[1]**2+p0[0]*p1[0]+p0[1]*p1[1]+p1[0]**2+p1[1]**2
            num+=c*d; den+=c
        return self.mass*num/(den*6) if den else self.mass

    def get_vertices(self):
        ca,sa=math.cos(self.angle),math.sin(self.angle)
        return [_rot(lx,ly,ca,sa,self.x,self.y) for lx,ly in self.local_points]

    def get_axes(self):
        v=self.get_vertices(); n=len(v); axes=[]
        for i in range(n):
            ex=v[(i+1)%n][0]-v[i][0]; ey=v[(i+1)%n][1]-v[i][1]
            l=math.hypot(ex,ey)
            if l: axes.append((-ey/l, ex/l))
        return axes

    def project(self, ax, ay):
        d=[vx*ax+vy*ay for vx,vy in self.get_vertices()]
        return min(d), max(d)

    def hit_test(self, px, py):
        verts=self.get_vertices(); n=len(verts); inside=False; j=n-1
        for i in range(n):
            xi,yi=verts[i]; xj,yj=verts[j]
            if ((yi>py)!=(yj>py)) and (px<(xj-xi)*(py-yi)/(yj-yi)+xi):
                inside=not inside
            j=i
        return inside

    def _screen_pts(self, cam):
        return [(int(x),int(y)) for x,y in
                [cam.w2s(vx,vy) for vx,vy in self.get_vertices()]]

    def draw(self, surface, cam, ghost=False):
        pts = self._screen_pts(cam)
        if ghost:
            _draw_ghost_poly(surface, pts)
            return

        col = tuple(min(255, max(0, int(c * 0.7))) for c in self.color) if self.fixed else self.color
        pygame.draw.polygon(surface, col, pts)
        pygame.draw.polygon(surface, Colors.BLACK, pts, 1)
        # Centre-of-mass dot
        sx, sy = cam.w2s(self.x, self.y)
        pygame.draw.circle(surface, (220, 60, 60), (int(sx), int(sy)), max(3, int(3*cam.zoom)))

    def draw_outline(self, surface, cam, color, width=2):
        pygame.draw.polygon(surface, color, self._screen_pts(cam), width)

    def get_handles(self):
        return self.get_vertices()

    def resize(self, handle_id, wp_x, wp_y):
        dx = wp_x - self.x
        dy = wp_y - self.y
        ca, sa = math.cos(-self.angle), math.sin(-self.angle)
        lx = dx * ca - dy * sa
        ly = dx * sa + dy * ca
        self.local_points[handle_id] = (lx, ly)

    def recenter(self):
        cx_local, cy_local = self._centroid(self.local_points)
        ca, sa = math.cos(self.angle), math.sin(self.angle)
        shift_x = cx_local * ca - cy_local * sa
        shift_y = cx_local * sa + cy_local * ca
        self.x += shift_x
        self.y += shift_y
        self.local_points = [(p[0] - cx_local, p[1] - cy_local) for p in self.local_points]
