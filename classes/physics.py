"""
Impulse-based 2D collision detection and response.
Shapes: CircleBody, RectBody (OBB), PolygonBody — all via SAT.
"""
import math
from dataclasses import dataclass
from typing import Optional
from classes.body import Body, CircleBody, RectBody, PolygonBody
from config import BOUNDARY_RESTITUTION, WIDTH, HEIGHT


@dataclass
class Manifold:
    a: Body
    b: Body
    normal: tuple   # unit vector from b toward a
    depth: float
    contact: tuple  # approximate world-space contact point


# ── SAT helpers ─────────────────────────────────────────────────────────────────

def _overlap_1d(amin, amax, bmin, bmax):
    return min(amax, bmax) - max(amin, bmin)


def _sat_poly_poly(a: Body, b: Body) -> Optional[Manifold]:
    best = float('inf')
    best_n = None
    for tester, other in [(a, b), (b, a)]:
        for ax, ay in tester.get_axes():
            amin, amax = a.project(ax, ay)
            bmin, bmax = b.project(ax, ay)
            ov = _overlap_1d(amin, amax, bmin, bmax)
            if ov <= 0:
                return None
            if ov < best:
                best = ov
                da = a.x*ax + a.y*ay
                db = b.x*ax + b.y*ay
                best_n = (ax, ay) if da > db else (-ax, -ay)
    if best_n is None:
        return None
    nx, ny = best_n
    contact = ((a.x+b.x)*.5 + nx*best*.5, (a.y+b.y)*.5 + ny*best*.5)
    return Manifold(a, b, best_n, best, contact)


def _sat_circle_poly(c: CircleBody, p: Body) -> Optional[Manifold]:
    best = float('inf')
    best_n = None
    axes = list(p.get_axes())
    # Extra axis: circle centre → closest polygon vertex
    verts = p.get_vertices()
    closest = min(verts, key=lambda v: (v[0]-c.x)**2+(v[1]-c.y)**2)
    dx, dy = c.x-closest[0], c.y-closest[1]
    l = math.hypot(dx, dy)
    if l > 1e-9:
        axes.append((dx/l, dy/l))
    for ax, ay in axes:
        cmin, cmax = c.project(ax, ay)
        pmin, pmax = p.project(ax, ay)
        ov = _overlap_1d(cmin, cmax, pmin, pmax)
        if ov <= 0:
            return None
        if ov < best:
            best = ov
            dc = c.x*ax+c.y*ay; dp = p.x*ax+p.y*ay
            best_n = (ax, ay) if dc > dp else (-ax, -ay)
    if best_n is None:
        return None
    nx, ny = best_n
    contact = (c.x - nx*c.radius, c.y - ny*c.radius)
    return Manifold(c, p, best_n, best, contact)


def _circle_circle(a: CircleBody, b: CircleBody) -> Optional[Manifold]:
    dx, dy = a.x-b.x, a.y-b.y
    dist = math.hypot(dx, dy)
    radii = a.radius + b.radius
    if dist >= radii:
        return None
    if dist < 1e-9:
        nx, ny = 1.0, 0.0
    else:
        nx, ny = dx/dist, dy/dist
    depth = radii - dist
    contact = (b.x + nx*(b.radius-depth*.5), b.y + ny*(b.radius-depth*.5))
    return Manifold(a, b, (nx, ny), depth, contact)


def detect(a: Body, b: Body) -> Optional[Manifold]:
    if isinstance(a, CircleBody) and isinstance(b, CircleBody):
        return _circle_circle(a, b)
    if isinstance(a, CircleBody):
        return _sat_circle_poly(a, b)
    if isinstance(b, CircleBody):
        m = _sat_circle_poly(b, a)
        if m:
            m.normal = (-m.normal[0], -m.normal[1])
        return m
    return _sat_poly_poly(a, b)


def resolve(m: Manifold):
    a, b = m.a, m.b
    nx, ny = m.normal
    rax = m.contact[0]-a.x; ray = m.contact[1]-a.y
    rbx = m.contact[0]-b.x; rby = m.contact[1]-b.y
    vax = a.vx - a.angular_velocity*ray
    vay = a.vy + a.angular_velocity*rax
    vbx = b.vx - b.angular_velocity*rby
    vby = b.vy + b.angular_velocity*rbx
    rvx = vax-vbx; rvy = vay-vby
    vn = rvx*nx + rvy*ny
    if vn > 0:
        return
    e = min(a.restitution, b.restitution)
    ra_n = rax*ny - ray*nx
    rb_n = rbx*ny - rby*nx
    denom = (a.inv_mass + b.inv_mass +
             ra_n**2*a.inv_inertia + rb_n**2*b.inv_inertia)
    if denom < 1e-10:
        return
    j = -(1+e)*vn / denom
    a.vx += j*a.inv_mass*nx;  a.vy += j*a.inv_mass*ny
    b.vx -= j*b.inv_mass*nx;  b.vy -= j*b.inv_mass*ny
    a.angular_velocity += j*a.inv_inertia*ra_n
    b.angular_velocity -= j*b.inv_inertia*rb_n
    # Friction
    tx = rvx - vn*nx; ty = rvy - vn*ny
    tl = math.hypot(tx, ty)
    if tl > 1e-9:
        tx /= tl; ty /= tl
        jt = -0.25 * abs(j)
        a.vx += jt*a.inv_mass*tx; a.vy += jt*a.inv_mass*ty
        b.vx -= jt*b.inv_mass*tx; b.vy -= jt*b.inv_mass*ty


def positional_correction(m: Manifold, percent=0.4, slop=0.5):
    corr = max(m.depth-slop, 0.0) / (m.a.inv_mass+m.b.inv_mass+1e-10) * percent
    cx = corr*m.normal[0]; cy = corr*m.normal[1]
    m.a.x += m.a.inv_mass*cx; m.a.y += m.a.inv_mass*cy
    m.b.x -= m.b.inv_mass*cx; m.b.y -= m.b.inv_mass*cy


def detect_all(bodies: list) -> list:
    manifolds = []
    for i in range(len(bodies)):
        for j in range(i+1, len(bodies)):
            m = detect(bodies[i], bodies[j])
            if m:
                manifolds.append(m)
    return manifolds


def boundary_collide(body: Body, W: int, H: int):
    if body.fixed:
        return
    e = BOUNDARY_RESTITUTION
    if isinstance(body, CircleBody):
        r = body.radius
        if body.x - r < 0:
            body.x = r;   body.vx =  abs(body.vx)*e; body.angular_velocity *= 0.8
        if body.x + r > W:
            body.x = W-r; body.vx = -abs(body.vx)*e; body.angular_velocity *= 0.8
        if body.y - r < 0:
            body.y = r;   body.vy =  abs(body.vy)*e
        if body.y + r > H:
            body.y = H-r; body.vy = -abs(body.vy)*e
            body.vx *= 0.97; body.angular_velocity *= 0.95
    else:
        verts = body.get_vertices()
        xs = [v[0] for v in verts]; ys = [v[1] for v in verts]
        if min(xs) < 0:
            body.x += -min(xs); body.vx =  abs(body.vx)*e; body.angular_velocity *= 0.8
        if max(xs) > W:
            body.x -= max(xs)-W; body.vx = -abs(body.vx)*e; body.angular_velocity *= 0.8
        if min(ys) < 0:
            body.y += -min(ys); body.vy =  abs(body.vy)*e
        if max(ys) > H:
            body.y -= max(ys)-H; body.vy = -abs(body.vy)*e
            body.vx *= 0.97; body.angular_velocity *= 0.95
