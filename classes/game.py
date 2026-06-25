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

SEL_COLOR  = SEL_COLOR
BAND_COLOR = BAND_COLOR
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
        self.show_com = True
        self.viz_all = False
        self.fast_forward = False
        self.trainer_class = None

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
        self.fast_forward = False
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
            if path:
                cam_data = {"x": self.camera.cam_x, "y": self.camera.cam_y, "zoom": self.camera.zoom}
                save_to_file(path, self.bodies, self.joints, cam_data)
        elif action == 'load':
            path = get_open_path()
            if path:
                self.bodies, self.joints, cam_data = load_from_file(path)
                if cam_data:
                    self.camera.cam_x = cam_data.get("x", 0.0)
                    self.camera.cam_y = cam_data.get("y", 0.0)
                    self.camera.zoom = cam_data.get("zoom", 1.0)
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
                new_bodies, new_joints, _ = load_from_file(path)
                self.bodies.extend(new_bodies)
                self.joints.extend(new_joints)
                self.selected = set(new_bodies)
        elif action == 'load_ai':
            from classes.serialization import get_script_path
            import importlib.util
            path = get_script_path()
            if path:
                spec = importlib.util.spec_from_file_location("ai_plugin", path)
                ai_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(ai_module)
                
                from classes.ai import BaseTrainer
                for name in dir(ai_module):
                    obj = getattr(ai_module, name)
                    if isinstance(obj, type) and issubclass(obj, BaseTrainer) and obj is not BaseTrainer:
                        self.trainer_class = obj
                        self._start_training()
                        break
        elif action == 'run_ai':
            if getattr(self, 'trainer_class', None):
                self._start_ai_playback()

    # ── AI Integration ──────────────────────────────────────────────────────────

    def _start_training(self):
        self.sim_state = 'training'
        self.fast_forward = False
        import neat
        import pickle
        try:
            config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                 neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                 self.trainer_class.config_path)
            self.pop = neat.Population(config)
            
            import os
            import copy
            if os.path.exists('best_genome.pkl'):
                try:
                    print("Seeding population from best_genome.pkl...")
                    with open('best_genome.pkl', 'rb') as f:
                        best_genome = pickle.load(f)
                        
                    pop_size = config.pop_size
                    half_size = pop_size // 2
                    new_pop = {}
                    
                    # 1 exact clone
                    exact_clone = copy.deepcopy(best_genome)
                    exact_clone.key = 1
                    exact_clone.fitness = None
                    new_pop[1] = exact_clone
                    
                    # 50% heavily mutated clones
                    for i in range(2, half_size + 1):
                        clone = copy.deepcopy(best_genome)
                        clone.key = i
                        clone.fitness = None
                        for _ in range(5):
                            clone.mutate(config.genome_config)
                        new_pop[i] = clone
                        
                    # 50% random genomes
                    for i in range(half_size + 1, pop_size + 1):
                        g = config.genome_type(i)
                        g.configure_new(config.genome_config)
                        new_pop[i] = g
                        
                    self.pop.population = new_pop
                    self.pop.species.speciate(config, self.pop.population, self.pop.generation)
                except Exception as e:
                    print(f"Failed to seed population: {e}")
                    
            self.pop.add_reporter(neat.StdOutReporter(True))
            self.stats = neat.StatisticsReporter()
            self.pop.add_reporter(self.stats)
            
            winner = self.pop.run(self._eval_genomes, 50)
            
            with open('best_genome.pkl', 'wb') as f:
                pickle.dump(winner, f)
            print("Training finished! Saved best_genome.pkl")
        except Exception as e:
            if str(e) != "Aborted":
                print(f"Training error: {e}")
            else:
                print("Training aborted by user.")
        self._stop()
        
    def _eval_genomes(self, genomes, config):
        import neat
        best_genome = None
        best_fitness = -float('inf')
        generation = getattr(self.pop, 'generation', 0)
        total = len(genomes)

        # 1. Evaluate all genomes in fast-forward mode
        for gi, (genome_id, genome) in enumerate(genomes):
            if self.sim_state != 'training': 
                raise Exception("Aborted")
                
            for b in self.bodies: b.reset()
                
            trainer = self.trainer_class()
            if not trainer.setup(self.bodies, self.joints):
                genome.fitness = -1000.0
                continue
                
            net = neat.nn.FeedForwardNetwork.create(genome, config)
            fitness = 0.0
            
            for step in range(trainer.max_steps):
                # Pump events and redraw HUD every 20 steps
                if step % 20 == 0:
                    for ev in pygame.event.get():
                        if ev.type == pygame.QUIT:
                            self.running = False
                            raise Exception("Aborted")
                        elif ev.type == pygame.KEYDOWN:
                            if ev.key == pygame.K_ESCAPE:
                                raise Exception("Aborted")
                            elif ev.key == pygame.K_f:
                                self.fast_forward = not self.fast_forward
                    
                    # Draw live training HUD
                    self.canvas.fill(CANVAS_BG)
                    if self.viz_all:
                        self._draw()
                        target = trainer.get_camera_target()
                        if target:
                            self.camera.cam_x += (target[0] - self.camera.cam_x) * 5.0 * (20.0 / FPS)
                            self.camera.cam_y += (target[1] - self.camera.cam_y) * 5.0 * (20.0 / FPS)
                    
                    self._draw_training_hud(generation, gi, total, best_fitness)
                    pygame.display.flip()

                obs = trainer.get_observation()
                action = net.activate(obs)
                trainer.apply_action(action)
                
                self._physics_step(1.0 / FPS)
                is_done, fitness = trainer.check_status()
                if is_done:
                    break
                    
            genome.fitness = fitness
            if fitness > best_fitness:
                best_fitness = fitness
                best_genome = genome
                print(f"New best genome: {best_genome.fitness}")
                
        # 2. Visually replay the best genome of this generation
        if best_genome is not None:
            # Save the best genome of this generation to file
            import pickle
            with open('best_genome.pkl', 'wb') as f:
                pickle.dump(best_genome, f)
                
            if not self.fast_forward:
                for b in self.bodies: b.reset()
                trainer = self.trainer_class()
                if trainer.setup(self.bodies, self.joints):
                    net = neat.nn.FeedForwardNetwork.create(best_genome, config)
                    last_activations = {}
                    for step in range(trainer.max_steps):
                        dt = min(self.clock.tick(FPS) / 1000.0, 0.033)
                        
                        for ev in pygame.event.get():
                            if ev.type == pygame.QUIT:
                                self.running = False
                                raise Exception("Aborted")
                            elif ev.type == pygame.KEYDOWN:
                                if ev.key == pygame.K_ESCAPE:
                                    raise Exception("Aborted")
                                elif ev.key == pygame.K_f:
                                    self.fast_forward = not self.fast_forward
                                    
                        if self.fast_forward:
                            break  # Skip the rest of the visual replay if user fast-forwards
                            
                        obs = trainer.get_observation()
                        action, last_activations = net.activate_with_values(obs) if hasattr(net, 'activate_with_values') else (net.activate(obs), {})
                        trainer.apply_action(action)
                        
                        self._physics_step(1.0 / FPS)
                        
                        target = trainer.get_camera_target()
                        if target:
                            self.camera.cam_x += (target[0] - self.camera.cam_x) * 5.0 * dt
                            self.camera.cam_y += (target[1] - self.camera.cam_y) * 5.0 * dt
                            
                        is_done, _ = trainer.check_status()
                        
                        self.canvas.fill(CANVAS_BG)
                        self._draw()
                        self._draw_network(self.canvas, best_genome, config, obs, action)
                        
                        # Draw text
                        ts = self.ctx_menu._font.render("Best of Gen | 'F': Fast Forward  'ESC': Abort", True, Colors.WHITE)
                        self.canvas.blit(ts, (10, 10))
                        
                        pygame.display.flip()
                        
                        if is_done:
                            break

    def _start_ai_playback(self):
        import pickle
        import neat
        try:
            with open('best_genome.pkl', 'rb') as f:
                winner = pickle.load(f)
            config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                 neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                 self.trainer_class.config_path)
            self.ai_net = neat.nn.FeedForwardNetwork.create(winner, config)
            self.trainer = self.trainer_class()
            
            for b in self.bodies: b.reset()
            
            if not self.trainer.setup(self.bodies, self.joints):
                self._stop()
                return
                
            self.sim_state = 'ai_playing'
            self.ctx_menu.close()
            self.selected.clear()
        except Exception as e:
            print("Failed to load AI:", e)
            self._stop()

    # ── run loop ────────────────────────────────────────────────────────────────

    def run(self):
        self._ai_last_obs    = []
        self._ai_last_action = []
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.033)
            self.handle_events()
            if self.sim_state == PLAYING:
                self._physics_step(dt)
            elif self.sim_state == 'ai_playing':
                obs = self.trainer.get_observation()
                action = self.ai_net.activate(obs)
                self._ai_last_obs    = obs
                self._ai_last_action = action
                self.trainer.apply_action(action)
                self._physics_step(dt)
                
                target = self.trainer.get_camera_target()
                if target:
                    self.camera.cam_x += (target[0] - self.camera.cam_x) * 5.0 * dt
                    self.camera.cam_y += (target[1] - self.camera.cam_y) * 5.0 * dt
                    
                is_done, _ = self.trainer.check_status()
                if is_done:
                    self._stop()
                    
            self.canvas.fill(CANVAS_BG)
            self._draw()
            if self.sim_state == 'ai_playing' and hasattr(self, 'ai_net') and hasattr(self, 'trainer'):
                import neat
                config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                     neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                     self.trainer_class.config_path)
                import pickle
                try:
                    with open('best_genome.pkl', 'rb') as f:
                        genome = pickle.load(f)
                    self._draw_network(self.canvas, genome, config,
                                       self._ai_last_obs, self._ai_last_action)
                except Exception:
                    pass
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
                if path:
                    cam_data = {"x": self.camera.cam_x, "y": self.camera.cam_y, "zoom": self.camera.zoom}
                    save_to_file(path, self.bodies, self.joints, cam_data)
            elif k == pygame.K_o:
                # Load Scene
                path = get_open_path()
                if path:
                    self.bodies, self.joints, cam_data = load_from_file(path)
                    if cam_data:
                        self.camera.cam_x = cam_data.get("x", 0.0)
                        self.camera.cam_y = cam_data.get("y", 0.0)
                        self.camera.zoom = cam_data.get("zoom", 1.0)
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
                    new_bodies, new_joints, _ = load_from_file(path)
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
        elif k == pygame.K_t and self.sim_state == STOPPED:
            self.drawing.set_mode(None if self.drawing.mode=='text' else 'text')
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
            cb = self.toolbox.get_checkbox_at(pos)
            if cb == 'show_com':
                self.show_com = not self.show_com
                for box in self.toolbox._checkboxes:
                    if box.name == 'show_com': box.checked = self.show_com
                return
            elif cb == 'viz_all':
                self.viz_all = not self.viz_all
                for box in self.toolbox._checkboxes:
                    if box.name == 'viz_all': box.checked = self.viz_all
                return

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
            if self.ctx_menu.contains(pos): 
                self.ctx_menu.handle_click(pos)
                self._ld_mode = 'ctx_menu'
            else:                            
                self.ctx_menu.close()
            return

        if self.sim_state == PLAYING:
            return

        cp = self._canvas_pos(pos)
        raw_wp = self.camera.s2w(*cp)
        snap_wp = self._get_snapped_wp(cp)

        # Drawing tool takes priority
        if self.drawing.mode and self.sim_state == STOPPED:
            self.drawing.handle_click(snap_wp, self.bodies.append, self.bodies, self.joints.append, cam=self.camera)
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

        if self._ld_mode == 'ctx_menu':
            self.ctx_menu.handle_up(pos)
        elif self._ld_mode == 'band':
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
        if self._ld_mode == 'ctx_menu':
            self.ctx_menu.handle_motion(pos)
        elif self._ld_mode == 'move':
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
            pygame.draw.line(self.canvas, GRID_COLOR, (int(sx), 0), (int(sx), cam.view_h))
            x += world_spacing
            
        # Draw horizontal lines
        y = start_y
        while y <= bottom_w:
            _, sy = cam.w2s(0, y)
            pygame.draw.line(self.canvas, GRID_COLOR, (0, int(sy)), (cam.view_w, int(sy)))
            y += world_spacing

    def _draw_training_hud(self, generation, genome_idx, total, best_fitness):
        """Render a compact training status HUD on the top-left of the canvas."""
        font   = self.ctx_menu._font
        font_t = self.ctx_menu._font_t

        PAD = 12
        W   = 260
        H   = 112

        # Semi-transparent backing panel
        panel = pygame.Surface((W, H), pygame.SRCALPHA)
        panel.fill((20, 16, 12, 220))
        pygame.draw.rect(panel, (58, 44, 26, 200), (0, 0, W, H), 1)
        self.canvas.blit(panel, (PAD, PAD))

        x0, y0 = PAD + 8, PAD + 8

        # Row 1 – title
        title = font_t.render(f"Training  ·  Gen {generation}", True, TRAINING_TITLE_COLOR)
        self.canvas.blit(title, (x0, y0))

        # Row 2 – genome progress bar
        y1 = y0 + 20
        bar_w = W - 16
        frac  = genome_idx / max(total, 1)
        pygame.draw.rect(self.canvas, TRAINING_BAR_BG, (x0, y1, bar_w, 10), border_radius=3)
        pygame.draw.rect(self.canvas, TRAINING_BAR_FILL, (x0, y1, int(bar_w * frac), 10), border_radius=3)
        prog_lbl = font.render(f"Genome {genome_idx}/{total}", True, TRAINING_PROG_LBL)
        self.canvas.blit(prog_lbl, (x0, y1 + 13))

        # Row 3 – best fitness
        y2 = y1 + 32
        fit_str  = f"{best_fitness:,.0f}" if best_fitness > -float('inf') else "—"
        fit_lbl  = font.render(f"Best fitness:  {fit_str}", True, TRAINING_FIT_LBL)
        self.canvas.blit(fit_lbl, (x0, y2))

        # Row 4 – VIZ indicator badge
        y3 = y2 + 20
        viz_on = not self.fast_forward
        pulse  = (pygame.time.get_ticks() % 1000) < 500   # 1 Hz blink when OFF

        if viz_on:
            badge_col = BADGE_PLAY_COL
            text_col  = BADGE_PLAY_TEXT
            label     = "VIZ  ON   [F] toggle"
        else:
            badge_col = BADGE_FAST_COL_PULSE if pulse else BADGE_FAST_COL
            text_col  = BADGE_FAST_TEXT_PULSE if pulse else BADGE_FAST_TEXT
            label     = "VIZ  OFF  [F] toggle"

        badge_rect = pygame.Rect(x0, y3, W - 16, 20)
        badge_surf = pygame.Surface((badge_rect.w, badge_rect.h), pygame.SRCALPHA)
        badge_surf.fill((*badge_col, 80))
        self.canvas.blit(badge_surf, (badge_rect.x, badge_rect.y))
        pygame.draw.rect(self.canvas, badge_col, badge_rect, 1, border_radius=3)

        badge_lbl = font.render(label, True, text_col)
        self.canvas.blit(badge_lbl, (x0 + 4, y3 + 2))

        # Hint line
        hint = font.render("ESC: abort", True, ESC_HINT_COL)
        self.canvas.blit(hint, (x0, y3 + 24))

    def _draw_network(self, surface, genome, config, inputs, outputs):
        """Draw a neural network visualisation as a semi-transparent HUD overlay."""
        import math

        gc = config.genome_config
        # ── collect node layers via BFS from inputs ────────────────────────────
        input_keys  = list(gc.input_keys)
        output_keys = list(gc.output_keys)
        hidden_keys = [k for k in genome.nodes if k not in output_keys and k not in input_keys]

        # Topological layer assignment
        layer_of = {}
        for k in input_keys:  layer_of[k] = 0
        changed = True
        max_passes = len(genome.nodes) + 2
        while changed and max_passes > 0:
            changed = False; max_passes -= 1
            for cg in genome.connections.values():
                if not cg.enabled: continue
                src, dst = cg.key
                if src in layer_of and dst not in output_keys:
                    new_l = layer_of[src] + 1
                    if layer_of.get(dst, -1) < new_l:
                        layer_of[dst] = new_l; changed = True
        max_hidden_layer = max((layer_of.get(k, 0) for k in hidden_keys), default=0)
        for k in output_keys:
            layer_of[k] = max_hidden_layer + 1

        layers = {}
        for k in input_keys + hidden_keys + output_keys:
            l = layer_of.get(k, 0)
            layers.setdefault(l, []).append(k)

        # ── activation values ──────────────────────────────────────────────────
        activations = {}
        for i, k in enumerate(input_keys):
            activations[k] = inputs[i] if i < len(inputs) else 0.0
        for i, k in enumerate(output_keys):
            activations[k] = outputs[i] if i < len(outputs) else 0.0

        # ── layout ─────────────────────────────────────────────────────────────
        PAD_R   = 14   # right-edge padding
        PAD_B   = 14   # bottom-edge padding
        W       = 260
        H       = 220
        cw, ch  = surface.get_size()
        ox      = cw - W - PAD_R          # top-left x of panel
        oy      = ch - H - PAD_B          # top-left y of panel
        node_r  = 9

        num_layers = max(layers.keys()) + 1 if layers else 1
        x_step     = (W - node_r * 2 - 20) / max(num_layers - 1, 1)

        pos = {}   # node_key -> (sx, sy) in panel-local coords then translated
        for l_idx, nodes_in_layer in sorted(layers.items()):
            n = len(nodes_in_layer)
            for row, k in enumerate(nodes_in_layer):
                px = node_r + 10 + l_idx * x_step
                py = (H / (n + 1)) * (row + 1)
                pos[k] = (ox + px, oy + py)

        # ── background panel ───────────────────────────────────────────────────
        panel = pygame.Surface((W, H), pygame.SRCALPHA)
        panel.fill((20, 16, 12, 220))
        pygame.draw.rect(panel, (58, 44, 26, 160), (0, 0, W, H), 1)
        surface.blit(panel, (ox, oy))

        # Label
        lbl_font = self.ctx_menu._font
        lbl = lbl_font.render("Neural Network", True, NN_TITLE_COL)
        surface.blit(lbl, (ox + 6, oy + 4))

        # ── edges ──────────────────────────────────────────────────────────────
        edge_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
        for cg in genome.connections.values():
            if not cg.enabled: continue
            src, dst = cg.key
            if src not in pos or dst not in pos: continue
            w = cg.weight
            alpha   = min(255, int(abs(w) * 80 + 60))
            width   = max(1, min(4, int(abs(w) * 2)))
            if w > 0:
                col = (212, 120, 42, alpha)   # amber for positive
            else:
                col = (200, 60, 60, alpha)    # deep red for negative
            pygame.draw.line(edge_surf, col,
                             (int(pos[src][0]), int(pos[src][1])),
                             (int(pos[dst][0]), int(pos[dst][1])), width)
        surface.blit(edge_surf, (0, 0))

        # ── nodes ──────────────────────────────────────────────────────────────
        def _act_color(v):
            """Amber-white-red gradient based on tanh activation."""
            t = max(-1.0, min(1.0, float(v)))
            if t >= 0:
                # Positive -> Amber
                r = int(212 * t + 60 * (1 - t))
                g = int(120 * t + 60 * (1 - t))
                b = int(42 * t + 60 * (1 - t))
            else:
                # Negative -> Deep Red
                t2 = -t
                r = int(200 * t2 + 60 * (1 - t2))
                g = int(60 * (1 - t2) + 20 * t2)
                b = int(60 * (1 - t2) + 20 * t2)
            return (r, g, b)

        glow_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
        for k, (sx, sy) in pos.items():
            val  = activations.get(k, 0.0)
            col  = _act_color(val)
            # Glow ring
            pygame.draw.circle(glow_surf, (*col, 40), (int(sx), int(sy)), node_r * 2)
        surface.blit(glow_surf, (0, 0))

        for k, (sx, sy) in pos.items():
            val  = activations.get(k, 0.0)
            col  = _act_color(val)
            # Filled node
            pygame.draw.circle(surface, col, (int(sx), int(sy)), node_r)
            # Border
            if k in input_keys:
                border = NN_BORDER_POS    # greenish
            elif val < -0.1:
                border = NN_BORDER_NEG    # gold
            else:
                border = NN_BORDER_NEUT     # muted warm brown
            pygame.draw.circle(surface, border, (int(sx), int(sy)), node_r, 2)
            # Value label
            val_lbl = lbl_font.render(f"{val:.2f}", True, NN_VAL_LBL)
            surface.blit(val_lbl, (int(sx - val_lbl.get_width() // 2),
                                   int(sy + node_r + 2)))

    def _draw(self):
        cam = self.camera
        
        if self.show_grid:
            self._draw_grid(cam)

        # Bodies
        for b in self.bodies:
            is_resizing = (self._ld_mode == 'resize' and getattr(self, '_resize_body', None) == b)
            b.draw(self.canvas, cam, ghost=is_resizing, show_com=self.show_com)

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
                    pygame.draw.circle(self.canvas, SELECTED_HANDLE_COL, (int(sx), int(sy)), max(3, int(4*cam.zoom)))

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
