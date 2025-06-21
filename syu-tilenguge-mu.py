import pyxel
import random
import math

# 定数の定義
SCREEN_WIDTH = 256
SCREEN_HEIGHT = 192
STAR_COUNT = 50
FROG_WIDTH = 16
FROG_HEIGHT = 16
BULLET_WIDTH = 4
BULLET_HEIGHT = 2
ENEMY_WIDTH = 16
ENEMY_HEIGHT = 16
ENEMY_SPAWN_INTERVAL = 60
FROG_BASE_MAX_HP = 100
HP_BAR_WIDTH = 50
HP_BAR_HEIGHT = 5
FORCE_DELAY = 8
FOCUS_GAUGE_BASE_MAX = 120
FOCUS_GAUGE_CONSUMPTION = 1
FOCUS_GAUGE_RECOVERY = 0.5
FOCUS_COOLDOWN_BASE_TIME = 180
CHARGE_MAX_BASE = 2400
FORCE_CHARGE_REDUCTION = 30
CHARGE_LEVEL_1_RATIO = 0.3
CHARGE_LEVEL_2_RATIO = 0.6
BOSS_WIDTH = 32
BOSS_HEIGHT = 32

# サウンドチャンネル
SOUND_ENEMY_DEATH = 0
SOUND_BULLET_SHOOT = 1
MUSIC_STAGE = 0
SOUND_ITEM_GET = 3
SOUND_LASER_SHOOT = 2
SOUND_HEAL_GET = 3

class Boss:
    def __init__(self, stage_number):
        self.w, self.h = BOSS_WIDTH, BOSS_HEIGHT
        self.x, self.y = SCREEN_WIDTH, SCREEN_HEIGHT / 2 - self.h / 2
        self.stage_number = stage_number
        self.max_hp = 150 + (stage_number // 10) * 100
        self.hp = self.max_hp
        self.alive = True; self.state = "enter"; self.speed_y = 1
        self.timer = 0; self.dash_target_y = 0; self.explosion = None
    def update(self, frog, enemy_bullets):
        if self.state == "enter":
            self.x -= 1
            if self.x <= SCREEN_WIDTH - self.w - 20: self.state = "fight"; self.timer = random.randint(60, 120)
        elif self.state == "fight":
            self.y += self.speed_y
            if self.y < 0 or self.y > SCREEN_HEIGHT - self.h: self.speed_y *= -1
            self.timer -= 1
            if self.timer <= 0:
                if random.random() < 0.4: self.state = "charge"; self.timer = 60
                else: self.shoot_spread(frog, enemy_bullets); self.timer = random.randint(90, 150)
        elif self.state == "charge":
            self.timer -= 1
            if self.timer <= 0: self.state = "dash"; self.dash_target_y = frog.y; self.timer = 90
        elif self.state == "dash":
            self.x -= 5; self.y += (self.dash_target_y - self.y) * 0.1; self.timer -= 1
            if self.x < -self.w or self.timer <= 0: self.x = SCREEN_WIDTH - self.w - 20; self.state = "fight"; self.timer = random.randint(60, 120)
        elif self.state == "dying":
            if pyxel.frame_count % 5 == 0: self.explosion = Explosion(self.x + random.uniform(-10, 10), self.y + random.uniform(-10, 10))
            self.timer -= 1
            if self.timer <= 0: self.alive = False
    def shoot_spread(self, frog, enemy_bullets):
        center_angle = math.atan2(frog.y - (self.y + self.h / 2), frog.x - self.x)
        for i in range(-2, 3):
            angle = center_angle + math.radians(i * 15)
            bullet = EnemyBullet(self.x, self.y + self.h/2, self.stage_number)
            bullet.speed = -3; bullet.vx = math.cos(angle) * bullet.speed; bullet.vy = math.sin(angle) * bullet.speed
            bullet.update = lambda b=bullet: self.update_angled_bullet(b)
            enemy_bullets.append(bullet)
    def update_angled_bullet(self, bullet): bullet.x += bullet.vx; bullet.y += bullet.vy
    def take_damage(self, damage):
        if self.state in ["fight", "charge"]:
            self.hp = max(0, self.hp - damage)
            if self.hp <= 0: self.state = "dying"; self.timer = 120
    def draw(self):
        color = 8 if self.state != "charge" else (8 if pyxel.frame_count % 10 < 5 else 9)
        pyxel.rect(self.x, self.y, self.w, self.h, color); pyxel.rectb(self.x, self.y, self.w, self.h, 1)
        pyxel.pset(self.x + 8, self.y + 10, 7); pyxel.pset(self.x + 24, self.y + 10, 7)
    def draw_hp_bar(self):
        hp_ratio = self.hp / self.max_hp; bar_width = int((SCREEN_WIDTH - 20) * hp_ratio)
        pyxel.rect(10, 5, SCREEN_WIDTH - 20, 10, 1); pyxel.rect(10, 5, bar_width, 10, 8)
        pyxel.text(SCREEN_WIDTH/2 - 10, 6, "BOSS", 7)
    def is_colliding(self, obj): return (self.x < obj.x + obj.w and self.x + self.w > obj.x and self.y < obj.y + obj.h and self.y + self.h > obj.y)

class RecoveryItem:
    def __init__(self, x, y):
        self.x, self.y, self.w, self.h = x, y, 10, 10; self.alive, self.speed_x, self.frame = True, -0.5, 0
    def update(self):
        self.x += self.speed_x; self.y += math.sin(self.frame * 0.05) * 1.5; self.frame += 1
        if self.x < -self.w: self.alive = False
    def draw(self):
        cx, cy, s = self.x + self.w / 2, self.y + self.h / 2, self.w / 2
        pyxel.circ(cx - s / 2, cy, s / 1.5, 11); pyxel.circ(cx + s / 2, cy, s / 1.5, 11)
        pyxel.tri(cx - s, cy, cx + s, cy, cx, cy + s, 11)
        if pyxel.frame_count % 30 < 5: pyxel.pset(cx, cy - 1, 7)
    def is_colliding(self, frog): return (self.x < frog.x + frog.w and self.x + self.w > frog.x and self.y < frog.y + frog.h and self.y + self.h > frog.y)

class DrillMissile:
    def __init__(self, x, y):
        self.x, self.y, self.w, self.h = x, y, 12, 5
        self.speed = 4; self.damage = 1.5; self.penetration_power = 20; self.animation_frame = 0
    def update(self):
        self.x += self.speed; self.animation_frame += 1
    def draw(self):
        offset = (self.animation_frame % 4) // 2
        pyxel.rect(self.x, self.y, self.w, self.h, 14); pyxel.rectb(self.x, self.y, self.w, self.h, 6)
        pyxel.tri(self.x + self.w, self.y, self.x + self.w, self.y + self.h, self.x + self.w + 4, self.y + self.h/2, 6)
        pyxel.line(self.x + 2, self.y + offset, self.x + self.w - 2, self.y + self.h - 1 - offset, 6)
        pyxel.line(self.x + 2, self.y + self.h - 1 - offset, self.x + self.w - 2, self.y + offset, 6)
    def is_offscreen(self): return self.x > SCREEN_WIDTH
    def take_damage(self, amount):
        self.penetration_power -= amount
        return self.penetration_power <= 0

class ChargeShot:
    def __init__(self, x, y, level, max_charge_time):
        self.x, self.y = x, y; self.level = level; self.speed = 3
        level_1_threshold = max_charge_time * CHARGE_LEVEL_1_RATIO
        level_2_threshold = max_charge_time * CHARGE_LEVEL_2_RATIO
        if level >= level_2_threshold: self.damage = 10 + int(level / max_charge_time * 10); self.size = 12; self.color = 9
        elif level >= level_1_threshold: self.damage = 5; self.size = 8; self.color = 10
        else: self.damage = 2; self.size = 5; self.color = 11
        self.w = self.h = self.size * 2
    def update(self): self.x += self.speed
    def draw(self):
        pyxel.circ(self.x, self.y, self.size, self.color); pyxel.circb(self.x, self.y, self.size, 7)
        if self.level >= self.size: pyxel.circ(self.x, self.y, self.size * 0.6, 7)
    def is_offscreen(self): return self.x > SCREEN_WIDTH + self.size

class Star:
    def __init__(self, x, y):
        self.x, self.y = x, y; self.speed = random.uniform(0.5, 1.5); self.color = random.choice([7, 15])
    def update(self):
        self.x -= self.speed
        if self.x < 0: self.x, self.y = SCREEN_WIDTH, random.randint(0, SCREEN_HEIGHT)
    def draw(self): pyxel.pset(self.x, self.y, self.color)

class Force:
    def __init__(self, delay):
        self.delay, self.x, self.y, self.w, self.h, self.size = delay, -16, -16, 0, 0, 3
    def update(self, frog_history):
        if len(frog_history) > self.delay:
            pos = frog_history[self.delay]; self.x, self.y = pos[0] + FROG_WIDTH / 2, pos[1] + FROG_HEIGHT / 2
    def draw(self):
        if self.x >= 0: pyxel.circ(self.x, self.y, self.size, 10); pyxel.circb(self.x, self.y, self.size, 3)
    def shoot(self): return Bullet(self.x, self.y - BULLET_HEIGHT / 2)
    def is_colliding(self, bullet):
        if self.x < 0: return False
        return math.hypot(self.x - (bullet.x + bullet.w / 2), self.y - (bullet.y + bullet.h / 2)) < self.size + 2

class ForceItem:
    def __init__(self, x, y):
        self.x, self.y, self.w, self.h = x, y, 8, 8; self.alive, self.speed_x, self.frame = True, -0.5, 0
    def update(self):
        self.x += self.speed_x; self.y += math.sin(self.frame * 0.1) * 5; self.frame += 1
        if self.x < -self.w: self.alive = False
    def draw(self):
        cx, cy, r = self.x + self.w/2, self.y + self.h/2, self.w/2
        pyxel.circb(cx, cy, r + 2, 7); pyxel.circ(cx, cy, r, 10); pyxel.circb(cx, cy, r, 3)
    def is_colliding(self, frog): return (self.x < frog.x + frog.w and self.x + self.w > frog.x and self.y < frog.y + frog.h and self.y + self.h > frog.y)

class Funnel:
    def __init__(self, frog, index):
        self.frog, self.index = frog, index; self.x, self.y = frog.x, frog.y
        self.target_x, self.target_y, self.move_timer = self.x, self.y, 0
        self.move_speed, self.size = 0.05, 4; self.shoot_timer = random.randint(30, 90)
        self.w, self.h = 0, 0
    def update(self):
        self.move_timer -= 1
        frog_center_x, frog_center_y = self.frog.x + self.frog.w / 2, self.frog.y + self.frog.h / 2
        if self.move_timer <= 0:
            angle, radius = random.uniform(0, 360), random.uniform(30, 80)
            self.target_x = frog_center_x + math.cos(math.radians(angle)) * radius
            self.target_y = frog_center_y + math.sin(math.radians(angle)) * radius
            self.move_timer = random.randint(30, 90)
        self.x += (self.target_x - self.x) * self.move_speed; self.y += (self.target_y - self.y) * self.move_speed
    def draw(self):
        pyxel.tri(self.x, self.y - self.size, self.x - self.size, self.y, self.x + self.size, self.y, 11)
        pyxel.tri(self.x, self.y + self.size, self.x - self.size, self.y, self.x + self.size, self.y, 11)
    def find_closest_enemy(self, enemies):
        closest_enemy, min_dist = None, float('inf')
        for enemy in enemies:
            if not enemy.alive: continue
            dist = math.hypot(self.x - enemy.x, self.y - enemy.y)
            if dist < min_dist: min_dist, closest_enemy = dist, enemy
        return closest_enemy
    def auto_shoot(self, is_focus_mode, enemies):
        self.shoot_timer -= 1
        if is_focus_mode: return None
        if self.shoot_timer <= 0:
            self.shoot_timer = random.randint(90, 180)
            pyxel.play(SOUND_LASER_SHOOT, 11)
            target = self.find_closest_enemy(enemies)
            if target: angle = math.atan2(target.y - self.y, target.x - self.x)
            else: angle = random.uniform(0, 2 * math.pi)
            return Laser(self.x, self.y, angle=angle)
        return None
    def is_colliding(self, bullet): return math.hypot(self.x - (bullet.x + bullet.w/2), self.y - (bullet.y + bullet.h/2)) < self.size + 2

class FunnelItem:
    def __init__(self, x, y):
        self.x, self.y, self.w, self.h = x, y, 8, 8; self.alive, self.speed_x, self.frame = True, -0.5, 0
    def update(self):
        self.x += self.speed_x; self.y += math.sin(self.frame * 0.08) * 4; self.frame += 1
        if self.x < -self.w: self.alive = False
    def draw(self):
        cx, cy, size = self.x + self.w/2, self.y + self.h/2, self.w/2
        pyxel.circb(cx, cy, size + 2, 7); pyxel.tri(cx, cy - size, cx - size, cy, cx + size, cy, 11); pyxel.tri(cx, cy + size, cx - size, cy, cx + size, cy, 11)
    def is_colliding(self, frog): return (self.x < frog.x + frog.w and self.x + self.w > frog.x and self.y < frog.y + frog.h and self.y + self.h > frog.y)

class FocusFunnel:
    def __init__(self, frog, index):
        self.frog, self.index, self.size = frog, index, 4
        self.x, self.y, self.w, self.h = frog.x, frog.y, 0, 0
        self.target_x, self.target_y = self.x, self.y
        self.move_speed, self.shoot_timer = 0.08, random.randint(15, 30)
    def update(self, is_focus_mode):
        frog_center_x, frog_center_y = self.frog.x + self.frog.w / 2, self.frog.y + self.frog.h / 2
        angle = (self.index * 137.5) % 360; radius = 15 + (self.index % 5) * 5
        offset_x = math.cos(math.radians(angle)) * radius
        offset_y = math.sin(math.radians(angle)) * radius
        if is_focus_mode: self.target_x, self.target_y = frog_center_x + offset_x, frog_center_y + offset_y
        else: self.target_x, self.target_y = frog_center_x - 20 + offset_x, frog_center_y + offset_y
        self.x += (self.target_x - self.x) * self.move_speed; self.y += (self.target_y - self.y) * self.move_speed
    def draw(self):
        s = self.size; pyxel.tri(self.x, self.y - s, self.x - s, self.y, self.x + s, self.y, 12); pyxel.tri(self.x, self.y + s, self.x - s, self.y, self.x + s, self.y, 5)
    def shoot(self, is_focus_mode):
        if not is_focus_mode: return None
        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            self.shoot_timer = 25
            pyxel.play(SOUND_LASER_SHOOT, 12)
            return FocusBeam(self.x + self.size, self.y)
        return None
    def is_colliding(self, bullet): return math.hypot(self.x - (bullet.x + bullet.w/2), self.y - (bullet.y + bullet.h/2)) < self.size + 2

class FocusBeam:
    def __init__(self, x, y):
        self.x, self.y, self.w, self.h = x, y, 8, 3; self.speed, self.damage = 6, 3
    def update(self): self.x += self.speed
    def draw(self): pyxel.rect(self.x, self.y - 1, self.w, self.h, 12)
    def is_offscreen(self): return self.x > SCREEN_WIDTH

class FocusFunnelItem:
    def __init__(self, x, y):
        self.x, self.y, self.w, self.h = x, y, 8, 8; self.alive, self.speed_x, self.frame = True, -0.5, 0
    def update(self):
        self.x += self.speed_x; self.y += math.sin(self.frame * 0.09) * 3; self.frame += 1
        if self.x < -self.w: self.alive = False
    def draw(self):
        cx, cy, s = self.x + self.w/2, self.y + self.h/2, self.w/2
        pyxel.circb(cx, cy, s + 2, 7); pyxel.tri(cx, cy - s, cx - s, cy, cx + s, cy, 12); pyxel.tri(cx, cy + s, cx - s, cy, cx + s, cy, 5)
    def is_colliding(self, frog): return (self.x < frog.x + frog.w and self.x + self.w > frog.x and self.y < frog.y + frog.h and self.y + self.h > frog.y)

class Missile:
    def __init__(self, x, y):
        self.x, self.y, self.w, self.h, self.damage = x, y, 6, 6, 2
        self.speed, self.angle, self.turn_speed = 2.0, 0.0, 4.0; self.target = None
    def update(self, enemies):
        if self.target is None or not self.target.alive: self.target = self.find_closest_enemy(enemies)
        if self.target:
            target_angle = math.degrees(math.atan2(self.target.y - self.y, self.target.x - self.x))
            angle_diff = (target_angle - self.angle + 180) % 360 - 180
            self.angle += max(-self.turn_speed, min(self.turn_speed, angle_diff))
        self.x += self.speed * math.cos(math.radians(self.angle)); self.y += self.speed * math.sin(math.radians(self.angle))
    def find_closest_enemy(self, enemies):
        closest_enemy, min_dist = None, float('inf')
        for enemy in enemies:
            if not enemy.alive: continue
            dist = math.hypot(self.x - enemy.x, self.y - enemy.y)
            if dist < min_dist: min_dist, closest_enemy = dist, enemy
        return closest_enemy
    def draw(self):
        angle_rad = math.radians(self.angle)
        p1_x,p1_y=self.x+self.w*math.cos(angle_rad),self.y+self.h*math.sin(angle_rad)
        p2_x,p2_y=self.x+self.w*0.5*math.cos(angle_rad+math.radians(150)),self.y+self.h*0.5*math.sin(angle_rad+math.radians(150))
        p3_x,p3_y=self.x+self.w*0.5*math.cos(angle_rad-math.radians(150)),self.y+self.h*0.5*math.sin(angle_rad-math.radians(150))
        pyxel.tri(p1_x,p1_y,p2_x,p2_y,p3_x,p3_y,8)
        tail_x,tail_y=self.x-self.w*0.7*math.cos(angle_rad),self.y-self.h*0.7*math.sin(angle_rad)
        pyxel.circ(tail_x,tail_y,random.uniform(1,2.5),random.choice([9,10]))
    def is_offscreen(self): return self.x < -self.w or self.x > SCREEN_WIDTH or self.y < -self.h or self.y > SCREEN_HEIGHT

class MissileItem:
    def __init__(self, x, y):
        self.x, self.y, self.w, self.h = x, y, 8, 8; self.alive, self.speed_x, self.frame = True, -0.5, 0
    def update(self):
        self.x += self.speed_x; self.y += math.sin(self.frame * 0.12) * 6; self.frame += 1
        if self.x < -self.w: self.alive = False
    def draw(self):
        cx, cy, size = self.x + self.w/2, self.y + self.h/2, self.w/2
        pyxel.circb(cx, cy, size + 2, 7); pyxel.tri(cx + size, cy, cx - size, cy - size, cx - size, cy + size, 8)
    def is_colliding(self, frog): return (self.x < frog.x + frog.w and self.x + self.w > frog.x and self.y < frog.y + frog.h and self.y + self.h > frog.y)

class DrillMissileItem:
    def __init__(self, x, y):
        self.x, self.y, self.w, self.h = x, y, 8, 8; self.alive, self.speed_x, self.frame = True, -0.5, 0
    def update(self):
        self.x += self.speed_x; self.y += math.sin(self.frame * 0.15) * 2; self.frame += 1
        if self.x < -self.w: self.alive = False
    def draw(self):
        cx, cy, s = self.x + self.w / 2, self.y + self.h / 2, self.w / 2
        pyxel.circb(cx, cy, s + 2, 7)
        pyxel.rect(self.x, self.y, self.w, self.h, 14)
        pyxel.tri(cx + s, cy - s, cx + s, cy + s, cx + s * 2, cy, 6)
    def is_colliding(self, frog): return (self.x < frog.x + frog.w and self.x + self.w > frog.x and self.y < frog.y + frog.h and self.y + self.h > frog.y)

class Frog:
    def __init__(self, x, y):
        self.x, self.y, self.w, self.h = x, y, FROG_WIDTH, FROG_HEIGHT
        self.alive, self.direction, self.animation_frame = True, 1, 0
        self.hp = FROG_BASE_MAX_HP; self.forces, self.funnels, self.history = [], [], []
        self.focus_funnels = []; self.charge_level = 0
        self.max_hp = FROG_BASE_MAX_HP
        self.missile_level = 0; self.has_drill = False
        self.recoil_x = 0; self.recoil_timer = 0
    def add_force(self):
        self.forces.append(Force(len(self.forces) * FORCE_DELAY + FORCE_DELAY)); pyxel.play(SOUND_ITEM_GET, 10)
        self.max_hp += 10; self.hp += 10
    def add_funnel(self):
        self.funnels.append(Funnel(self, len(self.funnels))); pyxel.play(SOUND_ITEM_GET, 10)
    def add_missile(self):
        self.missile_level += 1; pyxel.play(SOUND_ITEM_GET, 10)
    def add_drill_missile(self):
        self.has_drill = True; pyxel.play(SOUND_ITEM_GET, 10)
    def add_focus_funnel(self):
        self.focus_funnels.append(FocusFunnel(self, len(self.focus_funnels))); pyxel.play(SOUND_ITEM_GET, 12)
    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)
        pyxel.play(SOUND_HEAL_GET, 15)
    def apply_recoil(self, charge_level, max_charge):
        charge_ratio = charge_level / max_charge
        self.recoil_x = -charge_ratio * 70
        self.recoil_timer = 25
    def get_current_max_charge(self):
        reduction = len(self.forces) * FORCE_CHARGE_REDUCTION
        return CHARGE_MAX_BASE - reduction
    def update(self, is_focus_mode):
        if self.recoil_timer > 0:
            self.x += self.recoil_x
            self.recoil_x *= 0.9
            self.recoil_timer -= 1
        else:
            self.recoil_x = 0
        speed = 1 if is_focus_mode else 2
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_UP):
            self.y = max(0, self.y - speed)
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_DOWN):
            self.y = min(SCREEN_HEIGHT - self.h, self.y + speed)
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_LEFT):
            self.x = max(0, self.x - speed); self.direction = -1
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_RIGHT):
            self.x = min(SCREEN_WIDTH - self.w, self.x + speed); self.direction = 1
        self.x = max(0, min(self.x, SCREEN_WIDTH - self.w))
        self.y = max(0, min(self.y, SCREEN_HEIGHT - self.h))
        self.history.insert(0, (self.x, self.y))
        if len(self.history) > len(self.forces) * FORCE_DELAY + 10: self.history.pop()
        for force in self.forces: force.update(self.history)
        self.animation_frame = (self.animation_frame + 1) % 10
    def draw(self):
        for force in self.forces: force.draw()
        for funnel in self.funnels: funnel.draw()
        for ff in self.focus_funnels: ff.draw()
        if self.charge_level > 0:
            frog_cx, frog_cy = self.x + self.w / 2, self.y + self.h / 2
            for force in self.forces:
                if force.x >= 0: pyxel.line(force.x, force.y, frog_cx, frog_cy, 10)
            current_max_charge = self.get_current_max_charge()
            if current_max_charge > 0:
                charge_ratio = self.charge_level / current_max_charge
                charge_radius = charge_ratio * 15
                color = 10 if charge_ratio < CHARGE_LEVEL_2_RATIO else 9
                pyxel.circb(frog_cx, frog_cy, charge_radius, color)
                if charge_ratio > CHARGE_LEVEL_1_RATIO:
                     pyxel.circb(frog_cx, frog_cy, charge_radius * 0.5 + random.uniform(0, 2), 7)
        u, offset_y = (0, 3) if self.direction == 1 else (16, 3)
        if self.animation_frame not in [3, 6]: offset_y = 0
        pyxel.blt(self.x, self.y + offset_y, 0, u, 0, self.w * self.direction, self.h, 0)
    def shoot(self):
        new_bullets = [Bullet(self.x + self.w / 2, self.y)]
        for force in self.forces:
            if force.x >= 0: new_bullets.append(force.shoot())
        pyxel.play(SOUND_BULLET_SHOOT, 2)
        return new_bullets
    def is_colliding(self, obj): return (self.x-3 < obj.x+obj.w and self.x+self.w+3 > obj.x and self.y-3 < obj.y+obj.h and self.y+self.h+3 > obj.y)
    def take_damage(self, damage):
        self.hp = max(0, self.hp - damage)
        if self.hp <= 0: self.alive = False
    def draw_hp_bar(self, x, y):
        hp_ratio = self.hp / self.max_hp if self.max_hp > 0 else 0
        bar_width = int(HP_BAR_WIDTH * hp_ratio)
        pyxel.rect(x, y, HP_BAR_WIDTH, HP_BAR_HEIGHT, 8); pyxel.rect(x, y, bar_width, HP_BAR_HEIGHT, 10)

class Bullet:
    def __init__(self, x, y):
        self.x, self.y, self.w, self.h = x, y, BULLET_WIDTH, BULLET_HEIGHT; self.speed, self.damage = 4, 1
    def update(self): self.x += self.speed
    def draw(self): pyxel.rect(self.x, self.y + 4, self.w, self.h, 10)
    def is_offscreen(self): return self.x > SCREEN_WIDTH

class Laser:
    def __init__(self, x, y, angle):
        self.x, self.y, self.angle_rad, self.width, self.color, self.duration, self.damage = x, y, angle, 2, 10, 15, 1
        self.length = SCREEN_WIDTH * 1.5
    def update(self): self.duration -= 1; return self.duration <= 0
    def draw(self):
        end_x, end_y = self.x + self.length * math.cos(self.angle_rad), self.y + self.length * math.sin(self.angle_rad)
        pyxel.line(self.x, self.y, end_x, end_y, self.color); pyxel.line(self.x + 1, self.y, end_x + 1, end_y, self.color)
    def is_colliding(self, enemy):
        x1,y1=self.x,self.y; x2,y2=self.x+self.length*math.cos(self.angle_rad),self.y+self.length*math.sin(self.angle_rad)
        cx,cy=enemy.x+enemy.w/2,enemy.y+enemy.h/2; len_sq=(x2-x1)**2+(y2-y1)**2
        if len_sq == 0.0: return math.hypot(cx-x1,cy-y1)<(enemy.w+enemy.h)/2
        t=max(0,min(1,((cx-x1)*(x2-x1)+(cy-y1)*(y2-y1))/len_sq))
        dist=math.hypot(cx-(x1+t*(x2-x1)),cy-(y1+t*(y2-y1)))
        return dist < (enemy.w/2)+self.width

class EnemyBullet:
    def __init__(self, x, y, stage_number):
        self.x, self.y, self.w, self.h = x, y, BULLET_WIDTH, BULLET_HEIGHT
        self.speed = -(2 + stage_number * 0.08)
    def update(self): self.x += self.speed
    def draw(self): pyxel.rect(self.x, self.y + 4, self.w, self.h, 8)
    def is_offscreen(self): return self.x < 0

class Enemy:
    def __init__(self, x, y, enemy_type, stage_number, frog=None):
        self.x, self.y, self.w, self.h = x, y, ENEMY_WIDTH, ENEMY_HEIGHT
        self.stage_number = stage_number; self.speed = random.uniform(1, 4) + stage_number*0.05
        self.alive, self.type, self.animation_frame = True, enemy_type, 0
        self.explosion, self.drop_item_on_death = None, (self.type in [2, 3, 4])
        self.state_timer = 0; self.state = "move"
        self.shake_offset = random.uniform(0, 2 * math.pi)
        self.image_x, self.image_y = 0, 0

        if self.type == 0:
            self.score_value, self.image_x, self.image_y = 10, 0, 16
            self.max_hp = 1 + (stage_number // 2); self.hp = self.max_hp; self.damage = 10 + (stage_number // 2)
        elif self.type == 1:
            self.speed_y=random.uniform(0.5,1.5)+stage_number*0.05; self.score_value,self.image_x,self.image_y=20,16,16
            self.max_hp = 2 + (stage_number // 2); self.hp = self.max_hp; self.damage = 20 + (stage_number // 2)
        elif self.type == 2:
            self.score_value, self.image_x, self.image_y = 30, 32, 16
            self.max_hp = 1 + (stage_number // 2); self.hp = self.max_hp
            self.shoot_delay = max(40, random.randint(200, 360) - stage_number * 3); self.shoot_timer = 0
            self.damage = 30 + (stage_number // 2)
        elif self.type == 3:
            self.score_value = 50; self.max_hp = 3 + (stage_number // 2); self.hp = self.max_hp
            self.damage = 40 + (stage_number // 2); self.frog_ref = frog
        elif self.type == 4:
            self.score_value = 5; self.max_hp = 20 + stage_number * 2; self.hp = self.max_hp
            self.damage = 50 + (stage_number // 2); self.speed = 0.5

    def update(self, enemy_bullets=None):
        self.animation_frame = (self.animation_frame + 1) % 120
        if self.type == 3:
            if self.state == "move":
                self.x -= self.speed
                if self.x < SCREEN_WIDTH - 40: self.state = "aim"; self.state_timer = 90
            elif self.state == "aim":
                if self.frog_ref: self.y += (self.frog_ref.y - self.y) * 0.05
                self.state_timer -= 1
                if self.state_timer <= 0:
                    self.state = "shoot"; bullet = EnemyBullet(self.x, self.y + self.h/2, self.stage_number)
                    bullet.speed = -8; enemy_bullets.append(bullet); self.state_timer = 30
            elif self.state == "shoot":
                self.state_timer -= 1
                if self.state_timer <= 0: self.state = "retreat"
            elif self.state == "retreat": self.x += self.speed * 2
        else:
            self.x -= self.speed
            if self.type == 1: self.y = 50 + 30 * math.sin(self.x / 30)

        if self.x < -self.w: self.alive = False
        
        if self.type == 2:
            self.shoot_timer += 1
            if self.shoot_timer >= self.shoot_delay: self.shoot_timer=0; enemy_bullets.append(EnemyBullet(self.x, self.y, self.stage_number))

    def take_damage(self, damage):
        self.hp -= damage
        if self.hp <= 0: self.alive = False
        
    def draw(self):
        y_offset = 0
        if self.type != 1: y_offset = math.sin(self.animation_frame * 0.2 + self.shake_offset) * 1
        draw_y = self.y + y_offset

        if self.type == 3:
            body_color = 5; gun_color = 13
            if self.state == "aim" and (self.state_timer // 10) % 2 == 0: body_color = 9
            pyxel.rect(self.x + 4, draw_y, 12, 16, body_color)
            pyxel.rect(self.x, draw_y + 6, 16, 4, gun_color)
        elif self.type == 4:
            hp_ratio = self.hp / self.max_hp
            main_color = 6; damage_color = 1
            if hp_ratio < 0.5: main_color = 1
            if hp_ratio < 0.2: damage_color = 8
            pyxel.rect(self.x, draw_y, self.w, self.h, 1)
            pyxel.rect(self.x + 1, draw_y + 1, self.w - 2, self.h - 2, main_color)
            if hp_ratio < 0.7: pyxel.pset(self.x + 5, draw_y + 5, damage_color); pyxel.pset(self.x + 10, draw_y + 10, damage_color)
        else:
            pyxel.blt(self.x, draw_y, 0, self.image_x, self.image_y, self.w, self.h, 0)
        
        if self.hp < self.max_hp:
            hp_ratio = self.hp/self.max_hp if self.max_hp > 0 else 0
            bar_color = 10 if hp_ratio>0.5 else 9 if hp_ratio>0.25 else 8
            pyxel.rect(self.x, draw_y - 4, self.w * hp_ratio, 2, bar_color)
            
    def is_colliding(self, bullet): return (self.x-3 < bullet.x+bullet.w and self.x+self.w+3 > bullet.x and self.y-3 < bullet.y+bullet.h and self.y+self.h+3 > bullet.y)
    def explode(self): self.explosion = Explosion(self.x, self.y); pyxel.play(SOUND_ENEMY_DEATH, 1)

class Explosion:
    def __init__(self, x, y): self.x, self.y, self.frame = x, y, 0
    def update(self): self.frame += 1; return self.frame > 15
    def draw(self): pyxel.blt(self.x, self.y, 0, 48, 16, 16, 16, 0)

class Stage:
    def __init__(self, stage_number):
        self.stage_number = stage_number
        self.enemy_spawn_interval = max(1, ENEMY_SPAWN_INTERVAL - stage_number * 1.5)
        self.enemy_types = [0, 1, 2]
        if stage_number > 3: self.enemy_types.append(3)
        if stage_number > 5: self.enemy_types.append(4)
        self.background_color = (stage_number - 1) % 16
        
    def draw(self): pyxel.cls(self.background_color)

class App:
    def __init__(self):
        pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT); pyxel.load("frog_shooting.pyxres")
        pyxel.playm(MUSIC_STAGE, loop=True)
        self.stars = [Star(random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT)) for _ in range(STAR_COUNT)]
        self.reset_game(); pyxel.run(self.update, self.draw)

    def reset_game(self):
        self.frog = Frog(32, pyxel.height // 2)
        self.bullets, self.enemy_bullets, self.enemies, self.explosions, self.lasers, self.missiles, self.focus_beams = [], [], [], [], [], [], []
        self.charge_shots, self.drill_missiles = [], []
        self.force_items, self.funnel_items, self.missile_items, self.focus_funnel_items, self.drill_missile_items, self.recovery_items = [], [], [], [], [], []
        self.score, self.frame_count, self.game_over, self.stage_cleared = 0, 0, False, False
        self.stage_number, self.stage, self.missile_cooldown, self.drill_missile_cooldown = 1, Stage(1), 0, 0
        self.is_focus_mode = False; self.focus_gauge_max = FOCUS_GAUGE_BASE_MAX
        self.focus_gauge = self.focus_gauge_max; self.focus_cooldown_time = FOCUS_COOLDOWN_BASE_TIME
        self.focus_cooldown_timer = 0
        self.boss = None
        self.enemies_defeated = 0
    
    def reset_for_next_stage(self):
        self.bullets, self.enemy_bullets, self.enemies, self.explosions, self.lasers, self.missiles, self.focus_beams = [], [], [], [], [], [], []
        self.charge_shots, self.drill_missiles = [], []
        self.force_items, self.funnel_items, self.missile_items, self.focus_funnel_items, self.drill_missile_items, self.recovery_items = [], [], [], [], [], []
        self.frog.hp, self.stage_cleared = self.frog.max_hp, False; self.frog.alive = True
        self.focus_gauge = self.focus_gauge_max; self.focus_cooldown_timer = 0
        self.boss = None
        self.score = 0
        self.enemies_defeated = 0

    def update(self):
        if self.game_over:
            if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.GAMEPAD1_BUTTON_B): self.reset_game()
            return
        if self.stage_cleared:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.GAMEPAD1_BUTTON_A):
                self.stage_number += 1
                self.stage = Stage(self.stage_number)
                self.reset_for_next_stage()
                if self.stage_number % 10 == 0:
                    self.boss = Boss(self.stage_number)
            return

        self.frame_count += 1
        
        if self.boss:
            self.boss.update(self.frog, self.enemy_bullets)
            if self.boss.explosion:
                self.explosions.append(self.boss.explosion)
                self.boss.explosion = None
            if not self.boss.alive:
                self.score += 5000 * (self.stage_number // 10)
                self.enemies_defeated += 1
                self.stage_cleared = True
                self.boss = None
        
        if self.focus_cooldown_timer > 0: self.focus_cooldown_timer -= 1
        can_press_focus = pyxel.btn(pyxel.KEY_X) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_X)
        can_activate_focus = can_press_focus and self.focus_cooldown_timer <= 0 and self.frog.focus_funnels
        if can_activate_focus and self.focus_gauge > 0:
            self.is_focus_mode = True
            self.focus_gauge = max(0, self.focus_gauge - FOCUS_GAUGE_CONSUMPTION)
            if self.focus_gauge == 0: self.focus_cooldown_timer = self.focus_cooldown_time
        else:
            self.is_focus_mode = False
            if self.focus_gauge < self.focus_gauge_max: self.focus_gauge += FOCUS_GAUGE_RECOVERY
        
        if self.frog.alive: self.frog.update(self.is_focus_mode)

        updatable_groups = [self.stars, self.bullets, self.enemy_bullets, self.force_items, 
                            self.funnel_items, self.missile_items, self.focus_funnel_items,
                            self.focus_beams, self.charge_shots, self.drill_missiles, self.drill_missile_items, self.recovery_items]
        for group in updatable_groups:
            for obj in group: obj.update()
        for obj in self.explosions[:]:
            if obj.update(): self.explosions.remove(obj)
        for obj in self.lasers[:]:
            if obj.update(): self.lasers.remove(obj)
        for obj in self.missiles: obj.update(self.enemies)
        
        for funnel in self.frog.funnels:
            funnel.update()
            if new_laser := funnel.auto_shoot(self.is_focus_mode, self.enemies): self.lasers.append(new_laser)
        for ff in self.frog.focus_funnels:
            ff.update(self.is_focus_mode)
            if beam := ff.shoot(self.is_focus_mode): self.focus_beams.append(beam)

        if self.frog.missile_level > 0 and not self.frog.has_drill and self.enemies:
            self.missile_cooldown -= 1
            if self.missile_cooldown <= 0:
                self.missiles.append(Missile(self.frog.x + self.frog.w / 2, self.frog.y + self.frog.h / 2))
                self.missile_cooldown = max(15, 90 - self.frog.missile_level * 5)
        
        if self.frog.has_drill:
            self.drill_missile_cooldown -= 1
            if self.drill_missile_cooldown <= 0:
                self.drill_missiles.append(DrillMissile(self.frog.x + self.frog.w, self.frog.y + self.frog.h/2 - 2))
                self.drill_missile_cooldown = 180
        
        if not self.boss:
            for enemy in self.enemies[:]:
                enemy.update(self.enemy_bullets)
            self.enemies = [e for e in self.enemies if e.alive]
            if self.frame_count % int(self.stage.enemy_spawn_interval) == 0:
                enemy_type = random.choice(self.stage.enemy_types)
                self.enemies.append(Enemy(SCREEN_WIDTH, random.randint(0, SCREEN_HEIGHT - ENEMY_HEIGHT), enemy_type, self.stage_number, self.frog))

        self.bullets = [b for b in self.bullets if not b.is_offscreen()]
        self.enemy_bullets = [b for b in self.enemy_bullets if not b.is_offscreen()]
        self.missiles = [m for m in self.missiles if not m.is_offscreen()]
        self.focus_beams = [b for b in self.focus_beams if not b.is_offscreen()]
        self.charge_shots = [cs for cs in self.charge_shots if not cs.is_offscreen()]
        self.drill_missiles = [d for d in self.drill_missiles if not d.is_offscreen()]
        
        item_lists = [self.force_items, self.funnel_items, self.missile_items, self.focus_funnel_items, self.drill_missile_items, self.recovery_items]
        for item_list in item_lists: item_list[:] = [i for i in item_list if i.alive]

        for dm in self.drill_missiles[:]:
            if self.boss and self.boss.alive and self.boss.is_colliding(dm):
                self.boss.take_damage(dm.damage)
            for enemy in self.enemies:
                if enemy.alive and enemy.is_colliding(dm):
                    enemy.take_damage(dm.damage)
                    if not enemy.alive: self.handle_enemy_destruction(enemy)
                    if dm.take_damage(1):
                        try: self.drill_missiles.remove(dm)
                        except ValueError: pass
                        break
        
        projectiles = self.bullets + self.missiles + self.focus_beams + self.charge_shots
        if self.boss and self.boss.alive:
            for proj in projectiles[:]:
                if self.boss.is_colliding(proj):
                    self.boss.take_damage(proj.damage)
                    try:
                        if proj in self.charge_shots: self.charge_shots.remove(proj)
                        elif proj in self.bullets: self.bullets.remove(proj)
                        elif proj in self.missiles: self.missiles.remove(proj)
                        elif proj in self.focus_beams: self.focus_beams.remove(proj)
                    except ValueError: pass
        for proj in projectiles[:]:
            for enemy in self.enemies[:]:
                if enemy.alive and enemy.is_colliding(proj):
                    enemy.take_damage(proj.damage)
                    if not enemy.alive: self.handle_enemy_destruction(enemy)
                    if not isinstance(proj, Laser):
                        try:
                            if proj in self.charge_shots: self.charge_shots.remove(proj)
                            elif proj in self.bullets: self.bullets.remove(proj)
                            elif proj in self.missiles: self.missiles.remove(proj)
                            elif proj in self.focus_beams: self.focus_beams.remove(proj)
                        except ValueError: pass
                    break
        
        for laser in self.lasers:
            if self.boss and self.boss.alive and laser.is_colliding(self.boss):
                self.boss.take_damage(laser.damage)
            for enemy in self.enemies[:]:
                if enemy.alive and laser.is_colliding(enemy):
                    enemy.take_damage(laser.damage)
                    if not enemy.alive: self.handle_enemy_destruction(enemy)
                    
        for bullet in self.enemy_bullets[:]:
            if any(shield.is_colliding(bullet) for shield in self.frog.forces + self.frog.funnels + self.frog.focus_funnels):
                self.enemy_bullets.remove(bullet); continue
            if self.frog.alive and self.frog.is_colliding(bullet): self.frog.take_damage(10); self.enemy_bullets.remove(bullet)
        
        if self.frog.alive:
            if self.boss and self.boss.alive and self.frog.is_colliding(self.boss):
                self.frog.take_damage(50)

            for enemy in self.enemies[:]:
                if self.frog.is_colliding(enemy):
                    self.frog.take_damage(enemy.damage); enemy.take_damage(999)
                    if not enemy.alive: self.handle_enemy_destruction(enemy, no_item=True)
                    break
            
            item_groups = {'force': (self.force_items, self.frog.add_force),'funnel': (self.funnel_items, self.frog.add_funnel),'missile': (self.missile_items, self.frog.add_missile),'drill': (self.drill_missile_items, self.frog.add_drill_missile),'focus': (self.focus_funnel_items, self.frog.add_focus_funnel), 'heal': (self.recovery_items, lambda: self.frog.heal(25))}
            for key, (item_list, action) in item_groups.items():
                for item in item_list[:]:
                    if item.is_colliding(self.frog):
                        action(); item_list.remove(item)
                        if key == 'focus':
                            self.focus_gauge_max += 20
                            self.focus_cooldown_time = max(0, self.focus_cooldown_time - 15)

        if not self.frog.alive: self.game_over = True
        
        if self.frog.alive:
            shoot_btn = pyxel.btn(pyxel.KEY_SPACE) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_A)
            shoot_btn_released = pyxel.btnr(pyxel.KEY_SPACE) or pyxel.btnr(pyxel.GAMEPAD1_BUTTON_A)
            current_max_charge = self.frog.get_current_max_charge()
            if shoot_btn:
                if current_max_charge > 0 and self.frog.charge_level < current_max_charge: self.frog.charge_level += 1
            if (shoot_btn_released or (current_max_charge > 0 and self.frog.charge_level >= current_max_charge)) and self.frog.charge_level > 0:
                min_charge_threshold = 6 
                if self.frog.charge_level < min_charge_threshold: self.bullets.extend(self.frog.shoot())
                else:
                    self.charge_shots.append(ChargeShot(self.frog.x + self.frog.w, self.frog.y + self.frog.h / 2, self.frog.charge_level, current_max_charge))
                    self.frog.apply_recoil(self.frog.charge_level, current_max_charge)
                    pyxel.play(SOUND_BULLET_SHOOT, 8) 
                self.frog.charge_level = 0
        
        if not self.boss and self.score >= (500 + self.stage_number * 100): self.stage_cleared = True
    
    def handle_enemy_destruction(self, enemy, no_item=False):
        self.score += enemy.score_value
        self.enemies_defeated += 1
        enemy.explode(); self.explosions.append(enemy.explosion)
        if not no_item and enemy.drop_item_on_death:
            if random.randint(1, 10) == 1:
                item_choices = ['force', 'funnel']
                if self.frog.missile_level > 0 and not self.frog.has_drill:
                    item_choices.append('drill')
                else:
                    item_choices.append('missile')
                
                item_type = random.choice(item_choices)
                if item_type == 'force': self.force_items.append(ForceItem(enemy.x, enemy.y))
                elif item_type == 'funnel': self.funnel_items.append(FunnelItem(enemy.x, enemy.y))
                elif item_type == 'missile': self.missile_items.append(MissileItem(enemy.x, enemy.y))
                elif item_type == 'drill': self.drill_missile_items.append(DrillMissileItem(enemy.x, enemy.y))

            if random.randint(1, 20) == 1:
                self.focus_funnel_items.append(FocusFunnelItem(enemy.x, enemy.y))

            if random.randint(1, 1000) == 1:
                self.recovery_items.append(RecoveryItem(enemy.x, enemy.y))
                
        if enemy in self.enemies: self.enemies.remove(enemy)

    def draw(self):
        self.stage.draw(); [star.draw() for star in self.stars]
        if self.game_over:
            pyxel.text(SCREEN_WIDTH//2-30, SCREEN_HEIGHT//2-10, "GAME OVER", 8); pyxel.text(SCREEN_WIDTH//2-40, SCREEN_HEIGHT//2+5, f"SCORE: {self.score}", 7)
            pyxel.text(SCREEN_WIDTH//2-45, SCREEN_HEIGHT//2+15, f"REACHED STAGE: {self.stage_number}", 7); pyxel.text(SCREEN_WIDTH//2-50, SCREEN_HEIGHT//2+30, "PRESS R TO RESTART", 7)
            pyxel.text(SCREEN_WIDTH//2-50, SCREEN_HEIGHT//2+45, f"TOTAL KILLS: {self.enemies_defeated}", 7)
        elif self.stage_cleared:
            pyxel.text(SCREEN_WIDTH//2-40, SCREEN_HEIGHT//2-10, "STAGE CLEAR!", 7); pyxel.text(SCREEN_WIDTH//2-70, SCREEN_HEIGHT//2+5, "PRESS SPACE TO NEXT STAGE", 7)
        else:
            self.frog.draw()
            if self.boss:
                self.boss.draw()
                self.boss.draw_hp_bar()
            else:
                self.frog.draw_hp_bar(5, 15)
            
            drawable_groups = [self.enemies, self.bullets, self.enemy_bullets, self.force_items, self.funnel_items, 
                               self.missile_items, self.explosions, self.lasers, self.missiles, self.focus_funnel_items,
                               self.focus_beams, self.charge_shots, self.drill_missiles, self.drill_missile_items, self.recovery_items]
            for group in drawable_groups:
                for obj in group: obj.draw()
            
            if not self.boss:
                pyxel.text(5, 5, f"SCORE: {self.score}", 7)
                pyxel.text(5, 25, f"STAGE: {self.stage_number}", 7)
                pyxel.text(5, 35, f"KILLS: {self.enemies_defeated}", 7)
            
            if self.is_focus_mode: pyxel.text(5, 45, "FOCUS MODE", 8)
            if self.frog.focus_funnels:
                pyxel.text(5, 55, "FOCUS", 7)
                gauge_ratio = self.focus_gauge / self.focus_gauge_max if self.focus_gauge_max > 0 else 0
                gauge_width = int(HP_BAR_WIDTH * gauge_ratio)
                pyxel.rect(5, 65, HP_BAR_WIDTH, HP_BAR_HEIGHT, 13); pyxel.rect(5, 65, gauge_width, HP_BAR_HEIGHT, 12)
                if self.focus_cooldown_timer > 0 and pyxel.frame_count % 10 < 5: pyxel.text(5, 75, "COOLDOWN", 8)

App()