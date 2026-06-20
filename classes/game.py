import pygame
from config import *
from classes.body import Body
from classes.camera import Camera
from classes.drawing import DrawingTool
from classes.toolbox import Toolbox
from classes.context_menu import ContextMenu
from classes.physics import detect_all, resolve, positional_correction, kill_oob
from classes.joints import MotorJoint

STOPPED = 'stopped'
PLAYING = 'playing'
PAUSED  = 'paused'

SEL_COLOR  = (80, 200, 255)   # selection outline
BAND_COLOR = (80, 180, 255)   # rubber-band rect
DRAG_DIST  = 4                # px to distinguish click from drag (screen space)
ZOOM_IN    = 1.15
ZOOM_OUT   = 1 / 1.15


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((TOOLBOX_WIDTH + WIDTH, HEIGHT))
        self.clock  = pygame.time.Clock()
        self.running = True

        self.bodies:    list[Body] = []
        self.joints:    list[MotorJoint] = []
        self.selected:  set[Body]  = set()
        self.sim_state = STOPPED

        self.camera  = Camera(WIDTH, HEIGHT)
        self.drawing = DrawingTool()
        self.toolbox = Toolbox(0, 0, TOOLBOX_WIDTH, HEIGHT)
        self.toolbox.init_fonts()
        self.ctx_menu = ContextMenu()
        self.ctx_menu.init_fonts()

        self.canvas: pygame.Surface = self.screen.subsurface(
            pygame.Rect(TOOLBOX_WIDTH, 0, WIDTH, HEIGHT))

        # Left-drag state
        self._ld_mode    = None      # 'move' | 'band' | None
        self._ld_down_s  = None      # screen pos of LMB down
        self._ld_down_w  = None      # world pos of LMB down
        self._band_end_w = None      # current world pos for rubber-band
        self._move_off   = {}        # body -> (ox, oy) world offset

        # Right-drag state
        self._rd_down_s  = None      # screen pos of RMB down (canvas)
        self._rd_last_s  = None
        self._rd_moved   = False

    # ── helpers ─────────────────────────────────────────────────────────────────

    def _canvas_pos(self, screen_pos):
        return (screen_pos[0] - TOOLBOX_WIDTH, screen_pos[1])

    def _world_pos(self, screen_pos):
        return self.camera.s2w(*self._canvas_pos(screen_pos))

    def _body_at_world(self, wx, wy):
        for b in reversed(self.bodies):
            if b.hit_test(wx, wy):
                return b
        return None

    def _joint_at_world(self, wx, wy):
        import math
        for j in reversed(self.joints):
            ax, ay = j.get_anchor_a()
            if math.hypot(wx - ax, wy - ay) < max(10.0, 10.0 / self.camera.zoom):
                return j
        return None

    def _bodies_in_band(self):
        if self._ld_down_w is None or self._band_end_w is None:
            return set()
        x0 = min(self._ld_down_w[0], self._band_end_w[0])
        x1 = max(self._ld_down_w[0], self._band_end_w[0])
        y0 = min(self._ld_down_w[1], self._band_end_w[1])
        y1 = max(self._ld_down_w[1], self._band_end_w[1])
        return {b for b in self.bodies if b.hit_test((x0+x1)/2, (y0+y1)/2)
                or x0<=b.x<=x1 and y0<=b.y<=y1}

    # ── physics ─────────────────────────────────────────────────────────────────

    def _physics_step(self, dt: float):
        sub = dt / PHYSICS_SUBSTEPS
        for _ in range(PHYSICS_SUBSTEPS):
            for body in self.bodies:
                body.integrate(sub)
                
            self._last_manifolds = detect_all(self.bodies, self.joints)
            for m in self._last_manifolds:
                resolve(m)
                
            for j in self.joints:
                j.solve_velocity(sub)
                
            for m in self._last_manifolds:
                positional_correction(m)
                
            for j in self.joints:
                j.solve_position()
                
            for body in self.bodies:
                kill_oob(body)

    # ── sim control ─────────────────────────────────────────────────────────────

    def _play(self):
        if self.sim_state == STOPPED: self.drawing.cancel()
        self.sim_state = PLAYING;  self.ctx_menu.close();  self.selected.clear()

    def _pause(self):
        if self.sim_state == PLAYING: self.sim_state = PAUSED

    def _stop(self):
        self.sim_state = STOPPED
        for b in self.bodies: b.reset()
        for j in self.joints:
            # Re-calculate ref_angle on stop to avoid drift from manual edits
            angle_b = j.b.angle if j.b else 0.0
            j.ref_angle = angle_b - j.a.angle
        self.ctx_menu.close();  self.selected.clear()
        if hasattr(self, '_last_manifolds'):
            self._last_manifolds = []

    def _sim_action(self, a):
        if a == PLAYING: self._play()
        elif a == PAUSED: self._pause()
        elif a == STOPPED: self._stop()

    # ── run loop ────────────────────────────────────────────────────────────────

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.033)
            self.handle_events()
            if self.sim_state == PLAYING:
                self._physics_step(dt)
            self.canvas.fill(Colors.BLACK)
            self._draw()
            pygame.display.flip()
        pygame.quit()

    # ── events ──────────────────────────────────────────────────────────────────

    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False

            elif ev.type == pygame.KEYDOWN:
                if self.ctx_menu.is_open and self.ctx_menu.handle_key(ev):
                    continue
                self._key(ev.key)

            elif ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1: self._lmb_down(ev.pos)
                elif ev.button == 3: self._rmb_down(ev.pos)
                elif ev.button == 4: self._scroll(ev.pos, ZOOM_IN)
                elif ev.button == 5: self._scroll(ev.pos, ZOOM_OUT)

            elif ev.type == pygame.MOUSEBUTTONUP:
                if ev.button == 1: self._lmb_up(ev.pos)
                elif ev.button == 3: self._rmb_up(ev.pos)

            elif ev.type == pygame.MOUSEMOTION:
                self._motion(ev.pos)

    def _key(self, k):
        if k == pygame.K_ESCAPE:
            if self.ctx_menu.is_open: self.ctx_menu.close()
            elif self.drawing.mode:   self.drawing.cancel()
            else:                     self.running = False
        elif k == pygame.K_SPACE:
            if   self.sim_state == STOPPED: self._play()
            elif self.sim_state == PLAYING: self._pause()
            elif self.sim_state == PAUSED:  self._play()
        elif k == pygame.K_s: self._stop()
        elif k == pygame.K_r and self.sim_state == STOPPED:
            self.drawing.set_mode(None if self.drawing.mode=='rect'    else 'rect')
        elif k == pygame.K_c and self.sim_state == STOPPED:
            self.drawing.set_mode(None if self.drawing.mode=='circle'  else 'circle')
        elif k == pygame.K_p and self.sim_state == STOPPED:
            self.drawing.set_mode(None if self.drawing.mode=='polygon' else 'polygon')
        elif k == pygame.K_m and self.sim_state == STOPPED:
            self.drawing.set_mode(None if self.drawing.mode=='motor' else 'motor')
        elif k in (pygame.K_DELETE, pygame.K_BACKSPACE) and self.sim_state == STOPPED:
            if self.ctx_menu.is_open and self.ctx_menu.is_motor:
                # Delete the specific motor currently being edited
                motor = self.ctx_menu._body
                if motor in self.joints:
                    self.joints.remove(motor)
                self.ctx_menu.close()
            elif self.selected:
                # Delete selected bodies
                for b in self.selected:
                    if b in self.bodies:
                        self.bodies.remove(b)
                # Delete any joints attached to deleted bodies
                self.joints = [j for j in self.joints if j.a not in self.selected and j.b not in self.selected]
                self.selected.clear()
                self.ctx_menu.close()

    # ── left mouse ──────────────────────────────────────────────────────────────

    def _lmb_down(self, pos):
        # Toolbox
        if self.toolbox.contains(pos):
            act = self.toolbox.get_sim_action_at(pos)
            if act: self._sim_action(act); return
            tool = self.toolbox.get_tool_at(pos)
            if tool and self.sim_state == STOPPED:
                self.drawing.set_mode(None if self.drawing.mode==tool else tool)
            return

        # Context menu
        if self.ctx_menu.is_open:
            if self.ctx_menu.contains(pos): self.ctx_menu.handle_click(pos)
            else:                            self.ctx_menu.close()
            return

        if self.sim_state == PLAYING:
            return

        cp = self._canvas_pos(pos)
        wp = self.camera.s2w(*cp)

        # Drawing tool takes priority
        if self.drawing.mode and self.sim_state == STOPPED:
            self.drawing.handle_click(wp, self.bodies.append, self.bodies, self.joints.append)
            return

        # Begin left-drag tracking
        self._ld_down_s = cp
        self._ld_down_w = wp
        self._ld_mode   = None   # resolved in _motion or _lmb_up

        hit = self._body_at_world(*wp)
        if hit:
            if hit not in self.selected:
                mods = pygame.key.get_mods()
                if not (mods & pygame.KMOD_SHIFT):
                    self.selected.clear()
                self.selected.add(hit)
            # Prepare for possible move
            self._move_off = {b: (b.x - wp[0], b.y - wp[1]) for b in self.selected}
            self._ld_mode = 'move'
        else:
            self._ld_mode = 'band'
            self._band_end_w = wp

    def _lmb_up(self, pos):
        cp = self._canvas_pos(pos)
        wp = self.camera.s2w(*cp)

        if self._ld_mode == 'band':
            self._band_end_w = wp
            new_sel = self._bodies_in_band()
            mods = pygame.key.get_mods()
            if not (mods & pygame.KMOD_SHIFT):
                self.selected = new_sel
            else:
                self.selected |= new_sel
        elif self._ld_mode == 'move':
            # If barely moved, treat as single-select click
            if self._ld_down_s:
                dx = cp[0] - self._ld_down_s[0];  dy = cp[1] - self._ld_down_s[1]
                if dx*dx + dy*dy < DRAG_DIST**2:
                    hit = self._body_at_world(*wp)
                    if hit:
                        mods = pygame.key.get_mods()
                        if not (mods & pygame.KMOD_SHIFT):
                            self.selected = {hit}
                        else:
                            self.selected ^= {hit}
                else:
                    # Real drag — update each body's reset baseline to new position
                    for b in self._move_off:
                        b._snap()

        self._ld_mode = None;  self._ld_down_s = None
        self._move_off = {};   self._band_end_w = None

    # ── right mouse ─────────────────────────────────────────────────────────────

    def _rmb_down(self, pos):
        if self.toolbox.contains(pos): return
        cp = self._canvas_pos(pos)
        self._rd_down_s = cp;  self._rd_last_s = cp;  self._rd_moved = False

    def _rmb_up(self, pos):
        if self._rd_down_s is None: return
        cp = self._canvas_pos(pos)
        if not self._rd_moved and self.sim_state != PLAYING:
            wp = self.camera.s2w(*cp)
            hit_j = self._joint_at_world(*wp)
            if hit_j:
                self.ctx_menu.open(hit_j, *pos)
            else:
                hit = self._body_at_world(*wp)
                if hit:
                    self.ctx_menu.open(hit, *pos)
        self._rd_down_s = None;  self._rd_moved = False

    def _scroll(self, pos, factor):
        if self.toolbox.contains(pos): return
        cp = self._canvas_pos(pos)
        self.camera.zoom_at(cp[0], cp[1], factor)

    # ── motion ──────────────────────────────────────────────────────────────────

    def _motion(self, pos):
        cp = self._canvas_pos(pos)
        wp = self.camera.s2w(*cp)

        # Right: pan
        if self._rd_down_s is not None:
            dx = cp[0] - self._rd_last_s[0];  dy = cp[1] - self._rd_last_s[1]
            if abs(dx)+abs(dy) > 1:
                self.camera.pan(dx, dy)
                self._rd_moved = True
            self._rd_last_s = cp

        # Left: move or rubber-band
        if self._ld_mode == 'move':
            if self._ld_down_s:
                ddx = cp[0]-self._ld_down_s[0]; ddy = cp[1]-self._ld_down_s[1]
                if ddx*ddx+ddy*ddy >= DRAG_DIST**2:
                    for b, (ox,oy) in self._move_off.items():
                        b.x = wp[0]+ox;  b.y = wp[1]+oy
        elif self._ld_mode == 'band':
            self._band_end_w = wp

    # ── draw ────────────────────────────────────────────────────────────────────

    def _draw(self):
        cam = self.camera

        # Bodies
        for b in self.bodies:
            b.draw(self.canvas, cam)

        # Joints
        for j in self.joints:
            j.draw(self.canvas, cam)
            if self.ctx_menu.is_open and self.ctx_menu._body == j and j.limits_enabled:
                j.draw_limits(self.canvas, cam)

        # Selection outlines
        for b in self.selected:
            b.draw_outline(self.canvas, cam, SEL_COLOR, 2)

        # Contact points
        if DRAW_COLLISION_POINTS and hasattr(self, '_last_manifolds') and self._last_manifolds:
            for m in self._last_manifolds:
                for cx, cy in m.contacts:
                    sx, sy = cam.w2s(cx, cy)
                    pygame.draw.circle(self.canvas, (255, 255, 50), (int(sx), int(sy)), max(3, int(4*cam.zoom)))

        # Rubber-band
        if self._ld_mode == 'band' and self._ld_down_w and self._band_end_w:
            s0 = cam.w2s(*self._ld_down_w);  s1 = cam.w2s(*self._band_end_w)
            rx=int(min(s0[0],s1[0])); ry=int(min(s0[1],s1[1]))
            rw=int(abs(s1[0]-s0[0])); rh=int(abs(s1[1]-s0[1]))
            if rw>1 and rh>1:
                band = pygame.Surface((rw, rh), pygame.SRCALPHA)
                band.fill((*BAND_COLOR, 30))
                self.canvas.blit(band, (rx, ry))
                pygame.draw.rect(self.canvas, BAND_COLOR, (rx,ry,rw,rh), 1)

        # Ghost preview
        if self.sim_state == STOPPED and self.drawing.mode:
            mp = pygame.mouse.get_pos()
            wm = cam.s2w(*self._canvas_pos(mp))
            self.drawing.draw_preview(self.canvas, cam, wm)

        # Toolbox + context menu (on full screen)
        mp = pygame.mouse.get_pos()
        self.toolbox.draw(self.screen, self.drawing.mode, self.sim_state, mp)
        self.ctx_menu.draw(self.screen, mp)
