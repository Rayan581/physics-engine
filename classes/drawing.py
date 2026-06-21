import math
import pygame
from config import Colors

POLYGON_CLOSE_RADIUS = 20   # world-space pixels to snap-close a polygon


class DrawingTool:
    GHOST_COLOR   = (120, 200, 255)
    OUTLINE_COLOR = (120, 200, 255)
    CLOSE_RING_COLOR = (80, 255, 140)

    def __init__(self):
        self.mode: str | None = None
        self._points: list[tuple] = []   # world-space clicks
        pygame.font.init()
        self.font = pygame.font.SysFont("segoeui", 12)

    def set_mode(self, mode):
        self.mode = mode;  self._points = []

    def cancel(self):
        self.mode = None;  self._points = []

    def handle_click(self, world_pos, add_body_cb, bodies=None, add_joint_cb=None):
        if self.mode == 'rect':    return self._do_rect(world_pos, add_body_cb)
        if self.mode == 'circle':  return self._do_circle(world_pos, add_body_cb)
        if self.mode == 'polygon': return self._do_polygon(world_pos, add_body_cb)
        if self.mode == 'motor':   return self._do_motor(world_pos, bodies, add_joint_cb)
        return False

    def draw_preview(self, surface, cam, world_mouse):
        if self.mode == 'rect':    self._prev_rect(surface, cam, world_mouse)
        elif self.mode == 'circle':  self._prev_circle(surface, cam, world_mouse)
        elif self.mode == 'polygon': self._prev_polygon(surface, cam, world_mouse)
        elif self.mode == 'motor':   self._prev_motor(surface, cam, world_mouse)

    # ── rect ────────────────────────────────────────────────────────────────────

    def _do_rect(self, pos, cb):
        self._points.append(pos)
        if len(self._points) == 2:
            a, b = self._points
            x,y = min(a[0],b[0]), min(a[1],b[1])
            w,h = abs(b[0]-a[0]), abs(b[1]-a[1])
            if w>1 and h>1:
                from classes.body import RectBody
                cb(RectBody(x+w/2, y+h/2, w, h))
            self._points = [];  return True
        return False

    def _prev_rect(self, surface, cam, wm):
        if not self._points: return
        sa = cam.w2s(*self._points[0]);  sm = cam.w2s(*wm)
        x=min(sa[0],sm[0]); y=min(sa[1],sm[1])
        w=abs(sm[0]-sa[0]); h=abs(sm[1]-sa[1])
        if w<1 or h<1: return
        g = pygame.Surface((int(w),int(h)), pygame.SRCALPHA)
        g.fill((*self.GHOST_COLOR, 40))
        surface.blit(g, (int(x),int(y)))
        pygame.draw.rect(surface, self.OUTLINE_COLOR, (int(x),int(y),int(w),int(h)), 2)

        world_w = abs(wm[0] - self._points[0][0])
        world_h = abs(wm[1] - self._points[0][1])
        ts = self.font.render(f"{world_w:.1f} x {world_h:.1f}", True, Colors.WHITE)
        surface.blit(ts, (int(x + w/2 - ts.get_width()/2), int(y + h + 4)))

    # ── circle ──────────────────────────────────────────────────────────────────

    def _do_circle(self, pos, cb):
        self._points.append(pos)
        if len(self._points) == 2:
            cx,cy = self._points[0];  rx,ry = self._points[1]
            r = math.hypot(rx-cx, ry-cy)
            if r>1:
                from classes.body import CircleBody
                cb(CircleBody(cx, cy, r))
            self._points = [];  return True
        return False

    def _prev_circle(self, surface, cam, wm):
        if not self._points: return
        sc = cam.w2s(*self._points[0]);  sm = cam.w2s(*wm)
        r = int(math.hypot(sm[0]-sc[0], sm[1]-sc[1]))
        if r<1: return
        g = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(g, (*self.GHOST_COLOR, 40), (r,r), r)
        surface.blit(g, (int(sc[0])-r, int(sc[1])-r))
        pygame.draw.circle(surface, self.OUTLINE_COLOR, (int(sc[0]),int(sc[1])), r, 2)
        pygame.draw.line(surface, self.OUTLINE_COLOR, (int(sc[0]),int(sc[1])), (int(sm[0]),int(sm[1])), 1)

        world_r = math.hypot(wm[0] - self._points[0][0], wm[1] - self._points[0][1])
        ts = self.font.render(f"r: {world_r:.1f}", True, Colors.WHITE)
        surface.blit(ts, (int(sc[0] + (sm[0]-sc[0])/2), int(sc[1] + (sm[1]-sc[1])/2)))

    # ── polygon ─────────────────────────────────────────────────────────────────

    def _near_first(self, wpos):
        if not self._points: return False
        return math.hypot(wpos[0]-self._points[0][0],
                          wpos[1]-self._points[0][1]) <= POLYGON_CLOSE_RADIUS

    def _do_polygon(self, pos, cb):
        if len(self._points) >= 3 and self._near_first(pos):
            from classes.body import PolygonBody
            cb(PolygonBody(list(self._points)))
            self._points = [];  return True
        self._points.append(pos)
        return False

    def _prev_polygon(self, surface, cam, wm):
        all_w = self._points + [wm]
        all_s = [(int(x),int(y)) for x,y in [cam.w2s(*p) for p in all_w]]
        if len(all_s) >= 2:
            pygame.draw.lines(surface, self.OUTLINE_COLOR, False, all_s, 2)
        if len(all_s) >= 3:
            g = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(g, (*self.GHOST_COLOR, 30), all_s)
            surface.blit(g, (0,0))
        if len(self._points) >= 2:
            pygame.draw.line(surface, self.OUTLINE_COLOR, all_s[-1], all_s[0], 1)
        if self._points:
            near = self._near_first(wm)
            first_s = (int(x) for x in cam.w2s(*self._points[0]))
            ring_r = max(2, int(POLYGON_CLOSE_RADIUS * cam.zoom))
            pygame.draw.circle(surface,
                               self.CLOSE_RING_COLOR if near else (160,160,160),
                               (int(cam.w2s(*self._points[0])[0]),
                                int(cam.w2s(*self._points[0])[1])),
                               ring_r, 2)
            
            # Show length of current edge
            world_dist = math.hypot(wm[0] - self._points[-1][0], wm[1] - self._points[-1][1])
            ts = self.font.render(f"{world_dist:.1f}", True, Colors.WHITE)
            sm = cam.w2s(*wm)
            slast = cam.w2s(*self._points[-1])
            surface.blit(ts, (int(slast[0] + (sm[0]-slast[0])/2), int(slast[1] + (sm[1]-slast[1])/2)))

    # ── motor ───────────────────────────────────────────────────────────────────

    def _do_motor(self, pos, bodies, add_joint_cb):
        if not bodies or not add_joint_cb: return False
        
        # Hit test all bodies under cursor, in reverse order (top first)
        hit_bodies = [b for b in reversed(bodies) if b.hit_test(*pos)]
        
        if not hit_bodies:
            return False  # Need at least one body to attach a motor to
            
        body_a = hit_bodies[0]
        body_b = hit_bodies[1] if len(hit_bodies) > 1 else None
        
        from classes.joints import MotorJoint
        joint = MotorJoint(body_a, body_b, pos[0], pos[1])
        add_joint_cb(joint)
        return True

    def _prev_motor(self, surface, cam, wm):
        sm = cam.w2s(*wm)
        pygame.draw.circle(surface, (255, 150, 0), (int(sm[0]), int(sm[1])), max(4, int(6*cam.zoom)), 2)
        pygame.draw.circle(surface, (255, 150, 0), (int(sm[0]), int(sm[1])), max(1, int(2*cam.zoom)))
