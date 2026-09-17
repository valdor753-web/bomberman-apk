"""
BOMBERMAN ULTRA COLOR - PORT KIVY (ANDROID)
Puerto completo del juego tkinter a Kivy con controles tactiles.
"""
import os, sys, random, math, time, wave, struct, io, tempfile

os.environ['KIVY_LOG_LEVEL'] = 'warning'

from PIL import Image as PILImage, ImageDraw

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, Rectangle, Ellipse, Line
from kivy.properties import StringProperty, NumericProperty
from kivy.core.text import Label as CoreLabel

try:
    from kivy.core.audio import SoundLoader
    HAS_AUDIO = SoundLoader is not None
except Exception:
    SoundLoader = None
    HAS_AUDIO = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRID_SIZE = 17
TILE_BASE = 40
TICK = 0.08
FINAL_BOSS_LEVEL = 10
PAIN_LEVEL = 5

EMPTY = 0; WALL_SOLID = 1; WALL_DESTRUCTIBLE = 2; BOMBA = 3; EXPLOSION = 4
POWERUP_RANGE = 5; POWERUP_BOMB = 6; POWERUP_LIFE = 7

MUSIC_ENABLED = True
MUSIC_OBJ = None
CURRENT_MUSIC_KEY = None

TEX = {}
_sound_queue = []
_temp_dir = tempfile.mkdtemp()

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))

def _find_music(name):
    for ext in ('.mp3', '.wav', '.ogg'):
        p = os.path.join(BASE_DIR, 'music', name + ext)
        if os.path.exists(p):
            return p
    for ext in ('.mp3', '.wav', '.ogg'):
        p = os.path.join(BASE_DIR, name + ext)
        if os.path.exists(p):
            return p
    return None

def _play_music(path, loops=-1):
    global MUSIC_OBJ, CURRENT_MUSIC_KEY
    if not HAS_AUDIO or not MUSIC_ENABLED:
        return
    try:
        if MUSIC_OBJ:
            MUSIC_OBJ.stop()
            MUSIC_OBJ.unload()
        MUSIC_OBJ = SoundLoader.load(path)
        if MUSIC_OBJ:
            MUSIC_OBJ.loop = True
            MUSIC_OBJ.volume = 0.6
            MUSIC_OBJ.play()
    except Exception:
        pass

def start_music(force=False):
    global MUSIC_ENABLED
    if not MUSIC_ENABLED: return
    p = _find_music('musica')
    if p: _play_music(p)

def start_boss_music():
    global MUSIC_ENABLED
    if not MUSIC_ENABLED: return
    p = _find_music('ojodetigre')
    if p: _play_music(p)

def start_pain_music():
    global MUSIC_ENABLED
    if not MUSIC_ENABLED: return
    p = _find_music('pain')
    if p: _play_music(p)

def stop_music():
    global MUSIC_OBJ
    if MUSIC_OBJ:
        try:
            MUSIC_OBJ.stop()
        except Exception:
            pass

def set_music_enabled(estado):
    global MUSIC_ENABLED
    MUSIC_ENABLED = estado
    if estado: start_music()
    else: stop_music()

def _gen_wav(name, tones, volume=0.4):
    path = os.path.join(_temp_dir, name + '.wav')
    if os.path.exists(path):
        return path
    sr = 22050
    frames = []
    for freq, dur in tones:
        n = int(sr * dur)
        for i in range(n):
            t = i / sr
            env = max(0.0, 1.0 - t / dur) if dur > 0 else 0
            val = int(32767 * volume * env * math.sin(2 * math.pi * freq * t))
            frames.append(struct.pack('<h', max(-32768, min(32767, val))))
    with wave.open(path, 'w') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr)
        f.writeframes(b''.join(frames))
    return path

def play_sound(s):
    paths = {
        'bomb': _gen_wav('bomb', [(250, 0.08)]),
        'explosion': _gen_wav('explosion', [(100, 0.15)]),
        'boss_alert': _gen_wav('boss_alert', [(300, 0.1), (450, 0.1), (600, 0.25)]),
        'win': _gen_wav('win', [(523, 0.1), (659, 0.1), (783, 0.2)]),
    }
    if not HAS_AUDIO or s not in paths:
        return
    try:
        snd = SoundLoader.load(paths[s])
        if snd:
            snd.volume = 0.5
            snd.play()
    except Exception:
        pass

def play_shinra_sfx():
    p = _find_music('shinra')
    if not HAS_AUDIO or not p: return
    try:
        snd = SoundLoader.load(p)
        if snd:
            snd.volume = 0.7
            snd.play()
    except Exception: pass

def play_chibaku_sfx():
    p = _find_music('ChibakuTensei')
    if not HAS_AUDIO or not p: return
    try:
        snd = SoundLoader.load(p)
        if snd:
            snd.volume = 0.7
            snd.play()
    except Exception: pass

def _load_tex(path):
    if path in TEX: return TEX[path]
    try:
        img = CoreImage(path)
        tex = img.texture
        TEX[path] = tex
        return tex
    except Exception:
        return None

def _pil_to_tex(pil_img):
    buf = io.BytesIO()
    pil_img.save(buf, format='png')
    buf.seek(0)
    return CoreImage(buf, ext='png').texture

def crear_imagenes_HD():
    tam = (TILE_BASE, TILE_BASE)
    files = {
        'player1.png': lambda d: (d.ellipse([3,3,37,37], fill="#00E5FF", outline="#FFFFFF", width=3),
                                   d.ellipse([10,10,30,30], fill="#00838F"),
                                   d.ellipse([12,14,18,20], fill="#FFFFFF"), d.ellipse([22,14,28,20], fill="#FFFFFF")),
        'player2.png': lambda d: (d.ellipse([3,3,37,37], fill="#76FF03", outline="#FFFFFF", width=3),
                                   d.ellipse([10,10,30,30], fill="#33691E"),
                                   d.ellipse([12,14,18,20], fill="#FFFFFF"), d.ellipse([22,14,28,20], fill="#FFFFFF")),
        'enemy.png': lambda d: (d.ellipse([3,3,37,37], fill="#FF1744", outline="#FF80AB", width=3),
                                 d.polygon([(10,10),(16,20),(8,20)], fill="#FFFF00"),
                                 d.polygon([(30,10),(32,20),(24,20)], fill="#FFFF00"),
                                 d.arc([10,22,30,32], start=0, end=180, fill="black", width=3)),
        'bomb.png': lambda d: (d.ellipse([5,8,35,38], fill="#212121", outline="#FF3D00", width=3),
                                d.ellipse([10,12,20,22], fill="#616161"),
                                d.rectangle([17,3,23,8], fill="#B0BEC5"),
                                d.line([20,4,28,0], fill="#FFEA00", width=3)),
        'explosion.png': lambda d: (d.rectangle([0,0,40,40], fill="#FF9100"),
                                     d.rectangle([5,5,35,35], fill="#FF3D00"),
                                     d.rectangle([12,12,28,28], fill="#FFEA00"),
                                     d.rectangle([17,17,23,23], fill="#FFFFFF")),
        'wall_solid.png': lambda d: (d.rectangle([0,0,40,40], fill="#263238", outline="#00E5FF", width=2),
                                      d.rectangle([6,6,34,34], fill="#37474F"),
                                      d.line([0,0,40,40], fill="#455A64", width=2),
                                      d.line([40,0,0,40], fill="#455A64", width=2)),
        'wall_destructible.png': lambda d: (d.rectangle([0,0,40,40], fill="#D84315", outline="#FF6E40", width=2),
                                             d.line([0,13,40,13], fill="#BF360C", width=2),
                                             d.line([0,26,40,26], fill="#BF360C", width=2),
                                             d.line([20,0,20,13], fill="#BF360C", width=2),
                                             d.line([10,13,10,26], fill="#BF360C", width=2),
                                             d.line([30,26,30,40], fill="#BF360C", width=2)),
    }
    for fname, draw_fn in files.items():
        fpath = os.path.join(BASE_DIR, fname)
        if not os.path.exists(fpath):
            img = PILImage.new("RGBA", tam, (0,0,0,0))
            draw_fn(ImageDraw.Draw(img))
            img.save(fpath)

def load_all_textures():
    crear_imagenes_HD()
    sprite_map = {
        'p1': 'player1.png', 'p2': 'player2.png', 'enemy': 'enemy.png',
        'bomb': 'bomb.png', 'explosion': 'explosion.png',
        'wall_solid': 'wall_solid.png', 'wall_destructible': 'wall_destructible.png',
        'boss_pain': os.path.join('sprites', 'boss_pain.png'),
        'madara': os.path.join('sprites', 'boss_madara.png'),
        'madara_edo': os.path.join('sprites', 'boss_madara_edo.png'),
    }
    for key, fname in sprite_map.items():
        p = os.path.join(BASE_DIR, fname)
        if os.path.exists(p):
            TEX[key] = _load_tex(p)

    for prefix in ('minero', 'capi'):
        for d in ('down', 'up', 'left', 'right'):
            for f in (1, 2):
                k = f'{prefix}_{d}_{f}'
                p = os.path.join(BASE_DIR, 'sprites', f'{k}.png')
                if os.path.exists(p): TEX[k] = _load_tex(p)
        for f in (1, 2, 3):
            k = f'{prefix}_dead_{f}'
            p = os.path.join(BASE_DIR, 'sprites', f'{k}.png')
            if os.path.exists(p): TEX[k] = _load_tex(p)

    pain_dir = os.path.join(BASE_DIR, 'sprites', 'movimiento')
    pain_frames = {
        'down': ['camiaba', 'camiaba1'],
        'left': ['camiizqui1','camiizqui2','camiizqui3','camiizqui4','camiizqui5','camiizqui6'],
        'right': ['camidere','camidere1','camidere2','camidere3','camidere4','camidere5'],
        'up': ['camiarri', 'camiarri1'],
    }
    for d, names in pain_frames.items():
        for i, name in enumerate(names):
            k = f'pain_{d}_{i}'
            p = os.path.join(pain_dir, f'{name}.png')
            if os.path.exists(p): TEX[k] = _load_tex(p)

    for i, name in enumerate(['eleva1', 'eleva2', 'eleva3']):
        p = os.path.join(BASE_DIR, 'sprites', f'{name}.png')
        if os.path.exists(p): TEX[f'pain_eleva_{i}'] = _load_tex(p)

    for i, name in enumerate(['espe1', 'espe2', 'espe3']):
        p = os.path.join(BASE_DIR, 'sprites', f'{name}.png')
        if os.path.exists(p): TEX[f'pain_chibaku_{i}'] = _load_tex(p)

    p = os.path.join(BASE_DIR, 'sprites', 'painshinra.jfif')
    if os.path.exists(p):
        try:
            pil = PILImage.open(p).convert('RGB').resize((680, 680), PILImage.Resampling.LANCZOS)
            TEX['painshinra'] = _pil_to_tex(pil)
        except Exception: pass

    madara_dir = os.path.join(BASE_DIR, 'madara')
    for prefix, count in [('madaradere',3),('madaramokuton',2),('susanodere',3),('susanoaba',2)]:
        for i in range(1, count + 1):
            p = os.path.join(madara_dir, f'{prefix}{i}.png')
            if os.path.exists(p): TEX[f'{prefix}_{i}'] = _load_tex(p)

    p = os.path.join(madara_dir, 'madera.png')
    if os.path.exists(p): TEX['madera'] = _load_tex(p)

    for k, fname in [('madara_clone', 'boss_madara.png'), ('limbo', 'boss_madara_edo.png'),
                      ('boss', 'enemy.png')]:
        p = os.path.join(BASE_DIR, 'sprites', fname)
        if os.path.exists(p): TEX[k] = _load_tex(p)

    p = os.path.join(BASE_DIR, 'pain_frames_big', 'pain_down_0.png')
    if os.path.exists(p): TEX['pain_big'] = _load_tex(p)


PAIN_FRAMES_MAP = {
    'down': ['camiaba', 'camiaba1'],
    'left': ['camiizqui1','camiizqui2','camiizqui3','camiizqui4','camiizqui5','camiizqui6'],
    'right': ['camidere','camidere1','camidere2','camidere3','camidere4','camidere5'],
    'up': ['camiarri', 'camiarri1'],
}

class GameCore:
    def __init__(self):
        self.mode = "1P"
        self.game_running = False
        self.time_left = 180
        self.current_level = 1
        self.boss = None
        self.map_grid = []
        self.p1 = {'pos':[1,1],'score':0,'lives':5,'max_bombs':1,'active_bombs':0,
                    'bomb_range':1,'alive':True,'dir':'down','frame':0,'dead_step':0}
        self.p2 = {'pos':[GRID_SIZE-2,GRID_SIZE-2],'score':0,'lives':5,'max_bombs':1,
                    'active_bombs':0,'bomb_range':1,'alive':False,'dir':'up','frame':0,'dead_step':0}
        self.bombs_list = []
        self.explosions_list = []
        self.enemies = []
        self.varas_list = []
        self.mokuton_list = []
        self.madara_limbo = []
        self.madara_dragones = []
        self.madara_clones = []
        self.meteorito = None
        self.boss_pain_aparecio = False
        self.cinematica_mostrada = False
        self.shinra_epico_timer = 0
        self.shinra_sfx_pendiente = False
        self.limbo_blink = 0
        self.pending_messages = []
        self.game_over_msg = None
        self.level_complete_msg = None
        self.victory_msg = None

    def queue_msg(self, title, text):
        self.pending_messages.append((title, text))

    def start_new_game(self, mode):
        self.mode = mode
        self.current_level = 1
        self.boss_pain_aparecio = False
        self.cinematica_mostrada = False
        self.shinra_sfx_pendiente = False
        is_2p = mode in ["2P_COOP", "2P_VS"]
        self.p1 = {'pos':[1,1],'score':0,'lives':5,'max_bombs':1,'active_bombs':0,
                    'bomb_range':1,'alive':True,'dir':'down','frame':0,'dead_step':0}
        self.p2 = {'pos':[GRID_SIZE-2,GRID_SIZE-2],'score':0,'lives':5,'max_bombs':1,
                    'active_bombs':0,'bomb_range':1,'alive':is_2p,'dir':'up','frame':0,'dead_step':0}
        self.load_level()

    def ir_directo_pain(self):
        self.mode = "1P"
        self.current_level = PAIN_LEVEL
        self.p1 = {'pos':[1,1],'score':0,'lives':5,'max_bombs':2,'active_bombs':0,
                    'bomb_range':2,'alive':True,'dir':'down','frame':0,'dead_step':0}
        self.p2.update({'alive': False})
        self.load_level()
        self.enemies.clear()
        self.boss_pain_aparecio = True
        self.spawn_jefe_nivel4()

    def ir_directo_madara(self):
        self.mode = "1P"
        self.current_level = FINAL_BOSS_LEVEL
        self.p1 = {'pos':[1,1],'score':0,'lives':5,'max_bombs':2,'active_bombs':0,
                    'bomb_range':2,'alive':True,'dir':'down','frame':0,'dead_step':0}
        self.p2.update({'alive': False})
        self.load_level()

    def load_level(self):
        start_music(force=True)
        self.shinra_epico_timer = 0
        self.varas_list.clear()
        self.p1['pos'] = [1, 1]
        self.p1['active_bombs'] = 0
        if self.mode in ["2P_COOP", "2P_VS"]:
            self.p2['pos'] = [GRID_SIZE-2, GRID_SIZE-2]
            self.p2['active_bombs'] = 0
        self.time_left = 180
        self.bombs_list.clear()
        self.explosions_list.clear()
        self.mokuton_list.clear()
        self.madara_limbo.clear()
        self.madara_dragones.clear()
        self.madara_clones.clear()
        self.meteorito = None
        self.boss = None
        self.game_over_msg = None
        self.level_complete_msg = None
        self.victory_msg = None
        self.init_map()
        if self.current_level == FINAL_BOSS_LEVEL and self.mode != "2P_VS":
            self.enemies.clear()
            self.spawn_jefe_nivel5()
        else:
            num = 0 if self.mode == "2P_VS" else self.current_level + 1
            self.spawn_enemies(num)
        self.game_running = True

    def next_level(self):
        self.game_running = False
        if self.current_level == FINAL_BOSS_LEVEL:
            play_sound("win")
            self.victory_msg = f"¡Has derrotado al Jefe Final!\nPuntuación: {self.p1['score']} pts"
            return
        self.current_level += 1
        if self.current_level % 3 == 0:
            if self.p1['alive']: self.p1['lives'] += 1
            if self.p2['alive']: self.p2['lives'] += 1
        play_sound("win")
        self.level_complete_msg = f"¡Avanzas al NIVEL {self.current_level}!"

    def init_map(self):
        self.map_grid = [[EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        safe = [(1,1),(1,2),(2,1),(GRID_SIZE//2,GRID_SIZE//2)]
        if self.mode in ["2P_COOP","2P_VS"]:
            safe.extend([(GRID_SIZE-2,GRID_SIZE-2),(GRID_SIZE-2,GRID_SIZE-3),(GRID_SIZE-3,GRID_SIZE-2)])
        density = 0.3 if self.current_level == FINAL_BOSS_LEVEL else min(0.75, 0.5 + self.current_level * 0.03)
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if r == 0 or r == GRID_SIZE-1 or c == 0 or c == GRID_SIZE-1 or (r%2==0 and c%2==0):
                    self.map_grid[r][c] = WALL_SOLID
                elif (r,c) not in safe and random.random() < density:
                    self.map_grid[r][c] = WALL_DESTRUCTIBLE

    def spawn_enemies(self, count):
        self.enemies.clear()
        if count <= 0: return
        valid = []
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                far1 = (abs(r-1)+abs(c-1)) > 4
                far2 = True if self.mode=="1P" else (abs(r-(GRID_SIZE-2))+abs(c-(GRID_SIZE-2))) > 4
                if self.map_grid[r][c] == EMPTY and far1 and far2:
                    valid.append([r, c])
        random.shuffle(valid)
        for i in range(min(count, len(valid))):
            self.enemies.append({'pos': valid[i], 'move_timer': 0})

    def can_move(self, r, c):
        return 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE and self.map_grid[r][c] in [EMPTY, EXPLOSION, POWERUP_RANGE, POWERUP_BOMB, POWERUP_LIFE]

    def place_bomb(self, player, owner_id):
        r, c = player['pos']
        if player['active_bombs'] < player['max_bombs'] and self.map_grid[r][c] == EMPTY:
            self.map_grid[r][c] = BOMBA
            self.bombs_list.append({'pos':[r,c],'timer':25,'owner':owner_id,'range':player['bomb_range']})
            player['active_bombs'] += 1

    def update_bombs(self):
        for bomb in self.bombs_list[:]:
            bomb['timer'] -= 1
            if bomb['timer'] <= 0:
                self.explode_bomb(bomb)
                self.bombs_list.remove(bomb)
                owner = self.p1 if bomb['owner'] == 1 else self.p2
                owner['active_bombs'] = max(0, owner['active_bombs'] - 1)

    def explode_bomb(self, bomb):
        play_sound("explosion")
        br, bc = bomb['pos']
        owner = self.p1 if bomb['owner'] == 1 else self.p2
        self.map_grid[br][bc] = EXPLOSION
        self.explosions_list.append({'pos':[br,bc],'timer':5})
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            for i in range(1, bomb['range']+1):
                nr, nc = br+dr*i, bc+dc*i
                if not (0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE): break
                if self.map_grid[nr][nc] == WALL_SOLID: break
                if self.map_grid[nr][nc] == WALL_DESTRUCTIBLE:
                    rand = random.random()
                    if rand < 0.25: self.map_grid[nr][nc] = POWERUP_RANGE
                    elif rand < 0.45: self.map_grid[nr][nc] = POWERUP_BOMB
                    elif rand < 0.55: self.map_grid[nr][nc] = POWERUP_LIFE
                    else: self.map_grid[nr][nc] = EXPLOSION
                    self.explosions_list.append({'pos':[nr,nc],'timer':5})
                    owner['score'] += 10
                    break
                if self.map_grid[nr][nc] in [EMPTY, POWERUP_RANGE, POWERUP_BOMB, POWERUP_LIFE]:
                    self.map_grid[nr][nc] = EXPLOSION
                    self.explosions_list.append({'pos':[nr,nc],'timer':5})

    def update_explosions(self):
        for exp in self.explosions_list[:]:
            exp['timer'] -= 1
            if exp['timer'] <= 0:
                r, c = exp['pos']
                if self.map_grid[r][c] == EXPLOSION: self.map_grid[r][c] = EMPTY
                self.explosions_list.remove(exp)

    def update_enemies(self):
        if not self.enemies: return
        speed = 4
        for enemy in self.enemies[:]:
            enemy['move_timer'] += 1
            if enemy['move_timer'] >= speed:
                enemy['move_timer'] = 0
                er, ec = enemy['pos']
                target = None
                min_dist = 999
                for p in [self.p1, self.p2]:
                    if p['alive']:
                        d = abs(er-p['pos'][0])+abs(ec-p['pos'][1])
                        if d < min_dist: min_dist = d; target = p['pos']
                if not target: continue
                pr, pc = target
                valid, destruct = [], []
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = er+dr, ec+dc
                    if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                        cell = self.map_grid[nr][nc]
                        if cell in [EMPTY,POWERUP_RANGE,POWERUP_BOMB,POWERUP_LIFE,EXPLOSION]:
                            valid.append((abs(nr-pr)+abs(nc-pc), [nr,nc]))
                        elif cell == WALL_DESTRUCTIBLE:
                            destruct.append([nr,nc])
                if valid:
                    valid.sort(key=lambda x: x[0])
                    enemy['pos'] = valid[0][1]
                elif destruct and random.random() < 0.3:
                    br, bc = random.choice(destruct)
                    self.map_grid[br][bc] = EMPTY

    def check_powerup_pickup(self, player):
        pr, pc = player['pos']
        cell = self.map_grid[pr][pc]
        if cell == POWERUP_RANGE: player['bomb_range'] += 1; player['score'] += 50; self.map_grid[pr][pc] = EMPTY
        elif cell == POWERUP_BOMB: player['max_bombs'] += 1; player['score'] += 50; self.map_grid[pr][pc] = EMPTY
        elif cell == POWERUP_LIFE: player['lives'] += 1; player['score'] += 50; self.map_grid[pr][pc] = EMPTY

    def player_hit(self, player, respawn_pos):
        player['lives'] -= 1
        player['pos'] = list(respawn_pos)
        player['dead_step'] = 0
        if player['lives'] <= 0: player['alive'] = False

    def spawn_jefe_nivel4(self):
        centro = GRID_SIZE // 2
        for dr in range(-3, 4):
            for dc in range(-3, 4):
                r, c = centro+dr, centro+dc
                if 0 < r < GRID_SIZE-1 and 0 < c < GRID_SIZE-1:
                    if self.map_grid[r][c] == WALL_DESTRUCTIBLE:
                        self.map_grid[r][c] = EMPTY
        self.boss = {'pos':[centro,centro],'hp':10,'max_hp':10,'move_timer':0,'attack_timer':0,
                     'big':True,'invuln':0,'tipo':'pain','elevado':0,'shinra_carga':0,
                     'fase':'subir','fase_tick':0,'varas_timer':0,'chibaku_activo':0,
                     'chibaku_timer':0,'chibaku_cool':0,'chibaku_ya_golpeo':0,
                     'dir':'down','frame':0}
        play_sound("boss_alert")
        start_pain_music()
        self.queue_msg("¡PAIN!", "¡Nivel 5: aparece PAIN!\n¡Aguanta 10 bombazos!")

    def spawn_jefe_nivel5(self):
        centro = GRID_SIZE // 2
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                r, c = centro+dr, centro+dc
                if 0 < r < GRID_SIZE-1 and 0 < c < GRID_SIZE-1:
                    if self.map_grid[r][c] == WALL_DESTRUCTIBLE:
                        self.map_grid[r][c] = EMPTY
        self.boss = {'pos':[centro,centro],'hp':8,'max_hp':8,'move_timer':0,'attack_timer':0,
                     'big':True,'invuln':0,'tipo':'madara','fase2':False,'dir':'down',
                     'susanoo':0,'susanoo_crece':20,'escudo_timer':0,'escudo_cooldown':0,
                     'chakra':0.0,'chakra_activo':False,'chakra_timer':0,
                     'mokuton':None,'mokuton_timer':0,'dragon_timer':0,'clone_timer':0}
        play_sound("boss_alert")
        start_boss_music()
        self.queue_msg("¡MADARA EDO TENSEI!", "¡NIVEL FINAL: MADARA con 8 VIDAS!\n¡SUERTE!")

    def entrar_fase2(self):
        self.boss.update({'tipo':'madara_edo','fase2':True,'hp':12,'max_hp':12,'invuln':0,
                          'susanoo':0,'susanoo_crece':20,'escudo_timer':0,'escudo_cooldown':0,
                          'chakra':0.0,'chakra_activo':False,'chakra_timer':0,
                          'mokuton':None,'mokuton_timer':0,'dragon_timer':0,'clone_timer':0})
        self.mokuton_list.clear(); self.madara_limbo.clear()
        self.madara_dragones.clear(); self.madara_clones.clear(); self.meteorito = None
        play_sound("boss_alert"); start_boss_music()
        self.queue_msg("¡MADARA RIKUDO!", "¡12 VIDAS y LIMBO!\n¡Destrúyelas!")
        for _ in range(4): self.spawn_limbo_copy()

    def spawn_limbo_copy(self):
        ref = self.p1['pos'] if self.p1['alive'] else self.p2['pos']
        spots = []
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.map_grid[r][c] == EMPTY and (abs(r-ref[0])+abs(c-ref[1])) > 6:
                    spots.append([r,c])
        if spots:
            r, c = random.choice(spots)
            self.madara_limbo.append({'pos':[r,c],'move_timer':0,'hp':2})

    def _moverse_hacia(self, pos, goal):
        er, ec = pos; pr, pc = goal
        moves = []
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = er+dr, ec+dc
            if self.can_move(nr, nc):
                moves.append((abs(nr-pr)+abs(nc-pc), [nr,nc]))
        if moves:
            moves.sort(key=lambda x: x[0])
            pos[0], pos[1] = moves[0][1]

    def update_boss(self):
        if not self.boss: return
        if self.boss.get('invuln',0) > 0: self.boss['invuln'] -= 1
        umbral = 5 if self.boss.get('big') else 2
        if self.boss.get('chakra_activo'): umbral = 3
        if not (self.boss.get('tipo')=='pain' and (self.boss.get('elevado',0)>0 or self.boss.get('chibaku_activo',0)>0)):
            self.boss['move_timer'] += 1
            if self.boss['move_timer'] >= umbral:
                self.boss['move_timer'] = 0
                br, bc = self.boss['pos']
                tp = self.p1['pos'] if self.p1['alive'] else self.p2['pos']
                pr, pc = tp
                valid_moves = []
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = br+dr, bc+dc
                    if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                        if self.map_grid[nr][nc] == EMPTY:
                            valid_moves.append((abs(nr-pr)+abs(nc-pc), [nr,nc]))
                        elif self.map_grid[nr][nc] == EXPLOSION:
                            if self.boss.get('tipo') != 'pain':
                                valid_moves.append((abs(nr-pr)+abs(nc-pc), [nr,nc]))
                        elif self.map_grid[nr][nc] == WALL_DESTRUCTIBLE:
                            if self.boss.get('tipo') != 'pain':
                                self.map_grid[nr][nc] = EMPTY
                if valid_moves:
                    valid_moves.sort(key=lambda x: x[0])
                    nv = valid_moves[0][1]
                    if self.boss.get('tipo') in ('pain','madara','madara_edo'):
                        mdr, mdc = nv[0]-br, nv[1]-bc
                        if mdr>0: self.boss['dir']='down'
                        elif mdr<0: self.boss['dir']='up'
                        elif mdc>0: self.boss['dir']='right'
                        elif mdc<0: self.boss['dir']='left'
                    self.boss['pos'] = nv

        if self.boss.get('tipo') == 'pain':
            self.boss['frame'] = self.boss.get('frame',0)+1
            if self.boss.get('chibaku_activo',0) > 0:
                self.boss['chibaku_timer'] = self.boss.get('chibaku_timer',60)-1
                self.update_chibaku()
                if self.boss['chibaku_timer'] <= 0:
                    self.explosion_chibaku()
                    self.boss['chibaku_activo'] = 0
                    self.boss['chibaku_ya_golpeo'] = 0
                    self.boss['chibaku_cool'] = 0
            elif self.boss.get('elevado',0) == 0:
                self.boss['shinra_carga'] = self.boss.get('shinra_carga',0)+1
                self.boss['chibaku_cool'] = self.boss.get('chibaku_cool',0)+1
                if self.boss['chibaku_cool'] >= 120 and self.boss['shinra_carga'] < 70:
                    self.boss['chibaku_activo'] = 1
                    self.boss['chibaku_timer'] = 60
                    play_chibaku_sfx()
                elif self.boss['shinra_carga'] >= 70:
                    self.boss['elevado'] = 1; self.boss['fase']='subir'; self.boss['fase_tick']=0
                self.boss['varas_timer'] = self.boss.get('varas_timer',0)+1
                if self.boss['varas_timer'] >= 30:
                    self.boss['varas_timer'] = 0; self.lanzar_vara()
            else:
                self.boss['fase_tick'] = self.boss.get('fase_tick',0)+1
                fase = self.boss.get('fase','subir')
                if fase=='subir' and self.boss['fase_tick']>=18:
                    self.boss['fase']='flotar'; self.boss['fase_tick']=0
                elif fase=='flotar' and self.boss['fase_tick']>=24:
                    br, bc = self.boss['pos']
                    self.explosion_10x10(br, bc, con_sfx=not self.cinematica_mostrada)
                    if not self.cinematica_mostrada:
                        self.cinematica_mostrada = True
                        self.shinra_sfx_pendiente = True
                    self.shinra_epico_timer = 6
                    self.boss['fase']='bajar'; self.boss['fase_tick']=0
                elif fase=='bajar' and self.boss['fase_tick']>=18:
                    self.boss['elevado']=0; self.boss['shinra_carga']=0; self.boss['fase_tick']=0
        elif self.boss.get('tipo') in ('madara','madara_edo'):
            self.update_madara()

    def lanzar_vara(self):
        br, bc = self.boss['pos']
        obj = self.p1['pos'] if self.p1['alive'] else self.p2['pos']
        pr, pc = obj
        if abs(pr-br)>=abs(pc-bc): dr, dc = (1 if pr>br else -1), 0
        else: dr, dc = 0, (1 if pc>bc else -1)
        self.varas_list.append({'pos':[br+dr,bc+dc],'dr':dr,'dc':dc,'avance':0,'max':3})

    def update_varas(self):
        for vara in self.varas_list[:]:
            vr, vc = vara['pos']
            if self.p1['alive'] and [vr,vc]==self.p1['pos']: self.player_hit(self.p1,[1,1])
            if self.mode in ["2P_COOP","2P_VS"] and self.p2['alive'] and [vr,vc]==self.p2['pos']:
                self.player_hit(self.p2,[GRID_SIZE-2,GRID_SIZE-2])
            if vara['avance'] >= vara['max']:
                self.varas_list.remove(vara); continue
            nr, nc = vr+vara['dr'], vc+vara['dc']
            if not (0<=nr<GRID_SIZE and 0<=nc<GRID_SIZE):
                self.varas_list.remove(vara); continue
            celda = self.map_grid[nr][nc]
            if celda in [WALL_DESTRUCTIBLE, WALL_SOLID]:
                self.map_grid[nr][nc] = EXPLOSION
                self.explosions_list.append({'pos':[nr,nc],'timer':6})
                self.varas_list.remove(vara)
            elif celda in [EMPTY,EXPLOSION,POWERUP_RANGE,POWERUP_BOMB,POWERUP_LIFE]:
                vara['pos'] = [nr,nc]; vara['avance'] += 1
            else: self.varas_list.remove(vara)

    def update_chibaku(self):
        br, bc = self.boss['pos']
        for player in (self.p1, self.p2):
            if not player['alive']: continue
            pr, pc = player['pos']
            if abs(pr-br)>5 or abs(pc-bc)>5: continue
            if pr==br and pc==bc:
                if not self.boss.get('chibaku_ya_golpeo',0):
                    self.boss['chibaku_ya_golpeo'] = 1; self.player_hit(player,[1,1])
                continue
            if abs(pr-br)>=abs(pc-bc):
                nr, nc = pr+(1 if pr<br else -1), pc
            else: nr, nc = pr, pc+(1 if pc<bc else -1)
            if 0<=nr<GRID_SIZE and 0<=nc<GRID_SIZE and self.can_move(nr,nc):
                player['pos'] = [nr,nc]

    def explosion_chibaku(self):
        play_sound("explosion")
        br, bc = self.boss['pos']; medio = 5
        base_r = max(0, min(br-medio, GRID_SIZE-1))
        base_c = max(0, min(bc-medio, GRID_SIZE-1))
        alto = min(GRID_SIZE-base_r, medio*2); ancho = min(GRID_SIZE-base_c, medio*2)
        for dr in range(alto):
            for dc in range(ancho):
                nr, nc = base_r+dr, base_c+dc
                if nr==br and nc==bc: continue
                if self.map_grid[nr][nc]==WALL_SOLID: continue
                if self.map_grid[nr][nc]==WALL_DESTRUCTIBLE:
                    self.map_grid[nr][nc]=EXPLOSION; self.p1['score']+=10
                elif self.map_grid[nr][nc] in [EMPTY,POWERUP_RANGE,POWERUP_BOMB,POWERUP_LIFE]:
                    self.map_grid[nr][nc]=EXPLOSION
                if self.map_grid[nr][nc]==EXPLOSION:
                    self.explosions_list.append({'pos':[nr,nc],'timer':8})

    def explosion_10x10(self, r, c, con_sfx=True):
        if con_sfx: play_sound("explosion"); play_shinra_sfx()
        medio = 5
        base_r = max(0,min(r-medio,GRID_SIZE-1)); base_c = max(0,min(c-medio,GRID_SIZE-1))
        alto = min(GRID_SIZE-base_r,medio*2); ancho = min(GRID_SIZE-base_c,medio*2)
        for dr in range(alto):
            for dc in range(ancho):
                nr, nc = base_r+dr, base_c+dc
                if nr==r and nc==c: continue
                if self.map_grid[nr][nc]==WALL_SOLID: continue
                if self.map_grid[nr][nc]==WALL_DESTRUCTIBLE:
                    self.map_grid[nr][nc]=EXPLOSION; self.p1['score']+=10
                elif self.map_grid[nr][nc] in [EMPTY,POWERUP_RANGE,POWERUP_BOMB,POWERUP_LIFE]:
                    self.map_grid[nr][nc]=EXPLOSION
                if self.map_grid[nr][nc]==EXPLOSION:
                    self.explosions_list.append({'pos':[nr,nc],'timer':7})

    def update_madara(self):
        b = self.boss
        b['frame'] = b.get('frame',0)+1
        pot = bool(b.get('chakra_activo'))
        b['attack_timer'] = b.get('attack_timer',0)+1
        if b['attack_timer'] >= 24:
            b['attack_timer'] = 0; self.taijutsu_strike()
        b['escudo_timer'] = max(0,b.get('escudo_timer',0)-1)
        b['escudo_cooldown'] = b.get('escudo_cooldown',0)+1
        if b.get('escudo_timer',0)<=0 and b.get('escudo_cooldown',0)>=140:
            b['escudo_cooldown']=0; b['escudo_timer']=80; b['susanoo']=3; b['susanoo_crece']=0
            play_sound("boss_alert")
        if b.get('susanoo',0)>0 and b.get('susanoo_crece',20)<20: b['susanoo_crece']+=1
        if pot:
            b['chakra_timer']=b.get('chakra_timer',0)+1
            if b['chakra_timer']>=60:
                b['chakra_activo']=False; b['chakra']=0.0; b['chakra_timer']=0
        else:
            b['chakra']=min(1.0,b.get('chakra',0.0)+1.0/150.0)
            if b['chakra']>=1.0:
                b['chakra_activo']=True; b['chakra_timer']=0; play_sound("boss_alert")
        b['mokuton_timer']=b.get('mokuton_timer',0)+1
        cadencia = 40 if pot else 60
        if b['mokuton'] is None and b['mokuton_timer']>=cadencia:
            b['mokuton_timer']=0
            br,bc=b['pos']; obj=self.p1['pos'] if self.p1['alive'] else self.p2['pos']
            pr,pc=obj
            if abs(pr-br)>=abs(pc-bc): dr,dc=(1 if pr>br else -1),0
            else: dr,dc=0,(1 if pc>bc else -1)
            b['mokuton']={'br':br,'bc':bc,'dr':dr,'dc':dc,'pr':-dc,'pc':dr,'step':0}
            play_sound("boss_alert")
        elif b['mokuton'] is not None:
            self.advance_mokuton(b['mokuton'])
            if pot and b['mokuton'] is not None: self.advance_mokuton(b['mokuton'])
        b['dragon_timer']=b.get('dragon_timer',0)+1
        cd = 60 if pot else 80
        if b['dragon_timer']>=cd:
            b['dragon_timer']=0; br,bc=b['pos']
            obj=self.p1['pos'] if self.p1['alive'] else self.p2['pos']
            pr,pc=obj
            if abs(pr-br)>=abs(pc-bc): dr,dc=(1 if pr>br else -1),0
            else: dr,dc=0,(1 if pc>bc else -1)
            cabeza=[br+dr,bc+dc]
            if not(0<=cabeza[0]<GRID_SIZE and 0<=cabeza[1]<GRID_SIZE): cabeza=[br,bc]
            segs=[]
            for i in range(5):
                rr=max(0,min(cabeza[0]-dr*i,GRID_SIZE-1))
                cc=max(0,min(cabeza[1]-dc*i,GRID_SIZE-1))
                if [rr,cc] not in segs: segs.append([rr,cc])
            if not segs: segs=[list(b['pos'])]
            self.madara_dragones.append({'segments':segs,'move_timer':0,'timer':50})
            play_sound("boss_alert")
        for drag in self.madara_dragones[:]:
            drag['timer']-=1
            if drag['timer']<=0: self.madara_dragones.remove(drag); continue
            for seg in drag['segments']:
                for p in (self.p1,self.p2):
                    if p['alive'] and seg==p['pos']:
                        self.player_hit(p,[1,1] if p is self.p1 else [GRID_SIZE-2,GRID_SIZE-2])
            drag['move_timer']+=1
            if drag['move_timer']<(3 if pot else 4): continue
            drag['move_timer']=0; target=None; md=999
            for p in (self.p1,self.p2):
                if p['alive']:
                    d=abs(drag['segments'][0][0]-p['pos'][0])+abs(drag['segments'][0][1]-p['pos'][1])
                    if d<md: md=d; target=p['pos']
            if target:
                ant=[s[:] for s in drag['segments']]
                self._moverse_hacia(drag['segments'][0],target)
                for i in range(1,len(drag['segments'])): drag['segments'][i]=ant[i-1]
        b['clone_timer']=b.get('clone_timer',0)+1
        if b['clone_timer']>=120:
            b['clone_timer']=0; br,bc=b['pos']
            for dr,dc in [(-2,0),(2,0),(0,-2),(0,2)]:
                nr,nc=br+dr,bc+dc
                if 0<=nr<GRID_SIZE and 0<=nc<GRID_SIZE and self.can_move(nr,nc):
                    self.madara_clones.append({'pos':[nr,nc],'move_timer':0,'timer':60})
            play_sound("boss_alert")
        for clon in self.madara_clones[:]:
            clon['timer']-=1
            if clon['timer']<=0: self.madara_clones.remove(clon); continue
            for p in (self.p1,self.p2):
                if p['alive'] and clon['pos']==p['pos']:
                    self.player_hit(p,[1,1] if p is self.p1 else [GRID_SIZE-2,GRID_SIZE-2])
            clon['move_timer']+=1
            if clon['move_timer']<(3 if pot else 5): continue
            clon['move_timer']=0; target=None; md=999
            for p in (self.p1,self.p2):
                if p['alive']:
                    d=abs(clon['pos'][0]-p['pos'][0])+abs(clon['pos'][1]-p['pos'][1])
                    if d<md: md=d; target=p['pos']
            if target: self._moverse_hacia(clon['pos'],target)
        if b.get('fase2'): self.update_limbo()
        for celda in self.mokuton_list[:]:
            celda['timer']-=1
            if celda['timer']<=0: self.mokuton_list.remove(celda)

    def advance_mokuton(self, onda):
        onda['step']+=1
        if onda['step']>4: self.boss['mokuton']=None; return
        br,bc=onda['br'],onda['bc']; dr,dc=onda['dr'],onda['dc']; pr,pc=onda['pr'],onda['pc']
        ancho=onda['step']*2-1
        for offset in range(-(ancho//2),ancho//2+1):
            nr=br+dr*onda['step']+pr*offset; nc=bc+dc*onda['step']+pc*offset
            if 0<=nr<GRID_SIZE and 0<=nc<GRID_SIZE:
                if self.map_grid[nr][nc]==WALL_SOLID: continue
                if self.map_grid[nr][nc]==WALL_DESTRUCTIBLE:
                    self.map_grid[nr][nc]=EXPLOSION
                    self.explosions_list.append({'pos':[nr,nc],'timer':5})
                    self.p1['score']+=10; continue
                self.mokuton_list.append({'pos':[nr,nc],'timer':3})
                for p in (self.p1,self.p2):
                    if p['alive'] and [nr,nc]==p['pos']:
                        self.player_hit(p,[1,1] if p is self.p1 else [GRID_SIZE-2,GRID_SIZE-2])

    def taijutsu_strike(self):
        br,bc=self.boss['pos']
        for p in (self.p1,self.p2):
            if p['alive']:
                pr,pc=p['pos']
                if abs(pr-br)+abs(pc-bc)<=2:
                    self.player_hit(p,[1,1] if p is self.p1 else [GRID_SIZE-2,GRID_SIZE-2]); return
        cand=[]
        for dr,dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr,nc=br+dr,bc+dc
            if 0<=nr<GRID_SIZE and 0<=nc<GRID_SIZE and self.map_grid[nr][nc]==WALL_DESTRUCTIBLE:
                cand.append([nr,nc])
        if cand:
            nr,nc=random.choice(cand)
            self.map_grid[nr][nc]=EXPLOSION
            self.explosions_list.append({'pos':[nr,nc],'timer':5}); self.p1['score']+=10

    def update_limbo(self):
        self.limbo_blink+=1
        if len(self.madara_limbo)<4 and self.limbo_blink%30==0: self.spawn_limbo_copy()
        speed=5
        for copia in self.madara_limbo[:]:
            for p in (self.p1,self.p2):
                if p['alive'] and copia['pos']==p['pos']:
                    self.player_hit(p,[1,1] if p is self.p1 else [GRID_SIZE-2,GRID_SIZE-2])
            copia['move_timer']+=1
            if copia['move_timer']<speed: continue
            copia['move_timer']=0; target=None; md=999
            for p in (self.p1,self.p2):
                if p['alive']:
                    d=abs(copia['pos'][0]-p['pos'][0])+abs(copia['pos'][1]-p['pos'][1])
                    if d<md: md=d; target=p['pos']
            if target: self._moverse_hacia(copia['pos'],target)

    def check_collisions(self):
        if self.boss:
            br,bc=self.boss['pos']
            if self.map_grid[br][bc]==EXPLOSION and self.boss.get('invuln',0)<=0:
                self.boss['invuln']=14
                if self.boss.get('tipo') in ('madara','madara_edo') and \
                   self.boss.get('escudo_timer',0)>0 and self.boss.get('susanoo',0)>0:
                    self.boss['susanoo']-=1; self.p1['score']+=200
                    if self.boss['susanoo']<=0:
                        self.boss['escudo_timer']=0; self.boss['susanoo_crece']=20
                else:
                    self.boss['hp']-=1; self.p1['score']+=200
                    if self.boss['hp']<=0:
                        self.p1['score']+=500
                        if self.boss.get('tipo')=='madara' and not self.boss.get('fase2'):
                            self.entrar_fase2()
                        else:
                            self.boss=None; start_music(force=True)
            if self.boss and self.p1['alive'] and br==self.p1['pos'][0] and bc==self.p1['pos'][1]:
                if not (self.boss.get('tipo')=='pain' and self.boss.get('chibaku_activo',0)):
                    self.player_hit(self.p1,[1,1])
        for copia in self.madara_limbo[:]:
            cr,cc=copia['pos']
            if self.map_grid[cr][cc]==EXPLOSION:
                copia['hp']=copia.get('hp',2)-1
                if copia['hp']<=0: self.madara_limbo.remove(copia); self.p1['score']+=100
        for enemy in self.enemies[:]:
            er,ec=enemy['pos']
            if self.map_grid[er][ec]==EXPLOSION:
                self.enemies.remove(enemy); self.p1['score']+=100
            if self.p1['alive'] and er==self.p1['pos'][0] and ec==self.p1['pos'][1]:
                self.player_hit(self.p1,[1,1])
            if self.mode in ["2P_COOP","2P_VS"] and self.p2['alive'] and er==self.p2['pos'][0] and ec==self.p2['pos'][1]:
                self.player_hit(self.p2,[GRID_SIZE-2,GRID_SIZE-2])
        if self.p1['alive'] and self.map_grid[self.p1['pos'][0]][self.p1['pos'][1]]==EXPLOSION:
            self.player_hit(self.p1,[1,1])
        if self.mode in ["2P_COOP","2P_VS"] and self.p2['alive'] and self.map_grid[self.p2['pos'][0]][self.p2['pos'][1]]==EXPLOSION:
            self.player_hit(self.p2,[GRID_SIZE-2,GRID_SIZE-2])

    def check_win_conditions(self):
        if self.mode == "1P":
            if not self.p1['alive']: self.game_running=False; self.game_over_msg="¡Has sido eliminado!"
            elif len(self.enemies)==0 and not self.boss:
                if self.current_level==PAIN_LEVEL and not self.boss_pain_aparecio:
                    self.boss_pain_aparecio=True; self.spawn_jefe_nivel4()
                else: self.next_level()
        elif self.mode == "2P_COOP":
            if not self.p1['alive'] and not self.p2['alive']:
                self.game_running=False; self.game_over_msg="¡Ambos cayeron!"
            elif len(self.enemies)==0 and not self.boss:
                if self.current_level==PAIN_LEVEL and not self.boss_pain_aparecio:
                    self.boss_pain_aparecio=True; self.spawn_jefe_nivel4()
                else: self.next_level()
        elif self.mode == "2P_VS":
            if not self.p1['alive'] and not self.p2['alive']:
                self.game_running=False; self.game_over_msg="¡EMPATE!"
            elif not self.p1['alive']:
                self.game_running=False; self.game_over_msg="¡VICTORIA P2!"
            elif not self.p2['alive']:
                self.game_running=False; self.game_over_msg="¡VICTORIA P1!"


class GameWidget(Widget):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref
        self.core = GameCore()
        self.tile = float(TILE_BASE)
        self.dir_held = None
        self.move_cooldown = 0
        self.bomb_pressed = False
        self._draw_job = None

        Window.bind(on_key_down=self._on_key_down)
        Window.bind(on_key_up=self._on_key_up)

    def start_mode(self, mode):
        self.core.start_new_game(mode)
        self._process_messages()

    def start_pain(self):
        self.core.ir_directo_pain()
        self._process_messages()

    def start_madara(self):
        self.core.ir_directo_madara()
        self._process_messages()

    def _on_key_down(self, window, key, scancode, codepoint, modifiers):
        if not self.core.game_running: return
        k = (codepoint or '').lower()
        if k == 'm':
            set_music_enabled(not MUSIC_ENABLED); return
        if self.core.p1['alive']:
            if k == 'w': self.dir_held = 'up'
            elif k == 's': self.dir_held = 'down'
            elif k == 'a': self.dir_held = 'left'
            elif k == 'd': self.dir_held = 'right'
            elif k == ' ':
                self.core.place_bomb(self.core.p1, 1); play_sound("bomb")
        if self.core.mode in ["2P_COOP","2P_VS"] and self.core.p2['alive']:
            if key == 273: self._p2_dir = 'up'
            elif key == 274: self._p2_dir = 'down'
            elif key == 275: self._p2_dir = 'right'
            elif key == 276: self._p2_dir = 'left'
            elif key in (13, 370):
                self.core.place_bomb(self.core.p2, 2); play_sound("bomb")

    def _on_key_up(self, window, key, scancode):
        self.dir_held = None

    def move_player(self, player, direction, owner_id):
        r, c = player['pos']
        moved = False
        if direction == 'up' and self.core.can_move(r-1,c):
            player['pos'][0]-=1; player['dir']='up'; moved=True
        elif direction == 'down' and self.core.can_move(r+1,c):
            player['pos'][0]+=1; player['dir']='down'; moved=True
        elif direction == 'left' and self.core.can_move(r,c-1):
            player['pos'][1]-=1; player['dir']='left'; moved=True
        elif direction == 'right' and self.core.can_move(r,c+1):
            player['pos'][1]+=1; player['dir']='right'; moved=True
        if moved:
            player['frame'] = 1 - player.get('frame', 0)
            self.core.check_powerup_pickup(player)

    def tick(self, dt):
        if not self.core.game_running: return
        if self.move_cooldown > 0: self.move_cooldown -= 1
        if self.dir_held and self.move_cooldown <= 0:
            self.move_player(self.core.p1, self.dir_held, 1)
            self.move_cooldown = 3
        self.core.update_bombs()
        self.core.update_explosions()
        self.core.update_enemies()
        self.core.update_boss()
        self.core.update_varas()
        self.core.check_collisions()
        self.core.check_win_conditions()
        if self.core.shinra_epico_timer > 0: self.core.shinra_epico_timer -= 1
        self._process_messages()
        self.canvas.clear()
        self._draw_game()

    def _process_messages(self):
        while self.core.pending_messages:
            t, txt = self.core.pending_messages.pop(0)
            self.app_ref.show_popup(t, txt)
        if self.core.game_over_msg:
            msg = self.core.game_over_msg; self.core.game_over_msg = None
            self.app_ref.show_popup("GAME OVER", msg, on_dismiss=self.app_ref.go_menu)
        if self.core.level_complete_msg:
            msg = self.core.level_complete_msg; self.core.level_complete_msg = None
            self.app_ref.show_popup("¡NIVEL COMPLETADO!", msg,
                                    on_dismiss=lambda: self.core.load_level())
        if self.core.victory_msg:
            msg = self.core.victory_msg; self.core.victory_msg = None
            self.app_ref.show_popup("¡VICTORIA!", msg, on_dismiss=self.app_ref.go_menu)

    def _g2c(self, row, col):
        return col * self.tile, (GRID_SIZE - 1 - row) * self.tile

    def _tex_size(self, key, size):
        tex = TEX.get(key)
        if not tex:
            return (size, size)
        tw, th = tex.size
        if tw == 0 or th == 0:
            return (size, size)
        aspect = tw / th
        if aspect >= 1:
            return (size, size / aspect)
        else:
            return (size * aspect, size)

    def _draw_game(self):
        c = self.core
        w, h = self.size
        t = min(w / GRID_SIZE, h / GRID_SIZE)
        self.tile = t
        ox = (w - GRID_SIZE * t) / 2
        oy = (h - GRID_SIZE * t) / 2

        with self.canvas:
            Color(0.11, 0.36, 0.13)
            Rectangle(pos=(0,0), size=(w,h))

            Color(0.18, 0.49, 0.2)
            for i in range(GRID_SIZE + 1):
                x = ox + i * t
                Line(points=[x, oy, x, oy + GRID_SIZE * t], width=1)
                y = oy + i * t
                Line(points=[ox, y, ox + GRID_SIZE * t, y], width=1)

            for r in range(GRID_SIZE):
                for col in range(GRID_SIZE):
                    x = ox + col * t
                    y = oy + (GRID_SIZE - 1 - r) * t
                    cell = c.map_grid[r][col]
                    if cell == WALL_SOLID:
                        tex = TEX.get('wall_solid')
                        if tex:
                            Color(1,1,1,1); Rectangle(texture=tex, pos=(x,y), size=(t,t))
                        else:
                            Color(0.15,0.2,0.22); Rectangle(pos=(x,y),size=(t,t))
                            Color(0,0.9,1,0.5); Line(points=[x,y,x+t,y+t],width=1)
                            Line(points=[x+t,y,x,y+t],width=1)
                    elif cell == WALL_DESTRUCTIBLE:
                        tex = TEX.get('wall_destructible')
                        if tex:
                            Color(1,1,1,1); Rectangle(texture=tex, pos=(x,y), size=(t,t))
                        else:
                            Color(0.85,0.26,0.08); Rectangle(pos=(x,y),size=(t,t))
                    elif cell == BOMBA:
                        tex = TEX.get('bomb')
                        if tex:
                            Color(1,1,1,1); Rectangle(texture=tex, pos=(x,y), size=(t,t))
                        else:
                            Color(0.13,0.13,0.13); Ellipse(pos=(x+t*0.15,y+t*0.2),size=(t*0.7,t*0.65))
                    elif cell == EXPLOSION:
                        tex = TEX.get('explosion')
                        if tex:
                            Color(1,1,1,1); Rectangle(texture=tex, pos=(x,y), size=(t,t))
                        else:
                            Color(1,0.57,0); Rectangle(pos=(x,y),size=(t,t))
                            Color(1,0.24,0); Rectangle(pos=(x+t*0.15,y+t*0.15),size=(t*0.7,t*0.7))
                            Color(1,0.92,0); Rectangle(pos=(x+t*0.3,y+t*0.3),size=(t*0.4,t*0.4))
                    elif cell == POWERUP_RANGE:
                        Color(1,0.92,0); Rectangle(pos=(x+t*0.15,y+t*0.15),size=(t*0.7,t*0.7),outline=(1,1,1))
                        Color(1,0.36,0); Ellipse(pos=(x+t*0.3,y+t*0.2),size=(t*0.4,t*0.6))
                    elif cell == POWERUP_BOMB:
                        Color(1,0.92,0); Rectangle(pos=(x+t*0.15,y+t*0.15),size=(t*0.7,t*0.7))
                        Color(0.13,0.13,0.13); Ellipse(pos=(x+t*0.25,y+t*0.25),size=(t*0.5,t*0.5))
                    elif cell == POWERUP_LIFE:
                        Color(0.94,0.33,0.31); Rectangle(pos=(x+t*0.15,y+t*0.15),size=(t*0.7,t*0.7))
                        Color(1,0.2,0.2)
                        cx2, cy2 = x+t*0.5, y+t*0.5; hr = t*0.2
                        Ellipse(pos=(cx2-hr,cy2-hr*0.6),size=(hr*2,hr*1.2))
                        Ellipse(pos=(cx2-hr*0.6,cy2-hr),size=(hr*1.2,hr*2))

            for cell_m in c.mokuton_list:
                mr, mc = cell_m['pos']
                mx = ox + mc * t; my = oy + (GRID_SIZE-1-mr) * t
                tex = TEX.get('madera')
                if tex:
                    Color(1,1,1,1); Rectangle(texture=tex, pos=(mx,my), size=(t,t))
                else:
                    Color(0.31,0.2,0.12); Rectangle(pos=(mx+t*0.1,my+t*0.1),size=(t*0.8,t*0.8))
                    Color(0.43,0.3,0.25); Ellipse(pos=(mx+t*0.3,my+t*0.3),size=(t*0.4,t*0.4))

            for enemy in c.enemies:
                er, ec = enemy['pos']
                ex = ox + ec * t; ey = oy + (GRID_SIZE-1-er) * t
                tex = TEX.get('enemy')
                if tex:
                    Color(1,1,1,1); Rectangle(texture=tex, pos=(ex,ey), size=(t,t))
                else:
                    Color(1,0.09,0.27); Ellipse(pos=(ex+t*0.1,ey+t*0.1),size=(t*0.8,t*0.8))

            if c.boss:
                br, bc = c.boss['pos']
                bx = ox + bc * t; by = oy + (GRID_SIZE-1-br) * t
                if c.boss.get('tipo') == 'pain':
                    elev = c.boss.get('elevado', 0)
                    if elev > 0:
                        fase = c.boss.get('fase','subir')
                        ft = c.boss.get('fase_tick',0)
                        ALTURA = t * 2.25
                        if fase=='subir': desp = ALTURA * min(1.0,ft/18.0)
                        elif fase=='flotar': desp = ALTURA
                        else: desp = ALTURA * (1.0 - min(1.0,ft/18.0))
                    else:
                        desp = 0
                    Color(0,0,0,0.3)
                    Ellipse(pos=(bx-t*0.25,by-t*0.1),size=(t*1.5,t*0.35))
                    tex = self._get_pain_sprite()
                    sz = t * 2
                    Color(1,1,1,1)
                    Rectangle(texture=tex, pos=(bx - t*0.5, by - t*0.5 - desp), size=(sz, sz))
                    hp = c.boss.get('hp',10); mhp = c.boss.get('max_hp',10)
                    hp_w = t * 1.65
                    hx = bx - t*0.5; hy = by + t*1.1 - desp
                    Color(0.07,0.07,0.07); Rectangle(pos=(hx,hy),size=(hp_w,t*0.25))
                    Color(0.9,0.22,0.21)
                    Rectangle(pos=(hx+1,hy+1),size=((hp_w-2)*max(0,min(1,hp/mhp)),t*0.25-2))
                    Color(1,1,1)
                    self._draw_text(hx+hp_w/2, hy+t*0.05, f"PAIN {hp}/{mhp}", int(t*0.35), (1,1,1))
                    if c.boss.get('chibaku_activo',0) > 0:
                        timer = max(0, c.boss.get('chibaku_timer',0))
                        p = max(0.0, min(1.0, (60-timer)/60.0))
                        radio = t*0.25 + t*0.85*p
                        cy = by - t*0.5 - desp - t*0.75 - t*3.25*p
                        Color(0.29,0.08,0.55)
                        Ellipse(pos=(bx+t*0.5-radio-t*0.15,cy-radio-t*0.15),size=(radio*2+t*0.3,radio*2+t*0.3))
                        Color(0,0,0)
                        Ellipse(pos=(bx+t*0.5-radio,cy-radio),size=(radio*2,radio*2))
                        Color(0.7,0.53,1)
                        self._draw_text(bx+t*0.5, cy, "X", int(t*0.4), (0.7,0.53,1))
                    if elev == 0:
                        carga = c.boss.get('shinra_carga',0)
                        porc = max(0,min(1,carga/70.0))
                        px2 = bx - t*0.5; py2 = by + t*1.6
                        Color(0.07,0.07,0.07); Rectangle(pos=(px2,py2),size=(t*2,t*0.3))
                        Color(0.67,0,1)
                        Rectangle(pos=(px2+1,py2+1),size=((t*2-2)*porc,t*0.3-2))
                        Color(0.92,0.5,1)
                        self._draw_text(px2+t, py2-t*0.1, "SHINRA", int(t*0.3), (0.92,0.5,1))
                    elif elev > 0:
                        Color(1,0.1,0.27)
                        self._draw_text(bx+t*0.5, by+t*2.5-desp, "SHINRA TENSEI!", int(t*0.4), (1,0.1,0.27))

                elif c.boss.get('tipo') in ('madara','madara_edo'):
                    pot = c.boss.get('chakra_activo')
                    tex = self._get_madara_sprite()
                    off = t*1.0 if pot else t*0.5
                    sz = t*2 if pot else t*2
                    Color(1,1,1,1)
                    Rectangle(texture=tex, pos=(bx-off, by-off), size=(sz, sz))
                    hp = c.boss.get('hp',8); mhp = c.boss.get('max_hp',8)
                    hp_w = t*1.65
                    hx = bx-t*0.5; hy = by-off-t*0.3
                    Color(0.07,0.07,0.07); Rectangle(pos=(hx,hy),size=(hp_w,t*0.25))
                    Color(0.9,0.22,0.21)
                    Rectangle(pos=(hx+1,hy+1),size=((hp_w-2)*max(0,min(1,hp/mhp)),t*0.25-2))
                    Color(1,1,1)
                    nombre = "RIKUDO" if c.boss.get('tipo')=='madara_edo' else "MADARA"
                    self._draw_text(hx+hp_w/2, hy+t*0.05, f"{nombre} {hp}/{mhp}", int(t*0.35), (1,1,1))
                    chakra = c.boss.get('chakra',0.0)
                    by2 = by + off*2 + t*0.1
                    Color(0.07,0.07,0.07); Rectangle(pos=(bx-t*0.6,by2),size=(t*2.2,t*0.25))
                    Color(0,0.9,1) if not pot else Color(1,0.84,0)
                    Rectangle(pos=(bx-t*0.58,by2+1),size=((t*2.16)*max(0,min(1,chakra)),t*0.25-2))
                    Color(1,1,1)
                    self._draw_text(bx+t*0.5, by2-t*0.1, "CHAKRA" if not pot else "MAX!", int(t*0.3), (1,1,1))
                    if c.boss.get('escudo_timer',0)>0 or c.boss.get('susanoo',0)>0:
                        Color(0,0.9,1,0.4)
                        radio = t*1.1 if pot else t*0.8
                        Ellipse(pos=(bx+t*0.5-radio,by+t*0.5-radio),size=(radio*2,radio*2),width=2)
                        Color(1,1,1)
                        self._draw_text(bx+t*0.5, by+t*0.5+radio+t*0.2, f"ESCUDO {c.boss.get('susanoo',0)}", int(t*0.35), (0,0.9,1))

            for dragon in c.madara_dragones:
                pts = []
                for seg in dragon['segments']:
                    pts.extend([ox+seg[1]*t+t/2, oy+(GRID_SIZE-1-seg[0])*t+t/2])
                if len(pts)>=4:
                    Color(0.18,0.49,0.2); Line(points=pts,width=t*0.3,cap='round',joint='round')
                    Color(0.46,1,0.02); Line(points=pts,width=t*0.12,cap='round',joint='round')

            mostrar_limbo = (c.limbo_blink % 30) < 12
            if mostrar_limbo:
                for copia in c.madara_limbo:
                    lr, lc = copia['pos']
                    lx = ox + lc*t; ly = oy + (GRID_SIZE-1-lr)*t
                    Color(0.3,0,0.6,0.7)
                    Ellipse(pos=(lx+t*0.1,ly+t*0.1),size=(t*0.8,t*0.8))
                    Color(1,0.1,0.17)
                    self._draw_text(lx+t*0.5, ly+t*0.15, "♥"*(copia.get('hp',2)), int(t*0.3), (1,0.1,0.17))

            for clon in c.madara_clones:
                cr2, cc2 = clon['pos']
                cx2 = ox + cc2*t; cy2 = oy + (GRID_SIZE-1-cr2)*t
                tex = TEX.get('madara_clone')
                if tex:
                    Color(0.5,0.5,0.5,0.7); Rectangle(texture=tex, pos=(cx2,cy2), size=(t,t))
                else:
                    Color(0.2,0,0.4,0.7); Ellipse(pos=(cx2+t*0.1,cy2+t*0.1),size=(t*0.8,t*0.8))

            for vara in c.varas_list:
                vr, vc = vara['pos']
                vx = ox + vc*t; vy = oy + (GRID_SIZE-1-vr)*t
                Color(0.07,0.07,0.07)
                Line(points=[vx+t/2,vy+t*0.1,vx+t/2,vy+t*0.9],width=t*0.15,cap='round')
                Color(0.29,0.29,0.29)
                Line(points=[vx+t/2-1,vy+t*0.1,vx+t/2-1,vy+t*0.9],width=t*0.05,cap='round')

            if c.p1['alive']:
                tex = self._get_sprite_p1()
                px = ox + c.p1['pos'][1]*t; py = oy + (GRID_SIZE-1-c.p1['pos'][0])*t
                Color(1,1,1,1); Rectangle(texture=tex, pos=(px,py), size=(t,t))
            else:
                paso = c.p1.get('dead_step',0)
                clave = f"minero_dead_{min(paso//8+1,3)}"
                tex = TEX.get(clave)
                px = ox + c.p1['pos'][1]*t; py = oy + (GRID_SIZE-1-c.p1['pos'][0])*t
                if tex:
                    Color(1,1,1,1); Rectangle(texture=tex, pos=(px,py), size=(t,t))
                else:
                    Color(0.3,0.3,0.3,0.5); Rectangle(pos=(px,py),size=(t,t))
                if c.game_running and paso < 24: c.p1['dead_step'] = paso + 1

            if c.mode in ["2P_COOP","2P_VS"]:
                if c.p2['alive']:
                    tex = self._get_sprite_p2()
                    px2 = ox + c.p2['pos'][1]*t; py2 = oy + (GRID_SIZE-1-c.p2['pos'][0])*t
                    Color(1,1,1,1); Rectangle(texture=tex, pos=(px2,py2), size=(t,t))
                else:
                    paso2 = c.p2.get('dead_step',0)
                    clave2 = f"capi_dead_{min(paso2//8+1,3)}"
                    tex2 = TEX.get(clave2)
                    px2 = ox + c.p2['pos'][1]*t; py2 = oy + (GRID_SIZE-1-c.p2['pos'][0])*t
                    if tex2:
                        Color(1,1,1,1); Rectangle(texture=tex2, pos=(px2,py2), size=(t,t))
                    if c.game_running and paso2 < 24: c.p2['dead_step'] = paso2 + 1

            if c.shinra_epico_timer > 0:
                tex = TEX.get('painshinra')
                if tex:
                    Color(1,1,1,min(1.0, c.shinra_epico_timer/3.0))
                    Rectangle(texture=tex, pos=(0,0), size=(w,h))

    def _draw_text(self, x, y, text, size=12, color=(1,1,1)):
        try:
            lbl = CoreLabel(text=str(text), font_size=max(1,size), color=(color[0],color[1],color[2],1), bold=True)
            lbl.refresh()
            tex = lbl.texture
            tw, th = tex.size
            Color(1,1,1,1)
            Rectangle(texture=tex, pos=(x-tw/2, y), size=(tw, th))
        except Exception:
            pass

    def _get_pain_sprite(self):
        b = self.core.boss
        if not b: return TEX.get('boss_pain')
        d = b.get('dir','down')
        frames = PAIN_FRAMES_MAP.get(d)
        if frames:
            idx = (b.get('frame',0)//4) % len(frames)
            k = f'pain_{d}_{idx}'
            if k in TEX: return TEX[k]
        return TEX.get('boss_pain', TEX.get('p1'))

    def _get_madara_sprite(self):
        b = self.core.boss
        if not b: return TEX.get('madara', TEX.get('p1'))
        d = b.get('dir','down')
        if d in ('left','right'):
            pre = 'madaradere' if d=='right' else 'madaradere'
            idx = (b.get('frame',0)//4) % 3
            k = f'{pre}_{idx+1}'
            if k in TEX: return TEX[k]
        elif b.get('mokuton') is not None:
            idx = (b.get('frame',0)//5) % 2
            k = f'madaramokuton_{idx+1}'
            if k in TEX: return TEX[k]
        return TEX.get('madara', TEX.get('p1'))

    def _get_sprite_p1(self):
        d = self.core.p1.get('dir','down')
        f = self.core.p1.get('frame',0) + 1
        k = f'minero_{d}_{f}'
        return TEX.get(k, TEX.get('p1', TEX.get('p1')))

    def _get_sprite_p2(self):
        d = self.core.p2.get('dir','down')
        f = self.core.p2.get('frame',0) + 1
        k = f'capi_{d}_{f}'
        return TEX.get(k, TEX.get('p2', TEX.get('p1')))

    def on_touch_down(self, touch):
        if not self.core.game_running:
            return super().on_touch_down(touch)
        return super().on_touch_down(touch)


class TouchControls(FloatLayout):
    def __init__(self, game_widget, **kwargs):
        super().__init__(**kwargs)
        self.gw = game_widget
        self.size_hint = (1, None)
        self.height = Window.width * 0.35
        self._dir = None

        btn_s = Window.width * 0.15
        spacing = Window.width * 0.02

        dpad = FloatLayout(size_hint=(None, None), size=(btn_s*3+spacing*2, btn_s*3+spacing*2),
                           pos_hint={'x':0.02, 'y':0.05})
        dirs = [('up',0.5,0.67,'^'), ('left',0,0.33,'<'), ('right',1,0.33,'>'), ('down',0.5,0,'v')]
        for d, xp, yp, ch in dirs:
            b = Button(text=ch, size_hint=(None,None), size=(btn_s,btn_s),
                       pos_hint={'center_x':xp,'center_y':yp},
                       font_size=btn_s*0.5, bold=True,
                       background_color=(0,0.9,1,0.35), color=(1,1,1,0.8))
            b.bind(on_press=lambda inst, dd=d: self._set_dir(dd))
            b.bind(on_release=lambda inst: self._clear_dir())
            dpad.add_widget(b)
        self.add_widget(dpad)

        bomb_btn = Button(text='BOMBA', size_hint=(None,None), size=(btn_s*1.3, btn_s*1.3),
                          pos_hint={'right':0.95, 'y':0.15},
                          font_size=btn_s*0.22, bold=True,
                          background_color=(1,0.2,0,0.5), color=(1,1,1,0.9))
        bomb_btn.bind(on_press=lambda inst: self._place_bomb())
        self.add_widget(bomb_btn)

        pause_btn = Button(text='||', size_hint=(None,None), size=(btn_s*0.5, btn_s*0.5),
                           pos_hint={'right':0.98, 'top':0.98},
                           font_size=btn_s*0.2, background_color=(1,1,1,0.2))
        pause_btn.bind(on_press=lambda inst: self.gw.app_ref.go_menu())
        self.add_widget(pause_btn)

    def _set_dir(self, d):
        self.gw.dir_held = d

    def _clear_dir(self):
        self.gw.dir_held = None

    def _place_bomb(self):
        if self.gw.core.game_running and self.gw.core.p1['alive']:
            self.gw.core.place_bomb(self.gw.core.p1, 1)
            play_sound("bomb")


class MenuWidget(FloatLayout):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref
        layout = BoxLayout(orientation='vertical', padding=Window.width*0.1, spacing=Window.height*0.02)

        title = Label(text='BOMBERMAN', font_size=Window.width*0.1, bold=True,
                      color=(1,0.08,0.58,1), size_hint_y=0.15)
        sub = Label(text='EDICION NEON COLOR', font_size=Window.width*0.04, bold=True,
                    color=(0,0.9,1,1), size_hint_y=0.08)
        layout.add_widget(title)
        layout.add_widget(sub)

        btn_h = 0.07
        buttons = [
            ('CAMPAÑA (1 jugador)', lambda: self._start('1P')),
            ('COOPERATIVA (2 jugadores)', lambda: self._start('2P_COOP')),
            ('VERSUS (2 jugadores)', lambda: self._start('2P_VS')),
            ('TEST PAIN', lambda: self._start('pain')),
            ('TEST MADARA', lambda: self._start('madara')),
            ('CONTROLES', self._controls),
            ('SALIR', self.app_ref.stop),
        ]
        for text, cb in buttons:
            b = Button(text=text, font_size=Window.width*0.035, bold=True,
                       size_hint_y=btn_h, background_color=(0.1,0.1,0.1,0.9),
                       color=(1,1,1,0.9))
            b.bind(on_release=lambda inst, c=cb: c())
            layout.add_widget(b)

        info = Label(text='Toque los botones para jugar\nWASD + Espacio en PC',
                     font_size=Window.width*0.025, color=(0.7,0.7,0.7,0.8),
                     size_hint_y=0.1, halign='center')
        layout.add_widget(info)
        self.add_widget(layout)

    def _start(self, mode):
        self.app_ref.start_game(mode)

    def _controls(self):
        self.app_ref.show_popup("CONTROLES",
            "JUGADOR 1 (Cian):\n  Mover: W,A,S,D\n  Bomba: ESPACIO\n\n"
            "JUGADOR 2 (Lima):\n  Mover: Flechas\n  Bomba: ENTER\n\n"
            "JEFES:\n  Nivel 5: PAIN\n  Nivel 10: MADARA\n\n"
            "Toque: D-Pad + BOMBA en pantalla")


class BombermanApp(App):
    def build(self):
        Window.clearcolor = (0.07, 0.07, 0.07, 1)
        self.root = FloatLayout()

        self.game_widget = GameWidget(self)
        self.game_widget.size_hint = (1, 1)
        self.game_widget.disabled = True
        self.game_widget.opacity = 0
        self.root.add_widget(self.game_widget)

        self.touch_controls = TouchControls(self.game_widget)
        self.touch_controls.disabled = True
        self.touch_controls.opacity = 0
        self.root.add_widget(self.touch_controls)

        self.menu_widget = MenuWidget(self)
        self.root.add_widget(self.menu_widget)

        self.game_widget._draw_job = Clock.schedule_interval(self.game_widget.tick, TICK)

        return self.root

    def start_game(self, mode):
        self.root.remove_widget(self.menu_widget)
        self.game_widget.disabled = False
        self.game_widget.opacity = 1
        self.touch_controls.disabled = False
        self.touch_controls.opacity = 1
        if mode == 'pain':
            self.game_widget.start_pain()
        elif mode == 'madara':
            self.game_widget.start_madara()
        else:
            self.game_widget.start_mode(mode)

    def go_menu(self, *args):
        stop_music()
        self.game_widget.core.game_running = False
        self.game_widget.disabled = True
        self.game_widget.opacity = 0
        self.touch_controls.disabled = True
        self.touch_controls.opacity = 0
        if self.menu_widget not in self.root.children:
            self.root.add_widget(self.menu_widget)

    def show_popup(self, title, text, on_dismiss=None):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        lbl = Label(text=text, font_size=Window.width*0.03, halign='center',
                    valign='middle', text_size=(Window.width*0.7, None))
        content.add_widget(lbl)
        btn = Button(text='OK', size_hint_y=0.25, font_size=Window.width*0.04,
                     background_color=(0,0.9,1,0.8))
        content.add_widget(btn)
        popup = Popup(title=title, content=content, size_hint=(0.85, 0.5),
                      auto_dismiss=False, title_font_size=Window.width*0.04)
        def dismiss(*a):
            popup.dismiss()
            if on_dismiss: on_dismiss()
        btn.bind(on_release=dismiss)
        popup.open()

    def on_pause(self):
        return True

    def on_resume(self):
        pass


if __name__ == '__main__':
    load_all_textures()
    BombermanApp().run()
