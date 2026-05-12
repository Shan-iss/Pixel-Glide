import pygame
import sys
import random
import math

pygame.init()

SCREEN_W, SCREEN_H = 800, 600
FPS = 60
BASE_WORLD_W = 3200
WORLD_W = BASE_WORLD_W

screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Pixel Glide")
clock = pygame.time.Clock()

BLACK      = (10, 10, 20)
CYAN       = (93, 202, 165)
GREEN      = (29, 158, 117)
DARK_GREEN = (15, 110, 86)
BLUE       = (55, 138, 221)
RED        = (226, 75, 74)
ORANGE     = (239, 159, 39)
WHITE      = (255, 255, 255)
GRAY       = (60, 60, 80)
PLATFORM_C = (40, 40, 60)
PURPLE     = (127, 119, 221)
YELLOW     = (250, 199, 117)
DARK_BLUE  = (15, 15, 35)
PINK       = (220, 80, 160)
TEAL       = (0, 180, 160)

BOSS_DATA = {
    1:  {"name":"SCOUT ALPHA",   "color":(55,138,221),  "armor":(24,90,160),  "eye":RED,    "hp":12,  "speed":1.2, "size":(50,55),  "ability":"triple_shot",  "desc":"Tembak 3 arah"},
    2:  {"name":"TANK CRUSHER",  "color":(100,180,60),  "armor":(60,120,30),  "eye":YELLOW, "hp":18,  "speed":0.8, "size":(65,65),  "ability":"ground_slam",  "desc":"Slam + shockwave"},
    3:  {"name":"SENTRY MK-I",   "color":(120,40,40),   "armor":(80,30,30),   "eye":RED,    "hp":25,  "speed":1.5, "size":(70,80),  "ability":"burst_fire",   "desc":"Burst 5 peluru"},
    4:  {"name":"AERO HUNTER",   "color":(80,60,180),   "armor":(50,40,130),  "eye":CYAN,   "hp":30,  "speed":2.0, "size":(75,60),  "ability":"dive_bomb",    "desc":"Terbang + bom"},
    5:  {"name":"PHANTOM BLADE", "color":(160,30,160),  "armor":(100,20,100), "eye":PINK,   "hp":38,  "speed":2.5, "size":(65,75),  "ability":"teleport",     "desc":"Teleport + spray"},
    6:  {"name":"TWIN GUNNER",   "color":(180,120,20),  "armor":(130,80,10),  "eye":ORANGE, "hp":45,  "speed":1.8, "size":(80,70),  "ability":"dual_cannon",  "desc":"2 meriam"},
    7:  {"name":"CRYO TITAN",    "color":(40,160,200),  "armor":(20,100,150), "eye":(200,240,255), "hp":55, "speed":1.4, "size":(85,90), "ability":"freeze_wave", "desc":"Gelombang beku"},
    8:  {"name":"STORM BRINGER", "color":(100,50,200),  "armor":(70,30,150),  "eye":YELLOW, "hp":65,  "speed":2.2, "size":(80,85),  "ability":"lightning",    "desc":"Petir + AOE"},
    9:  {"name":"TITAN MK-III",  "color":(80,80,80),    "armor":(50,50,50),   "eye":RED,    "hp":80,  "speed":1.6, "size":(95,100), "ability":"multi_phase",  "desc":"3 fase"},
    10: {"name":"CORE-X",        "color":(20,20,60),    "armor":(10,10,40),   "eye":CYAN,   "hp":100, "speed":2.0, "size":(100,110),"ability":"ultimate",     "desc":"FINAL BOSS"},
}

WEAPONS = {
    "laser":   {"name":"Laser Pistol", "color":CYAN,          "damage":1, "speed":12, "ammo":-1, "desc":"Default — ∞ ammo"},
    "plasma":  {"name":"Plasma Gun",   "color":(150,80,255),  "damage":2, "speed":9,  "ammo":20, "desc":"Damage besar"},
    "shotgun": {"name":"Shotgun",      "color":ORANGE,        "damage":1, "speed":10, "ammo":15, "desc":"5 peluru sekaligus"},
    "cryo":    {"name":"Cryo Blaster", "color":(100,200,255), "damage":1, "speed":8,  "ammo":12, "desc":"Bekukan enemy"},
    "thunder": {"name":"Thunder",      "color":YELLOW,        "damage":3, "speed":14, "ammo":10, "desc":"Damage tertinggi"},
}

# ══════════════════════════════════════════════
# FLY ZONE
# ══════════════════════════════════════════════
# ══════════════════════════════════════════════
# FLY ENEMY (Drone di fly zone)
# ══════════════════════════════════════════════
class FlyDrone:
    SIZE = 20
    def __init__(self, wx, wy, pattern="horizontal", speed=1.5):
        self.wx      = float(wx)
        self.wy      = float(wy)
        self.oy      = float(wy)
        self.ox      = float(wx)
        self.pattern = pattern   # horizontal / vertical / chase / circle
        self.speed   = speed
        self.hp      = 1
        self.alive   = True
        self.t       = random.uniform(0, math.pi*2)
        self.shoot_timer = random.randint(60, 120)
        self.angle   = 0.0

    def update(self, player_wx, player_wy, bullets):
        self.t += 0.03
        if self.pattern == "horizontal":
            self.wx = self.ox + math.sin(self.t * self.speed) * 120
        elif self.pattern == "vertical":
            self.wy = self.oy + math.sin(self.t * self.speed) * 80
        elif self.pattern == "circle":
            self.wx = self.ox + math.cos(self.t * self.speed) * 80
            self.wy = self.oy + math.sin(self.t * self.speed) * 60
        elif self.pattern == "chase":
            dx = player_wx - self.wx
            dy = player_wy - self.wy
            dist = math.hypot(dx, dy) or 1
            self.wx += dx/dist * self.speed * 0.8
            self.wy += dy/dist * self.speed * 0.8
        # Shoot
        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            dx = player_wx - self.wx
            dy = player_wy - self.wy
            dist = math.hypot(dx, dy) or 1
            bullets.append(WorldBullet(
                self.wx + self.SIZE//2,
                self.wy + self.SIZE//2,
                dx/dist * 3.0, dy/dist * 3.0, RED))
            self.shoot_timer = random.randint(80, 140)

    def draw(self, surface, cam):
        sx, sy = cam.apply(self.wx, self.wy)
        if not (-30 < sx < SCREEN_W+30): return
        t2 = pygame.time.get_ticks()
        s  = self.SIZE
        ix, iy = int(sx), int(sy)
        # Badan drone
        pygame.draw.ellipse(surface, (200,60,60),  (ix, iy, s, s//2+4))
        pygame.draw.ellipse(surface, (255,100,80), (ix+2, iy+2, s-4, s//2))
        # Mata merah menyala
        ep = int(180+75*math.sin(t2*0.1))
        pygame.draw.circle(surface, (ep,30,30), (ix+5,  iy+5), 4)
        pygame.draw.circle(surface, (ep,30,30), (ix+15, iy+5), 4)
        # Rotor
        ra = t2 * 0.1
        for ri in range(2):
            ang = ra + ri * math.pi
            rx1 = ix + s//2 + int(10*math.cos(ang))
            ry1 = iy - 4   + int(4 *math.sin(ang))
            rx2 = ix + s//2 - int(10*math.cos(ang))
            ry2 = iy - 4   - int(4 *math.sin(ang))
            pygame.draw.line(surface, (120,120,180), (rx1,ry1),(rx2,ry2), 2)
        # HP bar
        pygame.draw.rect(surface,(80,20,20),(ix,iy-8,s,4),border_radius=2)
        pygame.draw.rect(surface,RED,(ix,iy-8,int(s*self.hp),4),border_radius=2)

    def get_rect(self):
        return pygame.Rect(self.wx+2, self.wy+2, self.SIZE-4, self.SIZE-4)

# ══════════════════════════════════════════════
# FLY ZONE
# ══════════════════════════════════════════════
class FlyZone:
    def __init__(self, wx, width, level_num):
        self.wx      = wx
        self.width   = width
        self.level   = level_num
        self.rng     = random.Random(wx * 7 + level_num * 13)
        self.obstacles = []   # pipa statis
        self.mov_obs   = []   # rintangan bergerak
        self.drones    = []   # enemy fly

        # ── Pipa statis ──────────────────────
        gap_h   = max(110, 190 - level_num * 7)
        spacing = max(160, 260 - level_num * 8)
        ox = wx + 220
        while ox < wx + width - 200:
            gap_y = self.rng.randint(70, SCREEN_H - gap_h - 70)
            self.obstacles.append({
                "wx": ox, "gap_y": gap_y, "gap_h": gap_h, "w": 38
            })
            ox += spacing + self.rng.randint(-20, 20)

        # ── Rintangan bergerak (asteroid/batu) ──
        if level_num >= 2:
            num_mov = 2 + level_num
            for _ in range(num_mov):
                mx2  = wx + self.rng.randint(250, int(width)-200)
                my2  = self.rng.randint(80, SCREEN_H - 80)
                spd  = 0.8 + level_num * 0.12 + self.rng.uniform(0, 0.5)
                axis = self.rng.choice(["v","h"])
                rng2 = self.rng.randint(40, 80 + level_num * 6)
                self.mov_obs.append({
                    "wx": float(mx2), "wy": float(my2),
                    "ox": float(mx2), "oy": float(my2),
                    "speed": spd, "range": rng2,
                    "axis": axis, "t": self.rng.uniform(0, math.pi*2),
                    "size": self.rng.randint(18, 30)
                })

        # ── Drone enemy ──────────────────────
        num_drones = 1 + level_num // 2
        patterns   = ["horizontal", "vertical", "circle", "chase"]
        for i in range(num_drones):
            ex  = wx + 300 + i * int((width-400) / max(1, num_drones))
            ey  = self.rng.randint(100, SCREEN_H - 150)
            pat = self.rng.choice(patterns)
            spd = 1.2 + level_num * 0.1
            self.drones.append(FlyDrone(ex, ey, pat, spd))

    def contains(self, wx):
        return self.wx <= wx <= self.wx + self.width

    def update(self, player_wx, player_wy, bullets):
        t2 = pygame.time.get_ticks() * 0.001
        # Update moving obstacles
        for mo in self.mov_obs:
            mo["t"] += 0.025 * mo["speed"]
            if mo["axis"] == "v":
                mo["wy"] = mo["oy"] + math.sin(mo["t"]) * mo["range"]
            else:
                mo["wx"] = mo["ox"] + math.sin(mo["t"]) * mo["range"]
        # Update drones
        for d in self.drones:
            if d.alive:
                d.update(player_wx, player_wy, bullets)
        self.drones = [d for d in self.drones if d.alive]

    def hit_bullet(self, bullet_rect):
        """Cek apakah peluru player kena drone"""
        for d in self.drones:
            if d.alive and bullet_rect.colliderect(d.get_rect()):
                d.hp -= 1
                if d.hp <= 0:
                    d.alive = False
                    return True   # kill
                return False      # hit tapi belum mati
        return None               # miss

    def draw_bg(self, surface, cam, t):
        sx = int(cam.apply(self.wx, 0)[0])
        sw = int(self.width)
        # Gradient biru gelap di seluruh fly zone
        vis_x = max(0, sx)
        vis_w = min(SCREEN_W, sx + sw) - vis_x
        if vis_w > 0:
            bg = pygame.Surface((vis_w, SCREEN_H), pygame.SRCALPHA)
            for y in range(0, SCREEN_H, 2):
                alpha = int(35 + 15*math.sin(y*0.015 + t*0.001))
                pygame.draw.line(bg, (15, 35, 70, alpha), (0,y),(vis_w,y))
            surface.blit(bg, (vis_x, 0))

        # Border kiri
        if 0 < sx < SCREEN_W:
            pygame.draw.line(surface, CYAN, (sx,0),(sx,SCREEN_H), 2)
            fnt = pygame.font.SysFont("monospace", 11)
            lbl = fnt.render("✈ FLY ZONE", True, CYAN)
            surface.blit(lbl, (sx+4, SCREEN_H//2-20))
            hint = fnt.render("SPACE=Thrust", True, (80,160,140))
            surface.blit(hint, (sx+4, SCREEN_H//2))

        # Border kanan
        ex = int(cam.apply(self.wx + self.width, 0)[0])
        if 0 < ex < SCREEN_W:
            pygame.draw.line(surface, ORANGE,(ex,0),(ex,SCREEN_H),2)
            fnt2 = pygame.font.SysFont("monospace", 11)
            et   = fnt2.render("→ RUN", True, ORANGE)
            surface.blit(et, (ex-50, SCREEN_H//2-6))

    def draw_obstacles(self, surface, cam, t):
        # Pipa statis
        for obs in self.obstacles:
            sx  = int(cam.apply(obs["wx"], 0)[0])
            if not (-obs["w"]-10 < sx < SCREEN_W+10): continue
            w   = obs["w"]; gy  = obs["gap_y"]; gh  = obs["gap_h"]
            col_p = (30,100,60); col_p2 = (50,140,80)
            # Atas
            pygame.draw.rect(surface, col_p,  (sx, 0, w, gy), border_radius=3)
            pygame.draw.rect(surface, col_p2, (sx-3, gy-16, w+6, 16), border_radius=3)
            pygame.draw.rect(surface, (80,180,100),(sx+4,0,6,gy-16))
            # Bawah
            pygame.draw.rect(surface, col_p,  (sx, gy+gh, w, SCREEN_H-(gy+gh)), border_radius=3)
            pygame.draw.rect(surface, col_p2, (sx-3, gy+gh, w+6, 16), border_radius=3)
            pygame.draw.rect(surface, (80,180,100),(sx+4, gy+gh+16, 6, SCREEN_H-(gy+gh+16)))
            # Glow celah
            gl = pygame.Surface((w+20, 8), pygame.SRCALPHA)
            pygame.draw.rect(gl,(100,255,150,int(25+15*math.sin(t*0.005))),(0,0,w+20,8))
            surface.blit(gl,(sx-10, gy-4))
            surface.blit(gl,(sx-10, gy+gh-4))

        # Rintangan bergerak (asteroid)
        for mo in self.mov_obs:
            sx2,sy2 = cam.apply(mo["wx"], mo["wy"])
            if not (-50 < sx2 < SCREEN_W+50): continue
            sz = mo["size"]
            # Gambar asteroid
            pygame.draw.circle(surface,(80,70,60),(int(sx2),int(sy2)),sz)
            pygame.draw.circle(surface,(100,90,80),(int(sx2)-sz//4,int(sy2)-sz//4),sz//3)
            pygame.draw.circle(surface,(60,55,50),(int(sx2)+sz//3,int(sy2)+sz//3),sz//4)
            pygame.draw.circle(surface,(120,110,100),(int(sx2),int(sy2)),sz,1)

        # Drones
        for d in self.drones:
            d.draw(surface, cam)

    def get_collision_rects(self):
        """Return semua rect rintangan (pipa + asteroid)"""
        rects = []
        # Pipa
        for obs in self.obstacles:
            w=obs["w"]; gy=obs["gap_y"]; gh=obs["gap_h"]
            rects.append(("pipe", pygame.Rect(obs["wx"],0,w,gy)))
            rects.append(("pipe", pygame.Rect(obs["wx"],gy+gh,w,SCREEN_H)))
        # Asteroid
        for mo in self.mov_obs:
            sz=mo["size"]
            rects.append(("asteroid", pygame.Rect(mo["wx"]-sz,mo["wy"]-sz,sz*2,sz*2)))
        return rects
# ══════════════════════════════════════════════
# CHEST
# ══════════════════════════════════════════════
class Chest:
    SIZE = 22
    def __init__(self, wx, wy, chest_type="common"):
        self.wx=float(wx); self.wy=float(wy)
        self.type=chest_type; self.alive=True; self.anim_t=0
        if chest_type=="common":
            self.content=random.choice(["hp","hp","ammo","ammo","plasma","shotgun"])
        elif chest_type=="rare":
            self.content=random.choice(["plasma","cryo","thunder","hp","ammo"])
        else:
            self.content=random.choice(["thunder","cryo","plasma"])

    def draw(self, surface, cam):
        sx,sy=cam.apply(self.wx,self.wy)
        if not(-30<sx<SCREEN_W+30): return
        self.anim_t+=1
        bob=int(3*math.sin(self.anim_t*0.06))
        ix,iy=int(sx),int(sy)+bob; s=self.SIZE
        if self.type=="common": col,col2=(180,130,40),(220,170,60)
        elif self.type=="rare": col,col2=(60,80,200),(100,130,255)
        else: col,col2=(180,30,30),(255,80,80)
        pygame.draw.rect(surface,col,(ix,iy,s,s),border_radius=4)
        pygame.draw.rect(surface,col2,(ix,iy,s,8),border_radius=4)
        pygame.draw.rect(surface,(255,220,80),(ix+s//2-3,iy+s//2-4,6,8),border_radius=2)
        glow=pygame.Surface((s+12,s+12),pygame.SRCALPHA)
        pygame.draw.rect(glow,(*col2,int(40+30*math.sin(self.anim_t*0.08))),(0,0,s+12,s+12),border_radius=6)
        surface.blit(glow,(ix-6,iy-6))
        pygame.draw.rect(surface,col2,(ix,iy,s,s),border_radius=4,width=1)

    def get_rect(self):
        return pygame.Rect(self.wx,self.wy,self.SIZE,self.SIZE)

# ══════════════════════════════════════════════
# MOVING PLATFORM
# ══════════════════════════════════════════════
class MovingPlatform:
    def __init__(self, x, y, w, move_range=80, speed=1.2, vertical=False):
        self.rect=pygame.Rect(x,y,w,16)
        self.ox=float(x); self.oy=float(y)
        self.move_range=move_range; self.speed=speed
        self.vertical=vertical; self.t=random.uniform(0,math.pi*2)

    def update(self):
        self.t+=0.02*self.speed
        if self.vertical: self.rect.y=int(self.oy+math.sin(self.t)*self.move_range)
        else: self.rect.x=int(self.ox+math.sin(self.t)*self.move_range)

    def draw(self, surface, cam):
        sr=cam.apply_rect(self.rect)
        if not(-10<sr.x<SCREEN_W+10): return
        pygame.draw.rect(surface,(30,80,80),sr,border_radius=4)
        pygame.draw.rect(surface,(50,160,150),(sr.x,sr.y,sr.w,3),border_radius=2)
        pygame.draw.rect(surface,(50,160,150),sr,border_radius=4,width=1)
        arrow_col=(80,200,180)
        if self.vertical:
            pygame.draw.polygon(surface,arrow_col,[(sr.x+sr.w//2,sr.y-6),(sr.x+sr.w//2-5,sr.y),(sr.x+sr.w//2+5,sr.y)])
        else:
            pygame.draw.polygon(surface,arrow_col,[(sr.x+sr.w+4,sr.y+8),(sr.x+sr.w,sr.y+4),(sr.x+sr.w,sr.y+12)])

# ══════════════════════════════════════════════
# SPIKE TRAP
# ══════════════════════════════════════════════
class SpikeTrap:
    def __init__(self, x, y, count=4):
        self.x=x; self.y=y; self.count=count; self.w=count*14

    def draw(self, surface, cam):
        sx,sy=cam.apply(self.x,self.y)
        if not(-50<sx<SCREEN_W+50): return
        for i in range(self.count):
            px=int(sx)+i*14
            pygame.draw.polygon(surface,(180,40,40),[(px+1,int(sy)+12),(px+7,int(sy)-4),(px+13,int(sy)+12)])
            pygame.draw.polygon(surface,(220,80,80),[(px+3,int(sy)+12),(px+7,int(sy)-2),(px+11,int(sy)+12)])
        pygame.draw.rect(surface,(120,20,20),(int(sx),int(sy)+12,self.w,4))

    def get_rect(self):
        return pygame.Rect(self.x+2,self.y-4,self.w-4,16)

# ══════════════════════════════════════════════
# TUNNEL SEGMENT
# ══════════════════════════════════════════════
class TunnelSegment:
    def __init__(self, x, width, gap_y, gap_h=120):
        self.x=x; self.width=width; self.gap_y=gap_y; self.gap_h=gap_h
        self.top_rect=pygame.Rect(x,0,width,gap_y)
        self.bot_rect=pygame.Rect(x,gap_y+gap_h,width,SCREEN_H-(gap_y+gap_h)+80)

    def draw(self, surface, cam):
        sr_top=cam.apply_rect(self.top_rect); sr_bot=cam.apply_rect(self.bot_rect)
        if not(-self.width<sr_top.x<SCREEN_W+self.width): return
        col_wall=(25,25,45); col_edge=(60,60,100); col_light=(40,80,120)
        pygame.draw.rect(surface,col_wall,sr_top); pygame.draw.rect(surface,col_wall,sr_bot)
        for i in range(0,max(1,self.top_rect.h),20):
            pygame.draw.line(surface,col_edge,(sr_top.x,sr_top.y+i),(sr_top.x+sr_top.w,sr_top.y+i),1)
        for i in range(6):
            sx2=sr_top.x+i*max(1,sr_top.w//6)
            pygame.draw.line(surface,col_edge,(sx2,sr_top.y),(sx2,sr_top.y+sr_top.h),1)
        pygame.draw.rect(surface,col_light,(sr_top.x,sr_top.y+max(0,sr_top.h-4),sr_top.w,4))
        pygame.draw.rect(surface,col_light,(sr_bot.x,sr_bot.y,sr_bot.w,4))
        glow=pygame.Surface((max(1,sr_top.w),8),pygame.SRCALPHA)
        pygame.draw.rect(glow,(60,120,200,30),(0,0,max(1,sr_top.w),8))
        surface.blit(glow,(sr_top.x,sr_top.y+max(0,sr_top.h-4)))

    def get_top_rect(self): return self.top_rect
    def get_bot_rect(self): return self.bot_rect

# ══════════════════════════════════════════════
# CAMERA
# ══════════════════════════════════════════════
class Camera:
    def __init__(self):
        self.x=0.0

    def update(self, target_x):
        target_cam=target_x-SCREEN_W//3
        self.x+=(target_cam-self.x)*0.1
        self.x=max(0,min(WORLD_W-SCREEN_W,self.x))

    def apply(self, wx, wy): return wx-self.x, wy
    def apply_rect(self, rect): return pygame.Rect(rect.x-self.x,rect.y,rect.w,rect.h)

# ══════════════════════════════════════════════
# STAR FIELD
# ══════════════════════════════════════════════
class StarField:
    def __init__(self):
        self.layers=[]
        for speed,count,size,bright in[(0.05,80,1,50),(0.15,50,1,100),(0.3,30,2,180)]:
            self.layers.append([
                [random.randint(0,10000),random.randint(0,SCREEN_H-60),speed,size,bright]
                for _ in range(count)
            ])

    def draw(self, surface, cam_x):
        for layer in self.layers:
            for s in layer:
                sx=int(s[0]-cam_x*s[2])%SCREEN_W
                b=s[4]; tw=int(b*(0.8+0.2*math.sin(pygame.time.get_ticks()*0.002+s[1])))
                pygame.draw.rect(surface,(tw,tw,min(255,tw+30)),(sx,int(s[1]),s[3],s[3]))

# ══════════════════════════════════════════════
# SCROLLING BG
# ══════════════════════════════════════════════
def draw_scrolling_bg(surface, cam_x, level_num):
    sky_colors=[(15,15,35),(10,10,30),(8,8,28),(12,8,25),(20,8,20),(8,8,20),(5,10,25),(15,5,25),(10,5,15),(5,5,10)]
    sky=sky_colors[min(level_num-1,9)]; surface.fill(sky)
    t=pygame.time.get_ticks()
    bld_x=-int(cam_x*0.08)%(SCREEN_W+200)-200
    col1=tuple(max(0,c-5) for c in sky)
    for i in range(12):
        bx=bld_x+i*120+(i*37)%80; bh2=80+(i*53)%120
        pygame.draw.rect(surface,col1,(bx,SCREEN_H-bh2,50+(i*17)%40,bh2))
        if(t//1000+i)%4!=0: pygame.draw.rect(surface,(30,60,90),(bx+8,SCREEN_H-bh2+15,5,3))
    bld_x2=-int(cam_x*0.18)%(SCREEN_W+200)-200
    col2=tuple(max(0,c+3) for c in sky)
    for i in range(8):
        bx=bld_x2+i*160+(i*53)%100; bh3=60+(i*41)%100
        pygame.draw.rect(surface,col2,(bx,SCREEN_H-bh3,60+(i*23)%50,bh3))
    pygame.draw.line(surface,tuple(min(255,c+15) for c in sky),(0,SCREEN_H-45),(SCREEN_W,SCREEN_H-45),1)

# ══════════════════════════════════════════════
# DRAW HELPERS
# ══════════════════════════════════════════════
def draw_g7(surface, x, y, fly_mode=False):
    if fly_mode:
        # ── SPACESHIP MODE ─────────────────────
        t2 = pygame.time.get_ticks()
        # Badan pesawat utama
        pygame.draw.polygon(surface, (60,180,220), [
            (x+16, y),       # hidung depan
            (x+32, y+14),    # kanan tengah
            (x+28, y+28),    # kanan belakang
            (x+4,  y+28),    # kiri belakang
            (x,    y+14),    # kiri tengah
        ])
        # Garis tengah badan
        pygame.draw.polygon(surface, (100,220,255), [
            (x+16, y+2),
            (x+28, y+13),
            (x+24, y+24),
            (x+8,  y+24),
            (x+4,  y+13),
        ])
        # Sayap kiri
        wing_flap = int(5 * math.sin(t2 * 0.012))
        pygame.draw.polygon(surface, (40,140,180), [
            (x+4,  y+14),
            (x-20, y+22+wing_flap),
            (x-8,  y+28),
            (x+8,  y+22),
        ])
        # Sayap kanan
        pygame.draw.polygon(surface, (40,140,180), [
            (x+28, y+14),
            (x+52, y+22+wing_flap),
            (x+40, y+28),
            (x+24, y+22),
        ])
        # Cockpit (kaca)
        pygame.draw.ellipse(surface, (200,240,255), (x+11, y+6, 10, 10))
        pygame.draw.ellipse(surface, BLUE,           (x+13, y+8,  6,  6))
        # Thruster kiri
        thr_alpha = int(160 + 80*math.sin(t2*0.02))
        thr = pygame.Surface((10, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(thr, (255,150,50, thr_alpha), (0,0,10,16))
        surface.blit(thr, (x,    y+26))
        surface.blit(thr, (x+22, y+26))
        # Glow thruster
        gl = pygame.Surface((30, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(gl, (255,200,80, int(80+40*math.sin(t2*0.025))), (0,0,30,8))
        surface.blit(gl, (x+1, y+34))
        # Senjata bawah pesawat
        pygame.draw.rect(surface, (80,80,100), (x+10, y+22, 12, 6), border_radius=2)
        pygame.draw.rect(surface, (120,120,150),(x+13, y+26,  6, 4), border_radius=1)
    else:
        # ── ROBOT MODE (normal) ────────────────
        pygame.draw.rect(surface,GREEN,     (x+6, y+12,20,16),border_radius=3)
        pygame.draw.rect(surface,GREEN,     (x+8, y+2, 16,12),border_radius=3)
        pygame.draw.rect(surface,WHITE,     (x+10,y+5,  5, 4),border_radius=1)
        pygame.draw.circle(surface,BLUE,   (x+12,y+7),2)
        pygame.draw.rect(surface,WHITE,    (x+17,y+5,  5, 4),border_radius=1)
        pygame.draw.circle(surface,BLUE,   (x+19,y+7),2)
        pygame.draw.rect(surface,DARK_GREEN,(x+13,y,   2, 4))
        pygame.draw.rect(surface,DARK_GREEN,(x+17,y,   2, 4))
        pygame.draw.rect(surface,DARK_GREEN,(x+8, y+27,7, 8),border_radius=2)
        pygame.draw.rect(surface,DARK_GREEN,(x+17,y+27,7, 8),border_radius=2)
        pygame.draw.rect(surface,DARK_GREEN,(x+2, y+14,5,10),border_radius=2)
        pygame.draw.rect(surface,DARK_GREEN,(x+25,y+14,5,10),border_radius=2)
        pygame.draw.rect(surface,BLUE,     (x+11,y+16,10, 6),border_radius=2)

# ══════════════════════════════════════════════
# BOSS SPRITE
# ══════════════════════════════════════════════
def draw_boss_sprite(surface,x,y,data,anim_t,phase=1):
    bw,bh=data["size"]; bc,ac,ec=data["color"],data["armor"],data["eye"]
    ability=data["ability"]; t=anim_t
    sh=pygame.Surface((bw+10,12),pygame.SRCALPHA)
    pygame.draw.ellipse(sh,(0,0,0,60),(0,0,bw+10,12)); surface.blit(sh,(x-5,y+bh-8))
    leg_count=4 if bw>=70 else 2; leg_w=bw//(leg_count+1)
    for i in range(leg_count):
        lx=x+leg_w*(i+1)-5; ly=y+bh-20; la=int(5*math.sin(t*0.08+i*1.6))
        pygame.draw.rect(surface,ac,(lx,ly+la,10,20),border_radius=3)
        pygame.draw.rect(surface,(bc[0]//2,bc[1]//2,bc[2]//2),(lx-2,ly+la+18,14,5),border_radius=2)
    pygame.draw.rect(surface,bc,(x,y+10,bw,bh-30),border_radius=8)
    pygame.draw.rect(surface,ac,(x-3,y+15,bw+6,10),border_radius=4)
    pygame.draw.rect(surface,ac,(x-3,y+bh-45,bw+6,10),border_radius=4)
    hx,hy=x+bw//2-25,y-10
    pygame.draw.rect(surface,bc,(hx,hy,50,22),border_radius=6)
    ep=int(180+75*math.sin(t*0.1))
    ecol=(min(255,ec[0]),min(255,ec[1]+ep//4),min(255,ec[2]+ep//4)) if ability=="freeze_wave" else(min(255,ep),ec[1]//2,ec[2]//2)
    pygame.draw.rect(surface,(ep//2,ep//4,ep//4),(hx+5,hy+4,14,8),border_radius=3)
    pygame.draw.rect(surface,(ep//2,ep//4,ep//4),(hx+31,hy+4,14,8),border_radius=3)
    pygame.draw.rect(surface,ecol,(hx+8,hy+6,8,4),border_radius=1)
    pygame.draw.rect(surface,ecol,(hx+34,hy+6,8,4),border_radius=1)
    pygame.draw.line(surface,ac,(hx+10,hy),(hx+5,hy-14),2)
    pygame.draw.line(surface,ac,(hx+40,hy),(hx+45,hy-14),2)
    gr=int(3+2*math.sin(t*0.08))
    pygame.draw.circle(surface,ec,(hx+5,hy-14),gr); pygame.draw.circle(surface,ec,(hx+45,hy-14),gr)
    if ability=="triple_shot":
        for ci in range(3): pygame.draw.rect(surface,ac,(x+10+ci*(bw//3),y+bh//2,18,8),border_radius=2)
    elif ability=="ground_slam":
        pygame.draw.rect(surface,ac,(x-15,y+20,16,30),border_radius=5)
        pygame.draw.rect(surface,ac,(x+bw-1,y+20,16,30),border_radius=5)
    elif ability=="burst_fire":
        pygame.draw.rect(surface,ac,(x+bw-5,y+25,25,15),border_radius=3)
    elif ability=="dive_bomb":
        wa=int(8*math.sin(t*0.06))
        pygame.draw.polygon(surface,ac,[(x-5,y+20),(x-30,y+10+wa),(x-5,y+40)])
        pygame.draw.polygon(surface,ac,[(x+bw+5,y+20),(x+bw+30,y+10+wa),(x+bw+5,y+40)])
    elif ability=="teleport":
        ps=pygame.Surface((bw,bh-30),pygame.SRCALPHA)
        pygame.draw.ellipse(ps,(*PURPLE,int(100+80*math.sin(t*0.05))),(0,0,bw,bh-30))
        surface.blit(ps,(x,y+10))
    elif ability=="dual_cannon":
        pygame.draw.rect(surface,ac,(x-8,y+20,20,12),border_radius=3)
        pygame.draw.rect(surface,ac,(x+bw-12,y+20,20,12),border_radius=3)
    elif ability=="freeze_wave":
        for fi in range(3):
            fa=pygame.Surface((bw+fi*20,bh+fi*20),pygame.SRCALPHA)
            pygame.draw.ellipse(fa,(100,200,255,max(0,30-fi*8)),(0,0,bw+fi*20,bh+fi*20))
            surface.blit(fa,(x-fi*10,y+10-fi*10))
    elif ability=="lightning":
        if t%20<10:
            for li in range(4):
                ang=t*0.3+li*90
                pygame.draw.line(surface,YELLOW,(x+bw//2,y+bh//2),(int(x+bw//2+40*math.cos(math.radians(ang))),int(y+bh//2+30*math.sin(math.radians(ang)))),2)
    elif ability in("multi_phase","ultimate"):
        for fi in range(4):
            fa=pygame.Surface((bw+fi*24,bh+fi*24),pygame.SRCALPHA)
            col=[(255,50,50),(255,150,50),(200,50,255),(50,200,255)][fi]
            pygame.draw.ellipse(fa,(*col,int(20+10*math.sin(t*0.05+fi))),(0,0,bw+fi*24,bh+fi*24))
            surface.blit(fa,(x-fi*12,y+10-fi*12))
        if ability=="ultimate" and t%60<15:
            pygame.draw.line(surface,CYAN,(hx+12,hy+8),(0,hy+8),2)
            pygame.draw.line(surface,CYAN,(hx+38,hy+8),(SCREEN_W,hy+8),2)
    if phase>=2:
        for fi in range(4):
            fx=x+8+fi*(bw//4); fy=y+8+int(5*math.sin(t*0.15+fi))
            fl=pygame.Surface((10,14),pygame.SRCALPHA)
            pygame.draw.ellipse(fl,(255,120,30,int(160*abs(math.sin(t*0.1+fi)))),(0,0,10,14))
            surface.blit(fl,(fx,fy))

# ══════════════════════════════════════════════
# BOSS CLASS
# ══════════════════════════════════════════════
class Boss:
    def __init__(self,level_num,wx):
        lvl=min(level_num,10); d=BOSS_DATA[lvl]
        self.data=d; self.level=lvl; self.name=d["name"]; self.ability=d["ability"]
        bw,bh=d["size"]; self.bw=bw; self.bh=bh
        bonus=(level_num-lvl)*15
        self.max_hp_p1=d["hp"]+bonus; self.max_hp_p2=d["hp"]//2+bonus
        self.hp=self.max_hp_p1; self.max_hp=self.max_hp_p1
        self.wx=float(wx); self.wy=float(SCREEN_H-bh-80)
        self.vx=d["speed"]*(1+level_num*0.05)
        self.phase=1; self.alive=True; self.anim_t=0; self.invincible=0
        self.shoot_timer=80; self.ability_timer=random.randint(150,240)
        self.stomp_active=False; self.stomp_wx=wx; self.stomp_frames=0
        self.spawn_timer=300; self.freeze_active=False; self.freeze_timer=0
        self.teleport_cd=0; self.lightning_bolts=[]
        self.laser_active=False; self.laser_timer=0
        self.fly_y=float(SCREEN_H-bh-80); self.fly_dir=-1
        self.arena_left=float(wx-280); self.arena_right=float(wx+280)

    def update(self,player,e_bullets,enemies_list,platforms,cam):
        self.anim_t+=1
        if self.invincible>0: self.invincible-=1
        if self.phase==1 and self.hp<=0:
            self.phase=2; self.hp=self.max_hp_p2; self.max_hp=self.max_hp_p2
            self.vx*=1.4; self.shoot_timer=20
        if self.ability=="dive_bomb":
            self.fly_y+=self.fly_dir*1.5
            if self.fly_y<60 or self.fly_y>SCREEN_H-self.bh-60: self.fly_dir*=-1
            self.wy=self.fly_y
        else: self.wy=float(SCREEN_H-self.bh-80)
        self.wx+=self.vx*(1.3 if self.phase==2 else 1.0)
        if self.wx<self.arena_left or self.wx>self.arena_right: self.vx*=-1
        if self.freeze_active:
            self.freeze_timer-=1
            if self.freeze_timer<=0: self.freeze_active=False
        self.lightning_bolts=[(b[0],b[1],b[2]-1) for b in self.lightning_bolts if b[2]>0]
        if self.laser_active:
            self.laser_timer-=1
            if self.laser_timer<=0: self.laser_active=False
        self.shoot_timer-=1
        cd=max(25,70-self.level*4) if self.phase==2 else max(35,90-self.level*4)
        if self.shoot_timer<=0: self._shoot_normal(player,e_bullets); self.shoot_timer=cd
        self.ability_timer-=1
        if self.ability_timer<=0:
            self._use_ability(player,e_bullets,enemies_list)
            self.ability_timer=max(100,220-self.level*10)
        if self.phase==2:
            self.spawn_timer-=1
            if self.spawn_timer<=0:
                enemies_list.append(ScoutBot(self.wx+random.choice([-200,200]),520,1.0+self.level*0.1,100))
                self.spawn_timer=max(180,300-self.level*15)

    def _shoot_normal(self,player,e_bullets):
        cx=self.wx+self.bw//2; cy=self.wy+self.bh//2
        dx=player.wx-cx; dy=player.wy-cy; dist=math.hypot(dx,dy) or 1
        spd=2.8+self.level*0.1
        if self.ability=="triple_shot":
            for ang in[-25,0,25]:
                rad=math.atan2(dy,dx)+math.radians(ang)
                e_bullets.append(self._mb(cx,cy,math.cos(rad)*spd,math.sin(rad)*spd))
        elif self.ability=="dual_cannon":
            for ox in[-self.bw//2-5,self.bw//2+5]:
                e_bullets.append(self._mb(cx+ox,cy,dx/dist*spd,dy/dist*spd))
        elif self.ability=="burst_fire":
            for ang in([-40,-20,0,20,40] if self.phase==2 else[-25,0,25]):
                rad=math.atan2(dy,dx)+math.radians(ang)
                e_bullets.append(self._mb(cx,cy,math.cos(rad)*spd,math.sin(rad)*spd))
        else:
            for ang in([-15,0,15] if self.phase==2 else[0]):
                rad=math.atan2(dy,dx)+math.radians(ang)
                e_bullets.append(self._mb(cx,cy,math.cos(rad)*spd,math.sin(rad)*spd))

    def _use_ability(self,player,e_bullets,enemies_list):
        cx=self.wx+self.bw//2; cy=self.wy+self.bh//2; spd=3.0+self.level*0.1
        if self.ability=="ground_slam":
            self.stomp_active=True; self.stomp_wx=cx; self.stomp_frames=50
            for ang in range(0,360,30):
                rad=math.radians(ang)
                e_bullets.append(self._mb(cx,cy,math.cos(rad)*2.5,math.sin(rad)*2.5))
        elif self.ability=="dive_bomb":
            for i in range(5): e_bullets.append(self._mb(player.wx+random.randint(-80,80),player.wy-300,0,4.0))
        elif self.ability=="teleport":
            self.teleport_cd=30; self.wx=float(self.arena_left+random.randint(50,500))
            for ang in range(0,360,45):
                rad=math.radians(ang)
                e_bullets.append(self._mb(cx,cy,math.cos(rad)*spd,math.sin(rad)*spd))
        elif self.ability=="freeze_wave":
            self.freeze_active=True; self.freeze_timer=120
            for ang in range(0,360,20):
                rad=math.radians(ang)
                b=self._mb(cx,cy,math.cos(rad)*2.0,math.sin(rad)*2.0)
                b.color=(100,200,255); b.cryo=True; e_bullets.append(b)
        elif self.ability=="lightning":
            for _ in range(6):
                lx=cx+random.randint(-300,300)
                self.lightning_bolts.append((lx,0,40))
                e_bullets.append(self._mb(lx,0,0,5.0))
        elif self.ability=="multi_phase":
            for ang in range(0,360,15):
                rad=math.radians(ang)
                e_bullets.append(self._mb(cx,cy,math.cos(rad)*spd*0.8,math.sin(rad)*spd*0.8))
        elif self.ability=="ultimate":
            self.laser_active=True; self.laser_timer=80
            for ang in range(0,360,10):
                rad=math.radians(ang)
                e_bullets.append(self._mb(cx,cy,math.cos(rad)*spd,math.sin(rad)*spd))

    def _mb(self,x,y,vx,vy):
        b=WorldBullet(x,y,vx,vy,RED); return b

    def take_hit(self,dmg=1):
        if self.invincible>0: return False
        self.hp-=dmg; self.invincible=10
        return self.hp<=0 and self.phase==2

    def draw(self,surface,cam):
        sx,sy=cam.apply(self.wx,self.wy)
        if sx<-self.bw-50 or sx>SCREEN_W+50: return
        if self.stomp_active:
            self.stomp_frames=max(0,self.stomp_frames-1)
            sw=int((50-self.stomp_frames)*5)
            ssx=cam.apply(self.stomp_wx,0)[0]
            if sw>0:
                wave=pygame.Surface((sw*2,24),pygame.SRCALPHA)
                pygame.draw.ellipse(wave,(255,150,50,max(0,self.stomp_frames*4)),(0,0,sw*2,24))
                surface.blit(wave,(ssx-sw,int(sy)+self.bh-20))
        for bwx,_,life in self.lightning_bolts:
            if life>0:
                lsx=int(cam.apply(bwx,0)[0])
                pygame.draw.line(surface,(200,200,255),(lsx,0),(lsx+random.randint(-5,5),SCREEN_H),2)
        if self.laser_active:
            ly=int(sy+self.bh//3)
            ls=pygame.Surface((SCREEN_W,8),pygame.SRCALPHA)
            pygame.draw.rect(ls,(100,240,255,180),(0,0,SCREEN_W,8))
            pygame.draw.rect(ls,(200,255,255,220),(0,3,SCREEN_W,2))
            surface.blit(ls,(0,ly))
        if self.teleport_cd>0:
            self.teleport_cd-=1
            fl=pygame.Surface((self.bw,self.bh),pygame.SRCALPHA)
            pygame.draw.rect(fl,(*PURPLE,min(200,self.teleport_cd*8)),(0,0,self.bw,self.bh),border_radius=6)
            surface.blit(fl,(int(sx),int(sy)))
        draw_boss_sprite(surface,int(sx),int(sy),self.data,self.anim_t,self.phase)
        if self.invincible>0 and self.invincible%3==0:
            fl=pygame.Surface((self.bw,self.bh),pygame.SRCALPHA)
            pygame.draw.rect(fl,(255,255,255,80),(0,0,self.bw,self.bh),border_radius=6)
            surface.blit(fl,(int(sx),int(sy)))

    def draw_hud(self,surface,font_md,font_sm,font_xs):
        bw2=320; bx=SCREEN_W//2-bw2//2; by=62
        col=ORANGE if self.phase==2 else RED
        lbl=font_sm.render(f"{self.name}  [{'⚡ FASE 2' if self.phase==2 else 'FASE 1'}]  — {self.data['desc']}",True,col)
        surface.blit(lbl,(SCREEN_W//2-lbl.get_width()//2,by))
        pygame.draw.rect(surface,(60,15,15),(bx,by+16,bw2,14),border_radius=6)
        fill=int(bw2*max(0,self.hp)/self.max_hp)
        if fill>0: pygame.draw.rect(surface,col,(bx,by+16,fill,14),border_radius=6)
        pygame.draw.rect(surface,(120,40,40),(bx,by+16,bw2,14),border_radius=6,width=1)
        hp_n=font_xs.render(f"{max(0,self.hp)}/{self.max_hp}",True,WHITE)
        surface.blit(hp_n,(SCREEN_W//2-hp_n.get_width()//2,by+17))

    def get_rect(self):
        return pygame.Rect(self.wx+5,self.wy,self.bw-10,self.bh-15)

# ══════════════════════════════════════════════
# WORLD BULLET
# ══════════════════════════════════════════════
class WorldBullet:
    def __init__(self,wx,wy,vx,vy,color=RED):
        self.wx,self.wy=float(wx),float(wy)
        self.vx,self.vy=vx,vy; self.alive=True
        self.color=color; self.damage=1; self.cryo=False

    def update(self):
        self.wx+=self.vx; self.wy+=self.vy
        if not(-100<self.wx<WORLD_W+100 and -100<self.wy<SCREEN_H+100): self.alive=False

    def draw(self,surface,cam):
        sx,sy=cam.apply(self.wx,self.wy)
        if not(-10<sx<SCREEN_W+10): return
        glow=pygame.Surface((12,12),pygame.SRCALPHA)
        pygame.draw.circle(glow,(*self.color,60),(6,6),6)
        surface.blit(glow,(int(sx)-6,int(sy)-6))
        pygame.draw.circle(surface,self.color,(int(sx),int(sy)),4)
        pygame.draw.circle(surface,WHITE,(int(sx),int(sy)),2)

    def get_rect(self):
        return pygame.Rect(self.wx-4,self.wy-4,8,8)

# ══════════════════════════════════════════════
# SCOUT BOT
# ══════════════════════════════════════════════
class ScoutBot:
    WIDTH=28; HEIGHT=28; DETECT=250; JUMP_POWER=-12

    def __init__(self,wx,wy,speed_mult=1.0,shoot_cd=150):
        self.wx,self.wy=float(wx),float(wy); self.vx=self.vy=0.0
        self.hp=1; self.speed=1.6*speed_mult; self.shoot_cd=shoot_cd
        self.shoot_timer=random.randint(60,shoot_cd); self.alive=True
        self.state="patrol"; self.patrol_dir=1; self.patrol_timer=0
        self.on_ground=False; self.speed_mult=speed_mult
        self.jump_timer=0; self.jump_cd=40

    def _find_plat_above(self,platforms):
        best=None; bd=float('inf')
        for p in platforms:
            if p.top<self.wy-20:
                dx=abs((p.left+p.right)//2-(self.wx+self.WIDTH//2))
                dy=self.wy-p.top
                if dx<p.width*0.8 and dy<200 and dy<bd: bd=dy; best=p
        return best

    def _blocked(self,platforms):
        cx=self.wx+self.WIDTH+4 if self.vx>0 else self.wx-4
        if any(pygame.Rect(cx,self.wy,4,self.HEIGHT).colliderect(p) for p in platforms): return True
        if self.on_ground:
            fx=self.wx+self.WIDTH+4 if self.vx>0 else self.wx-4
            if not any(pygame.Rect(fx,self.wy+self.HEIGHT+2,4,4).colliderect(p) for p in platforms): return True
        return False

    def update(self,player,platforms,bullets):
        dx=player.wx-self.wx; dy=player.wy-self.wy; dist=math.hypot(dx,dy)
        self.state="chase" if dist<self.DETECT else "patrol"
        if self.state=="patrol":
            self.patrol_timer+=1
            if self.patrol_timer>90: self.patrol_dir*=-1; self.patrol_timer=0
            self.vx=self.patrol_dir*1.0
        else:
            self.vx=self.speed if dx>0 else -self.speed
            self.jump_timer=max(0,self.jump_timer-1)
            if self.on_ground and self.jump_timer==0:
                if player.wy<self.wy-40 and self._find_plat_above(platforms):
                    self.vy=self.JUMP_POWER; self.on_ground=False; self.jump_timer=self.jump_cd
                elif self._blocked(platforms):
                    self.vy=self.JUMP_POWER-2; self.on_ground=False; self.jump_timer=self.jump_cd
            self.shoot_timer-=1
            if self.shoot_timer<=0:
                d2=dist or 1
                bullets.append(WorldBullet(self.wx+self.WIDTH//2,self.wy+self.HEIGHT//2,dx/d2*2.5,dy/d2*2.5,RED))
                self.shoot_timer=self.shoot_cd
        self.vy+=0.6
        if self.vy>18: self.vy=18
        self.wx+=self.vx; self.wy+=self.vy
        self.wx=max(0,min(WORLD_W-self.WIDTH,self.wx))
        self.on_ground=False
        er=pygame.Rect(self.wx,self.wy,self.WIDTH,self.HEIGHT)
        for plat in platforms:
            if er.colliderect(plat) and self.vy>=0:
                if self.wy+self.HEIGHT-self.vy<=plat.top+8:
                    self.wy=plat.top-self.HEIGHT; self.vy=0; self.on_ground=True
        if self.wy>SCREEN_H+50: self.alive=False

    def draw(self,surface,cam):
        sx,sy=cam.apply(self.wx,self.wy)
        if not(-30<sx<SCREEN_W+30): return
        col=(55,138,221) if self.speed_mult<1.5 else(221,100,55)
        ix,iy=int(sx),int(sy)
        pygame.draw.rect(surface,col,(ix+4,iy+6,20,16),border_radius=3)
        pygame.draw.rect(surface,(24,90,160),(ix+7,iy+10,5,4),border_radius=1)
        pygame.draw.rect(surface,(24,90,160),(ix+16,iy+10,5,4),border_radius=1)
        pygame.draw.circle(surface,RED,(ix+9,iy+12),2)
        pygame.draw.circle(surface,RED,(ix+18,iy+12),2)
        pygame.draw.rect(surface,(24,90,160),(ix,iy+8,6,8),border_radius=2)
        pygame.draw.rect(surface,(24,90,160),(ix+22,iy+8,6,8),border_radius=2)
        pygame.draw.rect(surface,(24,90,160),(ix+7,iy+21,5,7),border_radius=2)
        pygame.draw.rect(surface,(24,90,160),(ix+16,iy+21,5,7),border_radius=2)
        bw2=self.WIDTH
        pygame.draw.rect(surface,(80,20,20),(ix,iy-8,bw2,4),border_radius=2)
        pygame.draw.rect(surface,RED,(ix,iy-8,int(bw2*self.hp),4),border_radius=2)
        pygame.draw.circle(surface,ORANGE if self.state=="chase" else GRAY,(ix+self.WIDTH//2,iy-14),3)

    def get_rect(self):
        return pygame.Rect(self.wx+2,self.wy+2,self.WIDTH-4,self.HEIGHT-4)

# ══════════════════════════════════════════════
# PIXEL PARTIKEL
# ══════════════════════════════════════════════
class Pixel:
    def __init__(self,wx,wy,color):
        self.wx,self.wy=float(wx),float(wy)
        self.vx=random.uniform(-3,3); self.vy=random.uniform(-5,0)
        self.color=color; self.life=1.0

    def update(self):
        self.vy+=0.2; self.wx+=self.vx; self.wy+=self.vy; self.life-=0.03

    def draw(self,surface,cam):
        if self.life<=0: return
        sx,sy=cam.apply(self.wx,self.wy)
        s=pygame.Surface((4,4),pygame.SRCALPHA)
        s.fill((*self.color,int(self.life*255)))
        surface.blit(s,(int(sx),int(sy)))

def spawn_pixels(wx,wy,color,n=18):
    for _ in range(n):
        pixels.append(Pixel(wx+random.randint(0,28),wy+random.randint(0,28),color))

# ══════════════════════════════════════════════
# PLAYER
# ══════════════════════════════════════════════
class Player:
    WIDTH=32; HEIGHT=36; SPEED=4
    JUMP_POWER=-14; GRAVITY=0.6; GLIDE_GRAVITY=0.15
    FLY_THRUST=-5.5; FLY_GRAVITY=0.25
    SHOOT_CD=18; MAX_HP=5

    def __init__(self):
        self.wx=self.wy=0.0; self.vx=self.vy=0.0
        self.on_ground=False; self.gliding=False
        self.fly_mode=False; self.fly_thrust=False
        self.invincible=0; self.shoot_timer=0; self.facing=1
        self.hp=self.MAX_HP; self.frozen=0
        self.weapons=["laser"]; self.weapon_idx=0
        self.ammo={"laser":-1,"plasma":0,"shotgun":0,"cryo":0,"thunder":0}
        self.reset()

    def reset(self):
        self.wx,self.wy=120.0,480.0; self.vx=self.vy=0.0
        self.invincible=0; self.shoot_timer=0
        self.hp=self.MAX_HP; self.frozen=0
        self.fly_mode=False; self.fly_thrust=False
        self.weapons=["laser"]; self.weapon_idx=0
        self.ammo={"laser":-1,"plasma":0,"shotgun":0,"cryo":0,"thunder":0}

    def take_damage(self,amount=1):
        if self.invincible>0: return False
        self.hp-=amount; self.invincible=120
        spawn_pixels(int(self.wx),int(self.wy),(93,202,165),10)
        return self.hp<=0

    def handle_input(self,keys,fly_zone_active):
        if self.frozen>0:
            self.frozen-=1; self.vx=0; self.shoot_timer-=1; return

        self.fly_mode = fly_zone_active

        if self.fly_mode:
            # FLY MODE — hanya naik/turun
            self.vx = self.SPEED * 0.8  # auto scroll kanan pelan
            self.fly_thrust = (keys[pygame.K_SPACE] or keys[pygame.K_UP]
                               or keys[pygame.K_w] or keys[pygame.K_x])
        else:
            # RUN MODE
            self.vx=0
            if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self.vx=-self.SPEED; self.facing=-1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.vx= self.SPEED; self.facing= 1
            if keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]:
                if self.on_ground: self.vy=self.JUMP_POWER; self.on_ground=False
            self.gliding=((keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w])
                          and not self.on_ground and self.vy>0)
        self.shoot_timer-=1

    def shoot_toward(self,p_bullets,screen_tx,screen_ty,cam):
        if self.frozen>0: return
        if self.shoot_timer<=0:
            w_key=self.weapons[self.weapon_idx]; w=WEAPONS[w_key]
            if w["ammo"]>0 and self.ammo[w_key]<=0:
                self.weapon_idx=0; w_key="laser"; w=WEAPONS["laser"]
            bwx=self.wx+self.WIDTH//2; bwy=self.wy+self.HEIGHT//2
            wtx=screen_tx+cam.x; wty=screen_ty
            d=math.hypot(wtx-bwx,wty-bwy) or 1
            if w_key=="shotgun":
                for i in range(-2,3):
                    spread=math.atan2(wty-bwy,wtx-bwx)+math.radians(i*8)
                    b=WorldBullet(bwx,bwy,math.cos(spread)*w["speed"],math.sin(spread)*w["speed"],w["color"])
                    b.damage=w["damage"]; p_bullets.append(b)
            else:
                b=WorldBullet(bwx,bwy,(wtx-bwx)/d*w["speed"],(wty-bwy)/d*w["speed"],w["color"])
                b.damage=w["damage"]
                if w_key=="cryo": b.cryo=True
                p_bullets.append(b)
            if self.ammo[w_key]>0: self.ammo[w_key]-=1
            self.shoot_timer=max(8,self.SHOOT_CD-(w["speed"]//3))
            self.facing=-1 if wtx<self.wx else 1

    def switch_weapon(self,direction=1):
        if len(self.weapons)>1:
            self.weapon_idx=(self.weapon_idx+direction)%len(self.weapons)

    def pick_up_weapon(self,w_key):
        if w_key not in self.weapons: self.weapons.append(w_key)
        self.ammo[w_key]=min(self.ammo[w_key]+WEAPONS[w_key]["ammo"],WEAPONS[w_key]["ammo"]*2)

    @property
    def current_weapon(self):
        return self.weapons[self.weapon_idx]

    def update(self,platforms,moving_plats,fly_zones):
        # Cek apakah player ada di fly zone
        in_fly=any(fz.contains(self.wx+self.WIDTH//2) for fz in fly_zones)
        self.fly_mode=in_fly

        if self.fly_mode:
            # Fly physics
            if self.fly_thrust:
                self.vy=max(self.vy+self.FLY_THRUST, -8)
            else:
                self.vy+=self.FLY_GRAVITY
            self.vy=max(-8, min(6, self.vy))
            self.wx+=self.vx
            self.wy+=self.vy
            # Batas atas bawah layar
            if self.wy<10: self.wy=10; self.vy=0
            if self.wy>SCREEN_H-50: self.wy=SCREEN_H-50; self.vy=0
        else:
            # Run physics
            self.vy+=self.GLIDE_GRAVITY if self.gliding else self.GRAVITY
            if self.vy>18: self.vy=18
            self.wx+=self.vx; self.wy+=self.vy
            self.wx=max(0,min(WORLD_W-self.WIDTH,self.wx))
            self.on_ground=False
            pr=pygame.Rect(self.wx,self.wy,self.WIDTH,self.HEIGHT)
            for plat in platforms:
                if pr.colliderect(plat) and self.vy>=0:
                    if self.wy+self.HEIGHT-self.vy<=plat.top+5:
                        self.wy=plat.top-self.HEIGHT; self.vy=0; self.on_ground=True
            for mp in moving_plats:
                if pr.colliderect(mp.rect) and self.vy>=0:
                    if self.wy+self.HEIGHT-self.vy<=mp.rect.top+8:
                        self.wy=mp.rect.top-self.HEIGHT; self.vy=0; self.on_ground=True
                        if not mp.vertical:
                            self.wx+=math.cos(mp.t)*mp.speed*mp.move_range*0.02
            if self.wy>SCREEN_H+50: self.wx,self.wy=120.0,480.0; self.vy=0

        self.wx=max(0,min(WORLD_W-self.WIDTH,self.wx))
        if self.invincible>0: self.invincible-=1

    def draw(self,surface,cam):
        sx,sy=cam.apply(self.wx,self.wy)
        if self.fly_mode:
            # Trail terbang
            for i in range(1,6):
                a=pygame.Surface((self.WIDTH,self.HEIGHT),pygame.SRCALPHA)
                pygame.draw.rect(a,(93,202,165,50-i*8),(0,0,self.WIDTH,self.HEIGHT),border_radius=4)
                surface.blit(a,(sx-i*4,sy+i*2))
        elif self.gliding:
            for i in range(1,5):
                a=pygame.Surface((self.WIDTH,self.HEIGHT),pygame.SRCALPHA)
                pygame.draw.rect(a,(93,202,165,60-i*12),(0,0,self.WIDTH,self.HEIGHT),border_radius=4)
                surface.blit(a,(sx-self.vx*i*1.5,sy))
        show=self.invincible==0 or(self.invincible//4)%2==0
        if show:
            draw_g7(surface,int(sx),int(sy),self.fly_mode)
            draw_hp_bar(surface,int(sx)-4,int(sy)-12,self.hp,self.MAX_HP,w=40)
        if self.frozen>0 and show:
            fl=pygame.Surface((self.WIDTH,self.HEIGHT),pygame.SRCALPHA)
            pygame.draw.rect(fl,(100,200,255,120),(0,0,self.WIDTH,self.HEIGHT),border_radius=4)
            surface.blit(fl,(int(sx),int(sy)))
        if self.fly_mode and show:
            # Thruster spark
            spark=pygame.Surface((8,16),pygame.SRCALPHA)
            pygame.draw.ellipse(spark,(255,180,50,int(150+100*math.sin(pygame.time.get_ticks()*0.03))),(0,0,8,16))
            surface.blit(spark,(int(sx)+12,int(sy)+32))

    def get_rect(self):
        return pygame.Rect(self.wx+4,self.wy+4,self.WIDTH-8,self.HEIGHT-4)

# ══════════════════════════════════════════════
# PCG WORLD GENERATION
# ══════════════════════════════════════════════
def generate_world(level_num):
    global WORLD_W
    WORLD_W=BASE_WORLD_W+level_num*800
    boss_x=WORLD_W-350
    rng=random.Random(level_num*1337+42)
    rng2=random.Random(level_num*999+7)

    platforms=[pygame.Rect(0,560,WORLD_W,40)]
    moving_plats=[]; spike_traps=[]; tunnels=[]; chests=[]; enemies_list=[]; fly_zones=[]

    # Zona 1: start
    for i in range(3):
        w=rng.randint(140,240); x=180+i*180; y=rng.randint(400,500)
        platforms.append(pygame.Rect(x,y,w,16))

    # Zona 2: main journey
    zone2_end=WORLD_W-700; x_cursor=600
    section_w=400+level_num*20
    fly_zone_count=0
    max_fly_zones=1+level_num//2  # makin banyak fly zone tiap level

    while x_cursor<zone2_end:
        section_type=rng.randint(0,5)

        # FLY ZONE — tipe baru!
        if section_type==5 and fly_zone_count<max_fly_zones and x_cursor+600<zone2_end:
            fz_width=rng.randint(900+level_num*120, 1400+level_num*150)
            fly_zones.append(FlyZone(x_cursor, fz_width, level_num))
            fly_zone_count+=1
            x_cursor+=fz_width+200  # gap setelah fly zone
            # Chest setelah fly zone sebagai reward
            chests.append(Chest(x_cursor-100, 510, "rare"))
            continue

        if section_type==0:
            for i in range(rng.randint(3,5+level_num//2)):
                w=rng.randint(100,200); x=x_cursor+rng.randint(0,200); y=rng.randint(200,510)
                if x+w<zone2_end: platforms.append(pygame.Rect(x,y,w,16))
                x_cursor=x+w+rng.randint(20,80)
                if x_cursor>=zone2_end: break

        elif section_type==1:
            for i in range(rng.randint(2,3+level_num//3)):
                w=rng.randint(80,140); x=x_cursor+i*200+rng.randint(-40,40); y=rng.randint(280,460)
                if x+w<zone2_end:
                    vert=rng.random()<0.4
                    spd=0.8+level_num*0.1+rng.uniform(0,0.5)
                    rng_=rng.randint(40,90+level_num*5)
                    moving_plats.append(MovingPlatform(x,y,w,rng_,spd,vert))
            x_cursor+=section_w

        elif section_type==2:
            tunnel_w=rng.randint(300+level_num*30,500+level_num*50)
            gap_y=rng.randint(160,280); gap_h=max(90,160-level_num*8)
            if x_cursor+tunnel_w<zone2_end:
                tunnels.append(TunnelSegment(x_cursor,tunnel_w,gap_y,gap_h))
                if level_num>=2:
                    for sx2 in range(x_cursor+40,x_cursor+tunnel_w-40,rng.randint(60,120)):
                        spike_traps.append(SpikeTrap(sx2,gap_y+gap_h-16,rng.randint(2,4)))
            x_cursor+=tunnel_w+100

        elif section_type==3:
            for i in range(rng.randint(2,4)):
                w=rng.randint(120,200); x=x_cursor+i*180+rng.randint(-30,30); y=rng.randint(300,480)
                if x+w<zone2_end:
                    platforms.append(pygame.Rect(x,y,w,16))
                    if rng.random()<0.5+level_num*0.05:
                        sc=rng.randint(2,min(5,w//16))
                        spike_traps.append(SpikeTrap(x+rng.randint(10,30),y-16,sc))
            x_cursor+=section_w

        else:
            for i in range(rng.randint(2,4)):
                w=rng.randint(100,180); x=x_cursor+rng.randint(50,180); y=rng.randint(250,500)
                if x+w<zone2_end: platforms.append(pygame.Rect(x,y,w,16))
                x_cursor=x+w+rng.randint(40,100)
                if x_cursor>=zone2_end: break

        # Enemy spawn
        if rng.random()<0.6+level_num*0.05:
            ex=max(650,rng.randint(int(x_cursor-section_w),int(min(x_cursor,zone2_end-100))))
            enemies_list.append(ScoutBot(ex,520,1.0+level_num*0.08,max(80,140-level_num*6)))

        # Chest
        if rng.random()<0.35:
            cx2=max(650,rng.randint(int(x_cursor-section_w),int(min(x_cursor,zone2_end-100))))
            chests.append(Chest(cx2,510,"common"))

        x_cursor+=rng.randint(50,150)

    # Rare chest tengah
    chests.append(Chest(WORLD_W//2+rng2.randint(-200,200),510,"rare"))

    # Minimal enemy
    num_min=3+level_num*2
    while len(enemies_list)<num_min:
        enemies_list.append(ScoutBot(rng.randint(700,int(zone2_end)),520,
                                      1.0+level_num*0.08,max(80,140-level_num*6)))

    # Boss arena
    arena_x=boss_x-300
    platforms.append(pygame.Rect(arena_x,420,220,16))
    platforms.append(pygame.Rect(arena_x+280,420,220,16))
    platforms.append(pygame.Rect(arena_x+100,310,300,16))
    platforms.append(pygame.Rect(arena_x+50,220,160,16))
    platforms.append(pygame.Rect(arena_x+320,220,160,16))

    return platforms,enemies_list,boss_x,chests,moving_plats,spike_traps,tunnels,fly_zones

# ══════════════════════════════════════════════
# MENU BUTTON
# ══════════════════════════════════════════════
class MenuButton:
    def __init__(self,x,y,w,h,text,color=None):
        self.rect=pygame.Rect(x,y,w,h); self.text=text
        self.color=color or CYAN; self.hovered=False; self.anim=0.0

    def update(self,mx,my):
        self.hovered=self.rect.collidepoint(mx,my)
        self.anim=min(1.0,self.anim+0.1) if self.hovered else max(0.0,self.anim-0.08)

    def draw(self,surface,font):
        gs=int(self.anim*6)
        if gs>0:
            gr=self.rect.inflate(gs*2,gs*2)
            gsurf=pygame.Surface((gr.w,gr.h),pygame.SRCALPHA)
            pygame.draw.rect(gsurf,(*self.color,int(self.anim*60)),(0,0,gr.w,gr.h),border_radius=8)
            surface.blit(gsurf,(gr.x,gr.y))
        bs=pygame.Surface((self.rect.w,self.rect.h),pygame.SRCALPHA)
        pygame.draw.rect(bs,(*self.color,int(self.anim*40)),(0,0,self.rect.w,self.rect.h),border_radius=6)
        surface.blit(bs,self.rect.topleft)
        bc=tuple(min(255,int(c*(0.6+0.4*self.anim)))for c in self.color)
        pygame.draw.rect(surface,bc,self.rect,border_radius=6,width=2)
        lbl=font.render(self.text,True,tuple(min(255,int(c*(0.7+0.3*self.anim)))for c in self.color))
        surface.blit(lbl,(self.rect.centerx-lbl.get_width()//2,self.rect.centery-lbl.get_height()//2))

    def is_clicked(self,event):
        return(event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and self.rect.collidepoint(event.pos))

# ══════════════════════════════════════════════
# FONTS & UI HELPERS
# ══════════════════════════════════════════════
font_xs=pygame.font.SysFont("monospace",11)
font_sm=pygame.font.SysFont("monospace",14)
font_md=pygame.font.SysFont("monospace",20)
font_lg=pygame.font.SysFont("monospace",32)
font_xl=pygame.font.SysFont("monospace",52)

def draw_glitch_text(surface, text, font, x, y, color, t):
    glitch_offset = int(3 * math.sin(t * 0.007))
    shadow = font.render(text, True, (color[0]//3, color[1]//3, color[2]//3))
    surface.blit(shadow, (x + 2, y + 2))
    if (t // 8) % 5 == 0:
        r_surf = font.render(text, True, (min(255, color[0]+80), 30, 30))
        surface.blit(r_surf, (x + glitch_offset + 2, y))
    main_surf = font.render(text, True, color)
    surface.blit(main_surf, (x, y))

def draw_hp_bar(surface, x, y, hp, max_hp, w=40):
    h = 5
    pygame.draw.rect(surface, (60, 15, 15), (x, y, w, h), border_radius=2)
    fill = int(w * max(0, hp) / max_hp)
    if fill > 0:
        ratio = hp / max_hp
        col = GREEN if ratio > 0.5 else (ORANGE if ratio > 0.25 else RED)
        pygame.draw.rect(surface, col, (x, y, fill, h), border_radius=2)
    pygame.draw.rect(surface, GRAY, (x, y, w, h), border_radius=2, width=1)

def draw_robot_head(surface, x, y, alive=True):
    col = GREEN if alive else (50, 50, 60)
    eye_col = BLUE if alive else (30, 30, 40)
    pygame.draw.rect(surface, col, (x, y, 20, 16), border_radius=3)
    pygame.draw.rect(surface, eye_col, (x+3, y+4, 5, 4), border_radius=1)
    pygame.draw.rect(surface, eye_col, (x+12, y+4, 5, 4), border_radius=1)
    if alive:
        pygame.draw.circle(surface, CYAN, (x+5, y+6), 2)
        pygame.draw.circle(surface, CYAN, (x+14, y+6), 2)

starfield=StarField()
btn_play  =MenuButton(SCREEN_W//2-100,320,200,44,"▶  PLAY",CYAN)
btn_quit  =MenuButton(SCREEN_W//2-100,380,200,44,"✕  QUIT",RED)
btn_resume=MenuButton(SCREEN_W//2-100,290,200,44,"▶  RESUME",CYAN)
btn_menu_b=MenuButton(SCREEN_W//2-100,350,200,44,"⌂  MAIN MENU",PURPLE)

def draw_progress_bar(surface,player_wx,boss_wx,font_xs,t):
    bar_x,bar_y=180,SCREEN_H-22; bar_w,bar_h=440,8
    progress=min(1.0,max(0.0,player_wx/boss_wx))
    pygame.draw.rect(surface,(20,20,40),(bar_x,bar_y,bar_w,bar_h),border_radius=4)
    if progress<0.5: fill_col=GREEN
    elif progress<0.8: fill_col=ORANGE
    else:
        pulse=int(180+75*math.sin(t*0.01)); fill_col=(pulse,30,30)
    fill_w=int(bar_w*progress)
    if fill_w>0: pygame.draw.rect(surface,fill_col,(bar_x,bar_y,fill_w,bar_h),border_radius=4)
    pygame.draw.rect(surface,GRAY,(bar_x,bar_y,bar_w,bar_h),border_radius=4,width=1)
    surface.blit(font_xs.render("START",True,(60,60,80)),(bar_x,bar_y-12))
    surface.blit(font_xs.render("BOSS",True,(100,30,30)),(bar_x+bar_w-20,bar_y-12))
    bi=font_xs.render("X",True,RED); bi.set_alpha(int(150+105*math.sin(t*0.008)))
    surface.blit(bi,(bar_x+bar_w+6,bar_y-1))
    pygame.draw.circle(surface,CYAN,(bar_x+fill_w,bar_y+bar_h//2),5)

def draw_weapon_hud(surface,player,font_xs,font_sm):
    w_key=player.current_weapon; w_data=WEAPONS[w_key]
    wx_h=SCREEN_W-162; wy_h=SCREEN_H-54
    wpanel=pygame.Surface((156,48),pygame.SRCALPHA); wpanel.fill((8,8,24,180))
    surface.blit(wpanel,(wx_h,wy_h))
    pygame.draw.rect(surface,w_data["color"],(wx_h,wy_h,156,48),border_radius=4,width=1)
    surface.blit(font_xs.render(w_data["name"],True,w_data["color"]),(wx_h+5,wy_h+4))
    ammo_val=player.ammo[w_key]
    ammo_str="∞" if ammo_val<0 else str(ammo_val)
    surface.blit(font_sm.render(f"AMMO: {ammo_str}",True,WHITE if ammo_val!=0 else RED),(wx_h+5,wy_h+18))
    for wi,wk in enumerate(player.weapons):
        dot_col=WEAPONS[wk]["color"] if wi==player.weapon_idx else GRAY
        pygame.draw.circle(surface,dot_col,(wx_h+8+wi*14,wy_h+42),4)
    surface.blit(font_xs.render("Q/Scroll=switch",True,(40,60,50)),(wx_h,wy_h+48))

def draw_fly_mode_hud(surface, font_sm, font_xs, t):
    """HUD khusus saat fly mode aktif"""
    panel=pygame.Surface((200,36),pygame.SRCALPHA)
    panel.fill((0,40,80,180))
    surface.blit(panel,(SCREEN_W//2-100,56))
    pygame.draw.rect(surface,CYAN,(SCREEN_W//2-100,56,200,36),border_radius=4,width=1)
    pulse=int(180+75*math.sin(t*0.008))
    txt=font_sm.render("✈  FLY MODE AKTIF",True,(pulse,255,200))
    surface.blit(txt,(SCREEN_W//2-txt.get_width()//2,60))
    hint=font_xs.render("SPACE/↑ = Thrust ke atas",True,(80,160,140))
    surface.blit(hint,(SCREEN_W//2-hint.get_width()//2,76))

# ══════════════════════════════════════════════
# GAME STATE
# ══════════════════════════════════════════════
scene="menu"; player=Player(); camera=Camera()
p_bullets=[]; e_bullets=[]; pixels=[]; chests=[]
score=0; lives=5; level=1; checkpoint=1
multiplier=1; mult_timer=0
boss=None; boss_spawned=False
level_clear=False; level_clear_timer=0
menu_anim=0; boss_x_world=2850
moving_plats=[]; spike_traps=[]; tunnels=[]; fly_zones=[]

platforms,enemies,boss_x_world,chests,moving_plats,spike_traps,tunnels,fly_zones=generate_world(level)

def start_game():
    global player,camera,p_bullets,e_bullets,pixels,chests,score,lives
    global level,checkpoint,multiplier,mult_timer,platforms,enemies
    global level_clear,scene,boss,boss_spawned,boss_x_world
    global moving_plats,spike_traps,tunnels,fly_zones
    player=Player(); camera=Camera()
    p_bullets=[]; e_bullets=[]; pixels=[]; chests=[]
    score=0; lives=5; level=1; checkpoint=1
    multiplier=1; mult_timer=0; level_clear=False
    boss=None; boss_spawned=False
    platforms,enemies,boss_x_world,chests,moving_plats,spike_traps,tunnels,fly_zones=generate_world(1)
    player.reset(); scene="playing"

def respawn():
    global p_bullets,e_bullets,pixels,chests,platforms,enemies
    global multiplier,mult_timer,scene,boss,boss_spawned,boss_x_world,camera
    global moving_plats,spike_traps,tunnels,fly_zones
    p_bullets=[]; e_bullets=[]; pixels=[]; chests=[]
    platforms,enemies,boss_x_world,chests,moving_plats,spike_traps,tunnels,fly_zones=generate_world(checkpoint)
    boss=None; boss_spawned=False
    camera=Camera(); player.reset(); multiplier=1; mult_timer=0; scene="playing"

# ══════════════════════════════════════════════
# MAIN LOOP
# ══════════════════════════════════════════════
running=True
while running:
    clock.tick(FPS)
    t=pygame.time.get_ticks()
    mx,my=pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type==pygame.QUIT: running=False
        if event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE:
                if scene=="playing": scene="paused"
                elif scene=="paused": scene="playing"
                else: running=False
            if event.key==pygame.K_q and scene=="playing": player.switch_weapon(1)
        if scene=="menu":
            if btn_play.is_clicked(event): start_game()
            if btn_quit.is_clicked(event): running=False
        if scene=="paused":
            if btn_resume.is_clicked(event): scene="playing"
            if btn_menu_b.is_clicked(event): scene="menu"
        if scene=="dead":
            if((event.type==pygame.KEYDOWN and event.key==pygame.K_r) or
               (event.type==pygame.MOUSEBUTTONDOWN and event.button==1)):
                if lives>0: respawn()
                else: scene="gameover"
        if scene=="gameover":
            if((event.type==pygame.KEYDOWN and event.key==pygame.K_r) or
               (event.type==pygame.MOUSEBUTTONDOWN and event.button==1)):
                scene="menu"
        if event.type==pygame.MOUSEBUTTONDOWN:
            if event.button==1 and scene=="playing" and not level_clear:
                player.shoot_toward(p_bullets,mx,my,camera)
            if event.button==4 and scene=="playing": player.switch_weapon(-1)
            if event.button==5 and scene=="playing": player.switch_weapon(1)

    if scene=="menu":
        menu_anim+=1; btn_play.update(mx,my); btn_quit.update(mx,my)
    if scene=="paused":
        btn_resume.update(mx,my); btn_menu_b.update(mx,my)

    # ══════════════════════════════════════════
    # UPDATE
    # ══════════════════════════════════════════
    if scene=="playing" and not level_clear:
        keys=pygame.key.get_pressed()

        # Cek fly zone
        in_fly_zone=any(fz.contains(player.wx+player.WIDTH//2) for fz in fly_zones)

        player.handle_input(keys,in_fly_zone)
        for mp in moving_plats: mp.update()
        player.update(platforms,moving_plats,fly_zones)
        camera.update(player.wx)

        # Fly zone update & collision
        if player.fly_mode:
            pr = player.get_rect()
            for fz in fly_zones:
                if not fz.contains(player.wx + player.WIDTH//2): continue
                # Update drones & moving obstacles
                fz.update(player.wx, player.wy, e_bullets)
                # Collision pipa & asteroid
                for kind, obs_rect in fz.get_collision_rects():
                    if pr.colliderect(obs_rect) and player.invincible==0:
                        if player.take_damage(1):
                            lives-=1; scene="dead"
                        break
                # Collision drone langsung (body)
                for d in fz.drones:
                    if d.alive and pr.colliderect(d.get_rect()) and player.invincible==0:
                        if player.take_damage(1):
                            lives-=1; scene="dead"
                        break

        # Peluru player kena drone di fly zone
        for b in list(p_bullets):
            if not b.alive: continue
            for fz in fly_zones:
                result = fz.hit_bullet(b.get_rect())
                if result is not None:
                    b.alive = False
                    if result:   # drone mati
                        score += 80 * multiplier
                        mult_timer = 120; multiplier = min(5, multiplier+1)
                    break

        # Tunnel collision (run mode)
        if not player.fly_mode:
            pr=player.get_rect()
            for tun in tunnels:
                if pr.colliderect(tun.get_top_rect()):
                    player.wy=float(tun.get_top_rect().bottom); player.vy=max(0,player.vy)
                if pr.colliderect(tun.get_bot_rect()):
                    player.wy=float(tun.get_bot_rect().top-player.HEIGHT)
                    player.vy=min(0,player.vy); player.on_ground=True

        # Spike
        pr=player.get_rect()
        for sp in spike_traps:
            if player.invincible==0 and pr.colliderect(sp.get_rect()):
                if player.take_damage(1): lives-=1; scene="dead"
                break

        for b in p_bullets: b.update()
        for b in e_bullets: b.update()
        p_bullets=[b for b in p_bullets if b.alive]
        e_bullets=[b for b in e_bullets if b.alive]

        for en in enemies: en.update(player,platforms,e_bullets)
        enemies=[e for e in enemies if e.alive]

        for px in pixels: px.update()
        pixels=[px for px in pixels if px.life>0]

        # Chest pickup
        pr=player.get_rect()
        for ch in chests:
            if ch.alive and pr.colliderect(ch.get_rect()):
                ch.alive=False
                if ch.content=="hp":
                    player.hp=min(player.MAX_HP,player.hp+2)
                    spawn_pixels(ch.wx,ch.wy,(29,158,117),12)
                elif ch.content=="ammo":
                    wk=player.current_weapon
                    if player.ammo[wk]>=0: player.ammo[wk]=min(player.ammo[wk]+8,WEAPONS[wk]["ammo"]*2)
                    spawn_pixels(ch.wx,ch.wy,(239,159,39),12)
                else:
                    player.pick_up_weapon(ch.content)
                    spawn_pixels(ch.wx,ch.wy,(127,119,221),20)
        chests=[ch for ch in chests if ch.alive]

        # Spawn boss
        if not boss_spawned and len(enemies)==0 and player.wx>boss_x_world-500:
            boss_spawned=True; boss=Boss(level,boss_x_world)

        # Collision peluru G7
        for b in list(p_bullets):
            if not b.alive: continue
            br=b.get_rect(); hit=False
            for en in enemies:
                if br.colliderect(en.get_rect()):
                    b.alive=False; en.hp-=b.damage
                    spawn_pixels(en.wx,en.wy,(55,138,221),8)
                    if en.hp<=0:
                        en.alive=False; score+=100*multiplier
                        mult_timer=180; multiplier=min(5,multiplier+1)
                        if random.random()<0.3: chests.append(Chest(en.wx,en.wy,"common"))
                        spawn_pixels(en.wx,en.wy,(55,138,221),20)
                    hit=True; break
            if not hit and boss and boss.alive:
                if br.colliderect(boss.get_rect()):
                    b.alive=False
                    if boss.take_hit(b.damage):
                        boss.alive=False
                        chests.append(Chest(boss.wx+boss.bw//2,boss.wy,"boss"))
                        score+=500*level*multiplier
                        for _ in range(80):
                            spawn_pixels(boss.wx+random.randint(0,boss.bw),
                                        boss.wy+random.randint(0,boss.bh),
                                        random.choice([RED,ORANGE,YELLOW,(255,255,100)]),6)
                    else:
                        spawn_pixels(boss.wx,boss.wy,tuple(boss.data["color"]),4)

        # Boss update
        if boss and boss.alive:
            boss.update(player,e_bullets,enemies,platforms,camera)
            if boss.freeze_active:
                for b in e_bullets:
                    if b.cryo and b.get_rect().colliderect(player.get_rect()) and player.invincible==0:
                        player.frozen=120; b.alive=False; break
            if boss.laser_active:
                ly=int(boss.wy+boss.bh//3)
                if pygame.Rect(0,ly-4,WORLD_W,16).colliderect(player.get_rect()):
                    if player.take_damage(1): lives-=1; scene="dead"
            if player.invincible==0 and boss.get_rect().colliderect(player.get_rect()):
                dmg=2 if boss.phase==2 else 1
                if player.take_damage(dmg): lives-=1; scene="dead"
            if boss.stomp_active:
                sw=pygame.Rect(int(boss.stomp_wx)-140,int(boss.wy)+boss.bh-30,280,25)
                if sw.colliderect(player.get_rect()) and player.invincible==0:
                    if player.take_damage(1): lives-=1; scene="dead"

        # Peluru enemy kena player
        pr=player.get_rect()
        for b in e_bullets:
            if pr.colliderect(b.get_rect()):
                b.alive=False
                if b.cryo: player.frozen=120
                elif player.take_damage(1): lives-=1; scene="dead"
                break

        # Knockback & injak
        for en in enemies:
            if pr.colliderect(en.get_rect()):
                player.wx+=-12 if player.wx<en.wx else 12; player.vy=-5; break
        for en in enemies:
            er=en.get_rect()
            if(pr.colliderect(er) and player.vy>0 and player.wy+player.HEIGHT-player.vy<er.top+10):
                en.hp-=1; player.vy=-8
                if en.hp<=0:
                    en.alive=False; score+=150*multiplier
                    mult_timer=180; multiplier=min(5,multiplier+1)
                    if random.random()<0.3: chests.append(Chest(en.wx,en.wy,"common"))
                    spawn_pixels(en.wx,en.wy,(55,138,221),20)

        mult_timer=max(0,mult_timer-1)
        if mult_timer==0: multiplier=max(1,multiplier-1)
        score+=1

        if boss and not boss.alive and not level_clear:
            level_clear=True; level_clear_timer=160

    if level_clear:
        level_clear_timer-=1
        if level_clear_timer<=0:
            level+=1; checkpoint=level; score+=1000*level
            p_bullets=[]; e_bullets=[]; pixels=[]; boss=None; boss_spawned=False
            platforms,enemies,boss_x_world,chests,moving_plats,spike_traps,tunnels,fly_zones=generate_world(level)
            camera=Camera(); player.reset(); level_clear=False

    # ══════════════════════════════════════════
    # DRAW
    # ══════════════════════════════════════════
    if scene=="menu":
        screen.fill(DARK_BLUE)
        for bx2,bh2,bw2 in[(30,220,30),(320,180,60),(680,200,50)]:
            pygame.draw.rect(screen,(18,18,38),(bx2,SCREEN_H-bh2,bw2,bh2))
        starfield.draw(screen,0)
        grad=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA)
        for gy in range(SCREEN_H): pygame.draw.line(grad,(5,5,20,int(120*(gy/SCREEN_H))),(0,gy),(SCREEN_W,gy))
        screen.blit(grad,(0,0))
        tx2=SCREEN_W//2-font_xl.size("PIXEL GLIDE")[0]//2
        draw_glitch_text(screen,"PIXEL GLIDE",font_xl,tx2,150,CYAN,t)
        screen.blit(font_md.render("A Sci-Fi Robot Adventure",True,(80,160,140)),
                    (SCREEN_W//2-font_md.size("A Sci-Fi Robot Adventure")[0]//2,220))
        screen.blit(font_xs.render("v4.0  |  Run & Fly Mode  |  Tunnels  |  10 Bosses  |  5 Weapons",True,(40,80,70)),
                    (SCREEN_W//2-font_xs.size("v4.0  |  Run & Fly Mode  |  Tunnels  |  10 Bosses  |  5 Weapons")[0]//2,252))
        pygame.draw.line(screen,(30,80,70),(SCREEN_W//2-160,278),(SCREEN_W//2+160,278),1)
        g7y=int(420+math.sin(t*0.002)*6)
        draw_g7(screen,SCREEN_W//2-16,g7y,abs(math.sin(t*0.001))>0.5)
        thr=pygame.Surface((20,10),pygame.SRCALPHA)
        pygame.draw.ellipse(thr,(93,202,165,int(60+40*math.sin(t*0.01))),(0,0,20,10))
        screen.blit(thr,(SCREEN_W//2-10,g7y+36))
        btn_play.draw(screen,font_md); btn_quit.draw(screen,font_md)
        screen.blit(font_xs.render("Run: ← → Move  SPACE Jump/Glide  |  Fly: SPACE/↑ Thrust  |  LClick Shoot  Q Weapon",
                                    True,(40,70,60)),
                    (SCREEN_W//2-font_xs.size("Run: ← → Move  SPACE Jump/Glide  |  Fly: SPACE/↑ Thrust  |  LClick Shoot  Q Weapon")[0]//2,460))
        screen.blit(font_xs.render("© 2025 Shaniss Ambotang Avila  |  Universitas Mulia Balikpapan",True,(30,55,50)),
                    (SCREEN_W//2-font_xs.size("© 2025 Shaniss Ambotang Avila  |  Universitas Mulia Balikpapan")[0]//2,SCREEN_H-18))

    elif scene in("playing","paused"):
        draw_scrolling_bg(screen,camera.x,level)
        starfield.draw(screen,camera.x)

        # Fly zone backgrounds
        for fz in fly_zones: fz.draw_bg(screen,camera,t)

        if boss and boss.alive:
            bc2=boss.data["color"]
            arena=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA)
            pygame.draw.rect(arena,(*bc2,int(6+3*math.sin(t*0.003))),(0,0,SCREEN_W,SCREEN_H))
            screen.blit(arena,(0,0))

        # Tunnel
        for tun in tunnels: tun.draw(screen,camera)

        # Platform
        for plat in platforms:
            sr=camera.apply_rect(plat)
            if -10<sr.x<SCREEN_W+10:
                sh2=pygame.Surface((sr.w,sr.h+4),pygame.SRCALPHA)
                pygame.draw.rect(sh2,(0,0,0,60),(0,4,sr.w,sr.h),border_radius=4)
                screen.blit(sh2,(sr.x,sr.y))
                pygame.draw.rect(screen,PLATFORM_C,sr,border_radius=4)
                pygame.draw.rect(screen,(70,70,100),(sr.x,sr.y,sr.w,3),border_radius=2)

        for mp in moving_plats: mp.draw(screen,camera)
        for sp in spike_traps: sp.draw(screen,camera)

        # Fly zone obstacles (pipa)
        for fz in fly_zones: fz.draw_obstacles(screen,camera,t)

        # Boss arena sign
        if boss_spawned or player.wx>boss_x_world-600:
            sign_sx=int(camera.apply(boss_x_world-350,0)[0])
            if 0<sign_sx<SCREEN_W:
                st=font_sm.render("⚠ BOSS ARENA",True,RED)
                screen.blit(st,(sign_sx-st.get_width()//2,80))
                pygame.draw.line(screen,RED,(sign_sx,90+st.get_height()),(sign_sx,SCREEN_H-50),1)

        for px in pixels: px.draw(screen,camera)
        for ch in chests: ch.draw(screen,camera)
        for en in enemies: en.draw(screen,camera)
        for b in e_bullets: b.draw(screen,camera)

        # Player bullets
        for b in p_bullets:
            sx2,sy2=camera.apply(b.wx,b.wy)
            if -10<sx2<SCREEN_W+10:
                glow=pygame.Surface((20,10),pygame.SRCALPHA)
                pygame.draw.ellipse(glow,(*b.color,60),(0,0,20,10))
                screen.blit(glow,(int(sx2)-10,int(sy2)-5))
                pygame.draw.rect(screen,b.color,(int(sx2)-8,int(sy2)-2,16,4),border_radius=2)
                pygame.draw.rect(screen,WHITE,(int(sx2)-4,int(sy2)-1,8,2),border_radius=1)

        if boss and boss.alive: boss.draw(screen,camera)
        player.draw(screen,camera)

        if player.frozen>0:
            fov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA)
            fov.fill((80,160,220,int(30*(player.frozen/120)))); screen.blit(fov,(0,0))
            ft=font_sm.render("❄ FROZEN!",True,(150,230,255))
            screen.blit(ft,(SCREEN_W//2-ft.get_width()//2,SCREEN_H//2))

        # Crosshair
        pygame.draw.line(screen,CYAN,(mx-14,my),(mx+14,my),2)
        pygame.draw.line(screen,CYAN,(mx,my-14),(mx,my+14),2)
        pygame.draw.circle(screen,CYAN,(mx,my),8,1)

        # HUD
        hud_h=82 if(boss and boss.alive) else 56
        hud=pygame.Surface((SCREEN_W,hud_h),pygame.SRCALPHA)
        hud.fill((8,8,24,200)); screen.blit(hud,(0,0))
        pygame.draw.line(screen,(*CYAN,80),(0,hud_h),(SCREEN_W,hud_h),1)

        screen.blit(font_xs.render("LIFE",True,(80,120,100)),(12,3))
        for i in range(5): draw_robot_head(screen,12+i*26,14,alive=(i<lives))
        screen.blit(font_xs.render("HP",True,(80,120,100)),(152,3))
        draw_hp_bar(screen,172,6,player.hp,player.MAX_HP,w=80)
        screen.blit(font_xs.render(f"{player.hp}/{player.MAX_HP}",True,WHITE),(258,2))

        sc_text=font_md.render(f"SCORE  {score:06d}",True,CYAN)
        screen.blit(sc_text,(SCREEN_W//2-sc_text.get_width()//2,8))
        if multiplier>1:
            pulse=int(200+55*math.sin(t*0.01))
            mxt=font_sm.render(f"✦ x{multiplier} COMBO!",True,(255,pulse,50))
            screen.blit(mxt,(SCREEN_W//2-mxt.get_width()//2,30))

        if boss and boss.alive:
            boss.draw_hud(screen,font_md,font_sm,font_xs)
        else:
            screen.blit(font_sm.render(f"LEVEL {level}",True,PURPLE),(SCREEN_W-130,6))
            en_str="⚠ BOSS!" if boss_spawned else f"ENEMY {len(enemies)}"
            screen.blit(font_sm.render(en_str,True,RED if boss_spawned else ORANGE),(SCREEN_W-130,22))
            if checkpoint>1:
                screen.blit(font_xs.render(f"CKPT L{checkpoint}",True,GREEN),(SCREEN_W-130,40))
            else:
                mode_str="✈ FLY" if player.fly_mode else("✦ GLIDE" if player.gliding else "RUN")
                mode_col=TEAL if player.fly_mode else(CYAN if player.gliding else WHITE)
                screen.blit(font_xs.render(f"MODE:{mode_str}",True,mode_col),(SCREEN_W-130,40))

        # Fly mode HUD
        if player.fly_mode:
            draw_fly_mode_hud(screen,font_sm,font_xs,t)

        draw_progress_bar(screen,player.wx,boss_x_world,font_xs,t)
        draw_weapon_hud(screen,player,font_xs,font_sm)
        screen.blit(font_xs.render("ESC=Pause",True,(40,60,50)),(SCREEN_W-80,SCREEN_H-16))

        if level_clear:
            ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((0,0,0,150)); screen.blit(ov,(0,0))
            prog=1.0-level_clear_timer/160; bw3=int(SCREEN_W*min(1.0,prog*3))
            bs=pygame.Surface((bw3,110),pygame.SRCALPHA); bs.fill((0,40,20,210))
            screen.blit(bs,(SCREEN_W//2-bw3//2,SCREEN_H//2-55))
            if prog>0.25 and boss:
                dn=font_lg.render(f"{boss.name} DEFEATED!",True,ORANGE)
                b2=font_sm.render(f"⭐ LEVEL {level} CLEAR!  +{1000*level} BONUS",True,YELLOW)
                nb=BOSS_DATA.get(level+1,BOSS_DATA[10])
                nxt=font_sm.render(f"Level {level+1}: {nb['name']} — {BASE_WORLD_W+level*800}px",True,CYAN)
                ck=font_xs.render(f"✔ Checkpoint L{level+1}  |  Boss chest dropped!",True,GREEN)
                screen.blit(dn,(SCREEN_W//2-dn.get_width()//2,SCREEN_H//2-45))
                screen.blit(b2,(SCREEN_W//2-b2.get_width()//2,SCREEN_H//2-5))
                screen.blit(nxt,(SCREEN_W//2-nxt.get_width()//2,SCREEN_H//2+22))
                screen.blit(ck,(SCREEN_W//2-ck.get_width()//2,SCREEN_H//2+45))

        if scene=="paused":
            ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((0,0,0,160)); screen.blit(ov,(0,0))
            panel=pygame.Surface((300,200),pygame.SRCALPHA); panel.fill((10,15,35,220))
            screen.blit(panel,(SCREEN_W//2-150,SCREEN_H//2-100))
            pygame.draw.rect(screen,CYAN,(SCREEN_W//2-150,SCREEN_H//2-100,300,200),border_radius=8,width=1)
            pt=font_lg.render("PAUSED",True,WHITE)
            screen.blit(pt,(SCREEN_W//2-pt.get_width()//2,SCREEN_H//2-85))
            ps=font_sm.render(f"Score: {score}  |  Level: {level}",True,CYAN)
            screen.blit(ps,(SCREEN_W//2-ps.get_width()//2,SCREEN_H//2-45))
            btn_resume.draw(screen,font_sm); btn_menu_b.draw(screen,font_sm)

    elif scene=="dead":
        screen.fill(DARK_BLUE)
        for plat in platforms:
            sr=camera.apply_rect(plat)
            if -10<sr.x<SCREEN_W+10: pygame.draw.rect(screen,PLATFORM_C,sr,border_radius=4)
        for en in enemies: en.draw(screen,camera)
        if boss and boss.alive: boss.draw(screen,camera)
        player.draw(screen,camera)
        ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((30,0,0,180)); screen.blit(ov,(0,0))
        panel=pygame.Surface((440,220),pygame.SRCALPHA); panel.fill((20,5,5,230))
        screen.blit(panel,(SCREEN_W//2-220,SCREEN_H//2-110))
        pygame.draw.rect(screen,RED,(SCREEN_W//2-220,SCREEN_H//2-110,440,220),border_radius=8,width=1)
        pr2=int(180+70*math.sin(t*0.005))
        dt=font_lg.render("YOU  DIED",True,(pr2,30,30))
        screen.blit(dt,(SCREEN_W//2-dt.get_width()//2,SCREEN_H//2-90))
        inf=font_sm.render(f"Nyawa: {lives}  |  Checkpoint: Level {checkpoint}",True,CYAN)
        screen.blit(inf,(SCREEN_W//2-inf.get_width()//2,SCREEN_H//2-45))
        if boss:
            bi=font_xs.render(f"Boss: {boss.name}  |  HP tersisa: {max(0,boss.hp)}",True,ORANGE)
            screen.blit(bi,(SCREEN_W//2-bi.get_width()//2,SCREEN_H//2-20))
        rs=font_sm.render("R / Klik  —  Lanjut dari Checkpoint",True,WHITE)
        screen.blit(rs,(SCREEN_W//2-rs.get_width()//2,SCREEN_H//2+20))
        for i in range(5): draw_robot_head(screen,SCREEN_W//2-62+i*26,SCREEN_H//2+60,alive=(i<lives))

    elif scene=="gameover":
        screen.fill(DARK_BLUE)
        ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((0,0,0,200)); screen.blit(ov,(0,0))
        panel=pygame.Surface((460,260),pygame.SRCALPHA); panel.fill((10,5,20,240))
        screen.blit(panel,(SCREEN_W//2-230,SCREEN_H//2-130))
        pygame.draw.rect(screen,PURPLE,(SCREEN_W//2-230,SCREEN_H//2-130,460,260),border_radius=10,width=1)
        draw_glitch_text(screen,"GAME  OVER",font_lg,SCREEN_W//2-font_lg.size("GAME  OVER")[0]//2,SCREEN_H//2-115,RED,t)
        screen.blit(font_md.render(f"SCORE  {score:06d}",True,CYAN),
                    (SCREEN_W//2-font_md.size(f"SCORE  {score:06d}")[0]//2,SCREEN_H//2-60))
        screen.blit(font_sm.render(f"Level: {level}  |  Boss: {BOSS_DATA.get(level,BOSS_DATA[10])['name']}",True,WHITE),
                    (SCREEN_W//2-200,SCREEN_H//2-10))
        screen.blit(font_sm.render("R / Klik  —  Kembali ke Main Menu",True,(150,150,200)),
                    (SCREEN_W//2-font_sm.size("R / Klik  —  Kembali ke Main Menu")[0]//2,SCREEN_H//2+40))
        draw_g7(screen,SCREEN_W//2-16,SCREEN_H//2+95)
        pygame.draw.line(screen,RED,(SCREEN_W//2-8,SCREEN_H//2+97),(SCREEN_W//2+8,SCREEN_H//2+113),3)
        pygame.draw.line(screen,RED,(SCREEN_W//2+8,SCREEN_H//2+97),(SCREEN_W//2-8,SCREEN_H//2+113),3)

    pygame.display.flip()

pygame.quit()
sys.exit()