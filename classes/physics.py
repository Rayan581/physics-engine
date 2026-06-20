import math
from dataclasses import dataclass
from typing import Optional
from classes.body import Body, CircleBody
from config import WORLD_KILL_LIMIT


@dataclass
class Manifold:
    a: Body
    b: Body
    normal: tuple   # unit vector pointing from b toward a
    depth: float
    contacts: list[tuple]  # list of world-space contact points


# ── Circle – Circle ─────────────────────────────────────────────────────────────

def _circle_circle(a: CircleBody, b: CircleBody) -> Optional[Manifold]:
    dx, dy = a.x-b.x, a.y-b.y
    dist   = math.hypot(dx, dy)
    radii  = a.radius + b.radius
    if dist >= radii:
        return None
    if dist < 1e-9:
        nx, ny = 1.0, 0.0
    else:
        nx, ny = dx/dist, dy/dist
    contact = (b.x + nx*b.radius, b.y + ny*b.radius)
    return Manifold(a, b, (nx, ny), radii-dist, [contact])


# ── Circle – Polygon ────────────────────────────────────────────────────────────

def _circle_poly(c: CircleBody, p: Body) -> Optional[Manifold]:
    verts   = p.get_vertices()
    n       = len(verts)
    best_sq = float('inf')
    best_q  = None

    for i in range(n):
        ax, ay = verts[i];  bx, by = verts[(i+1) % n]
        ex, ey = bx-ax, by-ay
        el_sq  = ex*ex + ey*ey
        if el_sq < 1e-12: continue
        t  = max(0.0, min(1.0, ((c.x-ax)*ex + (c.y-ay)*ey) / el_sq))
        qx = ax + t*ex;  qy = ay + t*ey
        sq = (c.x-qx)**2 + (c.y-qy)**2
        if sq < best_sq:
            best_sq = sq;  best_q = (qx, qy)

    if best_q is None: return None

    dist   = math.sqrt(best_sq)
    inside = p.hit_test(c.x, c.y)

    if inside:
        depth = c.radius + dist
        if dist > 1e-9:
            nx = (best_q[0] - c.x) / dist
            ny = (best_q[1] - c.y) / dist
        else:
            dx, dy = p.x - c.x, p.y - c.y
            l = math.hypot(dx, dy)
            nx, ny = (dx/l, dy/l) if l > 1e-9 else (0.0, 1.0)
    else:
        depth = c.radius - dist
        if depth <= 0: return None
        if dist > 1e-9:
            nx = (c.x - best_q[0]) / dist
            ny = (c.y - best_q[1]) / dist
        else:
            dx, dy = c.x - p.x, c.y - p.y
            l = math.hypot(dx, dy)
            nx, ny = (dx/l, dy/l) if l > 1e-9 else (0.0, -1.0)

    # Use the point on the boundary as the contact point
    return Manifold(c, p, (nx, ny), depth, [best_q])


# ── Polygon – Polygon (SAT + Multi-Contact) ─────────────────────────────────────

def _overlap_1d(amin, amax, bmin, bmax):
    return min(amax, bmax) - max(amin, bmin)

def _point_in_poly(p, poly: Body, slop=0.1):
    for ax, ay in poly.get_axes():
        pmin, pmax = poly.project(ax, ay)
        proj = p[0]*ax + p[1]*ay
        if proj < pmin - slop or proj > pmax + slop:
            return False
    return True

def _sat_poly_poly(a: Body, b: Body) -> Optional[Manifold]:
    best = float('inf');  best_n = None

    for tester in (a, b):
        for ax, ay in tester.get_axes():
            amin, amax = a.project(ax, ay)
            bmin, bmax = b.project(ax, ay)
            ov = _overlap_1d(amin, amax, bmin, bmax)
            if ov <= 0: return None
            if ov < best:
                best = ov
                da = a.x*ax + a.y*ay;  db = b.x*ax + b.y*ay
                best_n = (ax, ay) if da > db else (-ax, -ay)

    if best_n is None: return None
    nx, ny = best_n

    # Multi-contact generation: find all vertices of A inside B, and B inside A
    contacts = []
    for v in a.get_vertices():
        if _point_in_poly(v, b): contacts.append(v)
    for v in b.get_vertices():
        if _point_in_poly(v, a): contacts.append(v)

    if not contacts:
        # Fallback if edge-to-edge alignment causes point_in_poly to miss due to float precision
        contacts = [max(b.get_vertices(), key=lambda v: v[0]*nx + v[1]*ny)]

    return Manifold(a, b, best_n, best, contacts)


# ── Dispatch ────────────────────────────────────────────────────────────────────

def detect(a: Body, b: Body) -> Optional[Manifold]:
    if isinstance(a, CircleBody) and isinstance(b, CircleBody): return _circle_circle(a, b)
    if isinstance(a, CircleBody): return _circle_poly(a, b)
    if isinstance(b, CircleBody): return _circle_poly(b, a)
    return _sat_poly_poly(a, b)


# ── Impulse resolution ──────────────────────────────────────────────────────────

def resolve(m: Manifold):
    a, b   = m.a, m.b
    nx, ny = m.normal
    e      = min(a.restitution, b.restitution)

    # Apply impulse sequentially at each contact point (stabilizes flat resting contacts)
    for cx, cy in m.contacts:
        rax = cx - a.x;  ray = cy - a.y
        rbx = cx - b.x;  rby = cy - b.y

        vax = a.vx - a.angular_velocity*ray;  vay = a.vy + a.angular_velocity*rax
        vbx = b.vx - b.angular_velocity*rby;  vby = b.vy + b.angular_velocity*rbx
        rvx = vax-vbx;  rvy = vay-vby
        vn  = rvx*nx + rvy*ny
        if vn > 0: continue

        ra_n = rax*ny - ray*nx
        rb_n = rbx*ny - rby*nx
        denom = a.inv_mass + b.inv_mass + ra_n**2*a.inv_inertia + rb_n**2*b.inv_inertia
        if denom < 1e-10: continue

        j = -(1.0 + e) * vn / denom
        # Distribute impulse magnitude slightly if multiple contacts to prevent over-bouncing
        j /= len(m.contacts)

        a.vx += j*a.inv_mass*nx;  a.vy += j*a.inv_mass*ny
        b.vx -= j*b.inv_mass*nx;  b.vy -= j*b.inv_mass*ny
        a.angular_velocity += j*a.inv_inertia*ra_n
        b.angular_velocity -= j*b.inv_inertia*rb_n

        # Coulomb friction
        vax2 = a.vx - a.angular_velocity*ray;  vay2 = a.vy + a.angular_velocity*rax
        vbx2 = b.vx - b.angular_velocity*rby;  vby2 = b.vy + b.angular_velocity*rbx
        rvx2 = vax2-vbx2;  rvy2 = vay2-vby2
        vn2  = rvx2*nx + rvy2*ny
        tx = rvx2 - vn2*nx;  ty = rvy2 - vn2*ny
        tl = math.hypot(tx, ty)
        if tl > 1e-9:
            tx /= tl;  ty /= tl
            ra_t = rax*ty - ray*tx
            rb_t = rbx*ty - rby*tx
            denom_t = a.inv_mass + b.inv_mass + ra_t**2*a.inv_inertia + rb_t**2*b.inv_inertia
            if denom_t > 1e-10:
                mu = 0.3
                jt = -tl / denom_t
                jt = max(jt, -mu*abs(j))
                a.vx += jt*a.inv_mass*tx;  a.vy += jt*a.inv_mass*ty
                b.vx -= jt*b.inv_mass*tx;  b.vy -= jt*b.inv_mass*ty
                a.angular_velocity += jt*a.inv_inertia*ra_t
                b.angular_velocity -= jt*b.inv_inertia*rb_t


# ── Positional correction ───────────────────────────────────────────────────────

def positional_correction(m: Manifold, percent=0.8, slop=0.1):
    denom = m.a.inv_mass + m.b.inv_mass
    if denom < 1e-10: return
    # Clamp depth correction to prevent teleporting from extreme deep overlaps
    depth = min(m.depth, 20.0)
    corr = max(depth - slop, 0.0) / denom * percent
    m.a.x += m.a.inv_mass * corr * m.normal[0]
    m.a.y += m.a.inv_mass * corr * m.normal[1]
    m.b.x -= m.b.inv_mass * corr * m.normal[0]
    m.b.y -= m.b.inv_mass * corr * m.normal[1]


def detect_all(bodies: list) -> list:
    out = []
    for i in range(len(bodies)):
        for j in range(i+1, len(bodies)):
            m = detect(bodies[i], bodies[j])
            if m: out.append(m)
    return out


def kill_oob(body: Body):
    if not body.fixed and (abs(body.x) > WORLD_KILL_LIMIT or abs(body.y) > WORLD_KILL_LIMIT):
        body.vx = body.vy = body.angular_velocity = 0.0
