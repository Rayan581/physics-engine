import math
import pygame
from config import *

def _rot(lx, ly, a):
    ca, sa = math.cos(a), math.sin(a)
    return lx*ca - ly*sa, lx*sa + ly*ca

class MotorJoint:
    def __init__(self, body_a, body_b, world_anchor_x, world_anchor_y):
        self.a = body_a
        self.b = body_b
        
        # Local anchor for A
        ca, sa = math.cos(-self.a.angle), math.sin(-self.a.angle)
        dx, dy = world_anchor_x - self.a.x, world_anchor_y - self.a.y
        self.local_a = (dx*ca - dy*sa, dx*sa + dy*ca)
        
        # Local anchor for B (or world if B is None)
        if self.b:
            cb, sb = math.cos(-self.b.angle), math.sin(-self.b.angle)
            dx, dy = world_anchor_x - self.b.x, world_anchor_y - self.b.y
            self.local_b = (dx*cb - dy*sb, dx*sb + dy*cb)
        else:
            self.local_b = (world_anchor_x, world_anchor_y)
            
        # Initial relative angle for limits
        angle_b = self.b.angle if self.b else 0.0
        self.ref_angle = angle_b - self.a.angle
            
        # Motor properties
        self.motor_enabled = False
        self.motor_speed = 1.0  # radians per second
        self.motor_torque = 100000.0
        
        # Limits properties
        self.limits_enabled = False
        self.min_angle = -math.pi / 4.0
        self.max_angle = math.pi / 4.0
        
        # User controls
        self.ctrl_cw = ""
        self.ctrl_ccw = ""
        self.control_speed = 5.0
        
        # Accumulated impulses for warm-starting (optional, keeping it simple for now)
        self.acc_jx = 0.0
        self.acc_jy = 0.0
        self.acc_jm = 0.0
        self.acc_jl = 0.0

    def to_dict(self):
        return {
            "local_a": self.local_a,
            "local_b": self.local_b,
            "ref_angle": self.ref_angle,
            "motor_enabled": self.motor_enabled,
            "motor_speed": self.motor_speed,
            "motor_torque": self.motor_torque,
            "limits_enabled": self.limits_enabled,
            "min_angle": self.min_angle,
            "max_angle": self.max_angle,
            "ctrl_cw": self.ctrl_cw,
            "ctrl_ccw": self.ctrl_ccw,
            "control_speed": self.control_speed
        }
        
    @staticmethod
    def from_dict(d: dict, body_a, body_b):
        # We instantiate with temporary world anchors (0,0) and then overwrite with serialized locals
        j = MotorJoint(body_a, body_b, 0, 0)
        j.local_a = tuple(d.get("local_a", (0, 0)))
        j.local_b = tuple(d.get("local_b", (0, 0)))
        j.ref_angle = d.get("ref_angle", 0.0)
        j.motor_enabled = d.get("motor_enabled", False)
        j.motor_speed = d.get("motor_speed", 1.0)
        j.motor_torque = d.get("motor_torque", 100000.0)
        j.limits_enabled = d.get("limits_enabled", False)
        j.min_angle = d.get("min_angle", -math.pi / 4.0)
        j.max_angle = d.get("max_angle", math.pi / 4.0)
        j.ctrl_cw = d.get("ctrl_cw", "")
        j.ctrl_ccw = d.get("ctrl_ccw", "")
        j.control_speed = d.get("control_speed", 5.0)
        return j
        
    def get_anchor_a(self):
        rx, ry = _rot(*self.local_a, self.a.angle)
        return self.a.x + rx, self.a.y + ry
        
    def get_anchor_b(self):
        if not self.b:
            return self.local_b
        rx, ry = _rot(*self.local_b, self.b.angle)
        return self.b.x + rx, self.b.y + ry

    def solve_velocity(self, dt):
        # 1. Linear Constraint (Pin)
        rx_a, ry_a = _rot(*self.local_a, self.a.angle)
        va_x = self.a.vx - self.a.angular_velocity * ry_a
        va_y = self.a.vy + self.a.angular_velocity * rx_a
        
        inv_ma = self.a.inv_mass
        inv_ia = self.a.inv_inertia
        
        if self.b:
            rx_b, ry_b = _rot(*self.local_b, self.b.angle)
            vb_x = self.b.vx - self.b.angular_velocity * ry_b
            vb_y = self.b.vy + self.b.angular_velocity * rx_b
            inv_mb = self.b.inv_mass
            inv_ib = self.b.inv_inertia
        else:
            rx_b, ry_b = 0.0, 0.0
            vb_x, vb_y = 0.0, 0.0
            inv_mb = 0.0
            inv_ib = 0.0
            
        # Relative velocity
        Cdot_x = va_x - vb_x
        Cdot_y = va_y - vb_y
        
        # Effective mass matrix K
        k11 = inv_ma + inv_mb + inv_ia * ry_a**2 + inv_ib * ry_b**2
        k22 = inv_ma + inv_mb + inv_ia * rx_a**2 + inv_ib * rx_b**2
        k12 = -inv_ia * rx_a * ry_a - inv_ib * rx_b * ry_b
        
        # Invert K
        det = k11 * k22 - k12 * k12
        if det > 1e-10:
            inv_det = 1.0 / det
            jx = -(k22 * Cdot_x - k12 * Cdot_y) * inv_det
            jy = -(-k12 * Cdot_x + k11 * Cdot_y) * inv_det
        else:
            jx, jy = 0.0, 0.0
            
        # Apply linear impulse
        self.a.vx += jx * inv_ma
        self.a.vy += jy * inv_ma
        self.a.angular_velocity += inv_ia * (rx_a * jy - ry_a * jx)
        
        if self.b:
            self.b.vx -= jx * inv_mb
            self.b.vy -= jy * inv_mb
            self.b.angular_velocity -= inv_ib * (rx_b * jy - ry_b * jx)
            
        # 2. Motor Constraint
        if self.motor_enabled and (inv_ia + inv_ib) > 0:
            wb = self.b.angular_velocity if self.b else 0.0
            wa = self.a.angular_velocity
            # Target relative velocity: wb - wa = motor_speed
            Cdot_m = wb - wa - self.motor_speed
            
            impulse_m = -Cdot_m / (inv_ia + inv_ib)
            
            # Clamp to max torque per substep
            max_impulse = self.motor_torque * dt
            impulse_m = max(min(impulse_m, max_impulse), -max_impulse)
            
            self.a.angular_velocity -= impulse_m * inv_ia
            if self.b:
                self.b.angular_velocity += impulse_m * inv_ib
                
        # 3. Limits Constraint
        if self.limits_enabled and (inv_ia + inv_ib) > 0:
            angle_b = self.b.angle if self.b else 0.0
            current_angle = angle_b - self.a.angle - self.ref_angle
            
            # Normalize angle to [-pi, pi]
            current_angle = (current_angle + math.pi) % (2 * math.pi) - math.pi
            
            limit_impulse = 0.0
            if current_angle <= self.min_angle:
                # Hit lower limit, prevent negative relative velocity
                wb = self.b.angular_velocity if self.b else 0.0
                wa = self.a.angular_velocity
                Cdot_l = wb - wa
                if Cdot_l < 0:
                    limit_impulse = -Cdot_l / (inv_ia + inv_ib)
            elif current_angle >= self.max_angle:
                # Hit upper limit, prevent positive relative velocity
                wb = self.b.angular_velocity if self.b else 0.0
                wa = self.a.angular_velocity
                Cdot_l = wb - wa
                if Cdot_l > 0:
                    limit_impulse = -Cdot_l / (inv_ia + inv_ib)
                    
            if limit_impulse != 0.0:
                self.a.angular_velocity -= limit_impulse * inv_ia
                if self.b:
                    self.b.angular_velocity += limit_impulse * inv_ib

    def solve_position(self):
        # Move bodies to keep anchor points exactly together
        ax, ay = self.get_anchor_a()
        bx, by = self.get_anchor_b()
        
        Cx = ax - bx
        Cy = ay - by
        
        # Position error
        err = math.hypot(Cx, Cy)
        if err < 0.01:
            return
            
        inv_ma = self.a.inv_mass
        inv_ia = self.a.inv_inertia
        
        rx_a, ry_a = _rot(*self.local_a, self.a.angle)
        
        if self.b:
            inv_mb = self.b.inv_mass
            inv_ib = self.b.inv_inertia
            rx_b, ry_b = _rot(*self.local_b, self.b.angle)
        else:
            inv_mb = 0.0
            inv_ib = 0.0
            rx_b, ry_b = 0.0, 0.0
            
        k11 = inv_ma + inv_mb + inv_ia * ry_a**2 + inv_ib * ry_b**2
        k22 = inv_ma + inv_mb + inv_ia * rx_a**2 + inv_ib * rx_b**2
        k12 = -inv_ia * rx_a * ry_a - inv_ib * rx_b * ry_b
        
        det = k11 * k22 - k12 * k12
        if det > 1e-10:
            inv_det = 1.0 / det
            px = -(k22 * Cx - k12 * Cy) * inv_det
            py = -(-k12 * Cx + k11 * Cy) * inv_det
        else:
            px, py = 0.0, 0.0
            
        percent = 0.2  # Baumgarte stabilization factor
        px *= percent
        py *= percent
        
        self.a.x += px * inv_ma
        self.a.y += py * inv_ma
        self.a.angle += inv_ia * (rx_a * py - ry_a * px)
        
        if self.b:
            self.b.x -= px * inv_mb
            self.b.y -= py * inv_mb
            self.b.angle -= inv_ib * (rx_b * py - ry_b * px)

    def draw(self, surface, cam):
        ax, ay = self.get_anchor_a()
        sx, sy = cam.w2s(ax, ay)
        
        r = max(4, int(cam.zoom))
        color = MOTOR_ENABLED_COLOR if self.motor_enabled else MOTOR_DISABLED_COLOR
        
        lw = max(1, r // 4)
        pygame.draw.circle(surface, color, (int(sx), int(sy)), r, lw)
        
        # Draw a line showing the rotation of body A
        ca, sa = math.cos(self.a.angle), math.sin(self.a.angle)
        ex, ey = sx + ca * r, sy + sa * r
        pygame.draw.line(surface, color, (int(sx), int(sy)), (int(ex), int(ey)), lw)
        
        # Draw inner dot
        pygame.draw.circle(surface, color, (int(sx), int(sy)), max(1, r // 3))

    def draw_limits(self, surface, cam):
        if not self.limits_enabled:
            return
            
        ax, ay = self.get_anchor_a()
        sx, sy = cam.w2s(ax, ay)
        r = max(1, int(40 * cam.zoom))
        
        angle_b = self.b.angle if self.b else 0.0
        base_angle = angle_b - self.ref_angle
        
        min_a = base_angle + self.min_angle
        max_a = base_angle + self.max_angle
        
        p1 = (sx + math.cos(min_a) * r, sy + math.sin(min_a) * r)
        p2 = (sx + math.cos(max_a) * r, sy + math.sin(max_a) * r)
        
        # Red line for Min, Green line for Max
        pygame.draw.line(surface, LIMIT_MIN_COLOR, (int(sx), int(sy)), (int(p1[0]), int(p1[1])), 2)
        pygame.draw.line(surface, LIMIT_MAX_COLOR, (int(sx), int(sy)), (int(p2[0]), int(p2[1])), 2)
        
        # Draw a faded pie slice for the allowed area
        rect = pygame.Rect(0, 0, r*2, r*2)
        rect.center = (int(sx), int(sy))
        # pygame.draw.arc doesn't fill, we can just draw lines or leave it out. The 2 lines are clear enough.
        
        # Also draw current body A angle line longer to see where it is relative to limits
        ca, sa = math.cos(self.a.angle), math.sin(self.a.angle)
        pa = (sx + ca * (r - 5), sy + sa * (r - 5))
        pygame.draw.line(surface, Colors.WHITE, (int(sx), int(sy)), (int(pa[0]), int(pa[1])), 1)
