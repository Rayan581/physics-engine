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
        self.show_grid = True

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

    def _get_grid_spacing(self):
        import math
        target_world = 100.0 / self.camera.zoom
        magnitude = 10 ** math.floor(math.log10(target_world))
        norm = target_world / magnitude
        if norm < 2: return magnitude
        elif norm < 5: return 2 * magnitude
        else: return 5 * magnitude

    def _get_snapped_wp(self, cp):
        wp = list(self.camera.s2w(*cp))
        if getattr(self, 'show_grid', False):
            spacing = self._get_grid_spacing()
            wp[0] = round(wp[0] / spacing) * spacing
            wp[1] = round(wp[1] / spacing) * spacing
        return tuple(wp)

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

    def _file_action(self, action: str):
        from classes.serialization import get_save_path, get_open_path, save_to_file, load_from_file
        if action == 'save':
            path = get_save_path()
            if path: save_to_file(path, self.bodies, self.joints)
        elif action == 'load':
            path = get_open_path()
            if path:
                self.bodies, self.joints = load_from_file(path)
                self.selected.clear()
                self.ctx_menu.close()
        elif action == 'export':
            if self.selected:
                path = get_save_path()
                if path:
                    sel_joints = [j for j in self.joints if j.a in self.selected and (j.b is None or j.b in self.selected)]
                    save_to_file(path, list(self.selected), sel_joints)
        elif action == 'import':
            path = get_open_path()
            if path:
                new_bodies, new_joints = load_from_file(path)
                self.bodies.extend(new_bodies)
                self.joints.extend(new_joints)
                self.selected = set(new_bodies)

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
                self._key(ev)

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

    def _key(self, ev):
        k = ev.key
        mods = pygame.key.get_mods()
        ctrl = bool(mods & pygame.KMOD_CTRL)

        if ctrl and self.sim_state == STOPPED:
            from classes.serialization import get_save_path, get_open_path, save_to_file, load_from_file
            if k == pygame.K_s:
                # Save Scene
                path = get_save_path()
                if path: save_to_file(path, self.bodies, self.joints)
            elif k == pygame.K_o:
                # Load Scene
                path = get_open_path()
                if path:
                    self.bodies, self.joints = load_from_file(path)
                    self.selected.clear()
                    self.ctx_menu.close()
            elif k == pygame.K_e:
                # Export Selection
                if self.selected:
                    path = get_save_path()
                    if path:
                        # Find joints that only connect selected bodies
                        sel_joints = [j for j in self.joints if j.a in self.selected and (j.b is None or j.b in self.selected)]
                        save_to_file(path, list(self.selected), sel_joints)
            elif k == pygame.K_i:
                # Import Model
                path = get_open_path()
                if path:
                    new_bodies, new_joints = load_from_file(path)
                    self.bodies.extend(new_bodies)
                    self.joints.extend(new_joints)
                    self.selected = set(new_bodies)
            return

        if k == pygame.K_ESCAPE:
            if self.ctx_menu.is_open: self.ctx_menu.close()
            elif self.drawing.mode:   self.drawing.cancel()
            else:                     self.running = False
        elif k == pygame.K_SPACE:
            if   self.sim_state == STOPPED: self._play()
            elif self.sim_state == PLAYING: self._pause()
            elif self.sim_state == PAUSED:  self._play()
        elif k in (pygame.K_HOME, pygame.K_h):
            self.camera.cam_x = 0.0
            self.camera.cam_y = 0.0
        elif k == pygame.K_s: self._stop()
        elif k == pygame.K_r and self.sim_state == STOPPED:
            self.drawing.set_mode(None if self.drawing.mode=='rect'    else 'rect')
        elif k == pygame.K_g:
            self.show_grid = not self.show_grid
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
            
            file_act = self.toolbox.get_action_at(pos)
            if file_act and self.sim_state == STOPPED:
                self._file_action(file_act); return
                
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
        raw_wp = self.camera.s2w(*cp)
        snap_wp = self._get_snapped_wp(cp)

        # Drawing tool takes priority
        if self.drawing.mode and self.sim_state == STOPPED:
            self.drawing.handle_click(snap_wp, self.bodies.append, self.bodies, self.joints.append)
            return

        # Begin left-drag tracking
        self._ld_down_s = cp
        self._ld_down_w = raw_wp
        self._ld_mode   = None   # resolved in _motion or _lmb_up
        
        # Check resize handles first
        if self.sim_state == STOPPED:
            for b in self.selected:
                for i, h in enumerate(b.get_handles()):
                    hx, hy = self.camera.w2s(*h)
                    if (cp[0] - hx)**2 + (cp[1] - hy)**2 <= 64:  # 8px radius
                        self._ld_mode = 'resize'
                        self._resize_body = b
                        self._resize_handle = i
                        return

        hit = self._body_at_world(*raw_wp)
        if hit:
            if hit not in self.selected:
                mods = pygame.key.get_mods()
                if not (mods & pygame.KMOD_SHIFT):
                    self.selected.clear()
                self.selected.add(hit)
            # Prepare for possible move
            self._move_off = {b: (b.x - snap_wp[0], b.y - snap_wp[1]) for b in self.selected}
            self._ld_mode = 'move'
        else:
            self._ld_mode = 'band'
            self._band_end_w = raw_wp

    def _lmb_up(self, pos):
        cp = self._canvas_pos(pos)
        raw_wp = self.camera.s2w(*cp)

        if self._ld_mode == 'band':
            self._band_end_w = raw_wp
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
                    hit = self._body_at_world(*raw_wp)
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
        elif self._ld_mode == 'resize':
            if type(self._resize_body).__name__ == 'PolygonBody':
                self._resize_body.recenter()
            self._resize_body._snap()

        self._ld_mode = None;  self._ld_down_s = None
        self._move_off = {};   self._band_end_w = None

    # ── right mouse ─────────────────────────────────────────────────────────────

    def _rmb_down(self, pos):
        if self.toolbox.contains(pos): return
        
        if self.ctx_menu.is_open and self.ctx_menu.contains(pos):
            self.ctx_menu.handle_click(pos, button=3)
            return
            
        cp = self._canvas_pos(pos)
        self._rd_down_s = cp;  self._rd_last_s = cp;  self._rd_moved = False
        
        wp = self.camera.s2w(*cp)
        hit = self._body_at_world(*wp)
        if hit and self.sim_state == STOPPED:
            self._rd_mode = 'rotate'
            self._rotate_body = hit
            self._rotate_start_angle = hit.angle
            import math
            self._rotate_start_mouse_a = math.atan2(wp[1] - hit.y, wp[0] - hit.x)
        else:
            self._rd_mode = 'pan'

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
        elif getattr(self, '_rd_mode', None) == 'rotate' and self._rd_moved:
            self._rotate_body._snap()
            
        self._rd_down_s = None;  self._rd_moved = False; self._rd_mode = None

    def _scroll(self, pos, factor):
        if self.toolbox.contains(pos): return
        cp = self._canvas_pos(pos)
        self.camera.zoom_at(cp[0], cp[1], factor)

    # ── motion ──────────────────────────────────────────────────────────────────

    def _motion(self, pos):
        cp = self._canvas_pos(pos)
        raw_wp = self.camera.s2w(*cp)
        snap_wp = self._get_snapped_wp(cp)

        # Right: pan or rotate
        if self._rd_down_s is not None:
            dx = cp[0] - self._rd_last_s[0];  dy = cp[1] - self._rd_last_s[1]
            if abs(dx)+abs(dy) > 1:
                self._rd_moved = True
                if getattr(self, '_rd_mode', 'pan') == 'pan':
                    self.camera.pan(dx, dy)
                elif getattr(self, '_rd_mode', None) == 'rotate':
                    import math
                    ma = math.atan2(raw_wp[1] - self._rotate_body.y, raw_wp[0] - self._rotate_body.x)
                    da = ma - self._rotate_start_mouse_a
                    self._rotate_body.angle = self._rotate_start_angle + da
            self._rd_last_s = cp

        # Left: move or rubber-band
        if self._ld_mode == 'move':
            if self._ld_down_s:
                ddx = cp[0]-self._ld_down_s[0]; ddy = cp[1]-self._ld_down_s[1]
                if ddx*ddx+ddy*ddy >= DRAG_DIST**2:
                    for b, (ox,oy) in self._move_off.items():
                        b.x = snap_wp[0]+ox;  b.y = snap_wp[1]+oy
        elif self._ld_mode == 'band':
            self._band_end_w = raw_wp
        elif self._ld_mode == 'resize':
            if self._ld_down_s:
                ddx = cp[0]-self._ld_down_s[0]; ddy = cp[1]-self._ld_down_s[1]
                if ddx*ddx+ddy*ddy >= DRAG_DIST**2:
                    self._resize_body.resize(self._resize_handle, snap_wp[0], snap_wp[1])

    # ── draw ────────────────────────────────────────────────────────────────────

    def _draw_grid(self, cam):
        import math
        world_spacing = self._get_grid_spacing()
        
        left_w, top_w = cam.s2w(0, 0)
        right_w, bottom_w = cam.s2w(cam.view_w, cam.view_h)
        
        start_x = math.floor(left_w / world_spacing) * world_spacing
        start_y = math.floor(top_w / world_spacing) * world_spacing
        
        # Draw vertical lines
        x = start_x
        while x <= right_w:
            sx, _ = cam.w2s(x, 0)
            pygame.draw.line(self.canvas, (45, 45, 55), (int(sx), 0), (int(sx), cam.view_h))
            x += world_spacing
            
        # Draw horizontal lines
        y = start_y
        while y <= bottom_w:
            _, sy = cam.w2s(0, y)
            pygame.draw.line(self.canvas, (45, 45, 55), (0, int(sy)), (cam.view_w, int(sy)))
            y += world_spacing

    def _draw(self):
        cam = self.camera
        
        if self.show_grid:
            self._draw_grid(cam)

        # Bodies
        for b in self.bodies:
            is_resizing = (self._ld_mode == 'resize' and getattr(self, '_resize_body', None) == b)
            b.draw(self.canvas, cam, ghost=is_resizing)

        # Joints
        for j in self.joints:
            j.draw(self.canvas, cam)
            if self.ctx_menu.is_open and self.ctx_menu._body == j and j.limits_enabled:
                j.draw_limits(self.canvas, cam)

        # Selection outlines
        for b in self.selected:
            b.draw_outline(self.canvas, cam, SEL_COLOR, 2)
            if self.sim_state == STOPPED:
                for h in b.get_handles():
                    hx, hy = cam.w2s(*h)
                    pygame.draw.circle(self.canvas, (255, 255, 255, 100), (int(hx), int(hy)), 6)
                    pygame.draw.circle(self.canvas, SEL_COLOR, (int(hx), int(hy)), 6, 1)

        # Resize dimensions text
        if self._ld_mode == 'resize' and getattr(self, '_resize_body', None):
            b = self._resize_body
            ts = None
            import math
            if type(b).__name__ == 'RectBody':
                ts = self.ctx_menu._font.render(f"{b.width:.1f} x {b.height:.1f}", True, Colors.WHITE)
            elif type(b).__name__ == 'CircleBody':
                ts = self.ctx_menu._font.render(f"r: {b.radius:.1f}", True, Colors.WHITE)
            elif type(b).__name__ == 'PolygonBody':
                v = b.get_vertices()
                i = self._resize_handle
                prev_i = (i - 1) % len(v)
                next_i = (i + 1) % len(v)
                d1 = math.hypot(v[i][0] - v[prev_i][0], v[i][1] - v[prev_i][1])
                d2 = math.hypot(v[i][0] - v[next_i][0], v[i][1] - v[next_i][1])
                ts = self.ctx_menu._font.render(f"{d1:.1f}, {d2:.1f}", True, Colors.WHITE)

            if ts:
                if type(b).__name__ == 'PolygonBody':
                    hx, hy = cam.w2s(*v[self._resize_handle])
                    self.canvas.blit(ts, (int(hx + 10), int(hy + 10)))
                else:
                    cx, cy = cam.w2s(b.x, b.y)
                    self.canvas.blit(ts, (int(cx - ts.get_width()/2), int(cy - ts.get_height()/2)))

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

        # Rotate overlay
        if getattr(self, '_rd_mode', None) == 'rotate' and getattr(self, '_rd_moved', False):
            import math
            b = self._rotate_body
            sx, sy = cam.w2s(b.x, b.y)
            r = 60
            circ_surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(circ_surf, (255, 255, 255, 80), (r, r), r, 2)
            self.canvas.blit(circ_surf, (int(sx - r), int(sy - r)))
            
            ca, sa = math.cos(b.angle), math.sin(b.angle)
            pygame.draw.line(self.canvas, Colors.WHITE, (int(sx), int(sy)), (int(sx + ca*r), int(sy + sa*r)), 2)
            
            deg = math.degrees(b.angle - self._rotate_start_angle) % 360
            if deg > 180: deg -= 360
            ts = self.ctx_menu._font.render(f"{deg:+.1f}\u00b0", True, Colors.WHITE)
            self.canvas.blit(ts, (int(sx + r + 10), int(sy)))

        # Draw Scale Indicator
        target_px = 100
        world_units = target_px / cam.zoom
        if world_units > 0:
            import math
            magnitude = 10 ** math.floor(math.log10(world_units))
            fraction = world_units / magnitude
            if fraction < 2: nice_units = 1 * magnitude
            elif fraction < 5: nice_units = 2 * magnitude
            elif fraction < 10: nice_units = 5 * magnitude
            else: nice_units = 10 * magnitude
            
            px_len = nice_units * cam.zoom
            cw, ch = self.canvas.get_size()
            sx = cw - px_len - 20
            sy = ch - 20
            
            pygame.draw.line(self.canvas, Colors.WHITE, (int(sx), sy), (int(sx + px_len), sy), 2)
            pygame.draw.line(self.canvas, Colors.WHITE, (int(sx), sy - 5), (int(sx), sy + 5), 2)
            pygame.draw.line(self.canvas, Colors.WHITE, (int(sx + px_len), sy - 5), (int(sx + px_len), sy + 5), 2)
            
            ts = self.ctx_menu._font_t.render(f"{nice_units:g} m", True, Colors.WHITE)
            self.canvas.blit(ts, (int(sx + px_len/2 - ts.get_width()/2), int(sy - 10 - ts.get_height())))

        # Ghost preview
        if self.sim_state == STOPPED and self.drawing.mode:
            mp = pygame.mouse.get_pos()
            wm = self._get_snapped_wp(self._canvas_pos(mp))
            self.drawing.draw_preview(self.canvas, cam, wm)

        # Toolbox + context menu (on full screen)
        mp = pygame.mouse.get_pos()
        self.toolbox.draw(self.screen, self.drawing.mode, self.sim_state, mp)
        self.ctx_menu.draw(self.screen, mp)
