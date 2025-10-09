# maze_battleroyale_v3.py
"""
Maze Battle Royale v3
- Player and bots drawn as simple "characters" (head + body)
- Player shoots with SPACE toward mouse
- Bigger/more complex maze (extra random internal walls)
- Bots use A* pathfinding and attempt ricochet shots when close to other bots
- Bullets bounce off walls with energy loss
- Camera follows player
- 10 bots by default
"""

import pygame, random, math, sys, time, heapq

# ---------- Config ----------


WIDTH, HEIGHT = 1300, 800
FPS = 60

# ---------- Mini Map Settings ----------
MINIMAP_WIDTH = 200
MINIMAP_HEIGHT = 140
MINIMAP_X = WIDTH - MINIMAP_WIDTH - 10  # top-right corner
MINIMAP_Y = 10


CELL_SIZE = 90                # حجم الخلية
COLS = 70     # عدد الأعمدة (كبرت المتاهة)
ROWS = 36     # عدد الصفوف

PLAYER_SPEED = 2.6
BULLET_SPEED = 14
BOT_SPEED = 1.9
BOT_COUNT = 10

PLAYER_MAX_HEALTH = 100
BOT_MAX_HEALTH = 75

PICKUP_COUNT = 12

# ricochet
MAX_BOUNCES = 3
BOUNCE_ENERGY_LOSS = 0.62

CELL_SIZE = 40
COLS = 50
ROWS = 36

WORLD_W = COLS * CELL_SIZE
WORLD_H = ROWS * CELL_SIZE

SCALE_X = MINIMAP_WIDTH / WORLD_W
SCALE_Y = MINIMAP_HEIGHT / WORLD_H


# ---------- Mini Map Settings ----------
MINIMAP_WIDTH = 200
MINIMAP_HEIGHT = 140
MINIMAP_X = WIDTH - MINIMAP_WIDTH - 10
MINIMAP_Y = 10




# ---------- Init ----------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Maze Battle Royale v3 — Player = Human")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Consolas", 18)

def dist(a,b): return math.hypot(a[0]-b[0], a[1]-b[1])
def clamp(v,a,b): return max(a,min(b,v))
# min map helper
def draw_full_map(screen, rooms, cell_size, minimap_width, minimap_height, pos=(WIDTH-210, 10)):
    # سطح للـ mini-map
    minimap_surf = pygame.Surface((minimap_width, minimap_height))
    minimap_surf.set_alpha(220)
    minimap_surf.fill((10, 10, 30))

    # حساب أبعاد العالم الكامل بناءً على الغرف
    world_w = max(rx + rw for (rx, ry, rw, rh) in rooms) * cell_size
    world_h = max(ry + rh for (rx, ry, rw, rh) in rooms) * cell_size

    scale_x = minimap_width / world_w
    scale_y = minimap_height / world_h

    font_small = pygame.font.SysFont("Consolas", 12)

    # رسم الغرف
    for idx, (rx, ry, rw, rh) in enumerate(rooms):
        rx_px = rx * cell_size * scale_x
        ry_px = ry * cell_size * scale_y
        rw_px = rw * cell_size * scale_x
        rh_px = rh * cell_size * scale_y
        pygame.draw.rect(minimap_surf, (180, 180, 220), (rx_px, ry_px, rw_px, rh_px))
        minimap_surf.blit(font_small.render(f"R{idx+1}", True, (255, 255, 255)), (rx_px + 2, ry_px + 2))

    # رسم على الشاشة
    screen.blit(minimap_surf, pos)

# ---------- Maze generation (DFS) + add random internal walls ----------
# ---------- New "Room-based Maze" ----------
def make_maze(cols, rows):
    # كل الخلايا مفتوحة
    maze = [[[False, False, False, False] for _ in range(rows)] for _ in range(cols)]
# ---------- تصميم الغرف ثابت ----------
    rooms = [
        (2, 2, 6, 5),    
        (10, 3, 5, 6),   
        (18, 2, 7, 4),   
        (5, 12, 8, 5),   
        (15, 10, 6, 6),  
        (25, 5, 5, 7),   
        (30, 12, 6, 6),  
        (8, 20, 10, 5),  
        (18, 18, 7, 6),  
        (28, 20, 6, 6),  
    ]

    room_count = 10  # عدد الغرف
    min_size, max_size = 4, 8  # حجم الغرفة

    for _ in range(room_count):
        rw = random.randint(min_size, max_size)
        rh = random.randint(min_size, max_size)
        rx = random.randint(1, cols - rw - 1)
        ry = random.randint(1, rows - rh - 1)

        # تخزين الغرفة
        rooms.append((rx, ry, rw, rh))

        # إضافة جدران الغرفة
    for rx, ry, rw, rh in rooms:
        for x in range(rx, rx + rw):
            for y in range(ry, ry + rh):
                if x == rx: maze[x][y][3] = True  # left wall
                if x == rx + rw - 1: maze[x][y][1] = True  # right wall
                if y == ry: maze[x][y][0] = True  # top wall
                if y == ry + rh - 1: maze[x][y][2] = True  # bottom wall

 # ربط الغرف بالطرق (نفس الطريقة السابقة)
    for i in range(len(rooms) - 1):
        x1, y1, w1, h1 = rooms[i]
        x2, y2, w2, h2 = rooms[i + 1]
        cx1, cy1 = x1 + w1 // 2, y1 + h1 // 2
        cx2, cy2 = x2 + w2 // 2, y2 + h2 // 2
        for x in range(min(cx1, cx2), max(cx1, cx2) + 1):
            maze[x][cy1] = [False, False, False, False]
        for y in range(min(cy1, cy2), max(cy1, cy2) + 1):
            maze[cx2][y] = [False, False, False, False]

    return maze , rooms

maze, rooms = make_maze(COLS, ROWS)

# بناء مستطيلات الجدران (للكوليجن والLOS)
wall_rects = []
for x in range(COLS):
    for y in range(ROWS):
        wx = x*CELL_SIZE; wy = y*CELL_SIZE
        walls = maze[x][y]
        if walls[0]:
            wall_rects.append(pygame.Rect(wx, wy, CELL_SIZE, 3))
        if walls[1]:
            wall_rects.append(pygame.Rect(wx+CELL_SIZE-3, wy, 3, CELL_SIZE))
        if walls[2]:
            wall_rects.append(pygame.Rect(wx, wy+CELL_SIZE-3, CELL_SIZE, 3))
        if walls[3]:
            wall_rects.append(pygame.Rect(wx, wy, 3, CELL_SIZE))

WORLD_W = COLS * CELL_SIZE
WORLD_H = ROWS * CELL_SIZE

SCALE_X = MINIMAP_WIDTH / WORLD_W
SCALE_Y = MINIMAP_HEIGHT / WORLD_H



# ---------- Entities ----------
class Entity:
    def __init__(self,x,y,w,h,color):
        self.x=float(x); self.y=float(y); self.w=w; self.h=h; self.color=color
    def rect(self): return pygame.Rect(int(self.x-self.w/2), int(self.y-self.h/2), self.w, self.h)

class Player(Entity):
    def __init__(self,x,y):
        super().__init__(x,y,28,28,(50,180,255))
        self.health=PLAYER_MAX_HEALTH; self.speed=PLAYER_SPEED; self.ammo=30; self.alive=True
    def update(self, keys, dt):
        if not self.alive: return
        dx=dy=0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx-=1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx+=1
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy-=1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy+=1
        if dx!=0 or dy!=0:
            mag = math.hypot(dx,dy) or 1
            nx = self.x + (dx/mag)*self.speed
            ny = self.y + (dy/mag)*self.speed
            # فحص التصادم محورًا محورًا (smooth sliding)
            oldx, oldy = self.x, self.y
            self.x = nx
            if self.rect().collidelist(wall_rects) != -1: self.x = oldx
            self.y = ny
            if self.rect().collidelist(wall_rects) != -1: self.y = oldy
            self.x = clamp(self.x, 10, WORLD_W-10)
            self.y = clamp(self.y, 10, WORLD_H-10)

    def draw(self, surf, camx, camy):
        sx, sy = world_to_screen(self.x, self.y, camx, camy)
        # رسم شخصية مبسطة: رأس + جسم
        pygame.draw.circle(surf, (255,220,180), (sx, sy-8), 6)   # رأس
        pygame.draw.rect(surf, self.color, (sx-8, sy-6, 16, 18)) # جسم

class Bot(Entity):
    def __init__(self, x,y, idx):
        super().__init__(x,y,26,26,(240,100,100))
        self.health=BOT_MAX_HEALTH; self.speed=BOT_SPEED; self.state="wander"
        self.alive=True; self.idx=idx
        self.shoot_cooldown = random.uniform(0.6,1.6)
        self.path = []
        self.path_timer = 0
    def grid_pos(self):
        return int(self.x//CELL_SIZE), int(self.y//CELL_SIZE)
    def follow_path(self, dt):
        if not self.path: return
        target = self.path[0]
        tx = target[0]*CELL_SIZE + CELL_SIZE/2
        ty = target[1]*CELL_SIZE + CELL_SIZE/2
        dx = tx - self.x; dy = ty - self.y
        d = math.hypot(dx,dy) or 1
        step = min(self.speed, d)
        self.x += (dx/d)*step
        self.y += (dy/d)*step
        if d < 4:
            self.path.pop(0)
    def draw(self, surf, camx, camy):
        sx, sy = world_to_screen(self.x, self.y, camx, camy)
        # شخصية افتراضية (رأس + جسم بلون مختلف)
        pygame.draw.circle(surf, (255,200,200), (sx, sy-8), 6)
        pygame.draw.rect(surf, self.color, (sx-8, sy-6, 16, 18))

    def update(self, entities, bullets, dt):
        if not self.alive: return
        # اختيار أقرب هدف (لاعب أو بوت آخر)
        targets = [e for e in entities if e is not self and getattr(e,'alive',True)]
        if not targets:
            # wander random
            if random.random() < 0.01:
                nx = clamp(self.x + random.uniform(-80,80), 10, WORLD_W-10)
                ny = clamp(self.y + random.uniform(-80,80), 10, WORLD_H-10)
                self.path = astar_path(self.grid_pos(), (int(nx//CELL_SIZE), int(ny//CELL_SIZE)))
            self.follow_path(dt); return

        nearest = min(targets, key=lambda t: dist((self.x,self.y),(t.x,t.y)))
        d = dist((self.x,self.y),(nearest.x,nearest.y))

        # إعادة حساب المسار من وقت لآخر
        self.path_timer -= dt
        if self.path_timer <= 0:
            self.path_timer = 0.6 + random.random()*0.9
            start = self.grid_pos()
            goal = (int(nearest.x//CELL_SIZE), int(nearest.y//CELL_SIZE))
            self.path = astar_path(start, goal)
            if self.path and self.path[0]==start: self.path.pop(0)

        # تنفيذ المسار أو الحركة المباشرة
        if self.path:
            self.follow_path(dt)
        else:
            dx = nearest.x - self.x; dy = nearest.y - self.y
            mag = math.hypot(dx,dy) or 1
            nx = self.x + (dx/mag)*self.speed
            ny = self.y + (dy/mag)*self.speed
            oldx, oldy = self.x, self.y
            self.x = nx
            if self.rect().collidelist(wall_rects) != -1: self.x = oldx
            self.y = ny
            if self.rect().collidelist(wall_rects) != -1: self.y = oldy

        # منطق إطلاق النار: إذا في رؤية أو محاولة ricochet عند قرب بوت آخر
        self.shoot_cooldown -= dt
        if d < 260 and self.shoot_cooldown <= 0:
            if line_of_sight((self.x,self.y),(nearest.x,nearest.y)):
                tx = nearest.x + random.uniform(-10,10); ty = nearest.y + random.uniform(-10,10)
                bullets.append(Bullet(self.x, self.y, tx, ty, owner=self))
                self.shoot_cooldown = random.uniform(0.7,1.6)
            else:
                # محاولة ricochet إذا الهدف بوت وكان قريب
                if isinstance(nearest, Bot) and d < 170:
                    wpt = choose_wall_point_for_ricochet((self.x,self.y),(nearest.x,nearest.y))
                    if wpt:
                        bullets.append(Bullet(self.x, self.y, wpt[0], wpt[1], owner=self))
                        self.shoot_cooldown = random.uniform(0.9,1.8)

class Bullet:
    def __init__(self,x,y,tx,ty,owner):
        self.x=x; self.y=y; self.owner=owner
        dx,dy = tx-x, ty-y; mag = math.hypot(dx,dy) or 1
        self.vx = (dx/mag)*BULLET_SPEED; self.vy = (dy/mag)*BULLET_SPEED
        self.r = 4; self.alive=True; self.damage = 0 if isinstance(owner, Bot) else 32
        self.bounces = 0
    def update(self, dt):
        if not self.alive: return
        nx = self.x + self.vx
        ny = self.y + self.vy
        r = pygame.Rect(int(nx-self.r), int(ny-self.r), self.r*2, self.r*2)
        hit_any = None
        for wr in wall_rects:
            if r.colliderect(wr):
                hit_any = wr; break
        if hit_any:
            # حساب تقريبي لاعادة الانعكاس: نقرر أفقياً أم رأسياً حسب التداخل
            overlap_x = max(0, min(nx+self.r, hit_any.right) - max(nx-self.r, hit_any.left))
            overlap_y = max(0, min(ny+self.r, hit_any.bottom) - max(ny-self.r, hit_any.top))
            if overlap_y >= overlap_x:
                self.vy = -self.vy * BOUNCE_ENERGY_LOSS
            else:
                self.vx = -self.vx * BOUNCE_ENERGY_LOSS
            self.bounces += 1
            speed_mag = math.hypot(self.vx, self.vy)
            if self.bounces >= MAX_BOUNCES or speed_mag < 3:
                self.alive = False
                return
            self.x += self.vx * 0.4
            self.y += self.vy * 0.4
            return
        self.x = nx; self.y = ny
        if self.x < -40 or self.x > WORLD_W+40 or self.y < -40 or self.y > WORLD_H+40:
            self.alive = False

class Pickup(Entity):
    def __init__(self,x,y,typ):
        col = (200,200,50) if typ=="ammo" else (100,255,120)
        super().__init__(x,y,18,18,col); self.typ=typ

# ---------- Pathfinding A* ----------
def dir_between(a,b):
    ax,ay=a; bx,by=b
    if bx==ax and by==ay-1: return 0
    if bx==ax+1 and by==ay: return 1
    if bx==ax and by==ay+1: return 2
    if bx==ax-1 and by==ay: return 3
    return 0

def neighbors(cell):
    x,y = cell
    nbrs = []
    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
        nx,ny = x+dx, y+dy
        if 0 <= nx < COLS and 0 <= ny < ROWS:
            if not maze[x][y][dir_between((x,y),(nx,ny))]:
                nbrs.append((nx,ny))
    return nbrs

def astar_path(start, goal):
    if start == goal: return []
    sx,sy = start; gx,gy = goal
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    gscore = {start:0}
    fscore = {start: abs(sx-gx)+abs(sy-gy)}
    max_iters = COLS*ROWS*4
    iters = 0
    while open_set and iters < max_iters:
        iters += 1
        _, current = heapq.heappop(open_set)
        if current == goal:
            path = []
            c = current
            while c in came_from:
                path.append(c); c = came_from[c]
            path.reverse()
            return path
        for nb in neighbors(current):
            tentative = gscore[current] + 1
            if tentative < gscore.get(nb, 1e9):
                came_from[nb] = current
                gscore[nb] = tentative
                f = tentative + abs(nb[0]-gx)+abs(nb[1]-gy)
                if nb not in fscore or f < fscore[nb]:
                    fscore[nb] = f
                    heapq.heappush(open_set, (f, nb))
    return []

# ---------- LOS helper ----------
def line_of_sight(a,b):
    ax,ay=a; bx,by=b
    steps = int(dist(a,b)/6) + 1
    for i in range(1, steps):
        t = i/steps
        x = ax + (bx-ax)*t; y = ay + (by-ay)*t
        r = pygame.Rect(int(x-2), int(y-2), 4,4)
        for wr in wall_rects:
            if r.colliderect(wr):
                return False
    return True

# ---------- Ricochet helper ----------
def choose_wall_point_for_ricochet(shooter, target):
    sx,sy=shooter; tx,ty=target
    candidates=[]
    for wr in wall_rects:
        cx = wr.left + wr.width/2; cy = wr.top + wr.height/2
        dx = tx - sx; dy = ty - sy
        if dx==0 and dy==0: continue
        t = ((cx - sx)*dx + (cy - sy)*dy) / (dx*dx + dy*dy)
        if 0 < t < 1:
            px = sx + dx * t; py = sy + dy * t
            dperp = math.hypot(cx-px, cy-py)
            if dperp < 90:
                candidates.append((wr, dperp))
    if not candidates: return None
    candidates.sort(key=lambda x:x[1])
    wr = candidates[0][0]
    return (wr.left + wr.width/2 + random.uniform(-6,6), wr.top + wr.height/2 + random.uniform(-6,6))

# ---------- Setup world ----------
def random_open_cell():
    while True:
        gx = random.randint(0,COLS-1); gy = random.randint(0,ROWS-1)
        return gx,gy

px,py = random_open_cell()
player = Player(px*CELL_SIZE + CELL_SIZE/2, py*CELL_SIZE + CELL_SIZE/2)
bots = []
for i in range(BOT_COUNT):
    bx,by = random_open_cell()
    bots.append(Bot(bx*CELL_SIZE + CELL_SIZE/2, by*CELL_SIZE + CELL_SIZE/2, i+1))

bullets = []
pickups = []
for i in range(PICKUP_COUNT):
    gx,gy = random_open_cell()
    pickups.append(Pickup(gx*CELL_SIZE + CELL_SIZE/2, gy*CELL_SIZE + CELL_SIZE/2, random.choice(["ammo","med"])))

start_time = time.time()

# camera helper
def world_to_screen(wx, wy, camx, camy):
    return int(wx - camx + WIDTH/2), int(wy - camy + HEIGHT/2)

# ---------- Game loop ----------
running=True; winner=None
while running:
    dt = clock.tick(FPS)/1000.0

    # events
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running=False
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE: running=False
            if e.key == pygame.K_SPACE:
                # اطلاق من SPACE باتجاه موضع الماوس (تحكم كما طلبت)
                if player.alive and player.ammo>0:
                    mx,my = pygame.mouse.get_pos()
                    camx, camy = player.x, player.y
                    wx = mx - WIDTH/2 + camx
                    wy = my - HEIGHT/2 + camy
                    bullets.append(Bullet(player.x, player.y, wx, wy, owner="player"))
                    player.ammo -= 1
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button==1:
            # أيضًا نسمح بالفأرة لإطلاق (اختياري) — لكن الأساسي Space
            if player.alive and player.ammo>0:
                mx,my = pygame.mouse.get_pos()
                camx, camy = player.x, player.y
                wx = mx - WIDTH/2 + camx
                wy = my - HEIGHT/2 + camy
                bullets.append(Bullet(player.x, player.y, wx, wy, owner="player"))
                player.ammo -= 1

    keys = pygame.key.get_pressed()
    player.update(keys, dt)
    draw_full_map(screen, rooms, CELL_SIZE, MINIMAP_WIDTH, MINIMAP_HEIGHT)


    # bots update
    all_entities = [player] + bots
    for b in bots:
        b.update(all_entities, bullets, dt)

    # bullets update
    for bu in bullets:
        bu.update(dt)

    # bullet collisions
    for bu in bullets:
        if not bu.alive: continue
        # player hit
        if player.alive and bu.owner is not player and getattr(bu.owner,'alive',True):
            if dist((bu.x,bu.y),(player.x,player.y)) < player.w/2 + bu.r:
                player.health -= bu.damage
                bu.alive=False
                if player.health <= 0: player.alive=False
                continue
        # bots
        for b in bots:
            if not b.alive: continue
            if bu.owner is b: continue
            if isinstance(bu.owner, Bot) and bu.owner is b: continue
            if dist((bu.x,bu.y),(b.x,b.y)) < b.w/2 + bu.r:
                b.health -= bu.damage
                bu.alive=False
                if b.health <= 0:
                    b.alive=False
                    if random.random() < 0.6:
                        pickups.append(Pickup(b.x + random.randint(-10,10), b.y + random.randint(-10,10), random.choice(["ammo","med"])))
                break

    bullets = [b for b in bullets if b.alive]

    # pickups collision
    for p in pickups[:]:
        if player.alive and dist((p.x,p.y),(player.x,player.y)) < 18:
            if p.typ=="med": player.health = min(PLAYER_MAX_HEALTH, player.health + 40)
            else: player.ammo += 10
            pickups.remove(p)

    # win condition
    alive_entities = [e for e in ([player] + bots) if getattr(e,'alive',False)]
    if len(alive_entities) <= 1:
        if len(alive_entities)==1:
            winner = "You" if alive_entities[0] is player and player.alive else "Bots"
        else:
            winner = "No one"
        running=False

    # draw world with camera centered on player
    camx, camy = player.x, player.y
    screen.fill((12,12,25))

    # floor tiles (faint)
    start_cx = int((camx - WIDTH/2)//CELL_SIZE) - 1
    start_cy = int((camy - HEIGHT/2)//CELL_SIZE) - 1
    end_cx = int((camx + WIDTH/2)//CELL_SIZE) + 1
    end_cy = int((camy + HEIGHT/2)//CELL_SIZE) + 1
    for gx in range(max(0,start_cx), min(COLS,end_cx)):
        for gy in range(max(0,start_cy), min(ROWS,end_cy)):
            rx, ry = world_to_screen(gx*CELL_SIZE, gy*CELL_SIZE, camx, camy)
            pygame.draw.rect(screen, (18,18,30), (rx, ry, CELL_SIZE-1, CELL_SIZE-1))

    # walls (visible window only)
    for wr in wall_rects:
        # quick culling
        if (wr.left > camx + WIDTH/2 + 50) or (wr.right < camx - WIDTH/2 - 50) or (wr.top > camy + HEIGHT/2 + 50) or (wr.bottom < camy - HEIGHT/2 - 50):
            continue
        rx, ry = world_to_screen(wr.left, wr.top, camx, camy)
        pygame.draw.rect(screen, (100,100,120), (rx, ry, wr.width, wr.height))

    # pickups
    for p in pickups:
        sx, sy = world_to_screen(p.x, p.y, camx, camy)
        pygame.draw.rect(screen, p.color, pygame.Rect(sx-9, sy-9, p.w, p.h))
        pygame.draw.circle(screen, (255,255,255) if p.typ=="ammo" else (0,0,0), (sx, sy), 3)

    # bots
    for b in bots:
        sx, sy = world_to_screen(b.x, b.y, camx, camy)
        if not b.alive:
            pygame.draw.circle(screen, (90,90,90), (sx, sy), 10)
            continue
        b.draw(screen, camx, camy)
        pygame.draw.rect(screen, (80,80,80), (sx-20, sy-22, 40, 6))
        pygame.draw.rect(screen, (0,200,0), (sx-20, sy-22, 40*max(0,b.health)/BOT_MAX_HEALTH, 6))

    # player
    psx, psy = world_to_screen(player.x, player.y, camx, camy)
    if player.alive:
        player.draw(screen, camx, camy)
        pygame.draw.rect(screen, (80,80,80), (psx-30, psy-42, 60, 8))
        pygame.draw.rect(screen, (0,200,0), (psx-30, psy-42, 60*(player.health/PLAYER_MAX_HEALTH), 8))
    else:
        pygame.draw.circle(screen, (120,120,120), (psx, psy), 12)

    # bullets
    for bu in bullets:
        sx, sy = world_to_screen(bu.x, bu.y, camx, camy)
        col = (255,220,80) if str(bu.owner)=="player" or bu.owner=="player" else (255,120,120)
        pygame.draw.circle(screen, col, (sx, sy), bu.r)

    # HUD
    hud_text = f"HP: {int(player.health) if player.alive else 0}   Ammo: {player.ammo}   Bots Alive: {sum(1 for b in bots if b.alive)}"
    screen.blit(font.render(hud_text, True, (230,230,230)), (8,8))

    # bot status
    yy=32
    for i,b in enumerate(bots):
        st = f"Bot{i+1}: {'Alive' if b.alive else 'Dead'} HP:{int(b.health) if b.alive else 0}"
        screen.blit(font.render(st, True, (200,200,200)), (8, yy)); yy+=16

    # crosshair
    mx,my = pygame.mouse.get_pos()
    pygame.draw.circle(screen, (220,220,220), (mx,my), 6, 1)
    pygame.draw.line(screen, (220,220,220), (mx-10,my), (mx+10,my), 1)
    pygame.draw.line(screen, (220,220,220), (mx,my-10), (mx,my+10), 1)

# خلفية شفافة (باستخدام Surface)
   # ---------- Draw Mini Map ----------
    minimap_surf = pygame.Surface((MINIMAP_WIDTH, MINIMAP_HEIGHT))
    minimap_surf.set_alpha(180)  # شفافية
    minimap_surf.fill((10,10,30))

# رسم الغرف
    font_small = pygame.font.SysFont("Consolas", 12)
    for idx, (rx, ry, rw, rh) in enumerate(rooms):  
        rx_px = rx * CELL_SIZE * SCALE_X
        ry_px = ry * CELL_SIZE * SCALE_Y
        rw_px = rw * CELL_SIZE * SCALE_X
        rh_px = rh * CELL_SIZE * SCALE_Y
    pygame.draw.rect(minimap_surf, (180,180,220), (rx_px, ry_px, rw_px, rh_px))
    # اسم الغرفة
    minimap_surf.blit(font_small.render(f"R{idx+1}", True, (255,255,255)), (rx_px+2, ry_px+2))

# اللاعب
    px_minimap = player.x * SCALE_X
    py_minimap = player.y * SCALE_Y
    pygame.draw.circle(minimap_surf, (50,180,255), (int(px_minimap), int(py_minimap)), 4)

# البوتات
    for b in bots:
        if not b.alive: continue
        bx_minimap = b.x * SCALE_X
        by_minimap = b.y * SCALE_Y
    pygame.draw.circle(minimap_surf, (240,100,100), (int(bx_minimap), int(by_minimap)), 3)

# رسم الـ mini map على الشاشة
    screen.blit(minimap_surf, (MINIMAP_X, MINIMAP_Y))
    pygame.display.flip()

# end
pygame.time.wait(300)
screen.fill((10,10,20))
msg = f"Game Over - Winner: {winner}"
screen.blit(font.render(msg, True, (240,240,240)), (WIDTH//2-200, HEIGHT//2-10))
pygame.display.flip()
pygame.time.wait(4000)
pygame.quit()
sys.exit()
