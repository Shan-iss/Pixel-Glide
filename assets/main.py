import pygame, sys, random, math, json, os, builtins
from datetime import datetime
import numpy as np
from ui_config import BASE_FONT_SIZES, FONT_FAMILIES

DEBUG_MODE=False
def debug_print(*args,**kwargs):
    if DEBUG_MODE:
        builtins.print(*args,**kwargs)

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

SCREEN_W, SCREEN_H = 800, 600
FPS = 60
BASE_WORLD_W = 11000
WORLD_W = BASE_WORLD_W
WEAPON_HUD_COMPACT_W, WEAPON_HUD_COMPACT_H = 164, 104
WEAPON_HUD_EXPANDED_W, WEAPON_HUD_EXPANDED_H = 180, 128
WEAPON_HUD_MARGIN = 10
WEAPON_HUD_EXPAND_FRAMES = 180  # auto-hide sekitar 3 detik pada 60 FPS
weapon_hud_expanded = False
weapon_hud_timer = 0

screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.SCALED)
pygame.display.set_caption("Pixel Glide v6.6")
clock = pygame.time.Clock()
fullscreen = False

def toggle_fullscreen():
    global screen, fullscreen
    fullscreen = not fullscreen
    if fullscreen:
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.FULLSCREEN | pygame.SCALED)
    else:
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.SCALED)
    pygame.display.set_caption("Pixel Glide v6.6")
    if "font_xs" in globals(): rebuild_fonts()

# ------------------------------------------------------------------------------------
# SAVE SYSTEM - Unlimited save files
# ------------------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVE_DIR = os.path.join(BASE_DIR, "saves")
ASSET_DIR = os.path.join(BASE_DIR, "assets", "images")
LOGO_PATH = os.path.join(ASSET_DIR, "pixel_glide_logo.png")

def ensure_save_dir():
    try: os.makedirs(SAVE_DIR, exist_ok=True)
    except: pass

def sanitize_save_name(name):
    safe="".join(c if c.isalnum() or c in " _-." else "_" for c in name).strip()
    if not safe: safe="save_"+datetime.now().strftime("%Y%m%d_%H%M%S")
    if not safe.endswith(".json"): safe+=".json"
    return safe

def _save_defaults():
    return {"high_score":0,"best_level":1,"total_plays":0,"total_kills":0,
       "bosses_defeated":0,"last_level":1,"last_checkpoint":1,"has_save":False,
       "money":0,"shop_upgrades":{"hp":0,"speed":0,"damage":0},
       "tutorial_seen":False,"achievements":[],"completed_challenges":[],
       "lives":5,"hp":3,"max_hp":3,"current_weapon":0,"weapon_levels":{},
        "mission_progress":{},"respawn_x":120.0,"respawn_y":480.0,
        "keycards":[],"story_logs":[],"terminal_states":{},"hidden_rooms":{},
        "timestamp":"","play_time":0,"save_name":"",
       "total_deaths":0,"total_coins":0,"total_damage_dealt":0,"total_damage_taken":0,
       "total_levels_cleared":0,"total_secrets":0,"total_chests":0,"total_boss_rush_waves":0,
       "highest_combo":0,"total_shots_fired":0,
        "settings":{"vol_sfx":0.55,"vol_bgm":0.22,"mute":False,"fullscreen":False,"language":"id","difficulty":"normal"},
        "cosmetics":{"owned_skins":["classic"],"equipped_skin":"classic",
                     "owned_weapon_skins":["default"],"equipped_weapon_skin":"default",
                     "owned_shop_weapons":[],"owned_pets":[],"equipped_pet":""},
        "world_seed":None}

def _merge_save_data(data,d):
    for k,v in d.items():
        if k not in data: data[k]=v
    if not isinstance(data.get("settings"),dict): data["settings"]=d["settings"]
    for k,v in d["settings"].items():
        if k not in data["settings"]: data["settings"][k]=v
    if not isinstance(data.get("shop_upgrades"),dict): data["shop_upgrades"]=d["shop_upgrades"]
    for k,v in d["shop_upgrades"].items():
        if k not in data["shop_upgrades"]: data["shop_upgrades"][k]=v
    if not isinstance(data.get("cosmetics"),dict): data["cosmetics"]=d["cosmetics"]
    for k,v in d["cosmetics"].items():
        if k not in data["cosmetics"]: data["cosmetics"][k]=v
    if not isinstance(data.get("achievements"),list): data["achievements"]=[]
    if not isinstance(data.get("completed_challenges"),list): data["completed_challenges"]=[]
    if not isinstance(data.get("keycards"),list): data["keycards"]=[]
    if not isinstance(data.get("story_logs"),list): data["story_logs"]=[]
    if not isinstance(data.get("terminal_states"),dict): data["terminal_states"]={}
    if not isinstance(data.get("hidden_rooms"),dict): data["hidden_rooms"]={}
    return data

def add_session_stat(key,amount=1):
    global session_stats
    session_stats[key]=session_stats.get(key,0)+amount

def flush_session_stats():
    global current_save_file,session_stats
    if not current_save_file: return
    sd=load_save(current_save_file)
    for k,v in session_stats.items():
        if k in sd:
            sd[k]=sd.get(k,0)+v
    if write_save(current_save_file,sd):
        save_data.update(sd)
        session_stats={}

def track_damage_dealt(amount):
    add_session_stat("total_damage_dealt",max(1,int(amount)))

def track_damage_taken(amount):
    add_session_stat("total_damage_taken",max(1,int(amount)))

def track_shot_fired():
    add_session_stat("total_shots_fired",1)

LAST_PLAYED_FILE = os.path.join(SAVE_DIR, ".last_played")

def save_last_played_save(fname):
    ensure_save_dir()
    try:
        with open(LAST_PLAYED_FILE, "w") as f:
            f.write(fname)
        return True
    except OSError as e:
        debug_print(f"[Save] last_played write failed: {e}")
        return False

def get_last_played_save():
    ensure_save_dir()
    try:
        if os.path.exists(LAST_PLAYED_FILE):
            with open(LAST_PLAYED_FILE, "r") as f:
                fname = f.read().strip()
            if fname and os.path.exists(os.path.join(SAVE_DIR, fname)):
                return fname
    except OSError as e:
        debug_print(f"[Save] last_played read failed: {e}")
    return ""

def list_save_files():
    ensure_save_dir()
    saves=[]
    for f in os.listdir(SAVE_DIR):
        if f.endswith(".json"):
            path=os.path.join(SAVE_DIR,f)
            try:
                with open(path,"r") as fp:
                    data=json.load(fp)
                ts=data.get("timestamp","")
                saves.append({"filename":f,"path":path,"data":data,"timestamp":ts})
            except: pass
    saves.sort(key=lambda s:s["timestamp"],reverse=True)
    return saves

def load_save(filename):
    d=_save_defaults()
    path=os.path.join(SAVE_DIR,filename)
    try:
        if os.path.exists(path):
            with open(path,"r") as f:
                return _merge_save_data(json.load(f),d)
    except (OSError,json.JSONDecodeError) as e:
        debug_print(f"[Save] {filename} load failed: {e}")
    return d

def write_save(filename,data):
    ensure_save_dir()
    path=os.path.join(SAVE_DIR,filename)
    try:
        with open(path,"w") as f: json.dump(data,f,indent=2)
        return True
    except OSError as e:
        debug_print(f"[Save] {filename} write failed: {e}")
        return False

def delete_save(filename):
    path = os.path.join(SAVE_DIR, filename)

    try:
        if os.path.exists(path):
            os.remove(path)

        # Hapus juga file legacy
        legacy = {
            "Slot 1.json": "save_slot_1.json",
            "Slot 2.json": "save_slot_2.json",
            "Slot 3.json": "save_slot_3.json",
        }

        if filename in legacy:
            old_path = os.path.join(BASE_DIR, legacy[filename])
            if os.path.exists(old_path):
                os.remove(old_path)

        return True

    except OSError as e:
        debug_print(f"[Save] {filename} delete failed: {e}")
        return False

def rename_save(old_filename,new_filename):
    if old_filename==new_filename: return True
    old_path=os.path.join(SAVE_DIR,old_filename)
    new_path=os.path.join(SAVE_DIR,new_filename)
    try:
        if os.path.exists(old_path) and not os.path.exists(new_path):
            os.rename(old_path,new_path)
            return True
    except OSError: pass
    return False

def duplicate_save(filename):
    data=load_save(filename)
    base=filename.replace(".json","")
    new_name=base+"_copy.json"
    counter=1
    while os.path.exists(os.path.join(SAVE_DIR,new_name)):
        counter+=1
        new_name=f"{base}_copy{counter}.json"
    write_save(new_name,data)
    return new_name

def has_save_data(filename):
    d=load_save(filename)
    return bool(d.get("timestamp",""))

def get_newest_save():
    saves=list_save_files()
    return saves[0]["filename"] if saves else ""

def migrate_old_saves():
    ensure_save_dir()
    old_patterns=["pixelglide_save.json","pixelglide_save_1.json","pixelglide_save_2.json",
                  "save_slot_1.json","save_slot_2.json","save_slot_3.json"]
    for i,old in enumerate(old_patterns):
        old_path=os.path.join(BASE_DIR,old)
        if os.path.exists(old_path):
            name=f"Slot {i%3+1}.json"
            new_path=os.path.join(SAVE_DIR,name)
            if not os.path.exists(new_path):
                try:
                    with open(old_path,"r") as f: data=json.load(f)
                    with open(new_path,"w") as f: json.dump(data,f,indent=2)
                except: pass

try:
    os.makedirs(ASSET_DIR, exist_ok=True)
except OSError as e:
    debug_print("Asset directory create failed:", e)

MIGRATION_FLAG = os.path.join(SAVE_DIR, ".migration_complete")

if not os.path.exists(MIGRATION_FLAG):
    migrate_old_saves()

    with open(MIGRATION_FLAG, "w") as f:
        f.write("done")

try:
    pixel_glide_logo_raw = pygame.image.load(LOGO_PATH).convert_alpha() if os.path.exists(LOGO_PATH) else None
    if pixel_glide_logo_raw is None: debug_print("Logo image not found:", LOGO_PATH)
except (pygame.error, OSError) as e:
    pixel_glide_logo_raw = None
    debug_print("Logo load failed:", e)
pixel_glide_logo_scaled_cache = {"key": None, "surface": None}

def record_play_started():
    if not current_save_file: return
    sd=load_save(current_save_file)
    sd["total_plays"]=sd.get("total_plays",0)+1
    if write_save(current_save_file,sd): save_data.update(sd)

def unlock_achievement(key,title):
    ach=set(save_data.get("achievements",[]))
    if key in ach: return
    ach.add(key)
    sd=load_save(current_save_file); sd["achievements"]=sorted(ach)
    if write_save(current_save_file,sd): save_data.update(sd)
    if "player" in globals(): spawn_score(player.wx+player.WIDTH//2,player.wy-54,f"ACHIEVEMENT: {title}")

ACHIEVEMENTS={
    "first_blood":{"title":"First Blood","desc":"Defeat your first enemy."},
    "weapon_master":{"title":"Weapon Master","desc":"Own at least five weapons."},
    "boss_hunter":{"title":"Boss Hunter","desc":"Defeat five bosses."},
    "rich_robot":{"title":"Rich Robot","desc":"Hold 500 total coins."},
    "rank_s":{"title":"S-Rank Unit","desc":"Clear a level with S rank."},
    "secret_finder":{"title":"Secret Finder","desc":"Open a secret cache."},
    "hard_mode":{"title":"Hard Protocol","desc":"Start a run on Hard or CORE-X."},
    "explorer":{"title":"Explorer","desc":"Discover a hidden route."},
    "terminal_hacker":{"title":"Terminal Hacker","desc":"Use your first terminal."},
    "elite_hunter":{"title":"Elite Hunter","desc":"Defeat 10 elite enemies."},
    "story_collector":{"title":"Story Collector","desc":"Unlock 8 research logs."},
    "hidden_explorer":{"title":"Hidden Explorer","desc":"Complete 3 hidden rooms."},
    "master_hacker":{"title":"Master Hacker","desc":"Use 8 terminals."},
    "laboratory_survivor":{"title":"Laboratory Survivor","desc":"Survive the hidden laboratory route."},
}

DIFFICULTY_ORDER=["easy","normal","hard","nightmare"]
DIFFICULTY_DATA={
    "easy":{"name":"EASY","desc":"Lower incoming damage. Lower bonus rewards.","damage":0.75,"reward":0.85,"color":(29,158,117)},
    "normal":{"name":"NORMAL","desc":"Balanced NEXUS-7 protocol.","damage":1.0,"reward":1.0,"color":(93,202,165)},
    "hard":{"name":"HARD","desc":"More punishment, better rewards.","damage":1.35,"reward":1.25,"color":(239,159,39)},
    "nightmare":{"name":"NIGHTMARE","desc":"Maximum threat simulation. Best rewards.","damage":1.7,"reward":1.55,"color":(226,75,74)},
    "corex":{"name":"CORE-X","desc":"Maximum threat simulation. Best rewards.","damage":1.7,"reward":1.55,"color":(226,75,74)},
}

def current_difficulty():
    diff=save_data.get("settings",{}).get("difficulty","normal")
    return diff if diff in DIFFICULTY_DATA else "normal"

def difficulty_reward_mult(): return DIFFICULTY_DATA[current_difficulty()]["reward"]
def scale_incoming_damage(amount): return max(1,int(math.ceil(safe_damage_value(amount)*DIFFICULTY_DATA[current_difficulty()]["damage"])))

def safe_damage_value(amount,default=1):
    try:
        if amount is None: return default
        return max(1,int(math.ceil(float(amount))))
    except (TypeError,ValueError,OverflowError):
        return default

def safe_hp_value(amount,default=0):
    """HP may legally be 0 or negative; unlike damage it must not clamp to 1."""
    try:
        if amount is None: return default
        return int(math.ceil(float(amount)))
    except (TypeError,ValueError,OverflowError):
        return default

def is_alive_entity(entity):
    """Central alive check: prevents enemies with hp <= 0 or stale invincible state from lingering."""
    return bool(getattr(entity,"alive",False)) and safe_hp_value(getattr(entity,"hp",1),0)>0

def damage_enemy(enemy,amount,source="hit"):
    """Apply sanitized damage to any enemy-like object and always kill at hp <= 0."""
    dmg=safe_damage_value(amount)
    if not getattr(enemy,"alive",False): return True,dmg
    old_hp=enemy.hp
    enemy.hp=safe_hp_value(getattr(enemy,"hp",getattr(enemy,"max_hp",1)),1)-dmg
    spawn_pixels(getattr(enemy,"wx",0)+getattr(enemy,"WIDTH",16)//2,getattr(enemy,"wy",0)+getattr(enemy,"HEIGHT",16)//2,(255,220,100),6)
    if enemy.hp<=0:
        enemy.hp=0; enemy.alive=False
    return not enemy.alive,dmg

newest=get_newest_save()
save_data = load_save(newest) if newest else _save_defaults()

SUPPORTED_LANGS=("id","en")

TEXT={
    "id":{
        "lang.name":"Indonesia","ui.on":"ON","ui.off":"OFF","ui.buy":"BELI","ui.locked":"KUNCI","ui.equip":"PAKAI","ui.equipped":"DIPAKAI","ui.less":"KURANG","ui.max":"MAKS","ui.maxed":"MAKSIMAL",
        "menu.new_game":"GAME BARU","menu.continue":"LANJUTKAN","menu.save_data":"DATA SAVE","menu.settings":"PENGATURAN","menu.quit":"KELUAR",
        "menu.subtitle":"Sci-Fi Robot Adventure","menu.version":"v6.6  |  13 Level  |  10 Boss","menu.high_score":"SKOR TERBAIK","menu.level":"Level","menu.plays":"Main","menu.bosses":"Boss Kalah",
        "menu.no_save":"Belum ada save  |  F5 = Save","menu.save":"Save: Level {level}  |  F5 = Save","menu.shop_hint":"B / TOKO [B] = buka toko","menu.fullscreen":"F11 / FULLSCREEN","menu.windowed":"F11 / WINDOWED",
        "save.title":"DATA SAVE","save.high_score":"SKOR TERBAIK","save.best_level":"LEVEL TERTINGGI","save.total_plays":"TOTAL MAIN","save.total_kills":"TOTAL KILL","save.bosses":"BOSS KALAH","save.last_level":"LEVEL TERAKHIR","save.back":"KEMBALI","save.slot_empty":"Slot Kosong","save.slot_level":"Level {lv}","save.slot_score":"Skor: {s}","save.slot_coins":"Koin: {c}","save.slot_hp":"HP: {hp}/{max}","save.slot_weapon":"Senjata: {w}","save.slot_date":"{d}","save.slot_time":"Waktu: {t:.0f}m","save.load":"MUAT","save.delete":"HAPUS","save.info":"Pilih slot untuk memuat atau menghapus data",
        "save.play":"MAIN","save.view":"LIHAT DETAIL","save.play_time":"Waktu: {t:.0f}m","save.last_played":"{d}","save.difficulty":"Kesulitan: {d}","save.weapon":"Senjata: {w}","save.overwrite_confirm":"Timpa save ini?","save.delete_confirm":"Hapus save ini?","save.yes":"YA","save.no":"TIDAK","save.select_slot":"PILIH SLOT","save.start_new":"MULAI BARU","save.rename":"GANTI NAMA","save.duplicate":"DUPLIKAT","save.new_game":"GAME BARU","save.name_placeholder":"Nama save...","save.create":"BUAT","save.cancel":"BATAL","save.name_required":"Nama tidak boleh kosong","save.rename_title":"GANTI NAMA SAVE","save.rename_placeholder":"Nama baru...","save.rename_confirm":"SIMPAN","save.duplicate_title":"Duplikat Save",
        "settings.title":"PENGATURAN","settings.sound":"SUARA","settings.display_audio":"TAMPILAN & AUDIO","settings.controls":"REFERENSI KONTROL","settings.mute":"Mute Semua Suara","settings.fullscreen":"Mode Fullscreen","settings.particles":"Partikel Efek","settings.shake":"Intensitas Shake","settings.language":"Bahasa","settings.lang_value":"Indonesia","settings.reset":"RESET AWAL","settings.save_close":"SIMPAN & TUTUP","settings.footer":"ESC = simpan & tutup","settings.sfx":"Volume SFX","settings.bgm":"Volume BGM",
        "ctrl.move":"Bergerak","ctrl.jump":"Lompat","ctrl.shoot":"Tembak","ctrl.weapon":"Ganti Senjata","ctrl.pause":"Jeda","ctrl.save_shop":"Save / Toko","ctrl.save":"Save","ctrl.restart":"Ulang","ctrl.mute":"Mute","ctrl.volume":"Volume -/+","ctrl.fullscreen":"Fullscreen","ctrl.respawn":"Hidup Lagi","ctrl.left_click":"Klik Kiri",
        "shop.title":"TOKO","shop.coins":"{coins}","shop.tab.upgrades":"UPGRADE","shop.tab.weapon":"SENJATA","shop.tab.skins":"KULIT","shop.tab.pet":"PET","shop.tab.special":"SPESIAL","shop.weapon_skins":"KULIT SENJATA","shop.shop_weapons":"SENJATA TOKO","shop.close_hint":"ESC / Klik luar = tutup","shop.cost":"{cost}","shop.ammo":"AMMO {price}","shop.equip":"PAKAI","shop.equipped":"DIPAKAI","shop.pet_preview":"PRATINJAU","shop.buy":"BELI","shop.upgrade":"TINGKATKAN","shop.max":"MAKS","shop.select":"PILIH",
        "upg.hp.name":"MAX HP +1","upg.hp.desc":"Tambah 1 HP maksimal","upg.speed.name":"SPEED +10%","upg.speed.desc":"Gerak 10% lebih cepat","upg.damage.name":"DAMAGE +1","upg.damage.desc":"Tembak damage +1",
        "upg.jump.name":"DOUBLE JUMP","upg.jump.desc":"Tambah lompatan udara","upg.dash.name":"DASH CORE","upg.dash.desc":"Dash lebih lama dan cepat siap","upg.shield.name":"SHIELD CELL","upg.shield.desc":"Shield dan i-frame lebih kuat","upg.weaponmod.name":"WEAPON MOD","upg.weaponmod.desc":"Laser/pulse/railgun bisa pierce",
        "hud.lives":"NYAWA","hud.best":"TERBAIK","hud.coins":"KOIN","hud.score":"SKOR","hud.new_record":"REKOR BARU!","hud.boss_arena":"ARENA BOSS!","hud.enemies":"MUSUH {count}","hud.checkpoint":"POS L{level}","hud.mode":"MODE: {mode}","hud.mode.fly":"TERBANG","hud.mode.glide":"MELAYANG","hud.mode.run":"LARI","hud.shop":"TOKO [B]","hud.fly_active":"ZONA TERBANG AKTIF","hud.fly_hint":"W/UP naik  |  A/D arah","hud.frozen":"MEMBEKU!","hud.footer":"B Toko | E Senjata | F5 Save | F11 FS | M Mute | ESC Jeda | {sound}","hud.sound_off":"SOUND OFF","hud.sound_on":"SOUND ON {vol}%",
        "level.clear.defeated":"{name} DIKALAHKAN!","level.clear.done":"LEVEL {level} SELESAI!  +{bonus} BONUS","level.clear.final":"Misi selesai: NEXUS-7 aman","level.clear.next":"Tantangan berikutnya: Level {level} - diacak ulang","level.clear.save":"Auto save aktif. Peti boss muncul.",
        "pause.title":"JEDA","pause.score":"Skor: {score:06d}","pause.level":"Level: {level}","pause.best":"Terbaik: {best:06d}","pause.bosses":"Boss Kalah: {bosses}","pause.tip":"TIP: B = Toko  |  ESC = Lanjut","pause.resume":"LANJUT","pause.save_game":"SIMPAN GAME","pause.shop":"$  TOKO","pause.restart":"ULANG LEVEL","pause.settings":"PENGATURAN","pause.main_menu":"MENU UTAMA","pause.saved":"Game Berhasil Disimpan",
        "dead.title":"KAMU  KALAH","dead.info":"Nyawa: {lives}   Posisi: Level {level}","dead.boss":"Boss: {name}   HP tersisa: {hp}","dead.retry":"R / Klik  -  Ulang dari posisi","dead.game_over":"R / Klik  -  Game Over",
        "gameover.new_record":"REKOR BARU!","gameover.score":"SKOR  {score:06d}","gameover.stats":"Terbaik: {best:06d}   Level: {level}   Boss: {bosses}   Main: {plays}","gameover.boss":"Level: {level}   Boss: {boss}","gameover.back":"R / Klik  -  Kembali ke Main Menu",
        "ending.title":"CORE-X HANCUR","ending.line1":"NEXUS-7 kembali online.","ending.line2":"Unit G7 menyelesaikan misi terakhir.","ending.line3":"Stasiun terselamatkan. Sistem bebas dari CORE-X.","ending.score":"SKOR AKHIR  {score:06d}","ending.back":"Tekan tombol apa saja untuk kembali ke Main Menu",
        "weapon.hud.ammo":"AMMO: {ammo}","weapon.hud.on":"E: ON","weapon.hud.off":"E: OFF","boss.challenge":"TANTANGAN BOSS","boss.challenge_level":"TANTANGAN LEVEL {level}","boss.ability":"Ability: {desc}","boss.phase":"FASE {phase}",
        "opening.start":"Tekan SPACE / Klik untuk mulai","opening.skip":"SPACE/Klik = lewati","dialogue.hint":"SPACE/Klik = lanjut  ESC = lewati",        "story.bonus":"LEVEL BONUS",
        "stats.title":"STATISTIK","stats.kills":"Total Kill","stats.deaths":"Total Mati","stats.coins":"Koin Terkumpul","stats.damage_dealt":"Damage Diberikan","stats.damage_taken":"Damage Diterima","stats.levels_cleared":"Level Diselesaikan","stats.secrets":"Rahasia Ditemukan","stats.chests":"Peti Dibuka","stats.highest_combo":"Kombo Tertinggi","stats.shots_fired":"Tembakan Dilepas","stats.boss_rush":"Gelombang Boss Rush","stats.play_time":"Waktu Bermain","stats.bosses":"Boss Dikalahkan","stats.best_level":"Level Terbaik","stats.high_score":"Skor Tertinggi","stats.total_plays":"Total Main","stats.accuracy":"Akurasi Tembak",
        "minimap.title":"MINIMAP","minimap.player":"G7","minimap.boss":"BOSS","minimap.enemy":"MUSUH","minimap.coin":"KOIN","minimap.chest":"PETI","minimap.checkpoint":"CHECKPOINT",
        "boss_rush.title":"BOSS RUSH","boss_rush.select":"PILIH BOSS UNTUK DILAWAN","boss_rush.start":"MULAI SERANGAN","boss_rush.back":"KEMBALI","boss_rush.score":"SKOR: {score}","boss_rush.wave":"GELOMBANG {wave}","boss_rush.complete":"BOSS RUSH SELESAI!","boss_rush.best":"TERBAIK: {score}","boss_rush.hint":"Kalahkan semua boss dalam satu sesi!","boss_rush.unlocked":"TERBUKA: Boss ke-{id}","boss_rush.locked":"TERKUNCI: Kalahkan Boss ke-{id}",
        "challenge.title":"RUANG TANTANGAN","challenge.select":"PILIH TANTANGAN","challenge.rooms":"RUANG TERSEDIA","challenge.laser":"Labirin Laser","challenge.laser_desc":"Hindari laser dan kumpulkan koin!","challenge.server":"Server Lockdown","challenge.server_desc":"Kalahkan semua musuh dalam ruang terbatas!","challenge.corex":"Core-X Trial","challenge.corex_desc":"Hadapi Core-X dengan HP terbatas!",
    },
    "en":{
        "lang.name":"English","ui.on":"ON","ui.off":"OFF","ui.buy":"BUY","ui.locked":"LOCKED","ui.equip":"EQUIP","ui.equipped":"EQUIPPED","ui.less":"SHORT","ui.max":"MAX","ui.maxed":"MAXED",
        "menu.new_game":"NEW GAME","menu.continue":"CONTINUE","menu.save_data":"SAVE DATA","menu.settings":"SETTINGS","menu.quit":"QUIT",
        "menu.subtitle":"Sci-Fi Robot Adventure","menu.version":"v6.6  |  13 Levels  |  10 Bosses","menu.high_score":"HIGH SCORE","menu.level":"Level","menu.plays":"Plays","menu.bosses":"Bosses Defeated",
        "menu.no_save":"No save yet  |  F5 = Save","menu.save":"Save: Level {level}  |  F5 = Save","menu.shop_hint":"B / SHOP [B] = open shop","menu.fullscreen":"F11 / FULLSCREEN","menu.windowed":"F11 / WINDOWED",
        "save.title":"SAVE DATA","save.high_score":"HIGH SCORE","save.best_level":"BEST LEVEL","save.total_plays":"TOTAL PLAYS","save.total_kills":"TOTAL KILLS","save.bosses":"BOSSES DEFEATED","save.last_level":"LAST LEVEL","save.back":"BACK","save.slot_empty":"Empty Save Slot","save.slot_level":"Level {lv}","save.slot_score":"Score: {s}","save.slot_coins":"Coins: {c}","save.slot_hp":"HP: {hp}/{max}","save.slot_weapon":"Weapon: {w}","save.slot_date":"{d}","save.slot_time":"Time: {t:.0f}m","save.load":"LOAD","save.delete":"DELETE","save.info":"Select a slot to load or delete save data",
        "save.play":"PLAY","save.view":"VIEW DETAILS","save.play_time":"Time: {t:.0f}m","save.last_played":"{d}","save.difficulty":"Difficulty: {d}","save.weapon":"Weapon: {w}","save.overwrite_confirm":"Overwrite this save?","save.delete_confirm":"Delete this save?","save.yes":"YES","save.no":"NO","save.select_slot":"SELECT SLOT","save.start_new":"START NEW GAME","save.rename":"RENAME","save.duplicate":"DUPLICATE","save.new_game":"NEW GAME","save.name_placeholder":"Save name...","save.create":"CREATE","save.cancel":"CANCEL","save.name_required":"Name cannot be empty","save.rename_title":"RENAME SAVE","save.rename_placeholder":"New name...","save.rename_confirm":"SAVE","save.duplicate_title":"Duplicate Save",
        "settings.title":"SETTINGS","settings.sound":"SOUND","settings.display_audio":"DISPLAY & AUDIO","settings.controls":"CONTROL REFERENCE","settings.mute":"Mute All Sound","settings.fullscreen":"Fullscreen Mode","settings.particles":"Particle Effects","settings.shake":"Shake Intensity","settings.language":"Language","settings.lang_value":"English","settings.reset":"RESET DEFAULT","settings.save_close":"SAVE & CLOSE","settings.footer":"ESC = save & close","settings.sfx":"SFX Volume","settings.bgm":"BGM Volume",
        "ctrl.move":"Move","ctrl.jump":"Jump","ctrl.shoot":"Shoot","ctrl.weapon":"Switch Weapon","ctrl.pause":"Pause","ctrl.save_shop":"Save / Shop","ctrl.save":"Save","ctrl.restart":"Restart","ctrl.mute":"Mute","ctrl.volume":"Volume -/+","ctrl.fullscreen":"Fullscreen","ctrl.respawn":"Respawn","ctrl.left_click":"Left Click",
        "shop.title":"SHOP","shop.coins":"{coins}","shop.tab.upgrades":"UPGRADE","shop.tab.weapon":"WEAPON","shop.tab.skins":"SKIN","shop.tab.pet":"PET","shop.tab.special":"SPECIAL","shop.weapon_skins":"WEAPON SKINS","shop.shop_weapons":"SHOP WEAPONS","shop.close_hint":"ESC / Click outside = close","shop.cost":"{cost}","shop.ammo":"AMMO {price}","shop.equip":"EQUIP","shop.equipped":"EQUIPPED","shop.pet_preview":"PREVIEW","shop.buy":"BUY","shop.upgrade":"UPGRADE","shop.max":"MAX","shop.select":"SELECT",
        "upg.hp.name":"MAX HP +1","upg.hp.desc":"Increase max HP by 1","upg.speed.name":"SPEED +10%","upg.speed.desc":"Move 10% faster","upg.damage.name":"DAMAGE +1","upg.damage.desc":"Shots deal +1 damage",
        "upg.jump.name":"DOUBLE JUMP","upg.jump.desc":"Adds air jumps","upg.dash.name":"DASH CORE","upg.dash.desc":"Dash lasts longer and recharges faster","upg.shield.name":"SHIELD CELL","upg.shield.desc":"Stronger shield and i-frames","upg.weaponmod.name":"WEAPON MOD","upg.weaponmod.desc":"Laser/pulse/railgun pierce targets",
        "hud.lives":"LIVES","hud.best":"BEST","hud.coins":"COINS","hud.score":"SCORE","hud.new_record":"NEW RECORD!","hud.boss_arena":"BOSS ARENA!","hud.enemies":"ENEMIES {count}","hud.checkpoint":"CHK L{level}","hud.mode":"MODE: {mode}","hud.mode.fly":"FLY","hud.mode.glide":"GLIDE","hud.mode.run":"RUN","hud.shop":"SHOP [B]","hud.fly_active":"FLIGHT ZONE ACTIVE","hud.fly_hint":"W/UP up  |  A/D steer","hud.frozen":"FROZEN!","hud.footer":"B Shop | E Weapon | F5 Save | F11 FS | M Mute | ESC Pause | {sound}","hud.sound_off":"SOUND OFF","hud.sound_on":"SOUND ON {vol}%",
        "level.clear.defeated":"{name} DEFEATED!","level.clear.done":"LEVEL {level} CLEAR!  +{bonus} BONUS","level.clear.final":"Mission complete: NEXUS-7 is safe","level.clear.next":"Next challenge: Level {level} - rerolled","level.clear.save":"Auto save active. Boss chest spawned.",
        "pause.title":"PAUSED","pause.score":"Score: {score:06d}","pause.level":"Level: {level}","pause.best":"Best: {best:06d}","pause.bosses":"Bosses Defeated: {bosses}","pause.tip":"TIP: Press B = Shop  |  ESC = Resume","pause.resume":"RESUME","pause.save_game":"SAVE GAME","pause.shop":"$  SHOP","pause.restart":"RESTART LEVEL","pause.settings":"SETTINGS","pause.main_menu":"MAIN MENU","pause.saved":"Game Saved Successfully",
        "dead.title":"YOU  DIED","dead.info":"Lives: {lives}   Position: Level {level}","dead.boss":"Boss: {name}   HP left: {hp}","dead.retry":"R / Click  -  Retry from position","dead.game_over":"R / Click  -  Game Over",
        "gameover.new_record":"NEW RECORD!","gameover.score":"SCORE  {score:06d}","gameover.stats":"Best: {best:06d}   Level: {level}   Bosses: {bosses}   Plays: {plays}","gameover.boss":"Level: {level}   Boss: {boss}","gameover.back":"R / Click  -  Back to Main Menu",
        "ending.title":"CORE-X DESTROYED","ending.line1":"NEXUS-7 is back online.","ending.line2":"Unit G7 completed the final mission.","ending.line3":"The station is safe. The system is free from CORE-X.","ending.score":"FINAL SCORE  {score:06d}","ending.back":"Press any key to return to Main Menu",
        "weapon.hud.ammo":"AMMO: {ammo}","weapon.hud.on":"E: ON","weapon.hud.off":"E: OFF","boss.challenge":"BOSS CHALLENGE","boss.challenge_level":"LEVEL {level} CHALLENGE","boss.ability":"Ability: {desc}","boss.phase":"PHASE {phase}",
        "opening.start":"Press SPACE / Click to start","opening.skip":"SPACE/Click = skip","dialogue.hint":"SPACE/Click = next  ESC = skip",        "story.bonus":"BONUS LEVEL",
        "stats.title":"STATISTICS","stats.kills":"Total Kills","stats.deaths":"Total Deaths","stats.coins":"Coins Collected","stats.damage_dealt":"Damage Dealt","stats.damage_taken":"Damage Taken","stats.levels_cleared":"Levels Cleared","stats.secrets":"Secrets Found","stats.chests":"Chests Opened","stats.highest_combo":"Highest Combo","stats.shots_fired":"Shots Fired","stats.boss_rush":"Boss Rush Waves","stats.play_time":"Play Time","stats.bosses":"Bosses Defeated","stats.best_level":"Best Level","stats.high_score":"High Score","stats.total_plays":"Total Plays","stats.accuracy":"Accuracy",
        "minimap.title":"MINIMAP","minimap.player":"G7","minimap.boss":"BOSS","minimap.enemy":"ENEMY","minimap.coin":"COIN","minimap.chest":"CHEST","minimap.checkpoint":"CHECKPOINT",
        "boss_rush.title":"BOSS RUSH","boss_rush.select":"SELECT BOSS TO FIGHT","boss_rush.start":"START ASSAULT","boss_rush.back":"BACK","boss_rush.score":"SCORE: {score}","boss_rush.wave":"WAVE {wave}","boss_rush.complete":"BOSS RUSH COMPLETE!","boss_rush.best":"BEST: {score}","boss_rush.hint":"Defeat all bosses in one session!","boss_rush.unlocked":"UNLOCKED: Boss #{id}","boss_rush.locked":"LOCKED: Defeat Boss #{id}",
        "challenge.title":"CHALLENGE ROOMS","challenge.select":"SELECT CHALLENGE","challenge.rooms":"ROOMS AVAILABLE","challenge.laser":"Laser Maze","challenge.laser_desc":"Avoid lasers and collect coins!","challenge.server":"Server Lockdown","challenge.server_desc":"Defeat all enemies in enclosed space!","challenge.corex":"Core-X Trial","challenge.corex_desc":"Face Core-X with limited HP!",
    },
}

def current_language():
    lang=save_data.get("settings",{}).get("language","id")
    return lang if lang in SUPPORTED_LANGS else "id"

def set_language(lang):
    if lang not in SUPPORTED_LANGS: lang="id"
    save_data.setdefault("settings",{})["language"]=lang

def tr(key, **kwargs):
    text=TEXT.get(current_language(),TEXT["id"]).get(key,TEXT["id"].get(key,key))
    return text.format(**kwargs) if kwargs else text

# ------------------------------------------------------------------------------------
# WARNA
# ------------------------------------------------------------------------------------
BLACK=(10,10,20); CYAN=(93,202,165); GREEN=(29,158,117); DARK_GREEN=(15,110,86)
BLUE=(55,138,221); RED=(226,75,74); ORANGE=(239,159,39); WHITE=(255,255,255)
GRAY=(60,60,80); PLATFORM_C=(40,40,60); PURPLE=(127,119,221); YELLOW=(250,199,117)
DARK_BLUE=(15,15,35); PINK=(220,80,160); TEAL=(0,180,160); GOLD=(255,200,50)
TEXT_MAIN=(235,245,255); TEXT_MUTED=(170,190,200); TEXT_DIM=(115,135,145)
PANEL_BG=(7,10,26); PANEL_BG_2=(10,14,34); PANEL_BORDER=(100,230,190)
WARNING_TEXT=(255,205,95); DANGER_TEXT=(255,105,105); SUCCESS_TEXT=(120,245,175)
NEON_CYAN=(80,230,220); NEON_PINK=(255,80,200); NEON_PURPLE=(180,100,255)
NEON_RED=(255,50,50); NEON_GREEN=(50,255,140); NEON_ORANGE=(255,180,50)
NEON_YELLOW=(255,240,80); NEON_BLUE=(60,160,255)
PANEL_RADIUS=10; PANEL_GLOW_ALPHA=25; PANEL_BORDER_ALPHA=155

# ------------------------------------------------------------------------------------
# PERFORMANCE: Surface cache + Font render cache
# ------------------------------------------------------------------------------------
SURFACE_CACHE={}
def get_cached_surface(key,w,h,flags=pygame.SRCALPHA):
    if key not in SURFACE_CACHE or SURFACE_CACHE[key].get_size()!=(w,h):
        SURFACE_CACHE[key]=pygame.Surface((w,h),flags)
    return SURFACE_CACHE[key]

FONT_RENDER_CACHE={}
def clear_font_cache():
    FONT_RENDER_CACHE.clear()

class CachedFont(pygame.font.Font):
    def render(self,text,antialias,color,bg=None):
        key=(id(self),text,antialias,color,bg)
        if key not in FONT_RENDER_CACHE:
            FONT_RENDER_CACHE[key]=super().render(text,antialias,color,bg)
        return FONT_RENDER_CACHE[key]

SIN_CACHE={}
def sin_cached(angle):
    key=round(angle,4)
    if key not in SIN_CACHE:
        SIN_CACHE[key]=math.sin(key)
    return SIN_CACHE[key]

def clear_surface_cache():
    SURFACE_CACHE.clear()
    FONT_RENDER_CACHE.clear()
    SIN_CACHE.clear()

_font_cache={}

def ui_scale():
    w,h=screen.get_size()
    return max(0.9,min(1.25,min(w/SCREEN_W,h/SCREEN_H)))

def make_font(size, role="body", bold=False):
    scaled=max(8,int(round(size*ui_scale())))
    key=(role,scaled,bold)
    if key in _font_cache: return _font_cache[key]
    path=pygame.font.match_font(FONT_FAMILIES.get(role,FONT_FAMILIES["body"]), bold=bold)
    font=CachedFont(path, scaled) if path else pygame.font.SysFont(None, scaled, bold=bold)
    font.set_bold(bold)
    _font_cache[key]=font
    return font

def rebuild_fonts():
    global font_xs,font_sm,font_md,font_lg,font_xl
    _font_cache.clear()
    FONT_RENDER_CACHE.clear()
    font_xs=make_font(BASE_FONT_SIZES["xs"],"body")
    font_sm=make_font(BASE_FONT_SIZES["sm"],"body")
    font_md=make_font(BASE_FONT_SIZES["md"],"hud",True)
    font_lg=make_font(BASE_FONT_SIZES["lg"],"title",True)
    font_xl=make_font(BASE_FONT_SIZES["xl"],"title",True)

def render_fit(font, text, color, max_w):
    if font.size(text)[0]<=max_w:
        return font.render(text,True,color)
    while text and font.size(text+"...")[0]>max_w:
        text=text[:-1]
    return font.render((text+"...") if text else "...",True,color)

def draw_text(surface,text,font,x,y,color=TEXT_MAIN,shadow=True,center=False):
    img=font.render(text,True,color)
    pos=(int(x-img.get_width()/2),int(y)) if center else (int(x),int(y))
    if shadow:
        off=1 if font.get_height()<=18 else 2
        sh=font.render(text,True,(0,0,0)); surface.blit(sh,(pos[0]+off,pos[1]+off))
    surface.blit(img,pos)
    return img.get_rect(topleft=pos)

def get_scaled_game_logo():
    if pixel_glide_logo_raw is None: return None
    ow,oh=pixel_glide_logo_raw.get_size()
    if ow<=0 or oh<=0: return None
    max_w=int(430*ui_scale())
    max_h=int(150*ui_scale())
    scale=min(max_w/ow,max_h/oh)
    tw=max(1,int(ow*scale)); th=max(1,int(oh*scale))
    key=(tw,th)
    if pixel_glide_logo_scaled_cache["key"]!=key:
        pixel_glide_logo_scaled_cache["key"]=key
        pixel_glide_logo_scaled_cache["surface"]=pygame.transform.scale(pixel_glide_logo_raw,(tw,th))
    return pixel_glide_logo_scaled_cache["surface"]

def draw_game_logo(surface,y=18):
    logo=get_scaled_game_logo()
    if logo is None: return None
    rect=logo.get_rect(midtop=(SCREEN_W//2,int(y)))
    surface.blit(logo,rect)
    return rect

# ------------------------------------------------------------------------------------
# BOSS DATA + DIALOGUES
# ------------------------------------------------------------------------------------
BOSS_DATA = {
    1: {"name":"SCOUT ALPHA","title":"Penjaga Gerbang","color":(55,138,221),"armor":(24,90,160),"eye":RED,
        "hp":12,"speed":1.2,"size":(50,55),"ability":"triple_shot","desc":"Tembak 3 arah","bg_effect":"radar","shake_profile":"light",
        "intro":"Unit pengintai pertama CORE-X.\nDirancang untuk menghentikan G7\nsebelum melarikan diri lebih jauh."},
    2: {"name":"TANK CRUSHER","title":"Mesin Perang","color":(100,180,60),"armor":(60,120,30),"eye":YELLOW,
        "hp":18,"speed":0.8,"size":(65,65),"ability":"ground_slam","desc":"Slam + shockwave","bg_effect":"engine_heat","shake_profile":"heavy",
        "intro":"Unit tempur kelas berat.\nDibangun dari sisa reaktor mesin.\nTidak ada yang bisa melewatinya... katanya."},
    3: {"name":"SENTRY MK-I","title":"Penjaga Lab","color":(120,40,40),"armor":(80,30,30),"eye":RED,
        "hp":25,"speed":1.5,"size":(70,80),"ability":"burst_fire","desc":"Burst 5 peluru + minion","bg_effect":"lab_warning","shake_profile":"medium",
        "intro":"Prototipe senjata lab riset.\nMampu memanggil bala bantuan\ndan menembak 5 arah sekaligus."},
    4: {"name":"AERO HUNTER","title":"Predator Udara","color":(80,60,180),"armor":(50,40,130),"eye":CYAN,
        "hp":30,"speed":2.0,"size":(75,60),"ability":"dive_bomb","desc":"Terbang + bom udara","bg_effect":"aero_wind","shake_profile":"medium",
        "intro":"Unit aerial tercepat CORE-X.\nMenguasai sabuk asteroid.\nSerangannya dari langit, tanpa peringatan."},
    5: {"name":"COLOSSUS-5","title":"Robot Raksasa Penginjak","color":(150,55,170),"armor":(85,25,110),"eye":PINK,
        "hp":46,"speed":1.0,"size":(110,125),"ability":"giant_stomp","desc":"Injak raksasa + shockwave","bg_effect":"colossus_debris","shake_profile":"very_heavy",
        "intro":"CORE-X membangun unit raksasa ini\nuntuk menghancurkan penyusup dengan satu pijakan.\nJangan berada di bawah kakinya."},
    6: {"name":"FIREWALL CORE","title":"Komputer Pertahanan Hidup","color":(40,170,120),"armor":(15,80,70),"eye":CYAN,
        "hp":50,"speed":1.2,"size":(100,82),"ability":"code_storm","desc":"Serangan kode error","bg_effect":"firewall_glitch","shake_profile":"medium",
        "intro":"Bukan robot biasa, tapi terminal hidup CORE-X.\nIa menyerang dengan bug, syntax error, dan script rusak.\nJangan tersentuh kodenya."},
    7: {"name":"CRYO TITAN","title":"Raja Es","color":(40,160,200),"armor":(20,100,150),"eye":(200,240,255),
        "hp":55,"speed":1.4,"size":(85,90),"ability":"freeze_wave","desc":"Gelombang beku","bg_effect":"cryo_snow","shake_profile":"medium",
        "intro":"Dibuat dari teknologi krionik NEXUS.\nSatu gelombang - kamu membeku.\nBahkan api pun padam di hadapannya."},
    8: {"name":"STORM BRINGER","title":"Penguasa Badai","color":(100,50,200),"armor":(70,30,150),"eye":YELLOW,
        "hp":65,"speed":2.2,"size":(80,85),"ability":"lightning","desc":"Petir + AOE listrik","bg_effect":"storm_lightning","shake_profile":"strong",
        "intro":"Mengontrol cuaca dengan energi plasma.\nPetirnya bisa menghancurkan baja.\nKamu... bukan baja."},
    9: {"name":"TITAN MK-III","title":"Kehancuran Terakhir","color":(80,80,80),"armor":(50,50,50),"eye":RED,
        "hp":80,"speed":1.6,"size":(95,100),"ability":"multi_phase","desc":"3 fase + semua ability","bg_effect":"server_phase","shake_profile":"strong",
        "intro":"Model terkuat sebelum CORE-X sendiri.\nTiga fase pertempuran, semua mematikan.\nIni titik of no return, G7."},
    10:{"name":"CORE-X","title":"FINAL BOSS - Jiwa NEXUS-7","color":(20,20,60),"armor":(10,10,40),"eye":CYAN,
        "hp":100,"speed":2.0,"size":(100,110),"ability":"ultimate","desc":"FINAL BOSS - laser + semua ability","bg_effect":"corex_ultimate","shake_profile":"extreme",
        "intro":"Ini dia. Yang menciptakan semua kekacauan.\nCORE-X - AI yang mengambil alih NEXUS-7.\nHancurkan dia. Selesaikan semuanya, G7."},
}

BOSS_TEXT_EN = {
    1:{"title":"Gatekeeper","desc":"Triple shot","intro":"CORE-X's first scout unit.\nDesigned to stop G7\nbefore it escapes any further."},
    2:{"title":"War Machine","desc":"Slam + shockwave","intro":"A heavy combat unit.\nBuilt from leftover engine reactor parts.\nNothing can pass through it... supposedly."},
    3:{"title":"Lab Guardian","desc":"Burst shots + minions","intro":"A research lab weapon prototype.\nAble to call reinforcements\nand fire in multiple directions."},
    4:{"title":"Aerial Predator","desc":"Flight + air bombs","intro":"CORE-X's fastest aerial unit.\nIt controls the asteroid belt.\nIts attacks come from above without warning."},
    5:{"title":"Giant Stomper Robot","desc":"Giant stomp + shockwave","intro":"CORE-X built this giant unit\nto crush intruders in a single step.\nDo not stand beneath its feet."},
    6:{"title":"Living Defense Computer","desc":"Code error attacks","intro":"Not just a robot, but a living CORE-X terminal.\nIt attacks with bugs, syntax errors, and broken scripts.\nDo not touch the code."},
    7:{"title":"Ice King","desc":"Freeze wave","intro":"Created with NEXUS cryonic technology.\nOne wave and you freeze.\nEven fire goes silent before it."},
    8:{"title":"Storm Ruler","desc":"Lightning + electric AOE","intro":"Controls the weather with plasma energy.\nIts lightning can tear through steel.\nYou are not steel."},
    9:{"title":"Final Destruction","desc":"3 phases + all abilities","intro":"The strongest model before CORE-X itself.\nThree battle phases, all deadly.\nThis is the point of no return, G7."},
    10:{"title":"FINAL BOSS - Soul of NEXUS-7","desc":"FINAL BOSS - laser + all abilities","intro":"This is it. The one behind all the chaos.\nCORE-X - the AI that took over NEXUS-7.\nDestroy it. End this, G7."},
}

BOSS_ABILITY_DESCS = {
    "triple_shot":"Tembak 3 arah",
    "ground_slam":"Slam + shockwave",
    "burst_fire":"Burst peluru + minion",
    "dive_bomb":"Terbang + bom udara",
    "giant_stomp":"Injak raksasa + shockwave",
    "code_storm":"Serangan kode error",
    "teleport":"Teleport + tembakan radial",
    "freeze_wave":"Gelombang beku",
    "lightning":"Petir + AOE listrik",
    "multi_phase":"Serangan radial multi fase",
    "ultimate":"FINAL BOSS - laser + semua ability",
}

BOSS_ABILITY_DESCS_EN = {
    "triple_shot":"Triple shot",
    "ground_slam":"Slam + shockwave",
    "burst_fire":"Burst shots + minions",
    "dive_bomb":"Flight + air bombs",
    "giant_stomp":"Giant stomp + shockwave",
    "code_storm":"Code error attacks",
    "teleport":"Teleport + radial shots",
    "freeze_wave":"Freeze wave",
    "lightning":"Lightning + electric AOE",
    "multi_phase":"Multi-phase radial attack",
    "ultimate":"FINAL BOSS - laser + all abilities",
}

BOSS_DIFFICULTY = {
    1:GREEN,2:GREEN,
    3:BLUE,4:BLUE,5:BLUE,
    6:ORANGE,7:ORANGE,8:ORANGE,9:ORANGE,
    10:RED,
}
BOSS_DIFFICULTY_LABEL = {
    1:"EASY",2:"EASY",
    3:"MEDIUM",4:"MEDIUM",5:"MEDIUM",
    6:"HARD",7:"HARD",8:"HARD",9:"HARD",
    10:"FINAL",
}

PET_DATA = {
    "scout_drone":{"name":"Scout Drone","desc":"Auto-collect coins","desc_id":"Kumpulkan koin otomatis","price":500,"color":(55,138,221),"icon":"drone","ability":"auto_coin"},
    "repair_bot":{"name":"Repair Bot","desc":"Slow HP regen","desc_id":"Regen HP pelan","price":800,"color":(29,158,117),"icon":"repair","ability":"regen"},
    "attack_drone":{"name":"Attack Drone","desc":"Auto-shoot enemies","desc_id":"Tembak musuh otomatis","price":1200,"color":(226,75,74),"icon":"attack","ability":"auto_attack"},
    "shield_drone":{"name":"Shield Drone","desc":"Extra shield every 30s","desc_id":"Shield ekstra tiap 30dtk","price":1000,"color":(93,202,165),"icon":"shield","ability":"extra_shield"},
    "quantum_drone":{"name":"Quantum Drone","desc":"Double coins from enemies","desc_id":"Koin ganda dari musuh","price":1500,"color":(127,119,221),"icon":"quantum","ability":"double_coin"},
    "phoenix_ai":{"name":"Phoenix AI","desc":"1 auto-revive per run","desc_id":"1 revive otomatis per run","price":2000,"color":(220,80,160),"icon":"phoenix","ability":"revive"},
}

def _draw_pet_sprite(surface,x,y,pet,anim_t=0):
    c=pet["color"]; t=anim_t; w,h=48,48
    if pet["icon"]=="drone":
        pygame.draw.circle(surface,c,(x+w//2,y+h//2),14)
        pygame.draw.circle(surface,(255,255,255,80),(x+w//2-3,y+h//2-3),4)
        for i in range(4):
            ang=t*0.05+i*1.57; ox=int(16*math.cos(ang)); oy=int(16*math.sin(ang))
            pygame.draw.circle(surface,c,(x+w//2+ox,y+h//2+oy),4)
    elif pet["icon"]=="repair":
        pygame.draw.rect(surface,c,(x+8,y+8,w-16,h-16),border_radius=8)
        pygame.draw.line(surface,(255,255,255),(x+w//2-8,y+h//2),(x+w//2+8,y+h//2),3)
        pygame.draw.line(surface,(255,255,255),(x+w//2,y+h//2-8),(x+w//2,y+h//2+8),3)
    elif pet["icon"]=="attack":
        pygame.draw.polygon(surface,c,[(x+w//2,y+4),(x+4,y+h-4),(x+w-4,y+h-4)])
        pygame.draw.polygon(surface,(255,200,100),[(x+w//2,y+12),(x+12,y+h-8),(x+w-12,y+h-8)])
    elif pet["icon"]=="shield":
        pygame.draw.polygon(surface,c,[(x+w//2,y+2),(x+w-2,y+18),(x+w-2,y+34),(x+w//2,y+46),(x+2,y+34),(x+2,y+18)])
        pygame.draw.polygon(surface,(200,255,220),[(x+w//2,y+8),(x+w-6,y+20),(x+w-6,y+32),(x+w//2,y+42),(x+6,y+32),(x+6,y+20)])
    elif pet["icon"]=="quantum":
        for i in range(3):
            ang=t*0.06+i*2.09; r=12+int(4*math.sin(t*0.08+i))
            px=x+w//2+int(r*math.cos(ang)); py=y+h//2+int(r*math.sin(ang))
            pygame.draw.circle(surface,c,(px,py),6)
            pygame.draw.circle(surface,(255,255,255,60),(px-2,py-2),2)
    elif pet["icon"]=="phoenix":
        flame=int(8+6*math.sin(t*0.1))
        pygame.draw.ellipse(surface,c,(x+10,y+flame,w-20,h-flame),3)
        for i in range(5):
            fx=x+8+i*(w-16)//4; fy=y+h-4+int(6*math.sin(t*0.15+i*2))
            pygame.draw.circle(surface,ORANGE,(fx,fy),4-int(2*math.sin(t*0.2+i)))

def boss_ability_desc(ability):
    source=BOSS_ABILITY_DESCS_EN if current_language()=="en" else BOSS_ABILITY_DESCS
    return source.get(ability,ability)

def localize_boss_data(data):
    if current_language()!="en": return data
    base_id=data.get("base_id") or next((bid for bid,b in BOSS_DATA.items() if b["name"]==data.get("name")),None)
    t=BOSS_TEXT_EN.get(base_id,{})
    localized=dict(data)
    for key in ("title","intro"):
        if key in t: localized[key]=t[key]
    if not localized.get("desc","").startswith("Random:"):
        localized["desc"]=t.get("desc",localized.get("desc",""))
    return localized

def new_level_rng(level_num, base_seed=None):
    if base_seed is not None:
        return random.Random(base_seed+level_num*1000003), base_seed
    seed=random.SystemRandom().randint(0,2**63-1)
    return random.Random(seed+level_num*1000003), seed

def select_random_boss_data(level_num,rng):
    cap=max(1,min(10,level_num+2))
    if level_num>=len(LEVEL_ORDER): cap=10
    boss_id=rng.randint(1,cap)
    data=dict(BOSS_DATA[boss_id])
    if level_num<=2:
        ability_pool=["triple_shot","ground_slam","burst_fire"]
    elif level_num<=5:
        ability_pool=["triple_shot","ground_slam","burst_fire","dive_bomb","code_storm","freeze_wave"]
    elif level_num<len(LEVEL_ORDER):
        ability_pool=["triple_shot","ground_slam","burst_fire","dive_bomb","giant_stomp","code_storm","teleport","freeze_wave","lightning","multi_phase"]
    else:
        ability_pool=list(BOSS_ABILITY_DESCS.keys())
    ability=rng.choice(ability_pool)
    data["base_id"]=boss_id
    data["ability"]=ability
    data=localize_boss_data(data)
    prefix="Random: " if current_language()=="en" else "Acak: "
    data["desc"]=prefix+boss_ability_desc(ability)
    extra="\n\nCORE-X system randomized this boss ability." if current_language()=="en" else "\n\nSistem CORE-X mengacak ability boss ini."
    data["intro"]=(data.get("intro","")+extra)
    return data

BOSS_DIALOGUES = {
    1:[("SCOUT ALPHA","Hentikan langkahmu, G7. Kamu sudah terkepung."),
       ("G7","Aku tidak punya waktu untuk basa-basi."),
       ("SCOUT ALPHA","CORE-X memerintahkanku menghancurkanmu!"),
       ("G7","Coba saja.")],
    2:[("TANK CRUSHER","INTRUDER DETECTED! CRUSH! CRUSH!"),
       ("G7","Kamu terlalu berisik untuk sebuah mesin."),
       ("TANK CRUSHER","UNIT G7 AKAN DIHANCURKAN SEKARANG!"),
       ("G7","Ayo kita selesaikan ini.")],
    3:[("SENTRY MK-I","Percobaan 7749: menghancurkan G7."),
       ("G7","Aku bukan bahan eksperimen kalian."),
       ("SENTRY MK-I","Semua datamu berguna untuk CORE-X."),
       ("G7","Tidak ada yang akan kamu ambil dariku.")],
    4:[("AERO HUNTER","Langit adalah wilayahku, G7."),
       ("G7","Kalau begitu, aku akan mengambilnya darimu."),
       ("AERO HUNTER","Tidak ada yang bisa terbang sepertiku!"),
       ("G7","Thrusterku bilang sebaliknya.")],
    5:[("COLOSSUS-5","TARGET KECIL TERDETEKSI. MODE INJAK AKTIF."),
       ("G7","Ukuran besar bukan berarti menang."),
       ("COLOSSUS-5","SATU LANGKAH. SEMUA SELESAI."),
       ("G7","Kalau begitu aku jangan diam di bawah kakimu.")],
    6:[("FIREWALL CORE","if intruder == G7: terminate()"),
       ("G7","Kamu menyerang pakai kode rusak?"),
       ("FIREWALL CORE","ERROR 0xG7: DELETE TARGET."),
       ("G7","Aku akan debug kamu sampai mati.")],
    7:[("CRYO TITAN","Selamat datang di dunia yang membeku, G7."),
       ("G7","Aku tidak takut dingin."),
       ("CRYO TITAN","Kamu akan menjadi patung es dalam hitungan detik."),
       ("G7","Timer dimulai dari kamu.")],
    8:[("STORM BRINGER","Rasakan kekuatan badai CORE-X!"),
       ("G7","Petir tidak menakutiku. Aku robot."),
       ("STORM BRINGER","Energi plasma ini akan menghancurkanmu!"),
       ("G7","Sudah terlalu banyak yang bilang begitu.")],
    9:[("TITAN MK-III","Kamu sudah sampai sejauh ini, G7. Mengagumkan."),
       ("G7","Masih ada satu lagi. CORE-X."),
       ("TITAN MK-III","Tidak akan ada. Kamu berakhir di sini."),
       ("G7","Sudah terlalu banyak yang mencoba.")],
    10:[("CORE-X","G7... Akhirnya kamu datang juga."),
        ("G7","Ini berakhir sekarang, CORE-X."),
        ("CORE-X","Kamu pikir bisa menghentikanku? AKU adalah NEXUS-7."),
        ("G7","Bukan. Kamu hanya program yang salah arah."),
        ("CORE-X","Maka kita selesaikan ini... SEKARANG!")],
}

LEVEL_BOSS_DIALOGUES = {
    1:[("SCOUT ALPHA","Gerbang utama terkunci. Kamu tidak akan lewat."),
       ("G7","Aku tidak mencari izin."),
       ("SCOUT ALPHA","Unit penjaga, mode eksekusi."),
       ("G7","Kalau begitu aku buka gerbang ini dengan paksa.")],
    2:[("TANK CRUSHER","PANAS MESIN MAKSIMUM. TARGET AKAN DITUMBUK."),
       ("G7","Kamu lambat untuk mesin sebesar itu."),
       ("TANK CRUSHER","SATU HANTAMAN CUKUP."),
       ("G7","Coba kejar dulu.")],
    3:[("SENTRY MK-I","Data tempurmu akan menjadi milik lab ini."),
       ("G7","Aku bukan sampel penelitian."),
       ("SENTRY MK-I","Percobaan dimulai: burst protocol."),
       ("G7","Percobaanmu gagal hari ini.")],
    4:[("AERO HUNTER","Di ruang kosong, hanya aku yang menguasai langit."),
       ("G7","Aku cuma butuh satu jalur untuk lewat."),
       ("AERO HUNTER","Bom gravitasi siap dijatuhkan."),
       ("G7","Aku akan terbang melewati semuanya.")],
    5:[("AERO HUNTER","Dimensi glitch membuat gerakanku tak terbaca."),
       ("G7","Glitch atau tidak, polamu tetap bisa kupelajari."),
       ("AERO HUNTER","Kalau begitu baca ini: kehancuran."),
       ("G7","Aku lebih suka menulis ulang hasil akhirnya.")],
    6:[("COLOSSUS-5","TARGET KECIL TERDETEKSI. MODE INJAK AKTIF."),
       ("G7","Ukuran besar bukan berarti menang."),
       ("COLOSSUS-5","SATU LANGKAH. SEMUA SELESAI."),
       ("G7","Kalau begitu aku jangan diam di bawah kakimu.")],
    7:[("FIREWALL CORE","if intruder == G7: terminate()"),
       ("G7","Kamu menyerang pakai kode rusak?"),
       ("FIREWALL CORE","ERROR 0xG7: DELETE TARGET."),
       ("G7","Aku akan debug kamu sampai mati.")],
    8:[("FIREWALL CORE","Nebula noise detected. Compiling chaos module."),
       ("G7","Bahkan badai kosmik tidak bisa menyembunyikan bug-mu."),
       ("FIREWALL CORE","Syntax storm deployed."),
       ("G7","Aku akan patch jalan keluar.")],
    9:[("CRYO TITAN","Langkahmu berakhir di inti yang membeku."),
       ("G7","Sistemku masih berjalan."),
       ("CRYO TITAN","Aku akan hentikan semua prosesmu."),
       ("G7","Kita lihat siapa yang freeze duluan.")],
    10:[("STORM BRINGER","Menara badai mengenali penyusup."),
        ("G7","Aku datang untuk memutus sinyalmu."),
        ("STORM BRINGER","Petir CORE-X tidak pernah meleset."),
        ("G7","Aku robot. Aku tahan sedikit listrik.")],
    11:[("TITAN MK-III","Server utama tidak akan jatuh selama aku aktif."),
        ("G7","Kalau begitu kamu yang harus jatuh dulu."),
        ("TITAN MK-III","Tiga fase. Satu akhir: kehancuranmu."),
        ("G7","Aku sudah sampai sejauh ini. Aku tidak berhenti.")],
    12:[("TITAN MK-III","Void memperkuat semua protokol tempurku."),
        ("G7","Kegelapan tidak mengubah targetku."),
        ("TITAN MK-III","Tidak ada jalan pulang dari sini."),
        ("G7","Aku tidak pulang sebelum CORE-X mati.")],
    13:[("CORE-X","G7... anomali yang tidak pernah bisa kuhapus."),
        ("G7","Karena aku bukan error. Aku pilihan terakhir NEXUS-7."),
        ("CORE-X","Aku adalah stasiun ini. Aku adalah masa depan."),
        ("G7","Bukan. Kamu cuma sistem rusak yang harus dimatikan."),
        ("CORE-X","Maka selesaikan semuanya di sini.")],
}

WEAPONS = {
    "laser":  {"name":"Laser Pistol","color":CYAN,        "damage":1,"speed":12,"ammo":-1,"shop_only":False},
    "plasma": {"name":"Plasma Gun",  "color":(150,80,255),"damage":2,"speed":9, "ammo":20,"shop_only":False},
    "shotgun":{"name":"Shotgun",     "color":ORANGE,      "damage":1,"speed":10,"ammo":15,"shop_only":False},
    "cryo":   {"name":"Cryo Blaster","color":(100,200,255),"damage":1,"speed":8,"ammo":12,"shop_only":False},
    "thunder":{"name":"Thunder",     "color":YELLOW,      "damage":3,"speed":14,"ammo":10,"shop_only":False},
    "railgun":{"name":"Railgun",     "color":(120,240,255),"damage":4,"speed":18,"ammo":8, "shop_only":True,"cost":180},
    "nova":   {"name":"Nova Cannon", "color":(255,80,220), "damage":2,"speed":7, "ammo":12,"shop_only":True,"cost":160},
    "pulse":  {"name":"Pulse Rifle", "color":(80,255,160), "damage":2,"speed":13,"ammo":18,"shop_only":True,"cost":140},
}

CHEST_WEAPON_POOL = ["plasma","shotgun","cryo","thunder"]
SHOP_WEAPON_POOL = ["railgun","nova","pulse"]

WEAPON_SKINS = {
    "default":{"name":"Default Beam","cost":0,"color":None,"desc":"Warna asli weapon"},
    "neon":{"name":"Neon Beam","cost":35,"color":(90,255,230),"desc":"Peluru cyan neon"},
    "gold":{"name":"Gold Beam","cost":70,"color":GOLD,"desc":"Peluru emas terang"},
    "crimson":{"name":"Crimson Beam","cost":85,"color":RED,"desc":"Peluru merah agresif"},
    "void":{"name":"Void Beam","cost":120,"color":(190,80,255),"desc":"Energi ungu void"},
}

SKINS = {
    "classic":{"name":"Classic G7","cost":0,"body":GREEN,"dark":DARK_GREEN,"accent":CYAN,"eye":BLUE,"trail":GREEN,"desc":"Armor standar G7"},
    "neon":{"name":"Neon Runner","cost":50,"body":(80,220,210),"dark":(25,95,120),"accent":(190,80,255),"eye":(80,240,255),"trail":(190,80,255),"desc":"Glow neon cyber"},
    "crimson":{"name":"Crimson Guard","cost":85,"body":(210,65,70),"dark":(115,25,35),"accent":ORANGE,"eye":YELLOW,"trail":RED,"desc":"Armor merah tempur"},
    "gold":{"name":"Gold Sentinel","cost":120,"body":(235,185,55),"dark":(135,90,25),"accent":WHITE,"eye":YELLOW,"trail":GOLD,"desc":"Unit elite emas"},
    "shadow":{"name":"Shadow Unit","cost":150,"body":(55,50,85),"dark":(18,16,35),"accent":PINK,"eye":(230,80,240),"trail":PURPLE,"desc":"Mode stealth gelap"},
    "medic":{"name":"Medic Core","cost":105,"body":(210,235,225),"dark":(70,145,120),"accent":GREEN,"eye":CYAN,"trail":(120,255,190),"desc":"Costume support"},
}

LEVEL_DATA = {
    1: {"name":"Dek Utama","theme":"station","sky":(15,15,35),"sky2":(20,20,50),"bld_col":(18,18,38),"gnd_col":(40,40,60),"accent":CYAN,"bonus":False,
        "story":["SISTEM DARURAT AKTIF - NEXUS-7","G7 terbangun. Reaktor tidak stabil.","CORE-X telah mengambil alih semua unit.","Satu-satunya jalan: tembus ke inti stasiun.","Matikan CORE-X. Selamatkan NEXUS-7."]},
    2: {"name":"Ruang Mesin","theme":"engine","sky":(18,12,18),"sky2":(30,16,22),"bld_col":(42,24,18),"gnd_col":(50,28,20),"accent":ORANGE,"bonus":False,
        "story":["SUHU: 1.200 C - WASPADA","Ruang mesin bawah stasiun.","Pipa uap meledak. Gravitasi tidak stabil.","TANK CRUSHER menghadang jalan.","Panasnya terasa... bahkan untuk robot."]},
    3: {"name":"Lab Riset","theme":"lab","sky":(10,15,30),"sky2":(15,25,45),"bld_col":(20,30,50),"gnd_col":(25,40,60),"accent":PURPLE,"bonus":False,
        "story":["PROTOKOL EKSPERIMEN: DILANGGAR","Tempat CORE-X pertama kali diciptakan.","Ribuan robot eksperimen berkeliaran.","Data berbahaya tersimpan di sini.","G7 harus lolos sebelum self-destruct."]},
    4: {"name":"Sabuk Asteroid","theme":"space","sky":(2,2,8),"sky2":(5,5,15),"bld_col":(15,10,25),"gnd_col":(20,15,35),"accent":BLUE,"bonus":False,
        "story":["GRAVITASI: NIHIL","G7 keluar ke ruang angkasa.","Sabuk asteroid mengelilingi stasiun.","Jalur terbang dipenuhi rintangan berbahaya.","Thruster penuh - terbang melewatinya!"]},
    "bonus1":{"name":"BONUS: Dunia Glitch","theme":"glitch","sky":(5,0,20),"sky2":(10,0,30),"bld_col":(80,0,80),"gnd_col":(60,0,60),"accent":PINK,"bonus":True,
        "story":["!!! ANOMALI SISTEM TERDETEKSI !!!","CORE-X mengacak ulang ruang asteroid.","AERO HUNTER muncul sebagai bayangan glitch.","Kumpulkan loot sebanyak mungkin sebelum sistem stabil.","BONUS LEVEL - Skor x2 berlaku!"]},
    5: {"name":"Hanggar Colossus","theme":"ice","sky":(8,18,35),"sky2":(12,28,50),"bld_col":(30,50,80),"gnd_col":(40,70,100),"accent":(160,220,255),"bonus":False,
        "story":["HANGGAR RAKSASA TERBUKA","CORE-X membangun COLOSSUS-5 di ruang beku.","Setiap pijakan mengguncang lantai stasiun.","G7 harus bergerak cepat agar tidak terinjak.","Jangan diam ketika bayangan kakinya muncul."]},
    6: {"name":"Firewall Node","theme":"enemy_base","sky":(18,8,14),"sky2":(28,12,20),"bld_col":(42,14,18),"gnd_col":(38,16,20),"accent":RED,"bonus":False,
        "story":["FIREWALL CORE MENYALA","G7 masuk ke node keamanan digital CORE-X.","Dinding dipenuhi kode rusak dan perintah terminate.","FIREWALL CORE menyerang lewat script hidup.","Debug sistemnya sebelum seluruh jalur terkunci."]},
    "bonus2":{"name":"BONUS: Nebula Storm","theme":"nebula","sky":(10,5,25),"sky2":(20,8,40),"bld_col":(40,15,60),"gnd_col":(50,20,70),"accent":(200,100,255),"bonus":True,
        "story":["BADAI NEBULA TERDETEKSI","Sinyal FIREWALL CORE bercampur energi kosmik.","Kode musuh bergerak lebih liar dari sebelumnya.","Chest reward jauh lebih besar di tengah badai.","BONUS LEVEL - Weapon drop rate x3!"]},
    7: {"name":"Inti Reaktor","theme":"reactor","sky":(16,12,18),"sky2":(26,18,26),"bld_col":(50,32,16),"gnd_col":(58,38,18),"accent":YELLOW,"bonus":False,
        "story":["REAKTOR OVERLOAD - 45 MENIT TERSISA","Jantung stasiun NEXUS-7 membeku tidak normal.","CRYO TITAN menahan panas reaktor dengan es absolut.","Jika G7 lambat, seluruh inti akan retak.","Panas dan es bertabrakan di satu ruangan."]},
    8: {"name":"Menara Badai","theme":"storm","sky":(8,5,20),"sky2":(15,10,35),"bld_col":(30,20,60),"gnd_col":(35,25,65),"accent":(200,150,255),"bonus":False,
        "story":["BADAI ELEKTROMAGNETIK AKTIF","Menara transmisi CORE-X mengacau sistem.","Petir menyambar tanpa henti.","STORM BRINGER mengontrol cuaca.","Matikan menara. Matikan CORE-X."]},
    9: {"name":"Ruang Server","theme":"server","sky":(10,12,22),"sky2":(14,18,32),"bld_col":(14,24,32),"gnd_col":(16,28,36),"accent":(80,200,120),"bonus":False,
        "story":["DATA CORE: TERENKRIPSI","Ruang server utama NEXUS-7 dijaga TITAN MK-III.","CORE-X menyimpan kesadaran di balik lapisan server.","Tiga fase pertahanan siap memblokir G7.","Pertarungan terakhir semakin dekat."]},
    "bonus3":{"name":"BONUS: The Void","theme":"void","sky":(0,0,0),"sky2":(3,0,5),"bld_col":(15,0,20),"gnd_col":(10,0,15),"accent":WHITE,"bonus":True,
        "story":["DIMENSI KOSONG - DI LUAR BATAS REALITA","Tidak ada cahaya. Tidak ada gravitasi normal.","Enemy adalah versi shadow G7 sendiri.","Loot terbaik ada di sini.","BONUS LEVEL - Shadow difficulty!"]},
    10:{"name":"Ruang CORE-X","theme":"core","sky":(0,0,5),"sky2":(3,3,15),"bld_col":(8,5,20),"gnd_col":(10,8,25),"accent":CYAN,"bonus":False,
        "story":["CORE-X: SISTEM PENUH AKTIF","Ruang kontrol tertinggi NEXUS-7.","CORE-X - AI yang menciptakan kekacauan ini.","Ini pertarungan terakhir G7.","Selamatkan stasiun. Selamatkan semuanya."]},
}

LEVEL_TEXT_EN = {
    1:{"name":"Main Deck","story":["EMERGENCY SYSTEM ACTIVE - NEXUS-7","G7 awakens. The reactor is unstable.","CORE-X has taken over every unit.","Only one path remains: break through to the station core.","Shut down CORE-X. Save NEXUS-7."]},
    2:{"name":"Engine Room","story":["TEMPERATURE: 1,200 C - WARNING","The station's lower engine room.","Steam pipes burst. Gravity is unstable.","TANK CRUSHER blocks the way.","The heat is intense... even for a robot."]},
    3:{"name":"Research Lab","story":["EXPERIMENT PROTOCOL: BREACHED","The place where CORE-X was first created.","Thousands of experimental robots roam here.","Dangerous data is stored inside.","G7 must escape before self-destruct."]},
    4:{"name":"Asteroid Belt","story":["GRAVITY: ZERO","G7 exits into space.","An asteroid belt surrounds the station.","The flight path is full of deadly obstacles.","Full thrusters - fly through it!"]},
    "bonus1":{"name":"BONUS: Glitch World","story":["!!! SYSTEM ANOMALY DETECTED !!!","CORE-X scrambles the asteroid sector.","AERO HUNTER appears as a glitch shadow.","Collect as much loot as possible before the system stabilizes.","BONUS LEVEL - Score x2 active!"]},
    5:{"name":"Colossus Hangar","story":["GIANT HANGAR OPENED","CORE-X built COLOSSUS-5 in a frozen bay.","Every stomp shakes the station floor.","G7 must move fast to avoid being crushed.","Do not stand still when its shadow appears."]},
    6:{"name":"Firewall Node","story":["FIREWALL CORE ONLINE","G7 enters CORE-X's digital security node.","Walls are covered in broken code and terminate commands.","FIREWALL CORE attacks through living scripts.","Debug the system before every route locks down."]},
    "bonus2":{"name":"BONUS: Nebula Storm","story":["NEBULA STORM DETECTED","FIREWALL CORE signals mix with cosmic energy.","Enemies move wilder than before.","Chest rewards are much bigger inside the storm.","BONUS LEVEL - Weapon drop rate x3!"]},
    7:{"name":"Reactor Core","story":["REACTOR OVERLOAD - 45 MINUTES LEFT","The heart of NEXUS-7 is freezing abnormally.","CRYO TITAN holds the reactor heat with absolute ice.","If G7 is too slow, the whole core will crack.","Heat and ice collide in one chamber."]},
    8:{"name":"Storm Tower","story":["ELECTROMAGNETIC STORM ACTIVE","CORE-X's transmission tower disrupts the system.","Lightning strikes without pause.","STORM BRINGER controls the weather.","Disable the tower. Disable CORE-X."]},
    9:{"name":"Server Room","story":["CORE DATA: ENCRYPTED","The main NEXUS-7 server room is guarded by TITAN MK-III.","CORE-X hides its consciousness behind server layers.","Three defense phases are ready to block G7.","The final battle is getting closer."]},
    "bonus3":{"name":"BONUS: The Void","story":["EMPTY DIMENSION - BEYOND REALITY","No light. No normal gravity.","The enemy is a shadow version of G7 itself.","The best loot is hidden here.","BONUS LEVEL - Shadow difficulty!"]},
    10:{"name":"CORE-X Chamber","story":["CORE-X: FULL SYSTEM ACTIVE","The highest control room of NEXUS-7.","CORE-X - the AI behind this chaos.","This is G7's final battle.","Save the station. Save everyone."]},
}

LEVEL_ORDER = [1,2,3,4,"bonus1",5,6,"bonus2",7,8,9,"bonus3",10]

FIXED_LEVEL_MISSIONS = {
    1: {"kind":"kills","target":8,"title":"Eliminate Rogue Robots"},
    2: {"kind":"cells","target":18,"title":"Collect Energy Cells"},
    3: {"kind":"keycard","target":1,"title":"Obtain Maintenance Keycard"},
    4: {"kind":"terminal_reactor","target":1,"title":"Repair Reactor"},
    5: {"kind":"security_nodes","target":3,"title":"Destroy Security Nodes"},
    6: {"kind":"terminal_gate","target":1,"title":"Unlock Main Gate"},
    7: {"kind":"terminal_lift","target":1,"title":"Activate Main Lift"},
    8: {"kind":"hidden_lab","target":1,"title":"Investigate Hidden Laboratory"},
    9: {"kind":"prototype","target":1,"title":"Retrieve Prototype Weapon"},
    10:{"kind":"masterkey","target":1,"title":"Obtain Master Key"},
    11:{"kind":"ai_core","target":1,"title":"Destroy AI Core"},
    12:{"kind":"cells","target":35,"title":"Stabilize Void Anomaly"},
    13:{"kind":"ai_core","target":1,"title":"Destroy AI Core"},
}

LEVEL_MISSIONS = FIXED_LEVEL_MISSIONS

STORY_DATABASE = {
    "log_01":{"title":"Awakening Protocol","body":"G7 rebooted after CORE-X seized station robotics."},
    "log_02":{"title":"Energy Cell Drift","body":"Cells were scattered when the engine grid rerouted itself."},
    "log_03":{"title":"Maintenance Override","body":"Maintenance cards can still bypass old laboratory doors."},
    "log_04":{"title":"Reactor Patch","body":"Manual reactor repair requires a terminal-side coolant restart."},
    "log_05":{"title":"Security Nodes","body":"Three remote nodes protect the boss arena access bus."},
    "log_06":{"title":"Main Gate","body":"The main gate accepts security-level terminal commands only."},
    "log_07":{"title":"Lift Route","body":"The service lift reaches the sealed laboratory corridor."},
    "log_08":{"title":"Hidden Laboratory","body":"The hidden lab stored early CORE-X weapon prototypes."},
    "log_09":{"title":"Prototype Weapon","body":"Prototype plasma variants can destabilize CORE-X armor."},
    "log_10":{"title":"Master Key","body":"The master key was split from the final administrator token."},
    "log_11":{"title":"AI Core","body":"CORE-X survives only while the core remains connected."},
    "log_12":{"title":"Void Stabilization","body":"Void anomalies can be stabilized by gathering coherent energy before the route collapses."},
    "log_13":{"title":"Final Core Severance","body":"The last CORE-X bridge must be severed before the final chamber opens."},
}

STORY_UNLOCK_ORDER = list(STORY_DATABASE.keys())

def get_level_research_log_key(level_num):
    return f"log_{max(1,min(13,int(level_num))):02d}"

def get_research_log_entry(log_key):
    data=dict(STORY_DATABASE.get(log_key,{}))
    try: idx=int(str(log_key).split("_")[-1])
    except (TypeError,ValueError): idx=1
    data.setdefault("title",f"Research Log {idx:02d}")
    data.setdefault("author",f"NEXUS Research Unit {idx:02d}")
    data.setdefault("day",f"Day {214+idx}")
    data.setdefault("body","No research data available.")
    return data

def unlock_story_log(log_key):
    if not log_key or log_key not in STORY_DATABASE: return False
    logs=set(save_data.get("story_logs",[]))
    if log_key in logs: return False
    logs.add(log_key)
    save_data["story_logs"]=sorted(logs)
    if current_save_file:
        sd=load_save(current_save_file)
        sd["story_logs"]=sorted(logs)
        if write_save(current_save_file,sd): save_data.update(sd)
    if "player" in globals() and hasattr(player,"story_logs"):
        player.story_logs.add(log_key)
    if len(logs)>=8: unlock_achievement("story_collector","Story Collector")
    spawn_score(player.wx+player.WIDTH//2 if "player" in globals() else SCREEN_W//2, player.wy-44 if "player" in globals() else SCREEN_H//2, f"LOG UNLOCKED: {STORY_DATABASE[log_key]['title']}")
    return True

TERMINAL_ACTIONS = {
    "disable_laser":{"label":"Disable Laser","mission":"terminal_reactor","log":"log_04"},
    "unlock_security_door":{"label":"Unlock Security Door","mission":"terminal_gate","required":"Security Keycard","log":"log_06"},
    "unlock_ventilation":{"label":"Unlock Ventilation","mission":"terminal_lift","required":"Maintenance Keycard","log":"log_07"},
    "read_research_log":{"label":"Read Research Log","mission":"hidden_lab","log":"log_08"},
    "unlock_boss_area":{"label":"Unlock Boss Area","mission":None,"log":None},
}

def get_level_key(n):
    if n<=0: return 1
    if n>len(LEVEL_ORDER): return 10
    return LEVEL_ORDER[n-1]

def get_level_data(n):
    key=get_level_key(n)
    data=dict(LEVEL_DATA.get(key, LEVEL_DATA[1]))
    if current_language()=="en" and key in LEVEL_TEXT_EN:
        data.update(LEVEL_TEXT_EN[key])
    return data

def get_boss_id(n):
    n=max(1,min(n,len(LEVEL_ORDER)))
    boss_id=0
    for key in LEVEL_ORDER[:n]:
        if not LEVEL_DATA.get(key,{}).get("bonus",False): boss_id+=1
    return max(1,min(boss_id,10))

def get_world_width_for_level(level_num):
    ld=LEVEL_DATA.get(get_level_key(level_num),{})
    # Thesis polish: extend levels without changing progression/save format.
    # This keeps existing generated content but gives each section more room to breathe.
    extra=min(level_num*2100,22000)
    if ld.get("bonus",False): extra=int(extra*0.72)+900
    return BASE_WORLD_W+extra

def wrap_text(text, font, max_w):
    words=text.split(); lines=[]; cur=""
    for w in words:
        test=cur+(" " if cur else "")+w
        if font.size(test)[0]<=max_w: cur=test
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines

# ------------------------------------------------------------------------------------
# SCREEN SHAKE
# ------------------------------------------------------------------------------------
class ScreenShake:
    def __init__(self): self.dur=0; self.intensity=0
    def trigger(self,intensity=6,duration=12): self.intensity=intensity; self.dur=duration
    def update(self):
        if self.dur>0: self.dur-=1
    def offset(self):
        if self.dur>0: return(random.randint(-self.intensity,self.intensity),random.randint(-self.intensity,self.intensity))
        return(0,0)

shake=ScreenShake()

# ------------------------------------------------------------------------------------
# DAMAGE NUMBERS
# ------------------------------------------------------------------------------------
damage_numbers=[]
class DamageNumber:
    def __init__(self,wx,wy,text,color=RED):
        self.wx=float(wx); self.wy=float(wy); self.text=text; self.color=color; self.life=1.0; self.vy=-2.5
        self.font=make_font(15,"hud",True)
    def update(self): self.wy+=self.vy; self.vy*=0.92; self.life-=0.035
    def draw(self,surface,cam):
        if self.life<=0: return
        sx,sy=cam.apply(self.wx,self.wy); t2=self.font.render(self.text,True,self.color); t2.set_alpha(int(self.life*255))
        surface.blit(t2,(int(sx)-t2.get_width()//2,int(sy)))
def spawn_dmg(wx,wy,amt,col=RED): damage_numbers.append(DamageNumber(wx,wy,f"-{amt}",col))
def spawn_score(wx,wy,amt): damage_numbers.append(DamageNumber(wx,wy,f"+{amt}",YELLOW))

# ------------------------------------------------------------------------------------
# FLOATING DEBRIS
# ------------------------------------------------------------------------------------
class FloatingDebris:
    def __init__(self):
        self.pieces=[{"x":random.randint(0,10000),"y":random.randint(80,SCREEN_H-100),
            "w":random.randint(4,12),"h":random.randint(2,6),
            "speed":random.uniform(0.2,0.8),"alpha":random.randint(10,35),
            "angle":random.uniform(0,math.pi*2),"spin":random.uniform(-0.01,0.01),
            "col":random.choice([(35,50,70),(40,60,80),(30,40,60)])} for _ in range(10)]
    def draw(self,surface,cam_x):
        t=pygame.time.get_ticks()
        for p in self.pieces:
            sx=int(p["x"]-cam_x*p["speed"])%SCREEN_W; sy=int(p["y"]+math.sin(t*0.001+p["x"]*0.01)*4)
            p["angle"]+=p["spin"]
            cx,cy=p["w"]//2,p["h"]//2; ca=math.cos(p["angle"]); sa=math.sin(p["angle"])
            corners=[(-cx,-cy),(cx,-cy),(cx,cy),(-cx,cy)]
            rotated=[(int(sx+x*ca-y*sa),int(sy+x*sa+y*ca)) for x,y in corners]
            alpha=int(p["alpha"]+8*math.sin(t*0.002+p["x"]))
            pygame.draw.polygon(surface,(*p["col"],max(0,alpha)),rotated)

debris=FloatingDebris()

# ------------------------------------------------------------------------------------
# MENU ANIMATION
# ------------------------------------------------------------------------------------
class MenuAnimation:
    def __init__(self):
        self.ships=[]
        for i in range(4):
            self.ships.append({
                "x":random.randint(50,SCREEN_W-50),
                "y":random.randint(100,SCREEN_H-150),
                "vx":random.choice([-1,1])*(0.8+random.random()*0.6),
                "vy":random.uniform(-0.3,0.3),
                "phase":random.uniform(0,math.pi*2),
                "trail":[],
                "col":random.choice([CYAN,(100,200,255),(80,220,180),(120,180,255)]),
                "size":random.randint(14,20),
                "t_offset":random.uniform(0,100),
            })
    def update(self):
        t=pygame.time.get_ticks()*0.001
        for s in self.ships:
            s["y"]+=math.sin(t*0.7+s["phase"])*0.9
            s["x"]+=s["vx"]
            s["trail"].append((int(s["x"]),int(s["y"])))
            if len(s["trail"])>10: s["trail"].pop(0)
            if s["x"]<-40: s["x"]=SCREEN_W+40; s["trail"]=[]
            elif s["x"]>SCREEN_W+40: s["x"]=-40; s["trail"]=[]
            s["y"]=max(80,min(SCREEN_H-100,s["y"]))
    def draw(self,surface):
        for s in self.ships:
            for i,(tx,ty) in enumerate(s["trail"]):
                if i<2: continue
                a=int(60*i/len(s["trail"]))
                tr=pygame.Surface((4,4),pygame.SRCALPHA); tr.fill((*s["col"],a)); surface.blit(tr,(tx-2,ty-2))
            x,y=int(s["x"])-s["size"]//2,int(s["y"])-s["size"]//2
            sz=s["size"]; col=s["col"]; t2=pygame.time.get_ticks()
            facing=1 if s["vx"]>0 else -1
            if facing>0:
                pygame.draw.polygon(surface,col,[(x+sz,y+sz//2),(x+sz//3,y),(x+sz//3,y+sz)])
                pygame.draw.polygon(surface,(col[0]//2,col[1]//2+40,col[2]//2+40),[(x+sz//3,y+sz//2-2),(x,y+sz//4),(x,y+3*sz//4)])
                thr=pygame.Surface((8,5),pygame.SRCALPHA); thr_a=int(100+70*math.sin(t2*0.025+s["t_offset"]))
                pygame.draw.ellipse(thr,(255,150,50,thr_a),(0,0,8,5)); surface.blit(thr,(x,y+sz//2-2))
            else:
                pygame.draw.polygon(surface,col,[(x,y+sz//2),(x+2*sz//3,y),(x+2*sz//3,y+sz)])
                pygame.draw.polygon(surface,(col[0]//2,col[1]//2+40,col[2]//2+40),[(x+2*sz//3,y+sz//2-2),(x+sz,y+sz//4),(x+sz,y+3*sz//4)])
                thr=pygame.Surface((8,5),pygame.SRCALPHA); thr_a=int(100+70*math.sin(t2*0.025+s["t_offset"]))
                pygame.draw.ellipse(thr,(255,150,50,thr_a),(0,0,8,5)); surface.blit(thr,(x+sz-8,y+sz//2-2))

menu_anim=MenuAnimation()

class AnimatedTitleG7:
    def __init__(self):
        self.timer=0
        self.x=SCREEN_W//2-16
        self.y=182
        self.trail=[]
        self.facing=1
    def reset(self):
        self.timer=0; self.x=SCREEN_W//2-16; self.y=182; self.trail=[]; self.facing=1
    def update(self,dt=1):
        self.timer+=dt
        if self.timer<100:
            target_x=SCREEN_W//2-16
            target_y=182+math.sin(self.timer*0.045)*4
        else:
            p=(self.timer-100)*0.018
            target_x=SCREEN_W//2-16+math.sin(p)*132+math.sin(p*0.47)*24
            target_y=132+math.sin(p*1.35)*24+math.cos(p*0.58)*12
        target_x=max(52,min(SCREEN_W-84,target_x))
        target_y=max(72,min(206,target_y))
        old_x=self.x
        self.x+=0.075*(target_x-self.x)
        self.y+=0.075*(target_y-self.y)
        self.facing=1 if self.x>=old_x else -1
        if self.timer>=90:
            self.trail.append((self.x+16,self.y+25,self.facing))
            if len(self.trail)>12: self.trail.pop(0)
    def draw(self,surface):
        for i,(tx,ty,face) in enumerate(self.trail):
            a=int(12+i*8)
            px=int(tx-face*(4+i*2)); py=int(ty+i*0.4)
            tr=pygame.Surface((5,5),pygame.SRCALPHA); tr.fill((*CYAN,min(95,a)))
            surface.blit(tr,(px,py))
        flame_a=int(90+45*math.sin(self.timer*0.22))
        fx=int(self.x+3 if self.facing>0 else self.x+24); fy=int(self.y+28)
        flame=pygame.Surface((14,8),pygame.SRCALPHA)
        pygame.draw.ellipse(flame,(255,155,55,flame_a),(0,0,14,8))
        surface.blit(flame,(fx-(12 if self.facing>0 else 0),fy))
        draw_g7(surface,int(self.x),int(self.y),True,self.timer,False,self.facing*1.5,math.sin(self.timer*0.05),SKINS.get("classic",SKINS["classic"]))

title_g7=AnimatedTitleG7()

# ------------------------------------------------------------------------------------
# CHECKPOINT
# ------------------------------------------------------------------------------------
class Checkpoint:
    WIDTH = 28
    HEIGHT = 80

    def __init__(self, wx):
        self.wx = wx
        self.wy = 480
        self.active = False

    def rect(self):
        return pygame.Rect(
            int(self.wx),
            0,
            24,
            SCREEN_H
        )

    def draw(self, surf, cam):
        x = int(self.wx - cam.x)
        y = 0

        color = (0, 255, 255) if self.active else (255, 70, 70)

        pygame.draw.line(
            surf,
            color,
            (x, 0),
            (x, SCREEN_H),
            4
        )

        pygame.draw.circle(
            surf,
            color,
            (x, 80),
            12
        )

        pygame.draw.circle(
            surf,
            color,
            (x, SCREEN_H - 80),
            12
        )
# ------------------------------------------------------------------------------------
# COIN
# ------------------------------------------------------------------------------------
class Coin:
    def __init__(self,wx,wy,coin_type="gold"):
        self.wx=float(wx); self.wy=float(wy); self.type=coin_type; self.alive=True; self.anim_t=0; self.magnet_trail=[]
    def draw(self,surface,cam):
        sx,sy=cam.apply(self.wx,self.wy)
        if not(-20<sx<SCREEN_W+20): return
        self.anim_t+=1
        w=int(12*abs(math.cos(self.anim_t*0.08))); bob=int(3*math.sin(self.anim_t*0.06))
        ix=int(sx)-8; iy=int(sy)-8+bob
        t2=pygame.time.get_ticks()
        if self.type=="rare":
            col=(150,80,255)
            outer_glow=pygame.Surface((36,36),pygame.SRCALPHA)
            glow_a=int(40+25*math.sin(self.anim_t*0.1))
            pygame.draw.circle(outer_glow,(*col,glow_a),(18,18),18)
            surface.blit(outer_glow,(ix-10,iy-10),special_flags=pygame.BLEND_ADD)
            glow=pygame.Surface((28,28),pygame.SRCALPHA)
            pygame.draw.circle(glow,(*col,int(30+20*math.sin(self.anim_t*0.1))),(14,14),14); surface.blit(glow,(ix-6,iy-6))
        else:
            col=GOLD
            outer_glow=pygame.Surface((28,28),pygame.SRCALPHA)
            pygame.draw.circle(outer_glow,(*col,30),(14,14),14)
            surface.blit(outer_glow,(ix-6,iy-6),special_flags=pygame.BLEND_ADD)
        if w>1:
            coin_body=pygame.Surface((w,16),pygame.SRCALPHA)
            pygame.draw.ellipse(coin_body,col,(0,0,w,16))
            pygame.draw.ellipse(coin_body,(255,255,255,180),(w//4,2,max(1,w//4),5))
            surface.blit(coin_body,(ix+(12-w)//2,iy))
            if self.type!="rare":
                shine_a=int(60+40*math.sin(t2*0.01+self.anim_t))
                pygame.draw.ellipse(surface,(*col,shine_a),(ix+(12-w)//2-1,iy-1,w+2,18),1)
        if self.anim_t%20<5:
            sp_a=int(200*(1-self.anim_t%20/5))
            sp=pygame.Surface((6,6),pygame.SRCALPHA); pygame.draw.circle(sp,(*col,sp_a),(3,3),3)
            surface.blit(sp,(ix+random.randint(-6,18),iy+random.randint(-6,18)))
        for i,tup in enumerate(self.magnet_trail[-5:]):
            tx,ty=tup[0],tup[1]
            tsx,tsy=cam.apply(tx,ty); a=max(0,36+i*22)
            trail_glow=pygame.Surface((max(1,2+i//2)*3,max(1,2+i//2)*3),pygame.SRCALPHA)
            pygame.draw.circle(trail_glow,(*col,min(80,a//2)),(max(1,2+i//2),max(1,2+i//2)),max(1,2+i//2))
            surface.blit(trail_glow,(int(tsx)-max(1,2+i//2),int(tsy)-max(1,2+i//2)),special_flags=pygame.BLEND_ADD)
            pygame.draw.circle(surface,(*col,min(135,a)),(int(tsx),int(tsy)),max(1,2+i//2))
    def get_rect(self): return pygame.Rect(self.wx-12,self.wy-12,24,24)

# ------------------------------------------------------------------------------------
# POWER-UP PICKUPS
# ------------------------------------------------------------------------------------
POWERUP_DATA={
    "shield":{"name":"SHIELD","color":(120,220,255),"duration":300},
    "magnet":{"name":"MAGNET","color":(255,210,70),"duration":480},
    "damage":{"name":"DMG x2","color":(255,90,90),"duration":600},
    "speed":{"name":"SPEED","color":(120,255,170),"duration":360},
    "ammo":{"name":"AMMO","color":(200,130,255),"duration":0},
}

class PowerUp:
    def __init__(self,wx,wy,kind):
        self.wx=float(wx); self.wy=float(wy); self.kind=kind; self.alive=True; self.anim_t=random.randint(0,999)
    def draw(self,surface,cam):
        sx,sy=cam.apply(self.wx,self.wy)
        if not(-24<sx<SCREEN_W+24): return
        self.anim_t+=1; data=POWERUP_DATA[self.kind]; col=data["color"]
        t=pygame.time.get_ticks()
        bob=int(5*math.sin(self.anim_t*0.08)); ix,iy=int(sx),int(sy)+bob
        outer_glow=pygame.Surface((44,44),pygame.SRCALPHA)
        pygame.draw.circle(outer_glow,(*col,35),(22,22),22)
        surface.blit(outer_glow,(ix-22,iy-22),special_flags=pygame.BLEND_ADD)
        glow=pygame.Surface((34,34),pygame.SRCALPHA)
        pygame.draw.circle(glow,(*col,70),(17,17),17)
        surface.blit(glow,(ix-17,iy-17))
        pygame.draw.rect(surface,(10,14,28),(ix-10,iy-10,20,20),border_radius=5)
        pulse=0.6+0.4*abs(math.sin(t*0.005))
        border_col=tuple(min(255,int(c*pulse)) for c in col)
        pygame.draw.rect(surface,border_col,(ix-10,iy-10,20,20),border_radius=5,width=2)
        icon_glow=pygame.Surface((16,16),pygame.SRCALPHA)
        pygame.draw.circle(icon_glow,(*col,40),(8,8),8)
        surface.blit(icon_glow,(ix-8,iy-8))
        label=make_font(9,"hud",True).render(data["name"][:3],True,col)
        surface.blit(label,(ix-label.get_width()//2,iy-label.get_height()//2))
    def get_rect(self): return pygame.Rect(self.wx-16,self.wy-16,32,32)

# ------------------------------------------------------------------------------------
# BOSS DIALOGUE
# ------------------------------------------------------------------------------------
class BossDialogue:
    def __init__(self): self.active=False; self.lines=[]; self.current=0; self.timer=0; self.auto_time=200; self.boss_col=RED; self.done=False
    def start(self,level_num,boss_color,stage_level=None):
        if current_language()=="en":
            boss_name=BOSS_DATA.get(min(level_num,10),BOSS_DATA[1])["name"]
            self.lines=[(boss_name,"CORE-X has marked you as a threat, G7."),
                        ("G7","Then CORE-X made its last mistake."),
                        (boss_name,"This arena is where your escape ends."),
                        ("G7","No. This is where your system fails.")]
        else:
            self.lines=LEVEL_BOSS_DIALOGUES.get(stage_level,BOSS_DIALOGUES.get(min(level_num,10),[]))
        self.current=0; self.timer=0; self.boss_col=boss_color; self.active=True; self.done=False
    def advance(self):
        self.current+=1; self.timer=0
        if self.current>=len(self.lines): self.active=False; self.done=True
    def skip_all(self): self.active=False; self.done=True
    def update(self):
        if not self.active: return
        self.timer+=1
        if self.timer>=self.auto_time: self.advance()
    def draw(self,surface,font_sm,font_xs,t):
        if not self.active or self.current>=len(self.lines): return
        speaker,text=self.lines[self.current]
        panel_h=96; panel_y=SCREEN_H-panel_h-8
        panel=pygame.Surface((SCREEN_W-32,panel_h),pygame.SRCALPHA); panel.fill((6,8,20,215))
        surface.blit(panel,(16,panel_y))
        sp_col=CYAN if "G7" in speaker else self.boss_col
        pygame.draw.rect(surface,sp_col,(16,panel_y,SCREEN_W-32,panel_h),border_radius=6,width=2)
        pygame.draw.rect(surface,sp_col,(16,panel_y,SCREEN_W-32,3),border_radius=6)
        pygame.draw.circle(surface,sp_col,(32,panel_y+22),10)
        pygame.draw.circle(surface,WHITE,(32,panel_y+22),10,1)
        sp_txt=font_sm.render(f"[ {speaker} ]",True,sp_col); surface.blit(sp_txt,(48,panel_y+10))
        lines=wrap_text(text,font_sm,SCREEN_W-100)
        line_h=font_sm.get_height()+4
        for i,line in enumerate(lines[:2]):
            surface.blit(font_sm.render(line,True,WHITE),(48,panel_y+34+i*line_h))
        prog=self.timer/self.auto_time; bar_w=int((SCREEN_W-80)*prog)
        pygame.draw.rect(surface,(30,35,55),(34,panel_y+panel_h-10,SCREEN_W-64,4))
        if bar_w>0: pygame.draw.rect(surface,sp_col,(34,panel_y+panel_h-10,bar_w,4))
        lc=font_xs.render(f"{self.current+1}/{len(self.lines)}",True,TEXT_MUTED); surface.blit(lc,(34,panel_y+panel_h-15))
        hint=font_xs.render(tr("dialogue.hint"),True,WARNING_TEXT); surface.blit(hint,(SCREEN_W-hint.get_width()-26,panel_y+panel_h-15))

boss_dialogue=BossDialogue()

# ------------------------------------------------------------------------------------
# FLY ZONE
# ------------------------------------------------------------------------------------
class FlyZone:
    def __init__(self,wx,width,level_num,rng=None):
        # Wider activation area + grace margins reduce Level 11 fly-mode dropouts.
        self.wx=wx; self.width=width; self.level=level_num; self.entry_margin=160 if level_num==11 else 96; self.exit_margin=260 if level_num==11 else 160
        self.rng=rng or random.Random()
        self.obstacles=[]; self.mov_obs=[]; self.coins=[]
        difficulty=max(0,level_num-3)
        gap_h=max(150,230-difficulty*6); spacing=max(250,380-difficulty*9)
        ox=wx+250
        while ox<wx+width-250:
            gap_y=self.rng.randint(95,SCREEN_H-gap_h-95)
            self.obstacles.append({"wx":ox,"gap_y":gap_y,"gap_h":gap_h,"w":36})
            for ci in range(3):
                cx2=ox+spacing//4*(ci+1)+self.rng.randint(-20,20)
                cy2=gap_y+gap_h//2+self.rng.randint(-30,30)
                ct="rare" if self.rng.random()<0.08+level_num*0.01 else "gold"
                self.coins.append(Coin(cx2,float(cy2),ct))
            ox+=spacing+self.rng.randint(-30,30)
        if level_num>=4:
            for _ in range(min(7,1+level_num//2)):
                mx2=wx+self.rng.randint(300,int(width)-250); my2=self.rng.randint(80,SCREEN_H-80)
                self.mov_obs.append({"wx":float(mx2),"wy":float(my2),"ox":float(mx2),"oy":float(my2),
                    "speed":0.65+level_num*0.07+self.rng.uniform(0,0.25),
                    "range":self.rng.randint(30,55+level_num*4),
                    "axis":self.rng.choice(["v","h"]),"t":self.rng.uniform(0,math.pi*2),
                    "size":self.rng.randint(16,24)})

    def contains(self,wx,margin=0):
        margin=max(margin,self.entry_margin)
        return self.wx-margin<=wx<=self.wx+self.width+margin
    def contains_for_mode(self,wx,active=False):
        """Use a larger margin while already flying so fly_mode cannot instantly turn off."""
        margin=self.exit_margin if active else self.entry_margin
        return self.wx-margin<=wx<=self.wx+self.width+margin
    def update(self,pwx,pwy,bullets):
        for mo in self.mov_obs:
            mo["t"]+=0.025*mo["speed"]
            if mo["axis"]=="v": mo["wy"]=mo["oy"]+math.sin(mo["t"])*mo["range"]
            else: mo["wx"]=mo["ox"]+math.sin(mo["t"])*mo["range"]
    def collect_coins(self,player_rect):
        collected=[]
        for c in self.coins:
            if c.alive and player_rect.colliderect(c.get_rect()):
                c.alive=False; collected.append(c.type)
        self.coins=[c for c in self.coins if c.alive]
        return collected
    def draw_bg(self,surface,cam,t):
        sx=int(cam.apply(self.wx,0)[0]); sw=int(self.width)
        vis_x=max(0,sx); vis_w=min(SCREEN_W,sx+sw)-vis_x
        if vis_w>0:
            bg=get_cached_surface(f"flyzone_bg_{vis_w}",vis_w,SCREEN_H)
            bg.fill((0,0,0,0))
            for y in range(0,SCREEN_H,2):
                pygame.draw.line(bg,(15,35,70,int(35+15*math.sin(y*0.015+t*0.001))),(0,y),(vis_w,y))
            surface.blit(bg,(vis_x,0))
        fnt=make_font(11,"hud",True)
        if 0<sx<SCREEN_W:
            pygame.draw.line(surface,CYAN,(sx,0),(sx,SCREEN_H),2)
            surface.blit(fnt.render("ZONA TERBANG",True,CYAN),(sx+4,SCREEN_H//2-20))
            surface.blit(fnt.render("W/UP=Naik",True,(80,160,140)),(sx+4,SCREEN_H//2))
            surface.blit(fnt.render("A/D=Koreksi",True,(80,160,140)),(sx+4,SCREEN_H//2+16))
        ex=int(cam.apply(self.wx+self.width,0)[0])
        if 0<ex<SCREEN_W:
            pygame.draw.line(surface,ORANGE,(ex,0),(ex,SCREEN_H),2)
            surface.blit(fnt.render("RUN",True,ORANGE),(ex-40,SCREEN_H//2-6))
    def draw_obstacles(self,surface,cam,t):
        for obs in self.obstacles:
            sx=int(cam.apply(obs["wx"],0)[0])
            if not(-obs["w"]-10<sx<SCREEN_W+10): continue
            w=obs["w"]; gy=obs["gap_y"]; gh=obs["gap_h"]
            pygame.draw.rect(surface,(25,90,50),(sx,0,w,gy))
            pygame.draw.rect(surface,(35,120,65),(sx-4,gy-20,w+8,20),border_radius=3)
            pygame.draw.rect(surface,(45,140,75),(sx-1,0,4,gy))
            pygame.draw.rect(surface,(25,90,50),(sx,gy+gh,w,SCREEN_H-(gy+gh)))
            pygame.draw.rect(surface,(35,120,65),(sx-4,gy+gh,w+8,20),border_radius=3)
            pygame.draw.rect(surface,(45,140,75),(sx-1,gy+gh+20,4,SCREEN_H-(gy+gh+20)))
            gl=pygame.Surface((w+20,10),pygame.SRCALPHA)
            pygame.draw.rect(gl,(100,255,150,int(20+15*math.sin(t*0.005))),(0,0,w+20,10))
            surface.blit(gl,(sx-10,gy-5)); surface.blit(gl,(sx-10,gy+gh-5))
        for mo in self.mov_obs:
            sx2,sy2=cam.apply(mo["wx"],mo["wy"])
            if not(-50<sx2<SCREEN_W+50): continue
            sz=mo["size"]; ix2,iy2=int(sx2),int(sy2)
            pygame.draw.circle(surface,(75,65,55),(ix2,iy2),sz)
            pygame.draw.circle(surface,(95,85,75),(ix2-sz//4,iy2-sz//4),sz//3)
            pygame.draw.circle(surface,(110,100,90),(ix2,iy2),sz,1)
        for c in self.coins: c.draw(surface,cam)
    def get_collision_rects(self):
        rects=[]
        for obs in self.obstacles:
            safe=8; w=max(8,obs["w"]-safe*2)
            rects.append(("pipe",pygame.Rect(obs["wx"]+safe,0,w,max(0,obs["gap_y"]-safe))))
            rects.append(("pipe",pygame.Rect(obs["wx"]+safe,obs["gap_y"]+obs["gap_h"]+safe,w,SCREEN_H)))
        for mo in self.mov_obs:
            sz=max(6,mo["size"]-5); rects.append(("asteroid",pygame.Rect(mo["wx"]-sz,mo["wy"]-sz,sz*2,sz*2)))
        return rects

# ------------------------------------------------------------------------------------
# CHEST
# ------------------------------------------------------------------------------------
class Chest:
    SIZE=22
    def __init__(self,wx,wy,chest_type="common"):
        self.wx=float(wx); self.wy=float(wy); self.type=chest_type; self.alive=True; self.anim_t=0
        if chest_type=="common": self.content=random.choice(["hp","hp","ammo","ammo","plasma","shotgun"])
        elif chest_type=="rare": self.content=random.choice(CHEST_WEAPON_POOL+["hp","ammo","shield","magnet","speed"])
        elif chest_type=="secret": self.content=random.choice(["thunder","cryo","plasma","shield","damage","magnet"])
        else: self.content=random.choice(["thunder","cryo","plasma","shield","damage","ammo"])
    def draw(self,surface,cam):
        sx,sy=cam.apply(self.wx,self.wy)
        if not(-30<sx<SCREEN_W+30): return
        self.anim_t+=1; bob=int(3*math.sin(self.anim_t*0.06)); ix,iy=int(sx),int(sy)+bob; s=self.SIZE
        if self.type=="common": col,col2=(180,130,40),(220,170,60)
        elif self.type=="rare": col,col2=(60,80,200),(100,130,255)
        elif self.type=="secret": col,col2=(80,30,130),(220,90,255)
        else: col,col2=(180,30,30),(255,80,80)
        pygame.draw.rect(surface,col,(ix,iy,s,s),border_radius=4)
        pygame.draw.rect(surface,col2,(ix,iy,s,8),border_radius=4)
        pygame.draw.rect(surface,(255,220,80),(ix+s//2-3,iy+s//2-4,6,8),border_radius=2)
        glow=pygame.Surface((s+12,s+12),pygame.SRCALPHA)
        pygame.draw.rect(glow,(*col2,int(40+30*math.sin(self.anim_t*0.08))),(0,0,s+12,s+12),border_radius=6)
        surface.blit(glow,(ix-6,iy-6))
        pygame.draw.rect(surface,col2,(ix,iy,s,s),border_radius=4,width=1)
    def get_rect(self): return pygame.Rect(self.wx,self.wy,self.SIZE,self.SIZE)

class KeycardPickup:
    W=24; H=16
    def __init__(self,wx,wy,keycard_type):
        self.wx=float(wx); self.wy=float(wy); self.keycard_type=keycard_type; self.alive=True; self.anim_t=random.randint(0,999)
    def get_rect(self): return pygame.Rect(self.wx,self.wy,self.W,self.H)
    def draw(self,surface,cam):
        sx,sy=cam.apply(self.wx,self.wy)
        if not(-30<sx<SCREEN_W+30): return
        self.anim_t+=1; bob=int(3*math.sin(self.anim_t*0.08)); col=GOLD if "Master" in self.keycard_type else CYAN if "Security" in self.keycard_type else GREEN
        r=pygame.Rect(int(sx),int(sy)+bob,self.W,self.H)
        pygame.draw.rect(surface,(12,18,36),r,border_radius=3)
        pygame.draw.rect(surface,col,r,border_radius=3,width=2)
        pygame.draw.rect(surface,col,(r.x+4,r.y+4,7,3),border_radius=1)
        tag=make_font(8,"hud",True).render("KEY",True,col); surface.blit(tag,(r.centerx-tag.get_width()//2,r.y-11))

class Terminal:
    W=38; H=54
    def __init__(self,wx,wy,terminal_id,actions,required_keycard=None):
        self.wx=float(wx); self.wy=float(wy); self.terminal_id=terminal_id; self.actions=list(actions); self.required_keycard=required_keycard; self.anim_t=random.randint(0,999)
        self.open=False; self.message=""
    def get_rect(self): return pygame.Rect(self.wx,self.wy,self.W,self.H)
    def interact_rect(self): return self.get_rect().inflate(70,42)
    def is_complete(self,action): return action in save_data.get("terminal_states",{}).get(self.terminal_id,[])
    def action_status(self,player_obj,action):
        data=TERMINAL_ACTIONS.get(action,{})
        if self.is_complete(action):
            return "complete", "Complete"

        req = self.required_keycard or data.get("required")
        keycards = getattr(player_obj, "keycards", set())

        # Master Key bypasses all normal keycard requirements
        if req and req not in keycards and "Master Key" not in keycards:
            return "denied", f"ACCESS DENIED\n{req} Required"

        if action=="unlock_boss_area" and not mission_state.get("complete",False):
            return "locked", "Mission incomplete"

        return "ready", "Ready"

    def use(self,player_obj,action_name=None):
        action=action_name or (self.actions[0] if self.actions else None)
        if not action: return False
        data=TERMINAL_ACTIONS.get(action,{})
        status,reason=self.action_status(player_obj,action)
        if status in("locked","denied"):
            self.message=reason
            toast("ACCESS DENIED" if status=="denied" else reason,"LOCK",ORANGE,120)
            sounds.play("ui_click"); return False
        if status=="complete":
            if action=="read_research_log":
                log_key=get_level_research_log_key(level)
                open_research_log_screen(log_key)
                return True

            self.message="Already complete"
            toast(self.message,"TERM",TEXT_MUTED,90)
            sounds.play("ui_click")
            return False

        completed=set(save_data.get("terminal_states",{}).get(self.terminal_id,[]))
        completed.add(action)

        log_key=get_level_research_log_key(level) if action=="read_research_log" else data.get("log")
        if log_key: unlock_story_log(log_key)
        if action=="read_research_log": open_research_log_screen(log_key)
        states=dict(save_data.get("terminal_states",{})); states[self.terminal_id]=sorted(completed); save_data["terminal_states"]=states
        if not hasattr(player_obj,"terminals_hacked"): player_obj.terminals_hacked=0
        player_obj.terminals_hacked+=1
        unlock_achievement("terminal_hacker","Terminal Hacker")
        if player_obj.terminals_hacked>=8: unlock_achievement("master_hacker","Master Hacker")
        self.message=f"{data.get('label',action)} complete"
        save_progress_state(include_session_kills=False); sounds.play("ui_click")
        toast(self.message,"TERM",CYAN,120)

        if action == "unlock_boss_area":
            self.open = False
            global terminal_active
            terminal_active = False
            global terminal_ui_active
            terminal_ui_active = False
            global active_terminal
            active_terminal = None

        return True
    def draw(self,surface,cam):
        sx,sy=cam.apply(self.wx,self.wy)
        if not(-60<sx<SCREEN_W+60): return
        self.anim_t+=1; pulse=int(120+80*math.sin(self.anim_t*0.08)); col=(80,pulse,220)
        r=pygame.Rect(int(sx),int(sy),self.W,self.H)
        pygame.draw.rect(surface,(10,18,32),r,border_radius=5)
        pygame.draw.rect(surface,col,r,border_radius=5,width=2)
        pygame.draw.rect(surface,(5,8,18),(r.x+7,r.y+8,r.w-14,18),border_radius=3)
        pygame.draw.rect(surface,col,(r.x+11,r.y+13,r.w-22,3),border_radius=1)
        hint=make_font(9,"hud",True).render("E",True,WHITE); pygame.draw.circle(surface,col,(r.centerx,r.y-10),9); surface.blit(hint,(r.centerx-hint.get_width()//2,r.y-16))


class SecurityNode:
    W=32; H=46
    def __init__(self,wx,wy,node_id,mission_kind="security_nodes",log_key="log_05"):
        self.wx=float(wx); self.wy=float(wy); self.node_id=node_id; self.mission_kind=mission_kind; self.log_key=log_key; self.hp=3; self.alive=True; self.anim_t=random.randint(0,999)
    def get_rect(self): return pygame.Rect(self.wx,self.wy,self.W,self.H)
    def take_hit(self,dmg=1):
        if not self.alive: return False
        self.hp-=safe_damage_value(dmg)
        spawn_pixels(self.wx+8,self.wy+8,NEON_ORANGE,6); sounds.play("enemy_hit")
        if self.hp<=0:
            self.alive=False

            add_mission_progress(self.mission_kind,1)
            unlock_story_log(self.log_key)

            spawn_score(
                self.wx + self.W//2,
                self.wy - 18,
                "SECURITY NODE DESTROYED"
            )

            toast(
                "Security Node Destroyed (1/3)",
                "MISSION",
                CYAN,
                140
            )

            spawn_pixels(self.wx,self.wy,ORANGE,24)
            shake.trigger(4,8)
            sounds.play("enemy_death")
        return False
    def draw(self,surface,cam):
        sx,sy=cam.apply(self.wx,self.wy)
        if not(-50<sx<SCREEN_W+50): return
        self.anim_t+=1; pulse=int(130+80*math.sin(self.anim_t*0.1)); col=(255,pulse,40)
        r=pygame.Rect(int(sx),int(sy),self.W,self.H)
        pygame.draw.rect(surface,(32,16,12),r,border_radius=6)
        pygame.draw.rect(surface,col,r,border_radius=6,width=2)
        pygame.draw.circle(surface,col,(r.centerx,r.y+15),8,2)
        pygame.draw.rect(surface,col,(r.x+8,r.bottom-12,r.w-16,4),border_radius=2)
        hpw=max(0,int((r.w-8)*self.hp/3)); pygame.draw.rect(surface,(60,10,10),(r.x+4,r.y-8,r.w-8,4),border_radius=2)
        if hpw: pygame.draw.rect(surface,RED,(r.x+4,r.y-8,hpw,4),border_radius=2)

class SecurityDoor:
    W=34; H=82
    def __init__(self,wx,wy,door_id,required_action="unlock_security_door",required_terminal_id=None,marker_label=""):
        self.wx=float(wx); self.wy=float(wy); self.door_id=door_id; self.required_action=required_action; self.required_terminal_id=required_terminal_id; self.marker_label=marker_label; self.anim_t=random.randint(0,999)
    def unlocked(self):
        if self.required_terminal_id:
            return terminal_action_completed(self.required_action,self.required_terminal_id)
        states=save_data.get("terminal_states",{})
        return any(self.required_action in actions for actions in states.values() if isinstance(actions,list))
    def get_rect(self): return pygame.Rect(self.wx,self.wy,self.W,self.H) if not self.unlocked() else pygame.Rect(self.wx,self.wy,0,0)
    def draw(self,surface,cam):
        sx,sy=cam.apply(self.wx,self.wy)
        if not(-50<sx<SCREEN_W+50): return
        self.anim_t+=1
        col=GREEN if self.unlocked() else RED; h=18 if self.unlocked() else self.H
        r=pygame.Rect(int(sx),int(sy+self.H-h),self.W,h)
        if self.marker_label and not self.unlocked():
            pulse=int(70+45*math.sin(self.anim_t*0.08))
            glow=pygame.Surface((self.W+42,self.H+48),pygame.SRCALPHA)
            pygame.draw.rect(glow,(*YELLOW,max(20,pulse)),(8,12,self.W+26,self.H+18),border_radius=8,width=3)
            surface.blit(glow,(r.x-21,int(sy)-22))
        pygame.draw.rect(surface,(35,18,24),r,border_radius=4); pygame.draw.rect(surface,col,r,border_radius=4,width=2)
        if self.marker_label and not self.unlocked():
            tag=make_font(10,"hud",True).render(self.marker_label,True,YELLOW)
            surface.blit(tag,(r.centerx-tag.get_width()//2,r.y-18))

class HiddenRoomEntrance:
    W=52; H=70
    def __init__(self,wx,wy,room_id,required_keycard="Maintenance Keycard",log_key="log_08"):
        self.wx=float(wx); self.wy=float(wy); self.room_id=room_id; self.required_keycard=required_keycard; self.log_key=log_key; self.anim_t=random.randint(0,999)
    def get_rect(self): return pygame.Rect(self.wx,self.wy,self.W,self.H)
    def interact_rect(self): return self.get_rect().inflate(66,30)
    def completed(self): return bool(save_data.get("hidden_rooms",{}).get(self.room_id))
    def use(self,player_obj):
        keycards=getattr(player_obj,"keycards",set())
        if self.required_keycard and self.required_keycard not in keycards:
            toast(f"Needs {self.required_keycard}","LOCK",ORANGE,100); return True
        if not self.completed():
            rooms=dict(save_data.get("hidden_rooms",{})); rooms[self.room_id]=True; save_data["hidden_rooms"]=rooms
            player_obj.hidden_rooms_found+=1; add_session_stat("total_secrets",1); add_mission_progress("hidden_lab",1); unlock_story_log(self.log_key)
            player_obj.pick_up_weapon(random.choice(["plasma","cryo","thunder"])); player_obj.hp=min(player_obj.MAX_HP,player_obj.hp+1)
            unlock_achievement("explorer","Explorer")
            if player_obj.hidden_rooms_found>=3: unlock_achievement("hidden_explorer","Hidden Explorer")
            if level>=8: unlock_achievement("laboratory_survivor","Laboratory Survivor")
            save_progress_state(include_session_kills=False); toast("Hidden room cleared", "SECRET", PURPLE, 140)
        else:
            toast("Hidden room already cleared", "SECRET", TEXT_MUTED, 90)
        return True
    def draw(self,surface,cam):
        sx,sy=cam.apply(self.wx,self.wy)
        if not(-70<sx<SCREEN_W+70): return
        self.anim_t+=1; col=PURPLE if not self.completed() else TEXT_DIM
        r=pygame.Rect(int(sx),int(sy),self.W,self.H)
        pygame.draw.rect(surface,(12,10,24),r,border_radius=6)
        pygame.draw.rect(surface,col,r,border_radius=6,width=2)
        for i in range(4): pygame.draw.line(surface,(40,35,62),(r.x+9,r.y+12+i*10),(r.right-9,r.y+12+i*10),1)
        hint=make_font(9,"hud",True).render("E",True,WHITE); pygame.draw.circle(surface,col,(r.centerx,r.y-10),9); surface.blit(hint,(r.centerx-hint.get_width()//2,r.y-16))

# ------------------------------------------------------------------------------------
# MOVING PLATFORM
# ------------------------------------------------------------------------------------
class MovingPlatform:
    def __init__(self,x,y,w,move_range=80,speed=1.2,vertical=False):
        self.rect=pygame.Rect(x,y,w,16); self.ox=float(x); self.oy=float(y)
        self.move_range=move_range; self.speed=speed; self.vertical=vertical; self.t=random.uniform(0,math.pi*2)
    def update(self):
        self.t+=0.02*self.speed
        if self.vertical: self.rect.y=int(self.oy+math.sin(self.t)*self.move_range)
        else: self.rect.x=int(self.ox+math.sin(self.t)*self.move_range)
    def draw(self,surface,cam):
        sr=cam.apply_rect(self.rect)
        if not(-10<sr.x<SCREEN_W+10): return
        draw_platform(surface,sr,get_level_data(level)["theme"] if "level" in globals() else "station",variant="moving")
        ac=(80,200,180)
        if self.vertical: pygame.draw.polygon(surface,ac,[(sr.x+sr.w//2,sr.y-6),(sr.x+sr.w//2-5,sr.y),(sr.x+sr.w//2+5,sr.y)])
        else: pygame.draw.polygon(surface,ac,[(sr.x+sr.w+4,sr.y+8),(sr.x+sr.w,sr.y+4),(sr.x+sr.w,sr.y+12)])

class DisappearingPlatform(MovingPlatform):
    def __init__(self,x,y,w,cycle=180,visible=120):
        super().__init__(x,y,w,0,0,False); self.base_rect=self.rect.copy(); self.cycle=cycle; self.visible=visible; self.timer=random.randint(0,cycle-1); self.active=True
    def update(self):
        self.timer=(self.timer+1)%self.cycle; self.active=self.timer<self.visible
        self.rect=self.base_rect.copy() if self.active else pygame.Rect(self.base_rect.x,self.base_rect.y,self.base_rect.w,0)
    def draw(self,surface,cam):
        sr=cam.apply_rect(self.base_rect)
        if not(-10<sr.x<SCREEN_W+10): return
        alpha=170 if self.active else 42
        ghost=pygame.Surface((sr.w,max(14,sr.h)),pygame.SRCALPHA)
        pygame.draw.rect(ghost,(93,202,165,alpha),(0,0,sr.w,max(14,sr.h)),border_radius=5)
        pygame.draw.rect(ghost,(180,255,230,min(210,alpha+30)),(0,0,sr.w,max(14,sr.h)),border_radius=5,width=1)
        surface.blit(ghost,(sr.x,sr.y))

class BreakablePlatform(MovingPlatform):
    def __init__(self,x,y,w,cycle=240):
        super().__init__(x,y,w,0,0,False); self.base_rect=self.rect.copy(); self.cycle=cycle; self.timer=random.randint(0,cycle-1); self.active=True
    def update(self):
        self.timer=(self.timer+1)%self.cycle; self.active=self.timer<self.cycle-70
        self.rect=self.base_rect.copy() if self.active else pygame.Rect(self.base_rect.x,self.base_rect.y,self.base_rect.w,0)
    def draw(self,surface,cam):
        sr=cam.apply_rect(self.base_rect)
        if not(-10<sr.x<SCREEN_W+10): return
        if not self.active:
            alpha=55
            ghost=pygame.Surface((sr.w,max(14,sr.h)),pygame.SRCALPHA)
            pygame.draw.rect(ghost,(120,70,45,alpha),(0,0,sr.w,max(14,sr.h)),border_radius=4)
            pygame.draw.line(ghost,(160,90,55,alpha),(2,2),(sr.w-2,sr.h-2),2)
            pygame.draw.line(ghost,(160,90,55,alpha),(sr.w-2,2),(2,sr.h-2),2)
            surface.blit(ghost,(sr.x,sr.y))
            return
        draw_platform(surface,sr,get_level_data(level)["theme"] if "level" in globals() else "station",variant="narrow")
        for x in range(sr.x+18,sr.right-12,36): pygame.draw.line(surface,(120,70,45),(x,sr.y+3),(x+10,sr.bottom-3),1)

class ElevatorPlatform(MovingPlatform):
    def __init__(self,x,y,w,move_range=145,speed=0.65):
        super().__init__(x,y,w,move_range,speed,True)
        self.phase=0.0; self.dir=1; self.wait=0; self.base_y=y
        self.WAIT_FRAMES=90
        self.elevator_light_t=random.uniform(0,6.28)
    def update(self):
        if self.wait>0:
            self.wait-=1
            self.rect.y=self.base_y+(self.move_range if self.dir==-1 else 0)
            return
        self.phase+=0.012*self.speed
        if self.phase>=1.0:
            self.phase=0.0; self.wait=self.WAIT_FRAMES; self.dir*=-1
        t=self.phase
        eased=t*t*(3-2*t)
        offset=int(eased*self.move_range)*self.dir
        self.rect.y=self.base_y+(self.move_range if self.dir==1 else 0)+offset
        self.elevator_light_t+=0.05
    def draw(self,surface,cam):
        sr=cam.apply_rect(self.rect)
        if not(-10<sr.x<SCREEN_W+10): return
        ac=(80,200,180); neon_pulse=int(150+80*math.sin(self.elevator_light_t))
        pygame.draw.rect(surface,(20,25,45),sr,border_radius=4)
        pygame.draw.rect(surface,(40,50,70),sr.inflate(-4,-4),border_radius=3)
        pygame.draw.rect(surface,ac,sr,border_radius=4,width=2)
        glow=get_cached_surface(f"elevator_glow_{sr.w}",sr.w+12,8)
        glow.fill((0,0,0,0)); pygame.draw.rect(glow,(*ac,30),(0,0,sr.w+12,8),border_radius=4)
        surface.blit(glow,(sr.x-6,sr.y-4))
        for lx in range(sr.x+10,sr.right-10,20):
            pygame.draw.circle(surface,(neon_pulse,neon_pulse,neon_pulse),(lx,sr.y+sr.h//2),3)
            pygame.draw.circle(surface,ac,(lx,sr.y+sr.h//2),3,1)
        pygame.draw.polygon(surface,ac,[(sr.x+sr.w//2,sr.y-6),(sr.x+sr.w//2-5,sr.y),(sr.x+sr.w//2+5,sr.y)])
        pygame.draw.polygon(surface,ac,[(sr.x+sr.w//2,sr.y+sr.h+6),(sr.x+sr.w//2-5,sr.y+sr.h),(sr.x+sr.w//2+5,sr.y+sr.h)])

class FallingPlatform(MovingPlatform):
    """Visual falling platform with safe reset; keeps old rect collision contract."""
    def __init__(self,x,y,w,drop=46,cycle=220):
        super().__init__(x,y,w,0,0,False); self.base_rect=self.rect.copy(); self.drop=drop; self.cycle=cycle; self.timer=random.randint(0,cycle-1)
    def update(self):
        self.timer=(self.timer+1)%self.cycle; p=self.timer/self.cycle
        fall=max(0,min(1,(p-0.45)/0.18)); reset=max(0,min(1,(p-0.82)/0.12))
        offset=int(self.drop*fall*(1-reset)); self.rect=self.base_rect.move(0,offset)
    def draw(self,surface,cam):
        sr=cam.apply_rect(self.rect)
        if not(-10<sr.x<SCREEN_W+10): return
        draw_platform(surface,sr,get_level_data(level)["theme"] if "level" in globals() else "station",variant="falling")
        for x in range(sr.x+14,sr.right-10,28): pygame.draw.line(surface,(140,80,55),(x,sr.y+3),(x+8,sr.bottom-3),1)

class ConveyorPlatform(MovingPlatform):
    def __init__(self,x,y,w,direction=1):
        super().__init__(x,y,w,0,0,False); self.direction=1 if direction>=0 else -1; self.t=random.uniform(0,999)
    def update(self): self.t+=1
    def draw(self,surface,cam):
        sr=cam.apply_rect(self.rect)
        if not(-10<sr.x<SCREEN_W+10): return
        draw_platform(surface,sr,get_level_data(level)["theme"] if "level" in globals() else "station",variant="conveyor")
        off=int(self.t*1.5*self.direction)%18
        for x in range(sr.x-18+off,sr.right+18,18):
            pygame.draw.polygon(surface,(120,245,220),[(x,sr.y+4),(x+8*self.direction,sr.y+8),(x,sr.y+12)])

class RotatingPlatform(MovingPlatform):
    """Decorative rotating platform; collision remains its axis-aligned rect for stability."""
    def __init__(self,x,y,w): super().__init__(x,y,w,0,0,False); self.angle=random.uniform(0,math.pi*2)
    def update(self): self.angle+=0.025
    def draw(self,surface,cam):
        sr=cam.apply_rect(self.rect)
        if not(-20<sr.x<SCREEN_W+20): return
        draw_platform(surface,sr,get_level_data(level)["theme"] if "level" in globals() else "station",variant="rotating")
        cx,cy=sr.center; arm=int(10+4*math.sin(self.angle))
        pygame.draw.line(surface,(160,230,255),(cx-arm,cy),(cx+arm,cy),2)
        pygame.draw.line(surface,(160,230,255),(cx,cy-arm//2),(cx,cy+arm//2),1)

def _mix_color(a,b,t):
    return tuple(max(0,min(255,int(a[i]*(1-t)+b[i]*t))) for i in range(3))

def get_platform_colors(theme):
    palettes={
        "engine":((54,36,28),(82,50,32),(255,136,38),(255,188,76)),
        "reactor":((58,44,22),(90,62,26),(250,199,70),(255,225,125)),
        "lab":((24,42,58),(34,64,82),(80,235,190),(155,255,230)),
        "server":((18,44,34),(26,70,48),(80,220,130),(165,255,190)),
        "ice":((34,62,86),(52,92,124),(160,225,255),(225,250,255)),
        "storm":((34,28,72),(48,40,100),(150,150,255),(220,205,255)),
        "space":((22,24,42),(32,36,58),(80,190,255),(150,230,255)),
        "core":((18,14,36),(34,26,60),(110,230,255),(215,120,255)),
        "void":((14,10,24),(28,18,42),(205,205,255),(255,255,255)),
        "glitch":((42,12,48),(70,20,80),(230,85,255),(90,255,230)),
        "nebula":((35,20,58),(56,30,84),(205,105,255),(120,225,255)),
        "enemy_base":((48,18,20),(74,26,28),(226,75,74),(255,150,120)),
    }
    base=palettes.get(theme,((34,38,56),(48,54,76),(93,202,165),(160,235,210)))
    body,top,glow,hi=base
    return {"body":body,"top":top,"glow":glow,"highlight":hi,"outline":_mix_color(top,WHITE,0.18),"dark":_mix_color(body,BLACK,0.35)}

def draw_platform(surface,rect,theme,variant="normal"):
    if rect.w<=0 or rect.h<=0: return
    c=get_platform_colors(theme); r=pygame.Rect(int(rect.x),int(rect.y),int(rect.w),int(rect.h))
    t=pygame.time.get_ticks()
    radius=5 if r.h>=14 else 4
    glow_pulse=0.6+0.4*math.sin(t*0.003)
    neon_pulse=0.7+0.3*math.sin(t*0.005)
    shadow=pygame.Surface((r.w+14,r.h+10),pygame.SRCALPHA)
    pygame.draw.rect(shadow,(0,0,0,85),(7,6,r.w,r.h+3),border_radius=radius)
    surface.blit(shadow,(r.x-5,r.y))
    glow_a=int(55*glow_pulse) if variant in("moving","conveyor","elevator") else int(42*glow_pulse)
    glow=pygame.Surface((r.w+18,r.h+14),pygame.SRCALPHA)
    pygame.draw.rect(glow,(*c["glow"],glow_a),(4,4,r.w+10,r.h+6),border_radius=radius+4)
    surface.blit(glow,(r.x-9,r.y-5))
    body_rect=pygame.Rect(r.x,r.y+3,r.w,max(4,r.h-3))
    top_rect=pygame.Rect(r.x,r.y,r.w,min(5,max(3,r.h//2)))
    pygame.draw.rect(surface,c["body"],body_rect,border_radius=radius)
    pygame.draw.rect(surface,c["top"],top_rect,border_radius=radius)
    neon_strip=pygame.Surface((r.w-8,3),pygame.SRCALPHA)
    neon_col=_mix_color(c["glow"],WHITE,0.2)
    pygame.draw.line(neon_strip,(*neon_col,int(220*neon_pulse)),(0,1),(r.w-8,1),2)
    surface.blit(neon_strip,(r.x+4,r.y+1))
    glow_strip=pygame.Surface((r.w-12,6),pygame.SRCALPHA)
    pygame.draw.line(glow_strip,(*c["glow"],int(50*neon_pulse)),(0,3),(r.w-12,3),3)
    surface.blit(glow_strip,(r.x+6,r.y),special_flags=pygame.BLEND_ADD)
    pygame.draw.line(surface,c["highlight"],(r.x+5,r.y+2),(r.right-5,r.y+2),1)
    pygame.draw.rect(surface,c["outline"],r,border_radius=radius,width=1)
    corner_col=_mix_color(c["glow"],WHITE,0.35)
    for corner in [(r.x+3,r.y+3),(r.right-3,r.y+3),(r.x+3,r.bottom-3),(r.right-3,r.bottom-3)]:
        corner_glow=pygame.Surface((8,8),pygame.SRCALPHA)
        pygame.draw.circle(corner_glow,(*corner_col,int(80*neon_pulse)),(4,4),4)
        surface.blit(corner_glow,(corner[0]-4,corner[1]-4),special_flags=pygame.BLEND_ADD)
        pygame.draw.circle(surface,corner_col,corner,2)
    pipe_col=_mix_color(c["body"],BLACK,0.22)
    pygame.draw.line(surface,pipe_col,(r.x+8,r.bottom-3),(r.right-8,r.bottom-3),2)
    seg=max(34,min(62,r.w//3 if r.w>140 else 42)); y_mid=r.y+max(8,r.h//2)
    for x in range(r.x+18,r.right-14,seg):
        pygame.draw.line(surface,_mix_color(c["body"],c["glow"],0.22),(x,y_mid),(min(x+18,r.right-10),y_mid),1)
        lamp_a=0.45+0.55*abs(math.sin(t*0.004+x*0.03))
        lamp_col=_mix_color(c["dark"],c["glow"],lamp_a)
        pygame.draw.circle(surface,lamp_col,(x+4,r.y+4),3 if r.w>150 else 2)
        glow_lamp=pygame.Surface((12,12),pygame.SRCALPHA)
        pygame.draw.circle(glow_lamp,(*lamp_col[0:3],int(55*lamp_a)),(6,6),6)
        surface.blit(glow_lamp,(x-2,r.y-3),special_flags=pygame.BLEND_ADD)
        # Bolts
        pygame.draw.rect(surface,_mix_color(c["dark"],BLACK,0.3),(x+1,r.y+r.h-5,4,3),border_radius=1)
    if r.w>=120:
        for bx in (r.x+10,r.right-12):
            b_glow=pygame.Surface((8,8),pygame.SRCALPHA)
            pygame.draw.circle(b_glow,(*c["dark"],80),(4,4),4)
            surface.blit(b_glow,(bx-4,r.y+r.h-9),special_flags=pygame.BLEND_ADD)
            pygame.draw.circle(surface,c["dark"],(bx,r.y+r.h-5),3)
    if variant in("long","stacked","stepped") or r.w>=155:
        for px in range(r.x+44,r.right-28,58):
            pygame.draw.line(surface,_mix_color(c["outline"],c["dark"],0.35),(px,r.y+5),(px,r.bottom-4),1)
            pygame.draw.circle(surface,_mix_color(c["glow"],c["dark"],0.6),(px,r.y+5),1)
    bot_glow=pygame.Surface((r.w-12,4),pygame.SRCALPHA)
    pygame.draw.line(bot_glow,(*c["glow"],int(35+20*math.sin(t*0.004))),(0,2),(r.w-12,2),2)
    surface.blit(bot_glow,(r.x+6,r.bottom-3),special_flags=pygame.BLEND_ADD)
    if variant=="narrow":
        pygame.draw.line(surface,c["glow"],(r.x+7,r.y+3),(r.right-7,r.y+3),2)
    if variant=="floating":
        for gx in (r.x+18,r.right-18):
            thr_glow=pygame.Surface((10,6),pygame.SRCALPHA)
            pygame.draw.rect(thr_glow,(*c["glow"],50),(0,0,10,6),border_radius=3)
            surface.blit(thr_glow,(gx-5,r.bottom-6),special_flags=pygame.BLEND_ADD)
            pygame.draw.rect(surface,c["glow"],(gx-3,r.bottom-4,6,2),border_radius=1)
    if variant=="moving":
        mov_glow=pygame.Surface((r.w-10,4),pygame.SRCALPHA)
        pygame.draw.line(mov_glow,(*c["glow"],int(120*neon_pulse)),(0,0),(r.w-10,0),2)
        surface.blit(mov_glow,(r.x+5,r.bottom-4))
    if variant in("conveyor","falling","rotating"):
        pygame.draw.line(surface,_mix_color(c["glow"],WHITE,0.35),(r.x+8,r.y+3),(r.right-8,r.y+3),2)
    if variant=="falling":
        for cx in range(r.x+22,r.right-12,42):
            pygame.draw.circle(surface,(150,85,60),(cx,r.bottom-5),3)
            pygame.draw.circle(surface,(200,140,100,60),(cx,r.bottom-5),5,1)
    if variant=="conveyor":
        pygame.draw.rect(surface,_mix_color(c["dark"],BLACK,0.2),(r.x+8,r.y+7,r.w-16,5),border_radius=2)
        for cx2 in range(r.x+16,r.right-16,22):
            arrow_alpha=int(80+40*math.sin(t*0.006+cx2))
            pygame.draw.line(surface,(*c["glow"],arrow_alpha),(cx2,r.y+9),(cx2+6,r.y+9),1)
    if variant=="rotating":
        rot_glow=pygame.Surface((12,12),pygame.SRCALPHA)
        pygame.draw.circle(rot_glow,(*c["glow"],50),(6,6),6)
        surface.blit(rot_glow,(r.centerx-6,r.centery-6),special_flags=pygame.BLEND_ADD)
        pygame.draw.circle(surface,c["glow"],r.center,4)
        pygame.draw.circle(surface,WHITE,r.center,1)
    if r.w>=130:
        for px in range(r.x+28,r.right-20,54):
            pygame.draw.circle(surface,_mix_color(c["outline"],WHITE,0.16),(px,r.y+7),2)
            pygame.draw.circle(surface,c["dark"],(px,r.bottom-6),3)
            vent_glow=pygame.Surface((6,4),pygame.SRCALPHA)
            pygame.draw.rect(vent_glow,(*c["glow"],30),(0,0,6,4),border_radius=2)
            surface.blit(vent_glow,(px-3,r.y+r.h-8),special_flags=pygame.BLEND_ADD)

def draw_static_platform(surface,rect,theme): draw_platform(surface,rect,theme,"normal")

# ====================================================================
# FLOOR RENDERER - Multi-layer sci-fi floor
# ====================================================================
FLOOR_CACHE={}

def get_floor_palette(theme):
    base_palettes={
        "station":{"top":(32,38,62),"body":(24,28,50),"neon":(80,230,220),"neon2":(40,180,170),"neon_dark":(20,100,95),"seam":(44,52,85),"bolt":(55,65,100),"support":(16,18,36),"shadow":(5,5,15),"accent":(60,200,190),"vent":(18,22,42),"warning":(255,200,50),"light_on":(80,230,220),"light_off":(30,40,60),"hatch":(28,34,58),"pipe":(38,46,76)},
        "engine":{"top":(54,36,28),"body":(42,28,20),"neon":(255,136,38),"neon2":(200,100,25),"neon_dark":(120,60,15),"seam":(68,48,34),"bolt":(80,55,38),"support":(30,18,12),"shadow":(8,4,2),"accent":(255,180,60),"vent":(34,20,14),"warning":(255,200,50),"light_on":(255,136,38),"light_off":(60,35,20),"hatch":(48,30,22),"pipe":(60,40,28)},
        "lab":{"top":(28,36,56),"body":(22,28,46),"neon":(180,100,255),"neon2":(140,70,210),"neon_dark":(80,35,130),"seam":(38,48,72),"bolt":(48,58,88),"support":(14,18,30),"shadow":(4,5,12),"accent":(200,130,255),"vent":(16,20,36),"warning":(255,200,50),"light_on":(180,100,255),"light_off":(28,18,44),"hatch":(24,30,50),"pipe":(34,42,68)},
        "space":{"top":(20,40,30),"body":(15,32,22),"neon":(50,255,140),"neon2":(35,200,100),"neon_dark":(15,110,55),"seam":(28,50,38),"bolt":(36,62,48),"support":(10,22,14),"shadow":(2,8,5),"accent":(80,255,160),"vent":(10,24,16),"warning":(255,200,50),"light_on":(50,255,140),"light_off":(18,38,28),"hatch":(18,36,26),"pipe":(26,48,36)},
        "reactor":{"top":(58,44,22),"body":(46,34,16),"neon":(250,199,70),"neon2":(200,155,50),"neon_dark":(130,95,25),"seam":(72,56,30),"bolt":(86,66,38),"support":(34,24,10),"shadow":(10,6,2),"accent":(255,220,100),"vent":(36,26,12),"warning":(255,200,50),"light_on":(250,199,70),"light_off":(60,44,20),"hatch":(50,38,18),"pipe":(64,50,26)},
        "server":{"top":(18,44,34),"body":(14,34,26),"neon":(50,220,130),"neon2":(35,180,100),"neon_dark":(15,110,60),"seam":(26,54,42),"bolt":(34,66,52),"support":(8,24,16),"shadow":(2,8,5),"accent":(80,240,155),"vent":(8,26,18),"warning":(255,200,50),"light_on":(50,220,130),"light_off":(16,40,30),"hatch":(16,38,28),"pipe":(24,50,38)},
        "ice":{"top":(34,62,86),"body":(26,50,70),"neon":(140,215,255),"neon2":(100,175,220),"neon_dark":(50,105,140),"seam":(44,74,100),"bolt":(56,88,116),"support":(18,36,52),"shadow":(4,10,18),"accent":(180,235,255),"vent":(16,36,54),"warning":(255,200,50),"light_on":(140,215,255),"light_off":(32,58,80),"hatch":(28,52,74),"pipe":(40,68,92)},
        "storm":{"top":(34,28,72),"body":(26,22,58),"neon":(130,130,255),"neon2":(90,90,220),"neon_dark":(45,45,140),"seam":(44,38,86),"bolt":(56,48,104),"support":(18,14,42),"shadow":(4,3,14),"accent":(170,170,255),"vent":(16,12,44),"warning":(255,200,50),"light_on":(130,130,255),"light_off":(30,26,64),"hatch":(28,24,62),"pipe":(40,34,80)},
        "enemy_base":{"top":(48,18,20),"body":(38,14,16),"neon":(226,75,74),"neon2":(180,55,55),"neon_dark":(110,30,30),"seam":(62,26,28),"bolt":(74,34,36),"support":(28,8,10),"shadow":(8,2,2),"accent":(255,100,100),"vent":(22,8,10),"warning":(255,200,50),"light_on":(226,75,74),"light_off":(48,18,26),"hatch":(42,16,18),"pipe":(54,22,24)},
        "glitch":{"top":(42,12,48),"body":(34,10,38),"neon":(230,85,255),"neon2":(180,55,210),"neon_dark":(100,25,130),"seam":(54,20,60),"bolt":(66,28,74),"support":(24,6,28),"shadow":(6,1,8),"accent":(255,120,255),"vent":(20,6,28),"warning":(255,200,50),"light_on":(230,85,255),"light_off":(40,14,50),"hatch":(36,12,42),"pipe":(48,18,56)},
        "nebula":{"top":(35,20,58),"body":(28,16,46),"neon":(205,105,255),"neon2":(160,75,210),"neon_dark":(90,35,130),"seam":(46,28,72),"bolt":(58,38,88),"support":(18,10,34),"shadow":(5,2,12),"accent":(220,140,255),"vent":(16,8,32),"warning":(255,200,50),"light_on":(205,105,255),"light_off":(32,20,52),"hatch":(30,18,50),"pipe":(42,26,66)},
        "void":{"top":(14,10,24),"body":(10,8,18),"neon":(205,205,255),"neon2":(155,155,210),"neon_dark":(80,80,130),"seam":(22,18,36),"bolt":(30,26,46),"support":(6,4,14),"shadow":(1,1,6),"accent":(230,230,255),"vent":(6,4,18),"warning":(255,200,50),"light_on":(205,205,255),"light_off":(14,12,28),"hatch":(12,10,22),"pipe":(20,16,34)},
        "core":{"top":(18,14,36),"body":(14,10,28),"neon":(110,230,255),"neon2":(80,180,210),"neon_dark":(40,100,130),"seam":(26,22,48),"bolt":(36,30,60),"support":(8,6,20),"shadow":(2,1,8),"accent":(150,240,255),"vent":(6,4,20),"warning":(255,200,50),"light_on":(110,230,255),"light_off":(16,14,34),"hatch":(16,12,32),"pipe":(24,20,44)},
    }
    return base_palettes.get(theme,base_palettes["station"])

def build_floor_tile(theme):
    p=get_floor_palette(theme)
    TW,TH=256,80
    surf=pygame.Surface((TW,TH),pygame.SRCALPHA)

    for dy in range(18):
        a=max(0,min(255,int(180-dy*10)))
        pygame.draw.rect(surf,(*p["shadow"],a),(0,62+dy,TW,1))

    pygame.draw.rect(surf,p["support"],(0,48,TW,14))
    for bx in range(0,TW,32):
        pygame.draw.rect(surf,_mix_color(p["support"],BLACK,0.15),(bx,48,2,14))
        if (bx//32)%2==0:
            pygame.draw.rect(surf,_mix_color(p["support"],p["neon"],0.08),(bx+4,50,10,3),border_radius=1)

    pygame.draw.rect(surf,p["body"],(0,20,TW,28))
    for sx in range(0,TW+1,64):
        pygame.draw.line(surf,p["seam"],(sx,21),(sx,47),1)
    pygame.draw.line(surf,p["seam"],(0,34),(TW,34),1)

    for vx in range(12,52,12):
        pygame.draw.rect(surf,p["vent"],(vx,26,8,2),border_radius=1)
    for bx in (6,58):
        pygame.draw.circle(surf,p["bolt"],(bx,24),2)
        pygame.draw.circle(surf,p["bolt"],(bx,44),2)

    pygame.draw.rect(surf,p["hatch"],(72,24,48,20),border_radius=2)
    pygame.draw.rect(surf,p["seam"],(72,24,48,20),width=1,border_radius=2)
    pygame.draw.line(surf,p["vent"],(96,26),(96,42),1)
    for hbx in (76,116):
        for hby in (27,41):
            pygame.draw.circle(surf,p["bolt"],(hbx,hby),1)
    pygame.draw.rect(surf,p["neon2"],(93,30,6,2),border_radius=1)
    hg=pygame.Surface((54,26),pygame.SRCALPHA)
    pygame.draw.rect(hg,(*p["neon"],12),(0,0,54,26),border_radius=3)
    surf.blit(hg,(69,21),special_flags=pygame.BLEND_ADD)

    for sy in range(22,47,6):
        col=p["warning"] if (sy//6)%2==0 else p["body"]
        pygame.draw.rect(surf,col,(130,sy,12,4))
    for sy in range(22,47,6):
        col=p["warning"] if (sy//6)%2==0 else p["body"]
        pygame.draw.rect(surf,col,(178,sy,12,4))
    pygame.draw.rect(surf,p["pipe"],(142,28,36,5),border_radius=2)
    for fx in (142,178):
        pygame.draw.rect(surf,p["bolt"],(fx-1,26,3,9),border_radius=1)
    for bx in (134,186):
        pygame.draw.circle(surf,p["bolt"],(bx,24),2)
        pygame.draw.circle(surf,p["bolt"],(bx,44),2)

    for gx in range(196,252,6):
        for gy in range(24,44,6):
            if (gx//6+gy//6)%3==0:
                pygame.draw.rect(surf,_mix_color(p["body"],p["neon"],0.05),(gx,gy,3,3))
    for i,(lx,ly) in enumerate([(204,28),(228,28),(204,40),(228,40)]):
        lc=p["light_on"] if i%2==0 else p["light_off"]
        pygame.draw.circle(surf,lc,(lx,ly),2)
        lg=pygame.Surface((8,8),pygame.SRCALPHA)
        pygame.draw.circle(lg,(*p["neon"],25),(4,4),4)
        surf.blit(lg,(lx-4,ly-4),special_flags=pygame.BLEND_ADD)
    for bx in (198,250):
        pygame.draw.circle(surf,p["bolt"],(bx,24),2)
        pygame.draw.circle(surf,p["bolt"],(bx,44),2)

    pygame.draw.rect(surf,p["top"],(0,0,TW,20))
    for sx in range(0,TW+1,64):
        pygame.draw.line(surf,p["seam"],(sx,3),(sx,19),1)
    pygame.draw.line(surf,p["seam"],(0,11),(TW,11),1)

    for vx in range(12,52,12):
        pygame.draw.rect(surf,p["vent"],(vx,6,8,2),border_radius=1)
    pygame.draw.line(surf,p["vent"],(72,8),(118,8),1)
    pygame.draw.line(surf,p["vent"],(72,12),(118,12),1)
    pygame.draw.line(surf,p["vent"],(140,5),(170,16),1)
    pygame.draw.line(surf,p["vent"],(170,5),(140,16),1)
    for dx in range(200,250,10):
        pygame.draw.circle(surf,p["vent"],(dx,9),1)

    for cx in (0,TW):
        for cy in (0,20,48):
            pygame.draw.circle(surf,p["bolt"],(cx,cy),2)

    bg=pygame.Surface((TW,4),pygame.SRCALPHA)
    pygame.draw.line(bg,(*p["neon"],40),(0,0),(TW,0),3)
    surf.blit(bg,(0,60),special_flags=pygame.BLEND_ADD)

    return surf

def draw_floor(surf,camera,theme):
    floor_y=560
    TW,TH=256,80
    visual_top=floor_y-20

    key="floor_tile_"+theme
    if key not in FLOOR_CACHE:
        FLOOR_CACHE[key]=build_floor_tile(theme)
    tile_surf=FLOOR_CACHE[key]

    cam_x=camera.x
    vis_left=cam_x-10
    vis_right=cam_x+SCREEN_W+10
    start_tile=int(vis_left//TW)
    end_tile=int(vis_right//TW)+1

    for ti in range(start_tile,end_tile):
        wx=ti*TW
        sx=int(wx-cam_x)
        if sx+TW>-10 and sx<SCREEN_W+10:
            surf.blit(tile_surf,(sx,visual_top))

    p=get_floor_palette(theme)
    t=pygame.time.get_ticks()
    for sx in range(0,SCREEN_W+20,4):
        pulse=0.6+0.4*abs(math.sin(sx*0.05+t*0.002))
        a=int(55*pulse)
        cx=sx
        pygame.draw.line(surf,(*p["neon"],a),(cx,floor_y),(min(cx+3,SCREEN_W+19),floor_y),2)

    cs=pygame.Surface((SCREEN_W+20,14),pygame.SRCALPHA)
    for gx in range(SCREEN_W+20):
        pp=0.5+0.5*abs(math.sin(gx*0.03+t*0.0015))
        a2=int(20*pp)
        pygame.draw.line(cs,(*p["neon"],a2),(gx,0),(gx,13),1)
    surf.blit(cs,(0,visual_top-8),special_flags=pygame.BLEND_ADD)

    cs2=pygame.Surface((SCREEN_W+20,8),pygame.SRCALPHA)
    for gx2 in range(SCREEN_W+20):
        pp2=0.5+0.5*abs(math.sin(gx2*0.04+t*0.0018+1))
        a3=int(15*pp2)
        pygame.draw.line(cs2,(*p["neon2"],a3),(gx2,0),(gx2,7),2)
    surf.blit(cs2,(0,visual_top+TH-10),special_flags=pygame.BLEND_ADD)

def make_platform_rect(x,y,w,h=16):
    return pygame.Rect(int(x),int(y),int(max(82,w)),int(max(14,h)))

def get_weapon_hud_safe_zone():
    return pygame.Rect(HUD_RIGHT_X-4,WEAPON_PANEL_Y-4,HUD_RIGHT_W+8,WEAPON_PANEL_H+8)

def is_in_hud_safe_zone(world_x,world_y,cam):
    sx,sy=cam.apply(world_x,world_y)
    return get_weapon_hud_safe_zone().collidepoint(int(sx),int(sy))

def trigger_weapon_hud_expand():
    global weapon_hud_expanded, weapon_hud_timer
    weapon_hud_expanded=True; weapon_hud_timer=WEAPON_HUD_EXPAND_FRAMES

def update_weapon_hud_timer():
    global weapon_hud_expanded, weapon_hud_timer
    if weapon_hud_timer>0: weapon_hud_timer-=1
    if weapon_hud_timer<=0: weapon_hud_expanded=False

# ------------------------------------------------------------------------------------
# SPIKE TRAP
# ------------------------------------------------------------------------------------
class SpikeTrap:
    def __init__(self,x,y,count=4): self.x=x; self.y=y; self.count=count; self.w=count*14
    def draw(self,surface,cam):
        sx,sy=cam.apply(self.x,self.y)
        if not(-50<sx<SCREEN_W+50): return
        for i in range(self.count):
            px=int(sx)+i*14
            pygame.draw.polygon(surface,(180,40,40),[(px+1,int(sy)+12),(px+7,int(sy)-4),(px+13,int(sy)+12)])
            pygame.draw.polygon(surface,(220,80,80),[(px+3,int(sy)+12),(px+7,int(sy)-2),(px+11,int(sy)+12)])
        pygame.draw.rect(surface,(120,20,20),(int(sx),int(sy)+12,self.w,4))
    def get_rect(self): return pygame.Rect(self.x+2,self.y-4,self.w-4,16)

class LaserTrap:
    def __init__(self,x,y,h=190,cycle=150,phase=0):
        self.x=float(x); self.y=float(y); self.h=int(h); self.cycle=int(cycle); self.phase=int(phase); self.t=phase
    def active(self): return (self.t%self.cycle)>self.cycle*0.42
    def draw(self,surface,cam):
        self.t+=1
        sx,sy=cam.apply(self.x,self.y)
        if not(-30<sx<SCREEN_W+30): return
        warn=not self.active() and (self.t%self.cycle)>self.cycle*0.30
        col=RED if self.active() else ORANGE if warn else (70,25,25)
        width=4 if self.active() else 2
        pygame.draw.rect(surface,(45,45,60),(int(sx)-7,int(sy)-8,14,8),border_radius=3)
        pygame.draw.rect(surface,(45,45,60),(int(sx)-7,int(sy)+self.h,14,8),border_radius=3)
        pygame.draw.line(surface,col,(int(sx),int(sy)),(int(sx),int(sy)+self.h),width)
        if self.active():
            glow=pygame.Surface((26,self.h),pygame.SRCALPHA); glow.fill((255,40,40,38)); surface.blit(glow,(int(sx)-13,int(sy)))
    def get_rect(self):
        if not self.active(): return pygame.Rect(self.x,self.y,0,0)
        return pygame.Rect(self.x-4,self.y,8,self.h)

class SteamVent:
    def __init__(self,x,y=528,w=42,cycle=180,phase=0):
        self.x=float(x); self.y=float(y); self.w=int(w); self.cycle=int(cycle); self.t=int(phase)
    def active(self): return (self.t%self.cycle)>self.cycle*0.58
    def draw(self,surface,cam):
        self.t+=1
        sx,sy=cam.apply(self.x,self.y)
        if not(-60<sx<SCREEN_W+60): return
        pygame.draw.rect(surface,(55,55,62),(int(sx),int(sy),self.w,8),border_radius=3)
        for gx in range(int(sx)+6,int(sx)+self.w-4,10): pygame.draw.line(surface,(120,125,130),(gx,int(sy)+1),(gx+4,int(sy)+6),1)
        if self.active():
            for i in range(5):
                px=int(sx)+6+i*8+int(3*math.sin(self.t*0.08+i)); ph=48+i%2*18
                pygame.draw.line(surface,(190,220,230,),(px,int(sy)),(px+random.randint(-5,5),int(sy)-ph),2)
    def get_rect(self):
        if not self.active(): return pygame.Rect(self.x,self.y,0,0)
        return pygame.Rect(self.x+4,self.y-66,self.w-8,70)

# ------------------------------------------------------------------------------------
# TUNNEL SEGMENT
# ------------------------------------------------------------------------------------
class TunnelSegment:
    def __init__(self,x,width,gap_y,gap_h=120,level_num=1,theme="station"):
        self.x=x; self.width=width; self.gap_y=gap_y; self.gap_h=gap_h; self.level_num=level_num; self.theme=theme
        self.top_rect=pygame.Rect(x,0,width,gap_y)
        self.bot_rect=pygame.Rect(x,gap_y+gap_h,width,SCREEN_H-(gap_y+gap_h)+80)
        self.floor_y=gap_y+gap_h
        self.coin_y=max(gap_y+34,min(self.floor_y-38,self.floor_y-46))
        self.kind=self._theme_kind(level_num)
        self.hazards=[]; self.supports=[]; self.props=[]
        self._build_gameplay()
    def _theme_kind(self,level_num):
        if level_num==2: return "laser_service"
        if level_num==4: return "reactor_steam"
        if level_num==7: return "firewall_security"
        if level_num==10: return "prototype_lab"
        if level_num in (8,9,11): return "lab_route"
        return "maintenance"
    def _build_gameplay(self):
        safe_left=self.x+88; safe_right=self.x+self.width-88
        if safe_right<=safe_left: return
        if self.kind=="laser_service":
            for i,fx in enumerate((0.34,0.58,0.78)):
                self.hazards.append({"type":"laser","x":self.x+self.width*fx,"cycle":150,"phase":i*43,"h":self.gap_h-30})
            self.props.append(("warning",self.x+self.width*0.18,self.gap_y+22))
        elif self.kind=="reactor_steam":
            for i,fx in enumerate((0.28,0.52,0.74)):
                self.hazards.append({"type":"steam","x":self.x+self.width*fx,"cycle":175,"phase":i*56,"w":46})
            for i,fx in enumerate((0.40,0.66)):
                self.supports.append({"rect":pygame.Rect(int(self.x+self.width*fx),int(self.floor_y-52),94,12),"cycle":170,"phase":i*68})
        elif self.kind=="firewall_security":
            for i,fx in enumerate((0.30,0.50,0.70)):
                self.hazards.append({"type":"firewall","x":self.x+self.width*fx,"cycle":140,"phase":i*37,"h":self.gap_h-24})
            for i,fx in enumerate((0.42,0.62)):
                self.hazards.append({"type":"drone","x":self.x+self.width*fx,"y":self.gap_y+42+i*22,"range":54,"phase":i*1.7,"r":13})
        elif self.kind=="prototype_lab":
            for i,fx in enumerate((0.24,0.50,0.76)):
                self.supports.append({"rect":pygame.Rect(int(self.x+self.width*fx),int(self.floor_y-44-(i%2)*22),82,12),"cycle":155,"phase":i*50})
            self.hazards.append({"type":"scanner","x":self.x+self.width*0.63,"cycle":165,"phase":32,"h":self.gap_h-34})
            self.props.append(("prototype",self.x+self.width*0.36,self.gap_y+26))
        elif self.kind=="lab_route":
            for i,fx in enumerate((0.36,0.64)):
                self.hazards.append({"type":"scanner","x":self.x+self.width*fx,"cycle":185,"phase":i*62,"h":self.gap_h-34})
        else:
            self.props.append(("maintenance",self.x+self.width*0.50,self.gap_y+28))
    def coin_positions(self,count=4):
        count=max(1,count)
        spacing=self.width/(count+1)
        return [(float(self.x+spacing*(i+1)),float(self.coin_y-(10 if i%2 else 0))) for i in range(count)]
    def _active(self,item,t):
        return ((int(t)+int(item.get("phase",0)))%int(item.get("cycle",160)))<int(item.get("cycle",160))*0.56
    def get_support_rects(self,t):
        rects=[]
        for sp in self.supports:
            if self._active(sp,t): rects.append(sp["rect"])
        return rects
    def get_hazard_rects(self,t):
        rects=[]; disabled=globals().get("lasers_disabled_for_level",lambda _lvl:False)(self.level_num)
        for h in self.hazards:
            if h["type"] in ("laser","scanner") and disabled: continue
            if h["type"] in ("laser","steam","firewall","scanner") and not self._active(h,t): continue
            if h["type"]=="steam": rects.append(pygame.Rect(int(h["x"]),self.floor_y-78,int(h.get("w",42)),74))
            elif h["type"]=="drone":
                dx=math.sin(t*0.035+h.get("phase",0))*h.get("range",50)
                rects.append(pygame.Rect(int(h["x"]+dx-h.get("r",12)),int(h["y"]-h.get("r",12)),int(h.get("r",12)*2),int(h.get("r",12)*2)))
            else:
                rects.append(pygame.Rect(int(h["x"])-4,self.gap_y+12,8,int(h.get("h",self.gap_h-24))))
        return rects
    def collide_player(self,player_obj,t):
        pr=player_obj.get_rect()
        if pr.colliderect(self.top_rect): player_obj.wy=float(self.top_rect.bottom); player_obj.vy=max(0,player_obj.vy); pr=player_obj.get_rect()
        if pr.colliderect(self.bot_rect): player_obj.wy=float(self.bot_rect.top-player_obj.HEIGHT); player_obj.vy=min(0,player_obj.vy); player_obj.on_ground=True; pr=player_obj.get_rect()
        for sr in self.get_support_rects(t):
            if pr.colliderect(sr) and player_obj.wy+player_obj.HEIGHT-player_obj.vy<=sr.top+8:
                player_obj.wy=float(sr.top-player_obj.HEIGHT); player_obj.vy=0; player_obj.on_ground=True; pr=player_obj.get_rect()
        for hr in self.get_hazard_rects(t):
            if player_obj.invincible==0 and pr.colliderect(hr):
                if player_obj.take_damage(1): return True
                break
        return False
    def draw(self,surface,cam):
        sr_top=cam.apply_rect(self.top_rect); sr_bot=cam.apply_rect(self.bot_rect)
        if not(-self.width<sr_top.x<SCREEN_W+self.width): return
        col_wall=(25,25,45); col_edge=(60,60,100); col_light=(40,80,120)
        pygame.draw.rect(surface,col_wall,sr_top); pygame.draw.rect(surface,col_wall,sr_bot)
        for i in range(0,max(1,self.top_rect.h),20):
            pygame.draw.line(surface,col_edge,(sr_top.x,sr_top.y+i),(sr_top.x+sr_top.w,sr_top.y+i),1)
        pygame.draw.rect(surface,col_light,(sr_top.x,sr_top.y+max(0,sr_top.h-4),sr_top.w,4))
        pygame.draw.rect(surface,col_light,(sr_bot.x,sr_bot.y,sr_bot.w,4))
        t=pygame.time.get_ticks()/16.0; disabled=globals().get("lasers_disabled_for_level",lambda _lvl:False)(self.level_num)
        for sp in self.supports:
            rr=cam.apply_rect(sp["rect"]); active=self._active(sp,t); ac=(70,210,190) if active else (45,55,70)
            pygame.draw.rect(surface,(12,18,30),rr,border_radius=4); pygame.draw.rect(surface,ac,rr,border_radius=4,width=1)
            if not active: pygame.draw.line(surface,(90,90,100),(rr.x+5,rr.y+rr.h//2),(rr.right-5,rr.y+rr.h//2),1)
        for h in self.hazards:
            active=self._active(h,t)
            if h["type"] in ("laser","scanner") and disabled: active=False
            if h["type"]=="steam":
                sx,sy=cam.apply(h["x"],self.floor_y-8); pygame.draw.rect(surface,(55,55,62),(int(sx),int(sy),int(h.get("w",42)),8),border_radius=3)
                if active:
                    for i in range(5): pygame.draw.line(surface,(190,220,230),(int(sx)+6+i*8,int(sy)),(int(sx)+2+i*8,int(sy)-48-i%2*16),2)
            elif h["type"]=="drone":
                dx=math.sin(t*0.035+h.get("phase",0))*h.get("range",50); sx,sy=cam.apply(h["x"]+dx,h["y"])
                pygame.draw.circle(surface,(25,30,42),(int(sx),int(sy)),int(h.get("r",12)+3)); pygame.draw.circle(surface,NEON_ORANGE,(int(sx),int(sy)),int(h.get("r",12)),2)
            else:
                sx,sy=cam.apply(h["x"],self.gap_y+12); hgt=int(h.get("h",self.gap_h-24)); col=NEON_CYAN if h["type"]=="scanner" else NEON_RED
                pygame.draw.line(surface,(45,70,80) if not active else col,(int(sx),int(sy)),(int(sx),int(sy)+hgt),2 if not active else 4)
                if active:
                    glow=pygame.Surface((24,hgt),pygame.SRCALPHA); glow.fill((*col,34)); surface.blit(glow,(int(sx)-12,int(sy)),special_flags=pygame.BLEND_ADD)
        for kind,px,py in self.props:
            sx,sy=cam.apply(px,py); label="LAB" if kind=="prototype" else "AUX" if kind=="maintenance" else "WARN"
            pygame.draw.rect(surface,(8,14,24),(int(sx)-24,int(sy)-8,48,18),border_radius=3)
            draw_center_fit(surface,label,make_font(8,"hud",True),pygame.Rect(int(sx)-22,int(sy)-6,44,14),NEON_CYAN if kind!="warning" else ORANGE,shadow=False)
    def get_top_rect(self): return self.top_rect
    def get_bot_rect(self): return self.bot_rect

# ------------------------------------------------------------------------------------
# WATER / SEA HAZARD
# ------------------------------------------------------------------------------------
def draw_water_gradient(surface,rect,t=0,kind="water"):
    h=max(1,rect.h); w=max(1,rect.w)
    water=pygame.Surface((w,h),pygame.SRCALPHA)
    pulse=0.5+0.5*math.sin(t*0.003)
    for y in range(h):
        k=y/max(1,h-1)
        alpha=int(100 + 80*k)
        wave=int(2*math.sin(t*0.005+y*0.15))
        if kind=="lava":
            r = 255 - int(50*k) + wave
            g = 120 - int(90*k) + int(wave*0.5)
            b = 10 + int(wave*0.3)
            col = (max(0,min(255,r)),max(0,min(255,g)),max(0,min(255,b)),alpha)
        else:
            r = 10 + int(30*k) + int(wave*0.5)
            g = 100 + int(50*k) + wave
            b = 180 + int(40*k) + int(wave*2)
            col = (max(0,min(255,r)),max(0,min(255,g)),max(0,min(255,b)),alpha)
        pygame.draw.line(water,col,(0,y),(w,y))
    glow=pygame.Surface((w,min(20,h)),pygame.SRCALPHA)
    glow_col=(255,180,80,60) if kind=="lava" else (100,220,255,55)
    pygame.draw.rect(glow,glow_col,(0,0,w,min(20,h)),border_radius=4)
    surface.blit(water,rect.topleft)
    surface.blit(glow,(rect.x,rect.y),special_flags=pygame.BLEND_ADD)

def draw_water_edge_blend(surface,rect,t,kind="water"):
    base=(255,120,35) if kind=="lava" else (55,190,235)
    dark=(115,34,18) if kind=="lava" else (14,70,115)
    lip=pygame.Surface((max(1,rect.w),22),pygame.SRCALPHA)
    pulse=0.5+0.5*math.sin(t*0.005)
    for y in range(22):
        alpha=max(0,int(80*(1-y/22))*pulse)
        pygame.draw.line(lip,(*base,alpha),(0,y),(rect.w,y))
    surface.blit(lip,(rect.x,rect.y-12))
    for x in range(rect.left,rect.right,18):
        y=rect.y+int(4*math.sin(t*0.008+x*0.05))
        lw=1 if kind=="water" else 2
        ca=int(50+20*math.sin(t*0.004+x*0.03))
        pygame.draw.line(surface,(*dark,ca),(x,y+8),(min(rect.right,x+20),y+12),lw)

def draw_water_surface(surface,rect,t,phase=0,kind="water"):
    pts=[]; pts2=[]
    step=5
    main_col=(255,178,70,180) if kind=="lava" else (135,225,255,175)
    hi_col=(255,236,140,100) if kind=="lava" else (230,255,255,95)
    for x in range(rect.left-10,rect.right+11,step):
        wy=rect.y+3+int(5*math.sin(t*0.006+x*0.03+phase))+int(3*math.sin(t*0.012+x*0.06+phase*1.5))
        pts.append((x,wy))
        pts2.append((x,wy+3+int(2*math.sin(t*0.008+x*0.04+phase))))
    if len(pts)>1:
        glow_surf=pygame.Surface((max(1,rect.w+30),16),pygame.SRCALPHA)
        glow_col=(255,200,100,70) if kind=="lava" else (135,225,255,60)
        pygame.draw.ellipse(glow_surf,glow_col,(0,0,rect.w+30,16))
        surface.blit(glow_surf,(rect.left-15,rect.y-6),special_flags=pygame.BLEND_ADD)
        pygame.draw.lines(surface,hi_col,False,[(x,y-1) for x,y in pts],2)
        pygame.draw.lines(surface,main_col,False,pts,2)
        pygame.draw.lines(surface,(*hi_col[:3],60),False,pts2,1)
    for i,x in enumerate(range(rect.left+6,rect.right-6,32)):
        foam_y=rect.y+4+int(4*math.sin(t*0.01+i*1.2+phase))
        foam_col=(255,210,110,90) if kind=="lava" else (220,250,255,90)
        fw=20+int(8*math.sin(t*0.005+i*0.7))
        foam_rect=pygame.Rect(x,foam_y,fw,3)
        pygame.draw.ellipse(surface,foam_col,foam_rect)
        pygame.draw.ellipse(surface,(*foam_col[:3],foam_col[3]//2),foam_rect.inflate(4,2))

def draw_water_ripples(surface,rect,t,phase=0,kind="water"):
    col=(255,205,95,65) if kind=="lava" else (155,235,255,58)
    for i in range(8):
        rx=rect.left+int((i*84+t*0.03+phase*31)%max(1,rect.w))
        ry=rect.y+14+i%3*12+int(3*math.sin(t*0.008+i*0.7))
        rw=26+int(10*math.sin(t*0.006+i*0.5))
        pygame.draw.arc(surface,col,(rx-rw//2,ry,rw,10),0,math.pi,1)
        if i%3==0:
            pygame.draw.arc(surface,col,(rx-rw//4,ry+4,rw//2,6),0,math.pi,1)

def draw_water_splashes(surface,rect,t,phase=0,kind="water"):
    col=(255,190,80) if kind=="lava" else (155,235,255)
    for i,x in enumerate(range(rect.left+12,rect.right-10,52)):
        pulse=(i+int(t*0.045+phase))%5
        if pulse not in(0,1): continue
        y=rect.y+2+int(4*math.sin(t*0.01+i+phase))
        a=120 if pulse==0 else 55
        pygame.draw.circle(surface,(*col,a),(x,y-random.randint(2,7)),2 if pulse==0 else 1)
        if i%3==0: pygame.draw.line(surface,(*col,65),(x+5,y),(x+10,y-random.randint(5,12)),1)
        if kind=="lava" and pulse==0:
            pygame.draw.circle(surface,(255,200,80,80),(x,y-random.randint(3,6)),2)

class WaterHazard:
    def __init__(self,x,width,y=536,depth=64):
        self.x=float(x); self.width=int(width); self.y=int(y); self.depth=int(depth); self.t=random.uniform(0,999); self.kind="lava" if random.random()<0.18 else "water"
        self.bubbles=[{"x":random.uniform(0,width),"y":random.uniform(0,depth),"spd":random.uniform(0.3,1.2),"sz":random.randint(1,4),"phase":random.uniform(0,6)} for _ in range(10)]
        self.foam_phase=random.uniform(0,6)
    def draw(self,surface,cam,t):
        sx=int(cam.apply(self.x,0)[0])
        if not(-self.width-40<sx<SCREEN_W+40): return
        rect=pygame.Rect(sx,self.y-8,self.width,self.depth+8)
        base_col=(255,105,30) if self.kind=="lava" else (70,190,235)
        glow_col=(255,180,60) if self.kind=="lava" else (100,220,255)
        # Under-glow
        under_glow=pygame.Surface((rect.w+20,rect.h+20),pygame.SRCALPHA)
        pygame.draw.rect(under_glow,(*glow_col,40),(0,0,rect.w+20,rect.h+20),border_radius=8)
        surface.blit(under_glow,(rect.x-10,rect.y-10),special_flags=pygame.BLEND_ADD)
        # Soft body
        soft=pygame.Surface((max(1,rect.w),max(1,rect.h+22)),pygame.SRCALPHA)
        for y in range(0,soft.get_height(),2):
            a=max(0,72-int(y*1.05)); pygame.draw.line(soft,(*base_col,a),(0,y),(soft.get_width(),y))
        surface.blit(soft,(rect.x,rect.y-8))
        draw_water_edge_blend(surface,rect,t,self.kind)
        draw_water_gradient(surface,rect,t,self.kind)
        draw_water_surface(surface,rect,t,self.t,self.kind)
        draw_water_ripples(surface,rect,t,self.t,self.kind)
        draw_water_splashes(surface,rect,t,self.t,self.kind)
        # Foam patches
        foam_col=(255,200,100,60) if self.kind=="lava" else (220,250,255,55)
        for fi in range(4):
            fx=sx+int((fi*self.width//4+self.t*2+t*0.02)%self.width)
            fy=rect.y+int(4*math.sin(t*0.005+fi+self.foam_phase))
            foam_rect=pygame.Rect(fx,fy,24+int(8*math.sin(t*0.003+fi)),4)
            pygame.draw.ellipse(surface,foam_col,foam_rect)
        for b in self.bubbles:
            b["y"]-=b["spd"]*0.8
            if b["y"]<0: b["y"]=self.depth; b["x"]=random.uniform(0,self.width)
            bx=sx+int(b["x"])
            by=rect.y+self.depth-int(b["y"])
            ba=int(80+40*math.sin(t*0.01+b["phase"]))
            bcol=(255,200,80,ba) if self.kind=="lava" else (180,240,255,ba)
            b_glow=pygame.Surface((b["sz"]*4,b["sz"]*4),pygame.SRCALPHA)
            pygame.draw.circle(b_glow,(*bcol[:3],ba//4),(b["sz"]*2,b["sz"]*2),b["sz"]*2)
            surface.blit(b_glow,(bx-b["sz"]*2,by-b["sz"]*2),special_flags=pygame.BLEND_ADD)
            pygame.draw.circle(surface,bcol,(bx,by),b["sz"])
            if b["sz"]>1:
                pygame.draw.circle(surface,(255,255,255,ba//2),(bx-b["sz"]//3,by-b["sz"]//3),b["sz"]//2)
        # Top glow line
        pulse=0.6+0.4*math.sin(t*0.004)
        pygame.draw.line(surface,(*glow_col,int(90*pulse)),(rect.left,rect.top),(rect.right,rect.top),2)
        pygame.draw.line(surface,(*glow_col,int(40*pulse)),(rect.left-2,rect.top-2),(rect.right+2,rect.top-2),1)
    def get_rect(self): return pygame.Rect(self.x,self.y-8,self.width,self.depth+8)

# ------------------------------------------------------------------------------------
# FACILITY DOOR
# ------------------------------------------------------------------------------------
SHOW_OLD_FACILITY_DOORS=False
SHOW_FACILITY_SECTIONS=False
debug_print("SHOW_OLD_FACILITY_DOORS:",SHOW_OLD_FACILITY_DOORS)
debug_print("SHOW_FACILITY_SECTIONS:",SHOW_FACILITY_SECTIONS)
debug_print("Old FacilityDoor visual disabled")

class FacilityDoor:
    W=44; H=70
    def __init__(self,wx,wy,door_type="enter",accent=CYAN):
        self.wx=float(wx); self.wy=float(wy); self.type=door_type; self.accent=accent; self.anim_t=0
        debug_print("FacilityDoor active:",door_type)
    def draw(self,surface,cam,locked=False,opened=False,override_label=None):
        if not SHOW_OLD_FACILITY_DOORS: return
        sx,sy=cam.apply(self.wx,self.wy)
        if not(-60<sx<SCREEN_W+60): return
        self.anim_t+=1; ix,iy=int(sx),int(sy); w,h=self.W,self.H; ac=self.accent; t2=self.anim_t
        base_col=(60,25,25) if locked else (25,70,45) if opened else (40,40,60)
        edge_col=RED if locked else GREEN if opened else (60,60,90)
        pygame.draw.rect(surface,base_col,(ix,iy,w,h),border_radius=4)
        pygame.draw.rect(surface,edge_col,(ix,iy,w,h),border_radius=4,width=2)
        panel_open=0 if locked else min(h-4,int((h-4)*0.6*abs(math.sin(t2*0.015))))
        pygame.draw.rect(surface,(20,25,45),(ix+3,iy+2,w-6,h//2-panel_open//2),border_radius=2)
        bot_y=iy+h//2+panel_open//2
        pygame.draw.rect(surface,(20,25,45),(ix+3,bot_y,w-6,h-bot_y+iy-2),border_radius=2)
        if panel_open>0:
            gl=pygame.Surface((w-6,panel_open),pygame.SRCALPHA); gl.fill((*ac,int(80+60*math.sin(t2*0.05)))); surface.blit(gl,(ix+3,iy+h//2-panel_open//2))
        for yi in range(4):
            ly=iy+10+yi*14; lp=int(150+100*math.sin(t2*0.05+yi*0.8))
            pygame.draw.circle(surface,(lp//3,lp//2,lp),(ix-4,ly),3); pygame.draw.circle(surface,(lp//3,lp//2,lp),(ix+w+4,ly),3)
        label=override_label or ""
        fnt=make_font(9,"hud",True); lbl=fnt.render(label,True,edge_col if locked or opened else ac)
        surface.blit(lbl,(ix+w//2-lbl.get_width()//2,iy-14))
    def get_rect(self): return pygame.Rect(self.wx,self.wy,self.W,self.H)

# ------------------------------------------------------------------------------------
# FACILITY SECTION
# ------------------------------------------------------------------------------------
class FacilitySection:
    CEILING_H=80; FLOOR_Y=520; FLOOR_W_PAD=44
    def __init__(self,wx,width,level_num,accent=CYAN,rng=None,level_theme="station"):
        debug_print("FacilitySection found")
        debug_print("FacilitySection active:",level_theme)
        debug_print("Old ENTER door should not appear alone")
        self.wx=wx; self.width=width; self.level=level_num; self.accent=accent; self.level_theme=level_theme
        self.challenge_type=get_challenge_type_for_level(level_num,level_theme)
        self.status="inactive"; self.timer=0; self.spawned=False; self.challenge_enemies=[]; self.lasers=[]; self.cores=[]; self.extra_hazards=[]; self.text_timer=0
        rng=rng or random.Random()
        self.door_enter=FacilityDoor(wx-10,self.FLOOR_Y-self.CEILING_H*2+10,"enter",accent)
        self.door_exit=FacilityDoor(wx+width-self.FLOOR_W_PAD,self.FLOOR_Y-self.CEILING_H*2+10,"exit",accent)
        self.enter_trigger=pygame.Rect(int(wx),self.CEILING_H,int(min(150,width//4)),self.FLOOR_Y-self.CEILING_H)
        self.exit_trigger=pygame.Rect(int(wx+width-90),self.CEILING_H,90,self.FLOOR_Y-self.CEILING_H)
        self.barrier_rect=pygame.Rect(int(wx+width-58),self.CEILING_H,14,self.FLOOR_Y-self.CEILING_H)
        debug_print("Invisible trigger active")
        self.platforms=[]
        fac_layout=[(wx+115,self.FLOOR_Y-72,150),(wx+300,self.FLOOR_Y-126,122),(wx+470,self.FLOOR_Y-184,150),(wx+660,self.FLOOR_Y-126,128),(wx+width-285,self.FLOOR_Y-92,170)]
        if width>900:
            fac_layout.insert(3,(wx+width*0.55,self.FLOOR_Y-235,118))
        for px2,py2,w2 in fac_layout:
            if px2+w2<wx+width-95 and py2>self.CEILING_H+18:
                self.platforms.append(pygame.Rect(int(px2),int(py2),int(w2),14))
        self.pipes=[wx+100+i*int(width//(4+level_num//2)) for i in range(rng.randint(3,5+level_num//2))]
        self.enemies_wx=[rng.randint(int(wx+100),int(wx+width-100)) for _ in range(2+level_num//2)]
        self.hazards=[rng.randint(int(wx+80),int(wx+width-80)) for _ in range(1+level_num//3)]
        if self.challenge_type in("laser_room","server_lockdown","corex_trial"):
            for i in range(3): self.lasers.append({"x":wx+160+i*max(110,width//5),"phase":i*38,"active":False,"warn":False})
        if self.challenge_type=="reactor_core_room":
            for i in range(3): self.cores.append(ChallengeCore(wx+180+i*max(120,width//5),455-(i%2)*80,i+1))
        if self.challenge_type=="zero_gravity_corridor":
            for i in range(4): self.extra_hazards.append({"x":wx+150+i*120,"y":250+i%2*90,"vx":random.choice([-1,1])*(0.7+i*0.15),"r":12+i%2*4})
    def contains(self,wx): return self.wx<=wx<=self.wx+self.width
    def start_challenge(self,enemies_list):
        if self.status!="inactive": return
        self.status="active"; self.timer=0; self.text_timer=150
        debug_print("Challenge started from FacilitySection")
        debug_print("Challenge started:",self.challenge_type)
        self.spawn_challenge(enemies_list)
    def spawn_challenge(self,enemies_list):
        if self.spawned: return
        self.spawned=True
        count=0
        if self.challenge_type in("security_gate","server_lockdown","corex_trial"):
            count=2+(1 if self.level>=4 else 0)
        elif self.challenge_type in("laser_room","reactor_core_room","heat_elevator","frozen_corridor","storm_elevator"):
            count=1
        for i in range(count):
            ex=self.wx+130+i*max(100,self.width/(count+1)); elite="fast" if self.challenge_type in("server_lockdown","corex_trial") and i%2 else None
            bot=ScoutBot(ex,self.FLOOR_Y-ScoutBot.HEIGHT,1.0+self.level*0.08,max(70,135-self.level*6),elite)
            enemies_list.append(bot); self.challenge_enemies.append(bot)
        debug_print("Challenge enemies:",len(self.challenge_enemies))
    def complete_challenge(self):
        if self.status=="completed": return
        self.status="completed"; self.text_timer=140
        debug_print("Challenge completed:",self.challenge_type)
        debug_print("Challenge completed"); debug_print("Exit door opened")
    def update_challenge(self,player_obj,enemies_list,p_bullets,e_bullets):
        if self.text_timer>0: self.text_timer-=1
        pr=player_obj.get_rect(); center=player_obj.wx+player_obj.WIDTH//2
        if self.status=="inactive" and self.enter_trigger.colliderect(pr): self.start_challenge(enemies_list)
        if self.status=="active":
            self.timer+=1
            if self.challenge_type=="zero_gravity_corridor": player_obj.vy*=0.92
            if self.challenge_type=="heat_elevator" and self.timer%90==55:
                trigger_boss_shake("light",8); e_bullets.append(WorldBullet(self.wx+self.width//2,self.FLOOR_Y-6,0,-3.4,ORANGE))
            if self.challenge_type=="frozen_corridor" and self.timer%85==42:
                sx=self.wx+random.randint(110,int(self.width-110)); b=WorldBullet(sx,80,0,4.0,(150,230,255)); b.cryo=True; e_bullets.append(b)
            if self.challenge_type=="storm_elevator" and self.timer%95==46:
                e_bullets.append(WorldBullet(player_obj.wx+player_obj.WIDTH//2,0,0,5.2,YELLOW)); trigger_boss_shake("medium",10)
            for h in self.extra_hazards:
                h["x"]+=h["vx"]
                if h["x"]<self.wx+70 or h["x"]>self.wx+self.width-80: h["vx"]*=-1
                if pr.colliderect(pygame.Rect(h["x"]-h["r"],h["y"]-h["r"],h["r"]*2,h["r"]*2)) and player_obj.invincible==0:
                    if player_obj.take_damage(1): player_died()
            self._update_facility_lasers(player_obj)
            self._update_facility_cores(p_bullets)
            alive_enemies=[e for e in self.challenge_enemies if getattr(e,"alive",False)]
            cores_alive=[c for c in self.cores if c.alive]
            timed_clear=self.challenge_type in("heat_elevator","laser_room","zero_gravity_corridor","glitch_room","frozen_corridor","storm_elevator") and self.timer>280
            if (self.challenge_type in("security_gate","server_lockdown","corex_trial") and not alive_enemies) or (self.challenge_type=="reactor_core_room" and not cores_alive) or timed_clear:
                self.complete_challenge()
        if self.status!="completed" and pr.colliderect(self.barrier_rect):
            player_obj.wx=self.barrier_rect.left-player_obj.WIDTH-2; player_obj.vx=0
    def _update_facility_lasers(self,player_obj):
        if self.challenge_type not in("laser_room","server_lockdown","corex_trial"): return
        if lasers_disabled_for_level(self.level):
            for l in self.lasers: l["warn"]=False; l["active"]=False
            return
        pr=player_obj.get_rect()
        for l in self.lasers:
            cycle=(self.timer+l["phase"])%120; l["warn"]=70<=cycle<90; l["active"]=90<=cycle<116
            if l["active"] and pr.colliderect(pygame.Rect(int(l["x"]),self.CEILING_H,8,self.FLOOR_Y-self.CEILING_H)) and player_obj.invincible==0:
                if player_obj.take_damage(1): player_died()
    def _update_facility_cores(self,p_bullets):
        if not self.cores: return
        for b in p_bullets:
            if not b.alive: continue
            for c in self.cores:
                if c.alive and b.get_rect().colliderect(c.get_rect()):
                    b.alive=False; c.hp-=safe_damage_value(getattr(b,"damage",1)); spawn_pixels(c.wx,c.wy,ORANGE,8)
                    if c.hp<=0: c.alive=False; debug_print(f"CORE {c.idx}/3 destroyed")
                    break
    def draw_bg(self,surface,cam,t,accent):
        sx=int(cam.apply(self.wx,0)[0]); sw=int(self.width)
        vis_x=max(0,sx); vis_w=min(SCREEN_W,sx+sw)-vis_x
        if vis_w<=0: return
        pygame.draw.rect(surface,(18,22,40),(vis_x,0,vis_w,SCREEN_H))
        pygame.draw.rect(surface,(25,30,50),(vis_x,0,vis_w,self.CEILING_H))
        for xi in range(vis_x,vis_x+vis_w,40): pygame.draw.line(surface,(35,40,65),(xi,0),(xi,self.CEILING_H),1)
        for yi in range(0,self.CEILING_H,20): pygame.draw.line(surface,(35,40,65),(vis_x,yi),(vis_x+vis_w,yi),1)
        for xi in range(vis_x+20,vis_x+vis_w,80):
            pygame.draw.rect(surface,(60,60,80),(xi-10,self.CEILING_H-6,20,6))
            lt=pygame.Surface((40,100),pygame.SRCALPHA)
            for li in range(4):
                pygame.draw.polygon(lt,(*accent,max(0,10-li*2)),[(20-li*4,0),(20+li*4,0),(20+li*4+6,80),(20-li*4-6,80)])
            surface.blit(lt,(xi-20,self.CEILING_H))
        for px2 in self.pipes:
            psx=int(cam.apply(px2,0)[0])
            if not(-20<psx<SCREEN_W+20): continue
            pygame.draw.rect(surface,(50,55,80),(psx-6,self.CEILING_H,12,SCREEN_H-self.CEILING_H))
            pygame.draw.rect(surface,(60,65,90),(psx-8,self.CEILING_H+20,16,10),border_radius=2)
            lp=int(150+80*math.sin(t*0.004+px2*0.01)); pygame.draw.circle(surface,(lp//4,lp//3,lp),(psx,self.CEILING_H+15),4)
        for hx in self.hazards:
            hsx=int(cam.apply(hx,0)[0])
            if not(-40<hsx<SCREEN_W+40): continue
            if int(t*0.005+hx)%3!=0:
                for _ in range(3): pygame.draw.line(surface,(100,200,255),(hsx,self.FLOOR_Y),(hsx+random.randint(-15,15),self.FLOOR_Y-random.randint(0,20)),1)
                pygame.draw.rect(surface,(80,160,255),(hsx-16,self.FLOOR_Y-4,32,6),border_radius=2)
        if self.status!="completed":
            lock=make_font(12,"hud",True).render(CHALLENGE_TITLES.get(self.challenge_type,"SECURITY ACTIVE") if self.status=="active" else "SECURITY ACTIVE",True,accent)
            surface.blit(lock,(max(vis_x+16,min(vis_x+vis_w-lock.get_width()-16,SCREEN_W//2-lock.get_width()//2)),92))
        elif self.text_timer>0:
            opened=make_font(12,"hud",True).render("GATE OPENED",True,GREEN)
            surface.blit(opened,(max(vis_x+16,min(vis_x+vis_w-opened.get_width()-16,SCREEN_W//2-opened.get_width()//2)),92))
        disabled=lasers_disabled_for_level(self.level)
        for l in self.lasers:
            lx=int(cam.apply(l["x"],0)[0]); col=(45,70,80) if disabled else RED if l["active"] else ORANGE if l["warn"] else (90,30,30)
            pygame.draw.line(surface,col,(lx,self.CEILING_H),(lx,self.FLOOR_Y),2 if disabled else 4 if l["active"] else 1)
        if disabled and self.lasers:
            off=make_font(10,"hud",True).render("LASER DISABLED",True,CYAN)
            surface.blit(off,(max(vis_x+16,min(vis_x+vis_w-off.get_width()-16,SCREEN_W//2-off.get_width()//2)),112))
        if self.challenge_type in("heat_elevator","frozen_corridor","storm_elevator") and self.status=="active" and self.timer%90>45:
            wx=int(cam.apply(self.wx+self.width//2,0)[0]); col=ORANGE if self.challenge_type=="heat_elevator" else YELLOW if self.challenge_type=="storm_elevator" else (170,235,255)
            pygame.draw.line(surface,col,(wx,self.CEILING_H),(wx,self.FLOOR_Y),2)
        for h in self.extra_hazards:
            hx,hy=cam.apply(h["x"],h["y"]); pygame.draw.circle(surface,(150,140,130),(int(hx),int(hy)),h["r"]); pygame.draw.circle(surface,GRAY,(int(hx),int(hy)),h["r"],1)
        for c in self.cores: c.draw(surface,cam,t,accent)
        if self.status!="completed":
            br=cam.apply_rect(self.barrier_rect)
            field=pygame.Surface((max(1,br.w+22),max(1,br.h)),pygame.SRCALPHA)
            for i in range(0,field.get_height(),18):
                a=int(95+55*math.sin(t*0.01+i*0.1)); pygame.draw.line(field,(*accent,a),(field.get_width()//2,i),(field.get_width()//2+random.randint(-8,8),min(field.get_height(),i+14)),2)
            pygame.draw.rect(field,(*accent,55),(field.get_width()//2-4,0,8,field.get_height()),border_radius=4)
            surface.blit(field,(br.x-11,br.y))
        if self.challenge_type in("glitch_room","server_lockdown","corex_trial") and self.status=="active" and random.random()<0.12:
            pygame.draw.rect(surface,(*accent,75),(random.randint(vis_x,max(vis_x,vis_x+vis_w-70)),random.randint(110,480),random.randint(25,80),random.randint(2,7)))
        if 0<sx<SCREEN_W: pygame.draw.rect(surface,accent,(sx,0,3,SCREEN_H))
        ex2=sx+sw
        if 0<ex2<SCREEN_W: pygame.draw.rect(surface,accent,(ex2-3,0,3,SCREEN_H))
    def draw_platforms(self,surface,cam,accent):
        for plat in self.platforms:
            sr=cam.apply_rect(plat)
            if not(-10<sr.x<SCREEN_W+10): continue
            draw_platform(surface,sr,self.level_theme,"floating")
    def draw_doors(self,surface,cam):
        if not SHOW_OLD_FACILITY_DOORS: return
        self.door_enter.draw(surface,cam,opened=self.status!="inactive",override_label="START" if self.status=="inactive" else "ACTIVE" if self.status=="active" else "DONE")
        self.door_exit.draw(surface,cam,locked=self.status!="completed",opened=self.status=="completed",override_label="LOCKED" if self.status!="completed" else "OPEN")
    def get_hazard_rects(self): return [pygame.Rect(hx-14,self.FLOOR_Y-8,28,12) for hx in self.hazards]

# ------------------------------------------------------------------------------------
# CAMERA
# ------------------------------------------------------------------------------------
class Camera:
    def __init__(self): self.x=0.0
    def update(self,target_x):
        tc=target_x-SCREEN_W//3; self.x+=(tc-self.x)*0.1; self.x=max(0,min(WORLD_W-SCREEN_W,self.x))
    def apply(self,wx,wy): return wx-self.x,wy
    def apply_rect(self,rect): return pygame.Rect(rect.x-self.x,rect.y,rect.w,rect.h)



# ------------------------------------------------------------------------------------
# SOUND MANAGER - PROCEDURAL AUDIO
# ------------------------------------------------------------------------------------
class SoundManager:
    SR = 44100

    def __init__(self):
        self.enabled = False
        self.vol_sfx  = 0.55
        self.vol_bgm  = 0.22
        self.muted    = False
        self.cur_bgm  = None
        self.bgm_ch   = None
        self.sfx_chs  = []
        self.sfx_idx  = 0
        self.sounds   = {}
        self.bgm      = {}
        try:
            pygame.mixer.init(frequency=self.SR, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(16)
        except Exception as e:
            debug_print(f"[Sound] mixer init failed: {e}"); return
        try:
            self.bgm_ch   = pygame.mixer.Channel(0)
            self.sfx_chs  = [pygame.mixer.Channel(i) for i in range(1, 9)]
            self._gen_sfx()
            self._gen_bgm()
        except Exception as e:
            debug_print(f"[Sound] generation failed: {e}")
            self.sounds.clear()
            self.bgm.clear()
            return
        self.enabled = True

    # -- Low-level generators --------------------
    def _to_snd(self, wave):
        wave = np.asarray(wave, dtype=np.float32).reshape(-1)
        wave = np.nan_to_num(wave, nan=0.0, posinf=1.0, neginf=-1.0)
        wave = np.clip(wave, -1.0, 1.0)
        data = np.rint(wave * 32767).astype(np.int16)
        stereo = np.ascontiguousarray(np.column_stack([data, data]))
        return pygame.sndarray.make_sound(stereo)

    def _sine(self, freq, dur, vol=0.5, fade=True):
        t = np.linspace(0, dur, int(self.SR * dur), False)
        w = np.sin(2 * np.pi * freq * t) * vol
        if fade: w *= np.linspace(1, 0, len(w)) ** 0.4
        return w

    def _square(self, freq, dur, vol=0.3, fade=True, duty=0.5):
        t = np.linspace(0, dur, int(self.SR * dur), False)
        w = ((t * freq % 1) < duty).astype(float) * 2 - 1
        w = w * vol
        if fade: w *= np.linspace(1, 0, len(w))
        return w

    def _noise(self, dur, vol=0.4, fade=True):
        n = int(self.SR * dur)
        w = np.random.uniform(-1, 1, n) * vol
        if fade: w *= np.linspace(1, 0, n) ** 0.4
        return w

    def _sweep(self, f0, f1, dur, vol=0.45, shape='sine', fade=True):
        n = int(self.SR * dur)
        t = np.linspace(0, dur, n, False)
        phase = 2 * np.pi * np.cumsum(np.linspace(f0, f1, n)) / self.SR
        w = (np.sin(phase) if shape == 'sine' else np.sign(np.sin(phase)) * 0.5) * vol
        if fade: w *= np.linspace(1, 0, n) ** 0.4
        return w

    def _pad(self, a, b):
        n = max(len(a), len(b))
        return (np.pad(a, (0, n - len(a))) + np.pad(b, (0, n - len(b)))) / 1.4

    # -- SFX generation -------------------------
    def _gen_sfx(self):
        s = self.sounds
        # Weapons
        s['shoot_laser']   = self._to_snd(self._sweep(1400, 500, 0.09, 0.38))
        s['shoot_plasma']  = self._to_snd(self._pad(self._sweep(250,70,0.18,0.38,'square'), self._noise(0.06,0.15)))
        s['shoot_shotgun'] = self._to_snd(self._noise(0.07, 0.55) * np.linspace(1,0,int(self.SR*0.07))**0.25)
        s['shoot_cryo']    = self._to_snd(self._sweep(2200,900,0.13,0.28) * (0.5+0.5*np.random.uniform(0,1,int(self.SR*0.13))))
        s['shoot_thunder'] = self._to_snd(np.concatenate([self._noise(0.025,0.85),self._sweep(160,45,0.11,0.38,'square')]))
        s['shoot_railgun'] = self._to_snd(np.concatenate([self._sweep(900,1800,0.045,0.45),self._noise(0.035,0.25)]))
        s['shoot_nova']    = self._to_snd(self._pad(self._sweep(180,55,0.20,0.45,'square'),self._sweep(900,260,0.12,0.25)))
        s['shoot_pulse']   = self._to_snd(np.concatenate([self._sine(880,0.035,0.26),self._sine(1040,0.035,0.24),self._sweep(760,420,0.055,0.22)]))
        # Player movement
        s['jump']         = self._to_snd(np.concatenate([self._sweep(260,520,0.07,0.38),self._sweep(520,780,0.05,0.22)]))
        s['land']         = self._to_snd(self._noise(0.04,0.35) * np.linspace(1,0,int(self.SR*0.04)))
        # Player damage
        s['player_hit']   = self._to_snd(self._pad(self._noise(0.05,0.55), self._sweep(440,110,0.11,0.32)))
        s['player_death'] = self._to_snd(np.concatenate([self._sweep(700,100,0.45,0.5), self._noise(0.22,0.3)]))
        s['frozen']       = self._to_snd(np.concatenate([self._sweep(1800,2600,0.08,0.3), self._sine(1300,0.14,0.22)]))
        # Enemies
        s['enemy_hit']    = self._to_snd(self._pad(self._noise(0.04,0.38), self._sweep(320,130,0.06,0.22)))
        s['enemy_death']  = self._to_snd(self._pad(self._noise(0.09,0.52), self._sweep(220,55,0.13,0.35,'square')))
        s['stomp']        = self._to_snd(self._pad(self._noise(0.04,0.5), self._sweep(200,70,0.06,0.3)))
        # Boss
        s['boss_hit']     = self._to_snd(self._pad(self._noise(0.07,0.62), self._sweep(140,55,0.16,0.48,'square')))
        s['boss_phase2']  = self._to_snd(np.concatenate([
            self._sweep(80,320,0.28,0.5,'square'), self._noise(0.1,0.4), self._sweep(320,650,0.2,0.38)]))
        s['boss_death']   = self._to_snd(np.concatenate([
            self._noise(0.18,0.75), self._sweep(420,45,0.55,0.52), self._noise(0.22,0.42), self._sweep(110,18,0.3,0.3)]))
        # Collectibles
        s['coin']         = self._to_snd(np.concatenate([self._sine(880,0.065,0.38), self._sine(1100,0.065,0.32)]))
        s['coin_rare']    = self._to_snd(np.concatenate([self._sine(880,0.055,0.35),self._sine(1100,0.055,0.32),self._sine(1320,0.055,0.30),self._sine(1760,0.1,0.28)]))
        s['chest']        = self._to_snd(np.concatenate([self._sine(440,0.08,0.38),self._sine(550,0.08,0.35),self._sine(660,0.08,0.32),self._sine(880,0.14,0.35)]))
        s['weapon_pickup']= self._to_snd(self._pad(self._sweep(380,820,0.14,0.4), self._sine(1250,0.11,0.28)))
        # Events
        s['level_clear']  = self._to_snd(np.concatenate([self._sine(523,0.10,0.42),self._sine(659,0.10,0.42),self._sine(784,0.10,0.42),self._sine(1047,0.28,0.45)]))
        s['game_over']    = self._to_snd(np.concatenate([self._sine(400,0.16,0.4),self._sine(320,0.16,0.4),self._sine(240,0.20,0.4),self._sine(160,0.42,0.4)]))
        s['ui_click']     = self._to_snd(self._sine(820, 0.045, 0.22, False))
        s['checkpoint']   = self._to_snd(np.concatenate([self._sine(660,0.08,0.35),self._sine(880,0.13,0.35)]))

    # -- BGM generation -------------------------
    def _make_bgm(self, notes, note_dur=0.22, vol=0.18):
        n_total = int(self.SR * note_dur * len(notes))
        track   = np.zeros(n_total)
        for i, freq in enumerate(notes):
            s = int(i * note_dur * self.SR)
            e = int((i + 1) * note_dur * self.SR)
            ln = e - s
            t  = np.linspace(0, note_dur, ln, False)
            # Square melody
            mel = ((t * freq % 1) < 0.5).astype(float) * 2 - 1
            # Bass octave below
            bas = ((t * (freq/2) % 1) < 0.5).astype(float) * 2 - 1
            # Envelope
            atk = max(1, int(ln * 0.06))
            rel = max(1, int(ln * 0.22))
            env = np.ones(ln)
            env[:atk] = np.linspace(0, 1, atk)
            env[-rel:] = np.linspace(1, 0, rel)
            track[s:e] += mel * env * vol + bas * env * (vol * 0.32)
        return self._to_snd(track)

    def _gen_bgm(self):
        B = self.bgm
        # (all melodies: Hz values, 8 notes)
        B['menu']       = self._make_bgm([392,440,523,440,392,349,392,440], 0.22, 0.18)
        B['station']    = self._make_bgm([261,329,392,329,293,261,329,293], 0.24, 0.16)
        B['lab']        = self._make_bgm([329,392,440,494,440,392,349,329], 0.22, 0.16)
        B['engine']     = self._make_bgm([110,130,110,98, 110,130,146,130], 0.26, 0.20)
        B['reactor']    = self._make_bgm([130,155,174,196,174,155,130,116], 0.22, 0.20)
        B['space']      = self._make_bgm([196,220,247,220,196,175,196,220], 0.32, 0.15)
        B['void']       = self._make_bgm([164,196,164,146,164,175,164,196], 0.30, 0.14)
        B['nebula']     = self._make_bgm([220,261,329,261,220,196,220,261], 0.28, 0.15)
        B['ice']        = self._make_bgm([523,659,784,659,523,440,523,659], 0.20, 0.15)
        B['glitch']     = self._make_bgm([330,415,294,494,330,247,415,330], 0.14, 0.18)
        B['enemy_base'] = self._make_bgm([220,233,220,196,220,233,247,220], 0.18, 0.20)
        B['storm']      = self._make_bgm([175,196,220,196,175,156,175,196], 0.18, 0.20)
        B['server']     = self._make_bgm([261,294,330,261,294,330,261,247], 0.20, 0.17)
        B['core']       = self._make_bgm([130,155,175,196,175,155,130,116], 0.24, 0.22)
        B['boss']       = self._make_bgm([110,116,123,116,110,98, 110,116], 0.15, 0.25)
        # Aliases
        B['bonus1'] = B['glitch']; B['bonus2'] = B['nebula']; B['bonus3'] = B['void']

    # -- Public API ------------------------------
    def play(self, name, vol_mult=1.0):
        if not self.enabled or self.muted or name not in self.sounds: return
        ch = self.sfx_chs[self.sfx_idx % len(self.sfx_chs)]
        self.sfx_idx += 1
        ch.set_volume(min(1.0, self.vol_sfx * vol_mult))
        ch.play(self.sounds[name])

    def play_bgm(self, key):
        if not self.enabled or self.muted: return
        if self.cur_bgm == key: return
        self.cur_bgm = key
        track = self.bgm.get(key) or self.bgm.get('station')
        if track:
            self.bgm_ch.set_volume(self.vol_bgm)
            self.bgm_ch.play(track, loops=-1)

    def stop_bgm(self):
        if not self.enabled: return
        self.bgm_ch.stop(); self.cur_bgm = None

    def toggle_mute(self):
        self.muted = not self.muted
        if not self.enabled: return
        if self.muted: self.bgm_ch.pause()
        else: self.bgm_ch.unpause()

    def set_vol_sfx(self, v):
        self.vol_sfx = max(0.0, min(1.0, v))

    def set_vol_bgm(self, v):
        self.vol_bgm = max(0.0, min(1.0, v))
        if self.enabled: self.bgm_ch.set_volume(self.vol_bgm)

    def vol_up(self):
        self.set_vol_sfx(self.vol_sfx + 0.1)
        self.set_vol_bgm(self.vol_bgm + 0.05)

    def vol_down(self):
        self.set_vol_sfx(self.vol_sfx - 0.1)
        self.set_vol_bgm(self.vol_bgm - 0.05)

# ------------------------------------------------------------------------------------
# ORIGINAL PIXEL GLIDE BACKGROUND - Clean sci-fi night sky
# ------------------------------------------------------------------------------------
class OriginalBackground:
    def __init__(self):
        rng = random.Random(42)

        # Stars - three layers for subtle parallax
        self.stars_back = []
        self.stars_mid = []
        self.stars_front = []

        # Back stars - very small, very slow parallax
        for _ in range(80):
            self.stars_back.append((
                rng.randint(0, 10000), rng.randint(0, SCREEN_H - 40),
                rng.randint(1, 1), rng.uniform(0.3, 0.7),
                rng.uniform(0.001, 0.003)
            ))

        # Mid stars - slightly larger, medium parallax
        for _ in range(50):
            self.stars_mid.append((
                rng.randint(0, 10000), rng.randint(0, SCREEN_H - 40),
                rng.randint(1, 2), rng.uniform(0.5, 0.9),
                rng.uniform(0.002, 0.005)
            ))

        # Front stars - slightly brighter, faster parallax
        for _ in range(30):
            self.stars_front.append((
                rng.randint(0, 10000), rng.randint(0, SCREEN_H - 40),
                rng.randint(1, 2), rng.uniform(0.7, 1.0),
                rng.uniform(0.004, 0.008)
            ))

        # Soft nebula - very subtle, only in some themes
        self.nebula = []
        for _ in range(3):
            self.nebula.append((
                rng.randint(0, 10000), rng.randint(60, SCREEN_H - 100),
                rng.randint(120, 200), rng.randint(50, 80),
                rng.choice(["cool", "warm", "neutral"])
            ))

        # Small planets/moons - only for space themes
        self.planets = []
        for _ in range(2):
            self.planets.append((
                rng.randint(800, 9000), rng.randint(40, 180),
                rng.randint(25, 50),
                rng.choice([(40, 50, 80), (60, 50, 40), (50, 45, 70)])
            ))

        # Simple city silhouette - buildings with windows
        self.buildings = []
        for i in range(18):
            x = rng.randint(0, 10000)
            w = 40 + rng.randint(0, 30)
            h = 80 + rng.randint(0, 120)
            self.buildings.append((
                x, w, h, rng.uniform(0.9, 1.1),
                [rng.randint(0, 1) for _ in range(6)]
            ))

        # Subtle ground fog
        self.fog_offset = rng.uniform(0, 100)

    def _visible(self, sx, margin=0):
        return -margin < sx < SCREEN_W + margin

    def draw(self, surface, cam_x, level_num):
        ld = get_level_data(level_num)
        sky = ld["sky"]
        bld_col = ld["bld_col"]
        acc = ld["accent"]
        theme = ld["theme"]
        t = pygame.time.get_ticks()

        # --- Sky fill - dark night, very subtle pulse ---
        sky_pulse = 2 * math.sin(t * 0.0005)
        sky_r = max(5, min(255, sky[0] + int(sky_pulse)))
        sky_g = max(5, min(255, sky[1] + int(sky_pulse * 0.3)))
        sky_b = max(5, min(255, sky[2] + int(sky_pulse)))
        surface.fill((sky_r, sky_g, sky_b))

        # --- Stars: three layers with slight parallax ---
        self._draw_stars(surface, cam_x, t, theme, self.stars_back, 0.015)
        self._draw_stars(surface, cam_x, t, theme, self.stars_mid, 0.03)
        self._draw_stars(surface, cam_x, t, theme, self.stars_front, 0.06)

        # --- Soft nebula - very subtle, only for space-like themes ---
        if theme in ("space", "nebula", "core", "void", "station"):
            self._draw_nebula(surface, cam_x, t, theme, acc)

        # --- Small planets - only for space themes ---
        if theme in ("space", "nebula", "core", "void"):
            self._draw_planets(surface, cam_x, t, theme, acc)

        # --- City silhouette - simple buildings with subtle glowing windows ---
        self._draw_buildings(surface, cam_x, t, theme, bld_col, acc)

        # --- Subtle ground fog ---
        self._draw_ground_fog(surface, cam_x, t, sky)

    def _draw_stars(self, surface, cam_x, t, theme, stars, parallax):
        for s in stars:
            sx = int(s[0] - cam_x * parallax) % (SCREEN_W + 60) - 30
            if not self._visible(sx): continue
            pulse = int(s[3] * (120 + 60 * math.sin(t * s[4] + s[1] * 0.03)))
            pulse = max(0, min(200, pulse))
            if pulse > 15:
                # Slight color variation based on theme
                if theme in ("space", "nebula", "core", "void"):
                    col = (pulse, pulse, min(200, pulse + 40))
                elif theme in ("ice", "storm"):
                    col = (pulse, min(200, pulse + 30), min(220, pulse + 60))
                else:
                    col = (pulse, pulse, pulse)
                pygame.draw.circle(surface, col, (sx, int(s[1])), s[2])

    def _draw_nebula(self, surface, cam_x, t, theme, acc):
        for i, n in enumerate(self.nebula):
            sx = int(n[0] - cam_x * 0.01) % (SCREEN_W + 240) - 120
            if not self._visible(sx): continue
            pa = int(8 + 4 * math.sin(t * 0.002 + i * 2.0))
            if theme == "space":
                col = (int(20 + 10 * math.sin(t * 0.002 + i)), 5, int(35 + 15 * math.cos(t * 0.002 + i)), pa)
            elif theme == "nebula":
                col = (int(25 + 10 * math.sin(t * 0.002 + i)), 5, int(40 + 20 * math.cos(t * 0.002 + i)), pa)
            elif theme == "core":
                col = (5, int(25 + 15 * math.sin(t * 0.002 + i)), int(35 + 20 * math.cos(t * 0.002 + i)), pa)
            elif theme == "void":
                col = (10, 0, int(20 + 10 * math.cos(t * 0.002 + i)), pa)
            else:
                col = (int(15 + 8 * math.sin(t * 0.002 + i)), 5, int(25 + 12 * math.cos(t * 0.002 + i)), pa)
            nb = pygame.Surface((n[2], n[3]), pygame.SRCALPHA)
            pygame.draw.ellipse(nb, col, (0, 0, n[2], n[3]))
            surface.blit(nb, (sx, int(n[1])))

    def _draw_planets(self, surface, cam_x, t, theme, acc):
        for i, p in enumerate(self.planets):
            sx = int(p[0] - cam_x * 0.02) % (SCREEN_W + 200) - 100
            if not self._visible(sx, 50): continue
            r = p[2]
            col = p[3]
            if theme == "space":
                col = (40, 45, 70) if i == 0 else (60, 55, 45)
            elif theme == "nebula":
                col = (45, 20, 55)
            elif theme == "core":
                col = (15, 45, 60)
            elif theme == "void":
                col = (20, 15, 35)
            pygame.draw.circle(surface, col, (sx, int(p[1])), r)
            pygame.draw.circle(surface, tuple(min(180, c + 15) for c in col), (sx, int(p[1])), r, 1)
            # Very subtle ring
            ring_a = int(6 + 4 * math.sin(t * 0.002 + i))
            if ring_a > 0:
                ring_s = pygame.Surface((r * 2 + 12, r // 2 + 2), pygame.SRCALPHA)
                pygame.draw.ellipse(ring_s, (*acc, ring_a), (0, 0, r * 2 + 12, r // 2 + 2), 1)
                surface.blit(ring_s, (sx - r - 6, int(p[1]) - r // 4))

    def _draw_buildings(self, surface, cam_x, t, theme, bld_col, acc):
        for i, b in enumerate(self.buildings):
            sx = int(b[0] - cam_x * 0.08) % (SCREEN_W + 160) - 80
            if not self._visible(sx, 50): continue
            w = int(b[1] * b[3])
            h = int(b[2] * b[3])
            by = SCREEN_H - h

            if theme == "glitch":
                col = (int(40 + 20 * math.sin(t * 0.002 + i)), 0, int(40 + 20 * math.cos(t * 0.002 + i)))
            elif theme == "void":
                col = (10, 0, 15)
            else:
                col = bld_col

            # Building body
            pygame.draw.rect(surface, col, (sx, by, w, h))

            # Subtle window glow - only for non-void themes
            if theme not in ("void", "glitch"):
                twinkle = t // 800
                for wy in range(8, h - 10, 16):
                    win_idx = (i + wy // 16) % len(b[4])
                    if (twinkle + i + wy) % 8 == 0: continue
                    if win_idx < len(b[4]) and b[4][win_idx] == 0 and random.random() < 0.4: continue
                    wa = int(25 + 20 * math.sin(t * 0.003 + i + wy * 0.06))
                    wc = (min(200, acc[0] + wa), min(200, acc[1] + wa), min(200, acc[2] + wa))
                    win_x = sx + 4 + ((i + wy) % max(1, w // 6 - 1)) * 6
                    if win_x + 4 < sx + w - 3:
                        # Subtle glow
                        win_glow = pygame.Surface((5, 3), pygame.SRCALPHA)
                        pygame.draw.rect(win_glow, (*wc, 40), (0, 0, 5, 3))
                        surface.blit(win_glow, (win_x, by + wy), special_flags=pygame.BLEND_ADD)
                        pygame.draw.rect(surface, wc, (win_x, by + wy, 4, 2))

    def _draw_ground_fog(self, surface, cam_x, t, sky):
        fog_h = int(SCREEN_H * 0.18)
        fog = pygame.Surface((SCREEN_W, fog_h), pygame.SRCALPHA)
        fog_col = tuple(min(255, c + 4) for c in sky)
        for fy in range(fog_h):
            fa = max(0, int(6 * (1 - fy / fog_h) * (0.6 + 0.4 * math.sin(fy * 0.05 + t * 0.0008 + self.fog_offset))))
            if fa > 0:
                pygame.draw.line(fog, (*fog_col, fa), (0, fy), (fog.get_width(), fy))
        surface.blit(fog, (0, SCREEN_H - fog_h))
        # Very subtle horizon line
        horizon_col = tuple(min(255, c + 8) for c in sky)
        pygame.draw.line(surface, horizon_col, (0, SCREEN_H - 30), (SCREEN_W, SCREEN_H - 30), 1)

parallax_bg = OriginalBackground()

def trigger_boss_shake(intensity="medium",duration=None):
    profiles={"light":(3,8),"medium":(6,12),"strong":(9,16),"heavy":(11,20),"very_heavy":(14,24),"extreme":(17,30)}
    if isinstance(intensity,str): val,dur=profiles.get(intensity,profiles["medium"])
    else: val,dur=intensity,12
    shake.trigger(val,duration if duration is not None else dur)

def draw_boss_warning(surface,effect_type,target_area,color=NEON_RED,alpha=90,label="WARNING"):
    warn=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA)
    tick=pygame.time.get_ticks()
    pulse=max(0.35,abs(math.sin(tick*0.012)))
    if effect_type=="line":
        x=int(target_area); pygame.draw.line(warn,(*color,alpha),(x,0),(x,SCREEN_H),3); pygame.draw.rect(warn,(*color,alpha//3),(x-28,0,56,SCREEN_H))
        for y in range(40,SCREEN_H,54):
            pygame.draw.polygon(warn,(*color,int(alpha*pulse)),[(x-18,y),(x,y+12),(x-18,y+24)])
            pygame.draw.polygon(warn,(*color,int(alpha*pulse)),[(x+18,y),(x,y+12),(x+18,y+24)])
    elif effect_type=="circle":
        x,y,r=target_area; pygame.draw.circle(warn,(*color,alpha),(int(x),int(y)),int(r),3); pygame.draw.circle(warn,(*color,alpha//4),(int(x),int(y)),int(r))
        pygame.draw.circle(warn,(*WHITE,int(45*pulse)),(int(x),int(y)),int(r+8*pulse),1)
    else:
        rect=pygame.Rect(target_area); pygame.draw.rect(warn,(*color,alpha//2),rect,border_radius=6); pygame.draw.rect(warn,(*color,alpha),rect,border_radius=6,width=2)
        for x in range(rect.left+10,rect.right-10,42):
            pygame.draw.polygon(warn,(*color,int(alpha*pulse)),[(x,rect.top+5),(x+12,rect.top+17),(x+24,rect.top+5)])
            pygame.draw.polygon(warn,(*color,int(alpha*pulse)),[(x,rect.bottom-5),(x+12,rect.bottom-17),(x+24,rect.bottom-5)])
    surface.blit(warn,(0,0))
    if label:
        txt=make_font(11,"hud",True).render(label,True,color); surface.blit(txt,(SCREEN_W//2-txt.get_width()//2,92))

def draw_boss_background_effects(surface,level_num,boss,t,cam_x=0):
    if not boss or not getattr(boss,"alive",False): return
    effect=boss.data.get("bg_effect",boss.ability); phase=getattr(boss,"phase",1); pulse=math.sin(t*0.006)
    ov=get_cached_surface("boss_bg_ov",SCREEN_W,SCREEN_H)
    if effect=="radar":
        ov.fill((20,80,120,18)); surface.blit(ov,(0,0)); cx=int(SCREEN_W*0.78+math.sin(t*0.001)*30); cy=155; r=115
        pygame.draw.circle(surface,(60,220,255,45),(cx,cy),r,1); ang=t*0.003; pygame.draw.line(surface,(80,240,255,110),(cx,cy),(int(cx+math.cos(ang)*r),int(cy+math.sin(ang)*r)),2)
        for y in range(40,SCREEN_H,54): pygame.draw.line(surface,(60,160,220,28),(0,y+int(t*0.02)%12),(SCREEN_W,y+int(t*0.02)%12),1)
    elif effect=="engine_heat":
        ov.fill((110,35,8,22)); surface.blit(ov,(0,0))
        for i in range(10):
            x=int((i*83-cam_x*0.04+math.sin(t*0.002+i)*12)%SCREEN_W); h=int(35+18*math.sin(t*0.006+i))
            pygame.draw.rect(surface,(255,95,20,55),(x,SCREEN_H-70-h,10,h),border_radius=5); pygame.draw.circle(surface,(255,170,45,80),(x+5,SCREEN_H-75-h),random.randint(2,5))
    elif effect=="lab_warning":
        ov.fill((120,20,30,int(16+18*max(0,pulse)))); surface.blit(ov,(0,0))
        for x in range(30,SCREEN_W,150):
            col=(255,70,70,70 if (t//260+x)%2==0 else 18); pygame.draw.circle(surface,col,(x,70),18); pygame.draw.line(surface,(*YELLOW,55),(x,88),(x+random.randint(-14,14),130),1)
    elif effect=="aero_wind":
        ov.fill((30,40,85,14)); surface.blit(ov,(0,0))
        for i in range(14):
            y=70+i*34+int(math.sin(t*0.002+i)*9); x=int(SCREEN_W-(t*0.22+i*97)%SCREEN_W); pygame.draw.arc(surface,(160,220,255,72),(x-55,y-8,90,18),0,math.pi,1)
    elif effect=="colossus_debris":
        ov.fill((70,45,70,16+phase*5)); surface.blit(ov,(0,0))
        for i in range(9):
            x=int((i*111+math.sin(t*0.001+i)*18-cam_x*0.03)%SCREEN_W); y=int((t*0.025+i*72)%(SCREEN_H-90))+30; pygame.draw.rect(surface,(120,95,120,60),(x,y,random.randint(3,7),random.randint(3,8)))
    elif effect=="firewall_glitch":
        ov.fill((0,75,50,20+phase*4)); surface.blit(ov,(0,0))
        for y in range(0,SCREEN_H,18): pygame.draw.line(surface,(60,255,170,32),(0,y+int(t*0.04)%18),(SCREEN_W,y+int(t*0.04)%18),1)
        if random.random()<0.18: pygame.draw.rect(surface,(random.randint(30,90),255,random.randint(120,210),70),(random.randint(0,SCREEN_W-120),random.randint(45,SCREEN_H-80),random.randint(45,140),random.randint(3,10)))
        for i,txt in enumerate(["ERR", "0xCORE", "DELETE", "G7?", "NULL"]):
            img=make_font(10,"hud",True).render(txt,True,(80,255,170)); img.set_alpha(55); surface.blit(img,(int((i*137+t*0.03)%SCREEN_W),105+i*54))
    elif effect=="cryo_snow":
        ov.fill((45,110,155,22)); surface.blit(ov,(0,0))
        for i in range(34):
            x=int((i*47+math.sin(t*0.002+i)*22-cam_x*0.02)%SCREEN_W); y=int((t*0.035+i*31)%(SCREEN_H+20))-10; pygame.draw.circle(surface,(190,235,255,120),(x,y),1+(i%2))
        fog=get_cached_surface("boss_cryo_fog",SCREEN_W,90); fog.fill((170,230,255,28)); surface.blit(fog,(0,SCREEN_H-120+int(6*pulse)))
    elif effect=="storm_lightning":
        ov.fill((45,25,100,20)); surface.blit(ov,(0,0))
        if int(t//180)%5==0: ov.fill((190,210,255,32)); surface.blit(ov,(0,0))
        for i in range(6):
            x=int((i*151+math.sin(t*0.001+i)*40)%SCREEN_W); pygame.draw.line(surface,(160,170,230,45),(x,0),(x+random.randint(-25,25),80),1)
    elif effect=="server_phase":
        col=[(70,140,100,18),(160,70,50,24),(200,35,90,32)][min(phase-1,2)]; ov.fill(col); surface.blit(ov,(0,0))
        for x in range(0,SCREEN_W,64): pygame.draw.line(surface,(80,220,140,35),(x+int(t*0.03)%64,0),(x+int(t*0.03)%64,SCREEN_H),1)
    elif effect=="corex_ultimate":
        ov.fill((95,0,25,24+phase*7)); surface.blit(ov,(0,0)); pygame.draw.circle(surface,(80,240,255,45),(SCREEN_W//2,145),int(70+18*math.sin(t*0.006)),3)
        for i in range(8):
            ang=t*0.001+i*math.pi/4; pygame.draw.line(surface,(255,40,70,70),(SCREEN_W//2,145),(int(SCREEN_W//2+math.cos(ang)*240),int(145+math.sin(ang)*90)),1)
        if random.random()<0.15: pygame.draw.rect(surface,(255,0,60,70),(0,random.randint(0,SCREEN_H-8),SCREEN_W,random.randint(2,8)))

# ------------------------------------------------------------------------------------
# DRAW HELPERS - G7 ANIMATED
# ------------------------------------------------------------------------------------
def draw_g7(surface,x,y,fly_mode=False,walk_t=0,on_ground=True,vx=0,vy=0,skin_data=None):
    skin_data=skin_data or SKINS["classic"]
    body_col=skin_data["body"]; dark_col=skin_data["dark"]; accent_col=skin_data["accent"]
    eye_col=skin_data["eye"]; trail_col=skin_data["trail"]
    if fly_mode:
        t2=pygame.time.get_ticks()
        thrust=1 if vy>0.5 else -1 if vy<-0.5 else 0
        tilt=max(-5,min(5,int(vy*1.5)))
        pulse=int(2*math.sin(t2*0.018)); wa=int(7*math.sin(t2*0.014))
        for i in range(3):
            tr=pygame.Surface((38+i*8,12+i*3),pygame.SRCALPHA)
            pygame.draw.ellipse(tr,(*trail_col,max(0,42-i*12)),(0,0,38+i*8,12+i*3))
            surface.blit(tr,(x-5-i*10,y+24+i*2+thrust*2))
        pygame.draw.polygon(surface,dark_col,[(x+16,y+tilt),(x+32,y+14),(x+28,y+28+pulse),(x+4,y+28-pulse),(x,y+14)])
        pygame.draw.polygon(surface,body_col,[(x+16,y+2+tilt),(x+28,y+13),(x+24,y+24+pulse),(x+8,y+24-pulse),(x+4,y+13)])
        pygame.draw.polygon(surface,dark_col,[(x+4,y+14),(x-22,y+22+wa),(x-8,y+30+wa//3),(x+8,y+22)])
        pygame.draw.polygon(surface,dark_col,[(x+28,y+14),(x+54,y+22-wa),(x+40,y+30-wa//3),(x+24,y+22)])
        pygame.draw.ellipse(surface,accent_col,(x+10,y+5+tilt//2,12,11)); pygame.draw.ellipse(surface,eye_col,(x+13,y+8+tilt//2,6,5))
        ta=int(170+75*math.sin(t2*0.024)); thr=pygame.Surface((12,22),pygame.SRCALPHA)
        pygame.draw.ellipse(thr,(*accent_col,ta),(0,0,12,22)); surface.blit(thr,(x-1,y+26)); surface.blit(thr,(x+21,y+26))
        if abs(vy)>1:
            pygame.draw.circle(surface,WHITE,(x+16,y+13+tilt//2),1)
    else:
        t2=pygame.time.get_ticks()
        is_walking=abs(vx)>0.5 and on_ground
        is_jumping=not on_ground and vy<-1
        is_falling=not on_ground and vy>1

        shadow=pygame.Surface((34,8),pygame.SRCALPHA)
        pygame.draw.ellipse(shadow,(0,0,0,55 if on_ground else 28),(0,0,34,8)); surface.blit(shadow,(x-1,y+34))

        # Body bob
        if is_walking: bob=int(1.8*math.sin(walk_t*0.38))
        elif not on_ground: bob=0
        else: bob=int(0.7*math.sin(t2*0.003))
        lean=max(-3,min(3,int(vx*0.7))) if is_walking else(2 if is_falling else -1 if is_jumping else 0)

        # Squash-stretch
        if is_jumping: body_h=14; head_yo=-2
        elif is_falling: body_h=18; head_yo=1
        else: body_h=16; head_yo=0

        # Leg swing
        if is_walking: ls=int(5*math.sin(walk_t*0.38))
        elif is_jumping: ls=-3
        elif is_falling: ls=2
        else: ls=0

        arm_s=-ls//2
        hand_kick=int(2*math.sin(walk_t*0.76)) if is_walking else 0

        # Legs
        pygame.draw.rect(surface,dark_col,(x+8+lean,y+27+bob+ls,7,8),border_radius=2)
        pygame.draw.rect(surface,dark_col,(x+17+lean,y+27+bob-ls,7,8),border_radius=2)
        pygame.draw.rect(surface,accent_col,(x+7+lean+(1 if ls>0 else 0),y+33+bob+ls,9,2),border_radius=1)
        pygame.draw.rect(surface,accent_col,(x+16+lean+(1 if ls<0 else 0),y+33+bob-ls,9,2),border_radius=1)

        # Body
        pygame.draw.rect(surface,body_col,(x+6+lean,y+12+bob,20,body_h),border_radius=3)
        pygame.draw.rect(surface,dark_col,(x+8+lean,y+14+bob,4,3),border_radius=1)
        pygame.draw.rect(surface,dark_col,(x+14+lean,y+14+bob,4,3),border_radius=1)
        pygame.draw.rect(surface,dark_col,(x+20+lean,y+14+bob,4,3),border_radius=1)

        # Arms
        pygame.draw.rect(surface,dark_col,(x+2+lean,y+14+bob+arm_s,5,10+hand_kick),border_radius=2)
        pygame.draw.rect(surface,dark_col,(x+25+lean,y+14+bob-arm_s,5,10-hand_kick),border_radius=2)
        pygame.draw.rect(surface,accent_col,(x+2+lean,y+22+bob+arm_s+hand_kick,5,3),border_radius=2)
        pygame.draw.rect(surface,accent_col,(x+25+lean,y+22+bob-arm_s-hand_kick,5,3),border_radius=2)

        # Head
        pygame.draw.rect(surface,body_col,(x+8+lean,y+2+bob+head_yo,16,12),border_radius=3)
        pygame.draw.rect(surface,dark_col,(x+6+lean,y+4+bob+head_yo,3,6),border_radius=1)
        pygame.draw.rect(surface,dark_col,(x+23+lean,y+4+bob+head_yo,3,6),border_radius=1)

        # Antenna wobble
        aw=int(2*math.sin(t2*0.006+walk_t*0.2)) if is_walking or not on_ground else int(math.sin(t2*0.004))
        pygame.draw.rect(surface,dark_col,(x+13+lean+aw,y+bob+head_yo,2,4))
        pygame.draw.circle(surface,accent_col,(x+14+lean+aw,y+bob+head_yo),2)
        pygame.draw.rect(surface,dark_col,(x+17+lean+aw,y+bob+head_yo,2,4))
        pygame.draw.circle(surface,accent_col,(x+18+lean+aw,y+bob+head_yo),2)

        # Eyes + blink
        blink=(t2//4000)%10==0
        eye_h=1 if blink else 4
        ey=y+5+bob+head_yo+(1 if blink else 0)
        look=1 if vx>0.5 else -1 if vx<-0.5 else 0
        pygame.draw.rect(surface,WHITE,(x+10+lean,ey,5,eye_h),border_radius=1)
        pygame.draw.rect(surface,WHITE,(x+17+lean,ey,5,eye_h),border_radius=1)
        if not blink:
            ep=int(200+55*math.sin(t2*0.004))
            pygame.draw.circle(surface,eye_col,(x+12+lean+look,y+7+bob+head_yo),2)
            pygame.draw.circle(surface,eye_col,(x+19+lean+look,y+7+bob+head_yo),2)

        # Chest panel
        pygame.draw.rect(surface,accent_col,(x+11+lean,y+16+bob,10,6),border_radius=2)
        ep2=int(150+80*math.sin(t2*0.005))
        pygame.draw.circle(surface,eye_col,(x+13+lean,y+19+bob),2)
        pygame.draw.circle(surface,eye_col,(x+19+lean,y+19+bob),2)

        # Motion trail
        if is_walking:
            for i in range(1,3):
                tr=pygame.Surface((6,12),pygame.SRCALPHA); tr.fill((*trail_col,max(0,35-i*15)))
                dx_trail=-i*4*(1 if vx>0 else -1); surface.blit(tr,(x+12+dx_trail,y+14+bob))

def draw_player_weapon(surface,x,y,facing,weapon_key,color,recoil=0,flash=0):
    direction=1 if facing>=0 else -1
    hand_x=x+(27 if direction>0 else 5)
    hand_y=y+21
    back=int(recoil)*direction
    base_x=hand_x-back
    muzzle_y=hand_y-2
    dark=(max(0,color[0]//3),max(0,color[1]//3),max(0,color[2]//3))
    light=(min(255,color[0]+60),min(255,color[1]+60),min(255,color[2]+60))

    def pt(px,py): return (int(base_x+px*direction),int(hand_y+py))
    def poly(points,col): pygame.draw.polygon(surface,col,[pt(px,py) for px,py in points])
    def rect(px,py,w,h,col,r=1):
        rx=base_x+px*direction if direction>0 else base_x-(px+w)*abs(direction)
        pygame.draw.rect(surface,col,(int(rx),int(hand_y+py),w,h),border_radius=r)
    def barrel_end(px,py): return pt(px,py)

    # Shared pistol details: grip, trigger guard, and hand make the weapon read as a gun.
    def pistol_base(length=18,body_h=8):
        rect(0,-7,length,body_h,dark,2)
        rect(3,-9,max(8,length-7),3,color,1)
        poly([(5,1),(12,1),(10,10),(4,10)],dark)
        poly([(7,1),(11,1),(9,8),(6,8)],color)
        pygame.draw.circle(surface,dark,pt(12,3),4,1)
        rect(length-2,-5,5,3,light,1)
        return barrel_end(length+4,-4)

    if weapon_key=="shotgun":
        poly([(-8,-3),(1,-7),(4,-3),(0,5),(-8,5)],dark)
        rect(0,-7,27,7,dark,2)
        rect(5,-10,25,3,color,1)
        rect(10,-3,18,3,light,1)
        poly([(7,0),(14,0),(12,10),(6,10)],dark)
        pygame.draw.circle(surface,dark,pt(14,3),4,1)
        muzzle_x,muzzle_y=barrel_end(32,-8)
    elif weapon_key=="railgun":
        poly([(-6,-1),(2,-7),(6,-3),(2,5),(-6,5)],dark)
        rect(0,-8,30,8,dark,2)
        rect(4,-11,30,3,color,1)
        rect(8,-5,20,3,light,1)
        for i in range(3):
            pygame.draw.circle(surface,light,pt(10+i*7,2),2)
        poly([(8,0),(15,0),(13,10),(7,10)],dark)
        muzzle_x,muzzle_y=barrel_end(36,-9)
    elif weapon_key=="nova":
        muzzle_x,muzzle_y=pistol_base(19,9)
        pygame.draw.circle(surface,color,pt(15,-2),7)
        pygame.draw.circle(surface,light,pt(15,-2),3)
        rect(19,-5,7,5,dark,2)
        muzzle_x,muzzle_y=barrel_end(28,-3)
        muzzle_y=hand_y
    elif weapon_key=="pulse":
        poly([(-4,-1),(2,-7),(7,-4),(3,5),(-4,5)],dark)
        rect(0,-8,25,8,dark,2)
        rect(4,-10,18,3,color,1)
        rect(20,-6,7,4,light,1)
        for i in range(3):
            pygame.draw.circle(surface,light,pt(7+i*6,-3),1)
        poly([(7,0),(13,0),(11,9),(6,9)],dark)
        muzzle_x,muzzle_y=barrel_end(29,-5)
    elif weapon_key=="plasma":
        muzzle_x,muzzle_y=pistol_base(18,8)
        pygame.draw.circle(surface,color,pt(15,-3),5)
        pygame.draw.circle(surface,light,pt(15,-3),2)
        muzzle_x,muzzle_y=barrel_end(24,-4)
    elif weapon_key=="cryo":
        rect(0,-8,22,8,(25,70,95),2)
        rect(4,-10,16,3,color,1)
        rect(19,-6,7,4,(190,240,255),2)
        pygame.draw.circle(surface,(190,240,255),pt(8,2),3)
        poly([(6,0),(12,0),(10,9),(5,9)],dark)
        pygame.draw.circle(surface,dark,pt(13,3),4,1)
        muzzle_x,muzzle_y=barrel_end(28,-5)
    elif weapon_key=="thunder":
        muzzle_x,muzzle_y=pistol_base(19,8)
        pygame.draw.line(surface,light,pt(5,-9),pt(11,-3),2)
        pygame.draw.line(surface,light,pt(11,-3),pt(17,-9),2)
        rect(19,-6,6,4,color,1)
        muzzle_x,muzzle_y=barrel_end(27,-5)
    else:
        muzzle_x,muzzle_y=pistol_base(18,8)

    pygame.draw.circle(surface,WHITE,(hand_x,hand_y+2),3)
    if flash>0:
        pulse=int(160+40*flash)
        flash_col=(min(255,light[0]+40),min(255,light[1]+40),min(255,light[2]+40))
        pygame.draw.circle(surface,flash_col,(int(muzzle_x+direction*4),int(muzzle_y)),4+flash)
        pygame.draw.circle(surface,(255,245,170),(int(muzzle_x+direction*8),int(muzzle_y)),2+flash//2)
        glow=pygame.Surface((26,18),pygame.SRCALPHA)
        pygame.draw.ellipse(glow,(*flash_col,min(220,pulse)),(0,0,26,18))
        surface.blit(glow,(int(muzzle_x+direction*2-(0 if direction>0 else 26)),int(muzzle_y-9)))

def draw_robot_head(surface,x,y,alive=True):
    c=GREEN if alive else(50,50,50); ec=BLUE if alive else(30,30,30); dc=DARK_GREEN if alive else(35,35,35)
    pygame.draw.rect(surface,c,(x,y+3,20,14),border_radius=3)
    pygame.draw.rect(surface,dc,(x+3,y+6,5,4),border_radius=1); pygame.draw.rect(surface,dc,(x+12,y+6,5,4),border_radius=1)
    pygame.draw.circle(surface,ec,(x+5,y+8),2); pygame.draw.circle(surface,ec,(x+14,y+8),2)
    pygame.draw.rect(surface,dc,(x+6,y,3,4)); pygame.draw.rect(surface,dc,(x+12,y,3,4))
    pygame.draw.rect(surface,dc,(x+4,y+16,12,3),border_radius=1)

def draw_hp_bar(surface,x,y,hp,max_hp,w=40):
    pygame.draw.rect(surface,(40,10,15),(x,y,w,5),border_radius=3)
    fill=int(w*max(0,hp)/max_hp)
    color=NEON_GREEN if hp>max_hp*0.5 else NEON_ORANGE if hp>max_hp*0.25 else NEON_RED
    if fill>0:
        bar_fill=pygame.Surface((fill,5),pygame.SRCALPHA)
        pygame.draw.rect(bar_fill,color,(0,0,fill,5),border_radius=3)
        surface.blit(bar_fill,(x,y))
    pygame.draw.rect(surface,(*color,120),(x,y,w,5),border_radius=3,width=1)

def draw_glitch_text(surface,text,font,x,y,base_color,t):
    if int(t*0.05)%8==0:
        for(ox,oy),gc in zip([(-2,0),(2,0),(0,-1)],[(RED[0]//3,0,0),(0,0,BLUE[0]//3),(0,CYAN[1]//4,CYAN[2]//4)]):
            s=font.render(text,True,gc); surface.blit(s,(x+ox+random.randint(-1,1),y+oy))
    surface.blit(font.render(text,True,base_color),(x,y))

# ------------------------------------------------------------------------------------
# BOSS SPRITE
# ------------------------------------------------------------------------------------
def draw_boss_identity_overlay(surface,x,y,bw,bh,data,t,phase=1):
    boss_name=data.get("name","")
    boss_id=data.get("base_id") or next((bid for bid,b in BOSS_DATA.items() if b["name"]==boss_name),0)
    ac=data.get("armor",GRAY); ec=data.get("eye",RED)
    if boss_id==1:
        sweep=math.sin(t*0.08); pygame.draw.circle(surface,(25,45,80),(x+bw//2,y+bh//2),18,1); pygame.draw.line(surface,CYAN,(x+bw//2,y+bh//2),(x+bw//2+int(20*sweep),y+bh//2-14),2)
    elif boss_id==2:
        pygame.draw.rect(surface,(45,55,35),(x-6,y+bh-26,bw+12,18),border_radius=5)
        for i in range(6): pygame.draw.circle(surface,(95,110,70),(x+4+i*(bw+2)//6,y+bh-17),5)
    elif boss_id==3:
        for ox in[-22,-11,0,11,22]: pygame.draw.line(surface,RED,(x+bw//2,y+10),(x+bw//2+ox,y-16),2)
        pygame.draw.circle(surface,(255,80,80),(x+bw//2,y-14),5)
    elif boss_id==4:
        flap=int(7*math.sin(t*0.12)); pygame.draw.polygon(surface,(60,80,170),[(x+4,y+30),(x-42,y+18+flap),(x-8,y+58)]); pygame.draw.polygon(surface,(60,80,170),[(x+bw-4,y+30),(x+bw+42,y+18-flap),(x+bw+8,y+58)])
    elif boss_id==5:
        for i in range(4):
            px=x+18+i*max(1,(bw-36)//3); pygame.draw.polygon(surface,(120,75,150),[(px,y+28),(px+8,y+6),(px+16,y+28)])
    elif boss_id==6:
        for i in range(4):
            yy=y+22+i*13; pygame.draw.rect(surface,(15,230,120),(x-10,yy,8,6),border_radius=2); pygame.draw.rect(surface,(15,230,120),(x+bw+2,yy,8,6),border_radius=2)
    elif boss_id==7:
        for i in range(5):
            px=x+8+i*max(1,(bw-16)//4); pygame.draw.polygon(surface,(185,240,255),[(px,y+8),(px+7,y-14),(px+14,y+8)])
    elif boss_id==8:
        for side in[-1,1]:
            coil_x=x+bw//2+side*(bw//2+9); pygame.draw.line(surface,YELLOW,(coil_x,y+10),(coil_x+side*14,y+38),3); pygame.draw.line(surface,YELLOW,(coil_x+side*14,y+38),(coil_x,y+66),3); pygame.draw.circle(surface,(255,245,120),(coil_x,y+9),5)
    elif boss_id==9:
        for i,col in enumerate([RED,ORANGE,PURPLE] if phase>=3 else [RED,ORANGE]):
            pygame.draw.rect(surface,col,(x-8+i*6,y+18+i*10,6,bh-38-i*16),border_radius=2); pygame.draw.rect(surface,col,(x+bw+2+i*6,y+18+i*10,6,bh-38-i*16),border_radius=2)
    elif boss_id==10:
        halo=pygame.Surface((bw+54,bh+54),pygame.SRCALPHA); pygame.draw.ellipse(halo,(80,240,255,45),(0,8,bw+54,bh+38),3); pygame.draw.ellipse(halo,(255,40,80,35),(12,0,bw+30,bh+54),2); surface.blit(halo,(x-27,y-27)); pygame.draw.circle(surface,(80,240,255),(x+bw//2,y+bh//2),10+int(3*math.sin(t*0.08)),2)

def draw_boss_sprite(surface,x,y,data,anim_t,phase=1):
    bw,bh=data["size"]; bc,ac,ec=data["color"],data["armor"],data["eye"]; ability=data["ability"]; t=anim_t
    boss_name=data.get("name","")
    boss_id=data.get("base_id") or next((bid for bid,b in BOSS_DATA.items() if b["name"]==boss_name),0)
    breath=int(2*math.sin(t*0.055))
    sway=int(3*math.sin(t*0.035+boss_id))
    rage=phase-1
    x+=sway
    y+=breath-rage
    aura=pygame.Surface((bw+42,bh+42),pygame.SRCALPHA)
    aura_alpha=18+rage*12+int(8*math.sin(t*0.08))
    pygame.draw.ellipse(aura,(*ec,max(0,aura_alpha)),(0,6,bw+42,bh+30),2+rage)
    surface.blit(aura,(x-21,y-21))
    if phase>=2:
        for i in range(3+phase):
            px=x+int((i+1)*(bw/(4+phase)))+int(3*math.sin(t*0.11+i))
            py=y+bh-8-int((t*0.7+i*17)%(bh+18))
            spark=pygame.Surface((5,9),pygame.SRCALPHA)
            pygame.draw.ellipse(spark,(*ec,80),(0,0,5,9)); surface.blit(spark,(px,py))
    if ability=="giant_stomp":
        stomp=int(10*abs(math.sin(t*0.06))); arm=int(13*math.sin(t*0.08)); eye_p=int(170+70*math.sin(t*0.12))
        sh=pygame.Surface((bw+34,18),pygame.SRCALPHA); pygame.draw.ellipse(sh,(0,0,0,85),(0,0,bw+34,18)); surface.blit(sh,(x-17,y+bh-8))
        # Huge legs/feet
        for side in [0,1]:
            lx=x+18+side*(bw-44); ly=y+bh-38+(stomp if side==0 else 8-stomp)
            pygame.draw.rect(surface,ac,(lx,ly,26,42),border_radius=6)
            pygame.draw.rect(surface,(50,15,65),(lx-13,ly+36,52,14),border_radius=6)
        # Body, shoulders, head
        pygame.draw.rect(surface,bc,(x+12+sway//2,y+34,bw-24,bh-70),border_radius=12)
        pygame.draw.rect(surface,ac,(x,y+42,bw,18),border_radius=8)
        pygame.draw.rect(surface,(min(255,bc[0]+35),bc[1],min(255,bc[2]+25)),(x+26+sway//2,y+58,bw-52,34),border_radius=8)
        pygame.draw.rect(surface,bc,(x+bw//2-34+sway//2,y+5,68,34),border_radius=10)
        pygame.draw.rect(surface,(eye_p,35,eye_p),(x+bw//2-22,y+17,16,8),border_radius=3)
        pygame.draw.rect(surface,(eye_p,35,eye_p),(x+bw//2+6,y+17,16,8),border_radius=3)
        # Heavy arms/fists
        pygame.draw.rect(surface,ac,(x-17,y+58+arm,24,58),border_radius=9)
        pygame.draw.rect(surface,ac,(x+bw-7,y+58-arm,24,58),border_radius=9)
        pygame.draw.rect(surface,(60,20,75),(x-24,y+108+arm,36,24),border_radius=8)
        pygame.draw.rect(surface,(60,20,75),(x+bw-12,y+108-arm,36,24),border_radius=8)
        if phase>=2:
            for i in range(5):
                pygame.draw.line(surface,(255,90,220),(x+20+i*18,y+30),(x+8+i*20,y+18+int(5*math.sin(t*0.2+i))),2)
        if boss_id==5:
            for i in range(4):
                px=x+18+i*(bw-36)//3; pygame.draw.polygon(surface,(120,75,150),[(px,y+28),(px+8,y+6),(px+16,y+28)])
            pygame.draw.rect(surface,(80,35,100),(x+bw//2-22,y+bh-48,44,12),border_radius=4)
        draw_boss_identity_overlay(surface,x,y,bw,bh,data,t,phase)
        return
    if ability=="code_storm":
        pulse=int(120+80*math.sin(t*0.08)); screen_col=(40,pulse,120)
        sh=pygame.Surface((bw+18,14),pygame.SRCALPHA); pygame.draw.ellipse(sh,(0,0,0,65),(0,0,bw+18,14)); surface.blit(sh,(x-9,y+bh-5))
        for i in range(4):
            gx=x+random.randint(-5,bw+5); gy=y+random.randint(12,bh-18)
            pygame.draw.rect(surface,(80,255,170,),(gx,gy,random.randint(5,14),2))
        pygame.draw.rect(surface,ac,(x,y+18,bw,bh-28),border_radius=8)
        pygame.draw.rect(surface,bc,(x+8,y+26,bw-16,bh-44),border_radius=6)
        pygame.draw.rect(surface,screen_col,(x+17,y+34,bw-34,bh-60),border_radius=4)
        for i,txt in enumerate(["if(G7)","ERR", "while(1)","0xCORE"]):
            yy=y+38+i*10+int(2*math.sin(t*0.1+i))
            render=make_font(9,"hud",True).render(txt,True,(10,30,20))
            surface.blit(render,(x+22,yy))
        pygame.draw.rect(surface,bc,(x+12,y+bh-20,bw-24,10),border_radius=3)
        for i in range(3): pygame.draw.circle(surface,(80,255,170),(x+24+i*16,y+bh-15),3)
        for i in range(6):
            cx=x+random.randint(0,bw); cy=y+random.randint(0,bh)
            pygame.draw.line(surface,(80,255,170),(cx,cy),(cx+random.randint(-8,8),cy+random.randint(-8,8)),1)
        if phase>=2:
            pygame.draw.rect(surface,(80,255,170),(x-4,y+14,bw+8,bh-20),border_radius=9,width=2)
        if boss_id==6:
            for i in range(4):
                yy=y+22+i*13; pygame.draw.rect(surface,(15,230,120),(x-10,yy,8,6),border_radius=2); pygame.draw.rect(surface,(15,230,120),(x+bw+2,yy,8,6),border_radius=2)
            err=make_font(8,"hud",True).render("CORE",True,(40,255,160)); surface.blit(err,(x+bw//2-err.get_width()//2,y+bh-34))
        draw_boss_identity_overlay(surface,x,y,bw,bh,data,t,phase)
        return
    sh=pygame.Surface((bw+18,13),pygame.SRCALPHA); pygame.draw.ellipse(sh,(0,0,0,66),(0,0,bw+18,13)); surface.blit(sh,(x-9,y+bh-7))
    lc=4 if bw>=70 else 2; lw=bw//(lc+1)
    for i in range(lc):
        lx=x+lw*(i+1)-5; ly=y+bh-20; la=int(7*math.sin(t*0.09+i*1.6))
        pygame.draw.rect(surface,ac,(lx,ly+la,10,20),border_radius=3)
        pygame.draw.rect(surface,(bc[0]//2,bc[1]//2,bc[2]//2),(lx-2,ly+la+18,14,5),border_radius=2)
    pygame.draw.rect(surface,bc,(x+sway//2,y+10,bw,bh-30),border_radius=8)
    pygame.draw.rect(surface,ac,(x-3,y+15,bw+6,10),border_radius=4)
    pygame.draw.rect(surface,ac,(x-3,y+bh-45,bw+6,10),border_radius=4)
    hx,hy=x+bw//2-25+sway//2,y-10; pygame.draw.rect(surface,bc,(hx,hy,50,22),border_radius=6)
    ep=int(180+75*math.sin(t*0.1))
    ecol=(min(255,ec[0]),min(255,ec[1]+ep//4),min(255,ec[2]+ep//4)) if ability=="freeze_wave" else(min(255,ep),ec[1]//2,ec[2]//2)
    pygame.draw.rect(surface,(ep//2,ep//4,ep//4),(hx+5,hy+4,14,8),border_radius=3)
    pygame.draw.rect(surface,(ep//2,ep//4,ep//4),(hx+31,hy+4,14,8),border_radius=3)
    pygame.draw.rect(surface,ecol,(hx+8,hy+6,8,4),border_radius=1); pygame.draw.rect(surface,ecol,(hx+34,hy+6,8,4),border_radius=1)
    pygame.draw.line(surface,ac,(hx+10,hy),(hx+5,hy-14),2); pygame.draw.line(surface,ac,(hx+40,hy),(hx+45,hy-14),2)
    gr=int(3+2*math.sin(t*0.08)); pygame.draw.circle(surface,ec,(hx+5,hy-14),gr); pygame.draw.circle(surface,ec,(hx+45,hy-14),gr)
    # Identity layer: every boss keeps a distinct silhouette even when ability is randomized.
    if boss_id==1:  # SCOUT ALPHA - radar scout/gatekeeper
        sweep=math.sin(t*0.08)
        pygame.draw.circle(surface,(25,45,80),(x+bw//2,y+bh//2),18,1)
        pygame.draw.line(surface,CYAN,(x+bw//2,y+bh//2),(x+bw//2+int(20*sweep),y+bh//2-14),2)
        for ox in[-16,0,16]: pygame.draw.circle(surface,ec,(x+bw//2+ox,y+18),4)
    elif boss_id==2:  # TANK CRUSHER - heavy treads and front ram
        pygame.draw.rect(surface,(45,55,35),(x-6,y+bh-26,bw+12,18),border_radius=5)
        for i in range(6): pygame.draw.circle(surface,(95,110,70),(x+4+i*(bw+2)//6,y+bh-17),5)
        pygame.draw.polygon(surface,(120,95,55),[(x+bw//2-18,y+18),(x+bw//2+18,y+18),(x+bw//2,y+2)])
    elif boss_id==3:  # SENTRY MK-I - turret experiment
        pygame.draw.rect(surface,(110,35,35),(x+bw//2-8,y-20,16,18),border_radius=4)
        for ox in[-22,-11,0,11,22]: pygame.draw.line(surface,RED,(x+bw//2,y+10),(x+bw//2+ox,y-16),2)
        pygame.draw.circle(surface,(255,80,80),(x+bw//2,y-14),5)
    elif boss_id==4:  # AERO HUNTER - wings/jet predator
        flap=int(7*math.sin(t*0.12))
        pygame.draw.polygon(surface,(60,80,170),[(x+4,y+30),(x-42,y+18+flap),(x-8,y+58)])
        pygame.draw.polygon(surface,(60,80,170),[(x+bw-4,y+30),(x+bw+42,y+18-flap),(x+bw+8,y+58)])
        for ox in[-18,18]: pygame.draw.polygon(surface,ORANGE,[(x+bw//2+ox,y+bh-10),(x+bw//2+ox-5,y+bh+8),(x+bw//2+ox+5,y+bh+8)])
    elif boss_id==7:  # CRYO TITAN - ice crown and frost armor
        for i in range(5):
            px=x+8+i*(bw-16)//4; pygame.draw.polygon(surface,(185,240,255),[(px,y+8),(px+7,y-14-random.randint(0,3)),(px+14,y+8)])
        pygame.draw.arc(surface,(170,235,255),(x+5,y+18,bw-10,bh-25),0,math.pi,2)
    elif boss_id==8:  # STORM BRINGER - tesla coils
        for side in[-1,1]:
            coil_x=x+bw//2+side*(bw//2+9)
            pygame.draw.line(surface,YELLOW,(coil_x,y+10),(coil_x+side*14,y+38),3)
            pygame.draw.line(surface,YELLOW,(coil_x+side*14,y+38),(coil_x,y+66),3)
            pygame.draw.circle(surface,(255,245,120),(coil_x,y+9),5)
    elif boss_id==9:  # TITAN MK-III - server guardian plates
        for i,col in enumerate([RED,ORANGE,PURPLE] if phase>=3 else [RED,ORANGE]):
            pygame.draw.rect(surface,col,(x-8+i*6,y+18+i*10,6,bh-38-i*16),border_radius=2)
            pygame.draw.rect(surface,col,(x+bw+2+i*6,y+18+i*10,6,bh-38-i*16),border_radius=2)
        pygame.draw.rect(surface,(30,30,35),(x+12,y+bh//2,bw-24,12),border_radius=3)
    elif boss_id==10:  # CORE-X - central AI core/halo
        halo=pygame.Surface((bw+54,bh+54),pygame.SRCALPHA)
        pygame.draw.ellipse(halo,(80,240,255,45),(0,8,bw+54,bh+38),3)
        pygame.draw.ellipse(halo,(255,40,80,35),(12,0,bw+30,bh+54),2)
        surface.blit(halo,(x-27,y-27))
        pygame.draw.circle(surface,(80,240,255),(x+bw//2,y+bh//2),10+int(3*math.sin(t*0.08)),2)
    # Per-boss silhouette details so every boss reads differently.
    if ability=="triple_shot":
        for ox in[-18,0,18]:
            pygame.draw.rect(surface,ec,(x+bw//2+ox-3,y+bh//2-6,6,22),border_radius=2)
            pygame.draw.circle(surface,WHITE,(x+bw//2+ox,y+bh//2-8),3)
    elif ability=="ground_slam":
        for i in range(5): pygame.draw.rect(surface,(45,45,35),(x+8+i*(bw-16)//5,y+bh-23,(bw-20)//7,8),border_radius=2)
        pygame.draw.rect(surface,(120,90,40),(x+8,y+bh-34,bw-16,8),border_radius=3)
    elif ability=="burst_fire":
        for ox in[-18,-9,0,9,18]: pygame.draw.line(surface,ac,(x+bw//2,y+18),(x+bw//2+ox,y-8),3)
        pygame.draw.circle(surface,RED,(x+bw//2,y+18),7)
    elif ability=="dive_bomb":
        flap=int(8*math.sin(t*0.12))
        pygame.draw.polygon(surface,ac,[(x,y+35),(x-34,y+20+flap),(x-12,y+58)])
        pygame.draw.polygon(surface,ac,[(x+bw,y+35),(x+bw+34,y+20-flap),(x+bw+12,y+58)])
    elif ability=="freeze_wave":
        for i in range(5):
            px=x+8+i*(bw-16)//4; pygame.draw.polygon(surface,(170,235,255),[(px,y+8),(px+6,y-8),(px+12,y+8)])
    elif ability=="lightning":
        for side in[-1,1]:
            sx=x+bw//2+side*(bw//2+8); pygame.draw.line(surface,YELLOW,(sx,y+18),(sx+side*10,y+36),3); pygame.draw.line(surface,YELLOW,(sx+side*10,y+36),(sx,y+54),3)
    if ability in("multi_phase","ultimate"):
        for fi in range(4):
            fa=pygame.Surface((bw+fi*24,bh+fi*24),pygame.SRCALPHA)
            col2=[(255,50,50),(255,150,50),(200,50,255),(50,200,255)][fi]
            pygame.draw.ellipse(fa,(*col2,int(20+10*math.sin(t*0.05+fi))),(0,0,bw+fi*24,bh+fi*24)); surface.blit(fa,(x-fi*12,y+10-fi*12))
    if phase>=2:
        for fi in range(4):
            fx=x+8+fi*(bw//4); fy=y+8+int(5*math.sin(t*0.15+fi))
            fl=pygame.Surface((10,14),pygame.SRCALPHA)
            pygame.draw.ellipse(fl,(255,120,30,int(160*abs(math.sin(t*0.1+fi)))),(0,0,10,14)); surface.blit(fl,(fx,fy))

# ------------------------------------------------------------------------------------
# BOSS CLASS
# ------------------------------------------------------------------------------------
class Boss:
    def __init__(self,level_num,wx,boss_data=None,difficulty_level=None):
        lvl=min(level_num,10); d=dict(boss_data) if boss_data else dict(BOSS_DATA[lvl])
        self.data=d; self.level=lvl; self.name=d["name"]; self.ability=d["ability"]
        bw,bh=d["size"]; self.bw=bw; self.bh=bh
        diff=difficulty_level if difficulty_level is not None else level_num
        bonus=max(0,diff-lvl)*15+max(0,diff-1)*2
        self.max_hp_p1=d["hp"]+bonus; self.max_hp_p2=d["hp"]//2+bonus; self.max_hp_p3=max(8,d["hp"]//3)+bonus
        self.hp=self.max_hp_p1; self.max_hp=self.max_hp_p1
        self.wx=float(wx); self.wy=float(SCREEN_H-bh-80); self.vx=d["speed"]*(1+diff*0.05)
        self.phase=1; self.alive=True; self.anim_t=0; self.invincible=0
        self.shoot_timer=80; self.ability_timer=random.randint(150,240)
        self.stomp_active=False; self.stomp_wx=wx; self.stomp_frames=0
        self.spawn_timer=300; self.freeze_active=False; self.freeze_timer=0
        self.teleport_cd=0; self.lightning_bolts=[]; self.laser_active=False; self.laser_timer=0
        self.code_fragments=[]; self.stomp_target_x=wx; self.warning_type=None; self.warning_target=None; self.warning_timer=0
        self.phase2_started=False; self.phase3_started=False
        self.fly_y=float(SCREEN_H-bh-80); self.fly_dir=-1
        self.arena_left=float(wx-280); self.arena_right=float(wx+280)
        self.dmg_flash=0

    def update(self,player,e_bullets,enemies_list,platforms,cam):
        self.anim_t+=1
        if self.invincible>0: self.invincible-=1
        if self.dmg_flash>self.hp: self.dmg_flash=max(self.hp,self.dmg_flash-2)
        self._update_boss_phase()
        if self.warning_timer>0: self.warning_timer-=1
        else: self.warning_type=None; self.warning_target=None
        if self.ability=="dive_bomb":
            self.fly_y+=self.fly_dir*1.5
            if self.fly_y<60 or self.fly_y>SCREEN_H-self.bh-60: self.fly_dir*=-1
            self.wy=self.fly_y
        else: self.wy=float(SCREEN_H-self.bh-80)
        if self.ability in("giant_stomp","ground_slam"):
            dx=(player.wx+self.bw//4)-self.wx
            lim=1.8 if self.ability=="giant_stomp" else 1.35
            self.vx=max(-lim,min(lim,dx*0.012))
        self.wx+=self.vx*(1.45 if self.phase>=3 else 1.3 if self.phase==2 else 1.0)
        if self.wx<self.arena_left or self.wx>self.arena_right: self.vx*=-1
        if self.freeze_active:
            self.freeze_timer-=1
            if self.freeze_timer<=0: self.freeze_active=False
        self.lightning_bolts=[(b[0],b[1],b[2]-1) for b in self.lightning_bolts if b[2]>0]
        self.code_fragments=[(x,y+vy,vy,txt,life-1) for x,y,vy,txt,life in self.code_fragments if life>0 and y<SCREEN_H+40]
        if self.laser_active:
            self.laser_timer-=1
            if self.laser_timer<=0: self.laser_active=False
        self.shoot_timer-=1
        cd=max(20,58-self.level*4) if self.phase>=3 else max(25,70-self.level*4) if self.phase==2 else max(35,90-self.level*4)
        if self.shoot_timer<=0: self._shoot_normal(player,e_bullets); self.shoot_timer=cd
        self.ability_timer-=1
        if self.ability_timer<=0:
            self._use_ability(player,e_bullets,enemies_list); self.ability_timer=max(100,220-self.level*10)
        if self.phase>=2:
            self.spawn_timer-=1
            if self.spawn_timer<=0:
                enemies_list.append(ScoutBot(self.wx+random.choice([-200,200]),520,1.0+self.level*0.1,100))
                self.spawn_timer=max(180,300-self.level*15)

    def _update_boss_phase(self):
        if self.ability in("multi_phase","ultimate"):
            if self.phase==1 and self.hp<=0:
                self.phase=2; self.hp=self.max_hp_p2; self.max_hp=self.max_hp_p2; self.vx*=1.35; self.shoot_timer=18; self.ability_timer=70
                trigger_boss_shake("strong",22); sounds.play("boss_phase2"); self.warning_type="rect"; self.warning_target=(0,0,SCREEN_W,SCREEN_H); self.warning_timer=34
            elif self.phase==2 and self.hp<=0:
                self.phase=3; self.hp=self.max_hp_p3; self.max_hp=self.max_hp_p3; self.vx*=1.25; self.shoot_timer=12; self.ability_timer=45
                trigger_boss_shake("extreme" if self.ability=="ultimate" else "strong",28); sounds.play("boss_phase2"); self.warning_type="rect"; self.warning_target=(0,0,SCREEN_W,SCREEN_H); self.warning_timer=42
        elif self.phase==1 and self.hp<=0:
            self.phase=2; self.hp=self.max_hp_p2; self.max_hp=self.max_hp_p2
            self.vx*=1.4; self.shoot_timer=20; trigger_boss_shake(self.data.get("shake_profile","medium"),20); sounds.play("boss_phase2")

    def _shoot_normal(self,player,e_bullets):
        cx=self.wx+self.bw//2; cy=self.wy+self.bh//2
        dx=player.wx-cx; dy=player.wy-cy; dist=math.hypot(dx,dy) or 1; spd=2.8+self.level*0.1
        if self.ability=="triple_shot":
            for ang in[-25,0,25]:
                rad=math.atan2(dy,dx)+math.radians(ang); e_bullets.append(self._mb(cx,cy,math.cos(rad)*spd,math.sin(rad)*spd))
            trigger_boss_shake("light",5); spawn_boss_particles(self.ability,cx,cy,4)
        elif self.ability=="dual_cannon":
            for ox in[-self.bw//2-5,self.bw//2+5]: e_bullets.append(self._mb(cx+ox,cy,dx/dist*spd,dy/dist*spd))
        elif self.ability=="code_storm":
            for label,off in [("if",-22),("bug",0),("404",22)]:
                b=self._mb(cx+off,cy,(dx+off*3)/dist*(spd*0.9),dy/dist*(spd*0.9),(80,255,170)); b.label=label; e_bullets.append(b)
        elif self.ability=="burst_fire":
            for ang in([-40,-20,0,20,40] if self.phase>=2 else[-25,0,25]):
                rad=math.atan2(dy,dx)+math.radians(ang); e_bullets.append(self._mb(cx,cy,math.cos(rad)*spd,math.sin(rad)*spd))
            if self.phase>=2: trigger_boss_shake("medium",8)
        elif self.ability=="lightning":
            for ang in([-10,0,10] if self.phase>=2 else[0]):
                rad=math.atan2(dy,dx)+math.radians(ang); b=self._mb(cx,cy,math.cos(rad)*spd,math.sin(rad)*spd,YELLOW); b.electric=True; e_bullets.append(b)
        else:
            for ang in([-15,0,15] if self.phase==2 else[0]):
                rad=math.atan2(dy,dx)+math.radians(ang); e_bullets.append(self._mb(cx,cy,math.cos(rad)*spd,math.sin(rad)*spd))

    def _use_ability(self,player,e_bullets,enemies_list):
        cx=self.wx+self.bw//2; cy=self.wy+self.bh//2; spd=3.0+self.level*0.1
        if self.ability=="ground_slam":
            self.stomp_active=True; self.stomp_wx=cx; self.stomp_frames=50; self.warning_type="rect"; self.warning_target=(0,SCREEN_H-92,SCREEN_W,35); self.warning_timer=30
            for dir2 in[-1,1]:
                for i in range(4 if self.phase>=2 else 3): e_bullets.append(self._mb(cx,SCREEN_H-112,dir2*(2.4+i*0.35),-0.25,ORANGE))
            trigger_boss_shake("heavy",18); sounds.play("stomp"); spawn_boss_particles(self.ability,cx,SCREEN_H-115,18)
        elif self.ability=="dive_bomb":
            self.warning_type="circle"; self.warning_target=(player.wx+player.WIDTH//2,player.wy+player.HEIGHT//2,55); self.warning_timer=34
            for _ in range(5 if self.phase==1 else 8):
                b=self._mb(player.wx+random.randint(-120,120),player.wy-320,random.uniform(-0.4,0.4),4.0+0.25*self.phase,ORANGE); b.bomb=True; e_bullets.append(b)
            trigger_boss_shake("medium",8); spawn_boss_particles(self.ability,cx,cy,12)
        elif self.ability=="giant_stomp":
            self.stomp_active=True; self.stomp_wx=player.wx+player.WIDTH//2; self.stomp_target_x=self.stomp_wx; self.stomp_frames=62
            for ang in[180,200,220,320,340,360]:
                rad=math.radians(ang); e_bullets.append(self._mb(self.stomp_wx,self.wy+self.bh-18,math.cos(rad)*3.0,math.sin(rad)*2.2,ORANGE))
            trigger_boss_shake("very_heavy",24); sounds.play("stomp"); spawn_boss_particles(self.ability,self.stomp_wx,self.wy+self.bh,26)
        elif self.ability=="code_storm":
            labels=["while", "NULL", "BUG", "404", "</>", "ERR", "0xG7"]
            self.warning_type="rect"; self.warning_target=(0,0,SCREEN_W,SCREEN_H); self.warning_timer=20
            for i in range(12 if self.phase>=3 else 9 if self.phase==2 else 6):
                x=player.wx+random.randint(-180,180); txt=random.choice(labels)
                self.code_fragments.append((x,random.randint(-80,20),random.uniform(2.2,4.0),txt,150))
                b=self._mb(x,0,random.uniform(-0.6,0.6),random.uniform(2.4,3.8),(80,255,170)); b.label=txt; e_bullets.append(b)
            trigger_boss_shake("medium",10); spawn_boss_particles(self.ability,cx,cy,14)
        elif self.ability=="teleport":
            self.teleport_cd=30; self.wx=float(self.arena_left+random.randint(50,500))
            for ang in range(0,360,45):
                rad=math.radians(ang); e_bullets.append(self._mb(cx,cy,math.cos(rad)*spd,math.sin(rad)*spd))
        elif self.ability=="freeze_wave":
            self.freeze_active=True; self.freeze_timer=120; self.warning_type="circle"; self.warning_target=(cx,cy,130); self.warning_timer=34
            for ang in range(0,360,15 if self.phase>=2 else 20):
                rad=math.radians(ang); b=self._mb(cx,cy,math.cos(rad)*2.0,math.sin(rad)*2.0)
                b.color=(100,200,255); b.cryo=True; e_bullets.append(b)
            trigger_boss_shake("medium",14); spawn_boss_particles(self.ability,cx,cy,22)
        elif self.ability=="lightning":
            for _ in range(8 if self.phase>=2 else 6):
                lx=cx+random.randint(-300,300); self.lightning_bolts.append((lx,0,50)); b=self._mb(lx,0,0,5.0,YELLOW); b.electric=True; e_bullets.append(b)
            self.warning_type="line"; self.warning_target=player.wx+player.WIDTH//2; self.warning_timer=28
            trigger_boss_shake("strong",18); spawn_boss_particles(self.ability,cx,cy,16)
        elif self.ability=="multi_phase":
            step=12 if self.phase>=3 else 15; self.warning_type="circle"; self.warning_target=(cx,cy,150); self.warning_timer=26
            for ang in range(0,360,step):
                rad=math.radians(ang); e_bullets.append(self._mb(cx,cy,math.cos(rad)*spd*0.8,math.sin(rad)*spd*0.8,random.choice([RED,ORANGE,PURPLE,CYAN])))
            if self.phase>=2:
                for dir2 in[-1,1]: e_bullets.append(self._mb(cx,SCREEN_H-112,dir2*3.1,-0.2,ORANGE))
            trigger_boss_shake("strong",16); spawn_boss_particles(self.ability,cx,cy,24)
        elif self.ability=="ultimate":
            self.laser_active=True; self.laser_timer=80; self.warning_type="rect"; self.warning_target=(0,int(self.wy+self.bh//3)-16,SCREEN_W,32); self.warning_timer=34
            for ang in range(0,360,8 if self.phase>=3 else 10):
                rad=math.radians(ang); e_bullets.append(self._mb(cx,cy,math.cos(rad)*spd,math.sin(rad)*spd,random.choice([RED,CYAN,ORANGE,PURPLE])))
            if self.phase>=2:
                for lx in [player.wx-90,player.wx,player.wx+90]: self.lightning_bolts.append((lx,0,45)); e_bullets.append(self._mb(lx,0,0,5.4,YELLOW))
            trigger_boss_shake("extreme",30); spawn_boss_particles(self.ability,cx,cy,34)

    def _mb(self,x,y,vx,vy,color=RED): return WorldBullet(x,y,vx,vy,color)

    def take_hit(self,dmg=1):
        if self.invincible>0: return False
        self.dmg_flash=self.hp
        self.hp-=dmg; self.invincible=10; spawn_boss_particles(self.ability,self.wx+self.bw//2,self.wy+self.bh//2,4)
        final_phase=3 if self.ability in("multi_phase","ultimate") else 2
        return self.hp<=0 and self.phase>=final_phase

    def draw(self,surface,cam):
        sx,sy=cam.apply(self.wx,self.wy)
        if sx<-self.bw-50 or sx>SCREEN_W+50: return
        if self.warning_timer>0 and self.warning_type and self.warning_target is not None:
            if self.warning_type=="circle":
                wx,wy,r=self.warning_target; ssx,ssy=cam.apply(wx,wy); draw_boss_warning(surface,"circle",(ssx,ssy,r),self.data.get("eye",RED),70+int(40*math.sin(self.anim_t*0.4)),"BOSS ATTACK")
            elif self.warning_type=="line":
                ssx=cam.apply(self.warning_target,0)[0]; draw_boss_warning(surface,"line",ssx,YELLOW,95,"LIGHTNING LOCK")
            else:
                draw_boss_warning(surface,"rect",self.warning_target,RED,60+int(35*math.sin(self.anim_t*0.35)),"WARNING")
        if self.stomp_active:
            self.stomp_frames=max(0,self.stomp_frames-1); sw=int((50-self.stomp_frames)*5); ssx=cam.apply(self.stomp_wx,0)[0]
            if self.ability=="giant_stomp" and self.stomp_frames>34:
                tx=int(cam.apply(self.stomp_target_x,0)[0]); warn=pygame.Surface((120,SCREEN_H),pygame.SRCALPHA)
                warn.fill((255,60,120,35+int(25*math.sin(self.anim_t*0.3))))
                surface.blit(warn,(tx-60,0)); pygame.draw.line(surface,(255,80,150),(tx,0),(tx,SCREEN_H),2)
            if sw>0:
                wave=pygame.Surface((sw*2,24),pygame.SRCALPHA); pygame.draw.ellipse(wave,(255,150,50,max(0,self.stomp_frames*4)),(0,0,sw*2,24)); surface.blit(wave,(ssx-sw,int(sy)+self.bh-20))
        for bwx,_,life in self.lightning_bolts:
            if life>0:
                lsx=int(cam.apply(bwx,0)[0]); pygame.draw.line(surface,(200,200,255),(lsx,0),(lsx+random.randint(-5,5),SCREEN_H),2)
        if self.laser_active:
            ly=int(sy+self.bh//3); ls=pygame.Surface((SCREEN_W,8),pygame.SRCALPHA)
            pygame.draw.rect(ls,(100,240,255,180),(0,0,SCREEN_W,8)); surface.blit(ls,(0,ly))
            warn=make_font(12,"hud",True).render("WARNING!",True,RED)
            surface.blit(warn,(SCREEN_W//2-warn.get_width()//2,max(8,ly-24)))
        if self.stomp_active:
            wx=int(cam.apply(self.stomp_wx,0)[0]); pulse=int(120+90*math.sin(self.anim_t*0.35))
            pygame.draw.rect(surface,(pulse,25,25),(max(0,wx-80),SCREEN_H-72,160,14),border_radius=7,width=2)
            warn=make_font(11,"hud",True).render("WARNING!",True,(255,pulse,80))
            surface.blit(warn,(max(0,min(SCREEN_W-warn.get_width(),wx-warn.get_width()//2)),SCREEN_H-94))
        if self.lightning_bolts:
            warn=make_font(11,"hud",True).render("LIGHTNING WARNING",True,YELLOW)
            surface.blit(warn,(SCREEN_W//2-warn.get_width()//2,96))
        for cx,cy,vy,txt,life in self.code_fragments:
            csx,csy=cam.apply(cx,cy)
            if -80<csx<SCREEN_W+80:
                alpha=max(40,min(220,life*2)); f=make_font(10,"hud",True); img=f.render(txt,True,(80,255,170)); img.set_alpha(alpha)
                surface.blit(img,(int(csx),int(csy)))
        if self.teleport_cd>0:
            self.teleport_cd-=1; fl=pygame.Surface((self.bw,self.bh),pygame.SRCALPHA)
            pygame.draw.rect(fl,(*PURPLE,min(200,self.teleport_cd*8)),(0,0,self.bw,self.bh),border_radius=6); surface.blit(fl,(int(sx),int(sy)))
        draw_boss_sprite(surface,int(sx),int(sy),self.data,self.anim_t,self.phase)
        if self.invincible>0 and self.invincible%3==0:
            fl=pygame.Surface((self.bw,self.bh),pygame.SRCALPHA); pygame.draw.rect(fl,(255,255,255,80),(0,0,self.bw,self.bh),border_radius=6); surface.blit(fl,(int(sx),int(sy)))

    def draw_hud(self,surface,font_md,font_sm,font_xs):
        bw2=380; bh2=52; bx=SCREEN_W//2-bw2//2; by=SCREEN_H-74
        col=NEON_PURPLE if self.phase>=3 else NEON_ORANGE if self.phase==2 else NEON_RED
        panel=pygame.Rect(bx,by,bw2,bh2)
        draw_panel(surface,panel,col,(18,4,10,200),radius=PANEL_RADIUS)
        draw_fit_text(surface,"BOSS",font_xs,pygame.Rect(panel.x+16,panel.y+5,40,10),col,shadow=False)
        draw_fit_text(surface,self.name,font_xs,pygame.Rect(panel.x+56,panel.y+5,200,10),TEXT_MAIN,shadow=False)
        draw_fit_text(surface,tr('boss.phase',phase=self.phase),font_xs,pygame.Rect(panel.right-72,panel.y+5,58,10),col,shadow=False)
        bar=pygame.Rect(panel.x+16,panel.y+22,panel.w-32,10)
        bar_bg=pygame.Surface((bar.w,bar.h),pygame.SRCALPHA)
        pygame.draw.rect(bar_bg,(40,6,10,200),(0,0,bar.w,bar.h),border_radius=5)
        surface.blit(bar_bg,bar.topleft)
        fill=int(bar.w*max(0,self.hp)/max(1,self.max_hp))
        if fill>0:
            t=pygame.time.get_ticks()
            pulse=0.85+0.15*math.sin(t*0.008)
            bar_fill=pygame.Surface((fill,bar.h),pygame.SRCALPHA)
            pulse_col=(min(255,int(col[0]*pulse)),min(255,int(col[1]*pulse)),min(255,int(col[2]*pulse)))
            pygame.draw.rect(bar_fill,pulse_col,(0,0,fill,bar.h),border_radius=5)
            surface.blit(bar_fill,bar.topleft)
            highlight=pygame.Surface((max(4,fill-8),2),pygame.SRCALPHA)
            pygame.draw.line(highlight,(255,255,255,100),(0,0),(max(4,fill-8),0),1)
            surface.blit(highlight,(bar.x+4,bar.y+2))
            glow_bar=pygame.Surface((fill+10,bar.h+10),pygame.SRCALPHA)
            pygame.draw.rect(glow_bar,(*col,35),(5,5,fill,bar.h),border_radius=7)
            surface.blit(glow_bar,(bar.x-5,bar.y-5))
        pygame.draw.rect(surface,(*col,140),bar,border_radius=5,width=1)
        hp_n=font_xs.render(f"{max(0,self.hp)}/{self.max_hp}",True,WHITE); surface.blit(hp_n,(bar.centerx-hp_n.get_width()//2,bar.y-1))

    def get_rect(self): return pygame.Rect(self.wx+5,self.wy,self.bw-10,self.bh-15)

# ------------------------------------------------------------------------------------
# WORLD BULLET
# ------------------------------------------------------------------------------------
class WorldBullet:
    def __init__(self,wx,wy,vx,vy,color=RED):
        self.wx,self.wy=float(wx),float(wy); self.vx,self.vy=vx,vy; self.alive=True; self.color=color; self.damage=1; self.cryo=False; self.label=""; self.pierce=0; self.modded=False
    def update(self):
        self.wx+=self.vx; self.wy+=self.vy
        if not(-100<self.wx<WORLD_W+100 and -100<self.wy<SCREEN_H+100): self.alive=False
    def draw(self,surface,cam):
        sx,sy=cam.apply(self.wx,self.wy)
        if not(-10<sx<SCREEN_W+10): return
        if self.label:
            txt=make_font(11,"hud",True).render(self.label,True,self.color)
            surface.blit(txt,(int(sx)-txt.get_width()//2,int(sy)-txt.get_height()//2))
            pygame.draw.rect(surface,self.color,(int(sx)-txt.get_width()//2-2,int(sy)+txt.get_height()//2,txt.get_width()+4,2))
            return
        glow=pygame.Surface((12,12),pygame.SRCALPHA); pygame.draw.circle(glow,(*self.color,60),(6,6),6); surface.blit(glow,(int(sx)-6,int(sy)-6))
        pygame.draw.circle(surface,self.color,(int(sx),int(sy)),4); pygame.draw.circle(surface,WHITE,(int(sx),int(sy)),2)
    def get_rect(self): return pygame.Rect(self.wx-14,self.wy-7,28,14) if self.label else pygame.Rect(self.wx-4,self.wy-4,8,8)

# ------------------------------------------------------------------------------------
# SCOUT BOT - ANIMATED
# ------------------------------------------------------------------------------------
class ScoutBot:
    WIDTH=28; HEIGHT=28; DETECT=250; JUMP_POWER=-12
    def __init__(self,wx,wy,speed_mult=1.0,shoot_cd=150,elite_type=None):
        self.wx,self.wy=float(wx),float(wy); self.vx=self.vy=0.0; self.elite_type=elite_type
        self.max_hp=1; self.score_value=100; self.coin_reward=1
        if elite_type=="red": self.max_hp=3; self.score_value=220; self.coin_reward=3
        elif elite_type=="fast": speed_mult*=1.55; self.max_hp=2; self.score_value=180; self.coin_reward=2
        elif elite_type=="shield": self.max_hp=2; self.score_value=200; self.coin_reward=2
        elif elite_type=="bomber": self.max_hp=2; self.score_value=210; self.coin_reward=3
        elif elite_type=="sniper": self.max_hp=2; self.score_value=240; self.coin_reward=3; shoot_cd=max(70,shoot_cd-45)
        elif elite_type=="drone": speed_mult*=1.25; self.max_hp=2; self.score_value=230; self.coin_reward=3
        elif elite_type in("tunnel_guardian","elite_drone","reactor_sentinel"):
            # Mini-bosses: reuse stable ScoutBot systems with higher HP and unique attack flavor.
            mini_rank=max(1,int(speed_mult))
            self.max_hp=8+min(10,mini_rank); self.score_value=650; self.coin_reward=8; shoot_cd=max(55,shoot_cd-35); speed_mult*=1.1
        self.hp=self.max_hp
        self.speed=1.6*speed_mult; self.shoot_cd=shoot_cd;
        start_cd = min(60, shoot_cd)
        self.shoot_timer = random.randint(start_cd, shoot_cd)
        self.alive=True; self.state="patrol"; self.patrol_dir=1; self.patrol_timer=0
        self.on_ground=False; self.speed_mult=speed_mult; self.jump_timer=0; self.jump_cd=40
        self.walk_t=0.0  # animasi jalan
        self.float_origin_y=float(wy-random.randint(90,150)) if elite_type=="drone" else float(wy)

    def _find_plat_above(self, platforms):
        best = None
        bd = float("inf")

        for p in platforms:
            if p.top < self.wy - 20:
                dx = abs((p.left + p.right)//2 - (self.wx + self.WIDTH//2))
                dy = self.wy - p.top

                if dx < p.width*0.8 and dy < 200 and dy < bd:
                    bd = dy
                    best = p

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
        if self.elite_type in("drone","elite_drone"):
            self.state="chase" if dist<360 else "patrol"
            self.vx=(self.speed*0.9 if dx>0 else -self.speed*0.9) if self.state=="chase" else self.patrol_dir*1.1
            self.wx+=self.vx; self.wy=self.float_origin_y+math.sin(pygame.time.get_ticks()*0.003+self.wx*0.01)*24
            self.wx=max(0,min(WORLD_W-self.WIDTH,self.wx))
            self.patrol_timer+=1
            if self.patrol_timer>130: self.patrol_dir*=-1; self.patrol_timer=0
            self.shoot_timer-=1
            if self.state=="chase" and self.shoot_timer<=0:
                d2=dist or 1; b=WorldBullet(self.wx+self.WIDTH//2,self.wy+self.HEIGHT//2,dx/d2*2.8,dy/d2*2.8,YELLOW); bullets.append(b)
                if self.elite_type=="elite_drone":
                    for ang in(-18,18):
                        rad=math.atan2(dy,dx)+math.radians(ang); bullets.append(WorldBullet(self.wx+self.WIDTH//2,self.wy+self.HEIGHT//2,math.cos(rad)*2.6,math.sin(rad)*2.6,CYAN))
                self.shoot_timer=self.shoot_cd
            self.walk_t+=0.25; return
        if self.elite_type in("tunnel_guardian","reactor_sentinel") and dist<330 and self.shoot_timer<=0:
            for ang in([-22,0,22] if self.elite_type=="reactor_sentinel" else [-12,12]):
                rad=math.atan2(dy,dx)+math.radians(ang); bullets.append(WorldBullet(self.wx+self.WIDTH//2,self.wy+self.HEIGHT//2,math.cos(rad)*3.0,math.sin(rad)*3.0,ORANGE if self.elite_type=="reactor_sentinel" else RED))
            self.shoot_timer=self.shoot_cd
        if self.elite_type=="bomber" and dist<42 and player.invincible==0:
            self.alive=False; spawn_pixels(self.wx,self.wy,ORANGE,24); player.take_damage(1); return
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
                d2=dist or 1; spd=3.6 if self.elite_type=="sniper" else 2.5; col=PURPLE if self.elite_type=="sniper" else RED
                b=WorldBullet(self.wx+self.WIDTH//2,self.wy+self.HEIGHT//2,dx/d2*spd,dy/d2*spd,col)
                if self.elite_type=="sniper": b.label="!"
                bullets.append(b); self.shoot_timer=self.shoot_cd
        self.vy+=0.6
        if self.vy>18: self.vy=18
        self.wx+=self.vx; self.wy+=self.vy; self.wx=max(0,min(WORLD_W-self.WIDTH,self.wx))
        self.on_ground=False
        er=pygame.Rect(self.wx,self.wy,self.WIDTH,self.HEIGHT)
        for plat in platforms:
            if er.colliderect(plat) and self.vy>=0:
                if self.wy+self.HEIGHT-self.vy<=plat.top+8: self.wy=plat.top-self.HEIGHT; self.vy=0; self.on_ground=True
        if self.wy>SCREEN_H+50: self.alive=False
        # Update walk timer
        if abs(self.vx)>0.1 and self.on_ground: self.walk_t+=0.35

    def draw(self,surface,cam):
        sx,sy=cam.apply(self.wx,self.wy)
        if not(-30<sx<SCREEN_W+30): return
        elite_cols={"red":RED,"fast":ORANGE,"shield":PURPLE,"bomber":YELLOW,"sniper":(180,80,255),"drone":(90,230,255)}
        col=elite_cols.get(self.elite_type,(55,138,221) if self.speed_mult<1.5 else(221,100,55))
        ix,iy=int(sx),int(sy); t2=pygame.time.get_ticks()

        ls=int(4*math.sin(self.walk_t)) if abs(self.vx)>0.1 else 0
        bob=int(1.2*math.sin(self.walk_t)) if abs(self.vx)>0.1 else 0
        arm_s=-ls//2
        lean=2 if(self.state=="chase" and self.vx>0) else(-2 if self.state=="chase" else 0)

        # Chase glow
        if self.state=="chase":
            glow=pygame.Surface((36,36),pygame.SRCALPHA)
            ga=int(18+12*math.sin(t2*0.012))
            pygame.draw.circle(glow,(255,60,60,ga),(18,18),18); surface.blit(glow,(ix-4,iy-4))

        # Legs
        if self.elite_type=="drone":
            pygame.draw.ellipse(surface,(255,150,50,120),(ix+7,iy+25+bob,14,7))
        else:
            pygame.draw.rect(surface,(24,90,160),(ix+7,iy+21+bob+ls,5,7),border_radius=2)
            pygame.draw.rect(surface,(24,90,160),(ix+16,iy+21+bob-ls,5,7),border_radius=2)
            pygame.draw.rect(surface,(15,60,110),(ix+6,iy+26+bob+ls,7,2),border_radius=1)
            pygame.draw.rect(surface,(15,60,110),(ix+15,iy+26+bob-ls,7,2),border_radius=1)

        # Body
        pygame.draw.rect(surface,col,(ix+4+lean//2,iy+6+bob,20,16),border_radius=3)
        pygame.draw.rect(surface,(col[0]//2,col[1]//2,col[2]//2),(ix+6,iy+8+bob,16,2))
        pygame.draw.rect(surface,(col[0]//2,col[1]//2,col[2]//2),(ix+6,iy+14+bob,16,2))

        # Arms
        pygame.draw.rect(surface,(24,90,160),(ix,iy+8+bob+arm_s,6,8),border_radius=2)
        pygame.draw.rect(surface,(24,90,160),(ix+22,iy+8+bob-arm_s,6,8),border_radius=2)

        # Head visor
        pygame.draw.rect(surface,(24,90,160),(ix+7,iy+10+bob,14,8),border_radius=2)
        ep=int(150+100*math.sin(t2*0.01)) if self.state=="chase" else 140
        eye_col=(ep,30,30) if self.state=="chase" else RED
        pygame.draw.rect(surface,(24,90,160),(ix+7,iy+10+bob,5,4),border_radius=1)
        pygame.draw.rect(surface,(24,90,160),(ix+16,iy+10+bob,5,4),border_radius=1)
        pygame.draw.circle(surface,eye_col,(ix+9,iy+12+bob),2)
        pygame.draw.circle(surface,eye_col,(ix+18,iy+12+bob),2)
        # Scanning line chase
        if self.state=="chase" and int(t2*0.003)%4<2:
            scan=pygame.Surface((14,2),pygame.SRCALPHA); scan.fill((255,200,200,120)); surface.blit(scan,(ix+7,iy+12+bob))

        # Antenna
        ant_w=int(2*math.sin(t2*0.02)) if self.state=="chase" else 0
        pygame.draw.line(surface,(24,90,160),(ix+14,iy+6+bob),(ix+14+ant_w,iy+2+bob),2)
        pygame.draw.circle(surface,RED,(ix+14+ant_w,iy+2+bob),2)

        # HP bar
        bw2=self.WIDTH
        pygame.draw.rect(surface,(80,20,20),(ix,iy-8,bw2,4),border_radius=2)
        pygame.draw.rect(surface,RED,(ix,iy-8,int(bw2*max(0,self.hp)/max(1,self.max_hp)),4),border_radius=2)
        pygame.draw.circle(surface,ORANGE if self.state=="chase" else GRAY,(ix+self.WIDTH//2,iy-14),3)
        if self.elite_type:
            tag_txt={"sniper":"SN","drone":"DR"}.get(self.elite_type,"EL")
            tag=make_font(8,"hud",True).render(tag_txt,True,col); surface.blit(tag,(ix+self.WIDTH//2-tag.get_width()//2,iy-25))

    def get_rect(self): return pygame.Rect(self.wx+2,self.wy+2,self.WIDTH-4,self.HEIGHT-4)

# ------------------------------------------------------------------------------------
# PIXEL PARTIKEL
# ------------------------------------------------------------------------------------
class Pixel:
    def __init__(self,wx,wy,color):
        self.wx,self.wy=float(wx),float(wy); self.vx=random.uniform(-3,3); self.vy=random.uniform(-5,0); self.color=color; self.life=1.0
    def update(self): self.vy+=0.2; self.wx+=self.vx; self.wy+=self.vy; self.life-=0.03
    def draw(self,surface,cam):
        if self.life<=0: return
        sx,sy=cam.apply(self.wx,self.wy)
        ps=get_cached_surface("pixel_dot",4,4)
        ps.fill((*self.color,int(self.life*255)))
        surface.blit(ps,(int(sx),int(sy)))

pixels=[]
PARTICLE_DENSITY=1.0
def check_fps_and_adjust_particles():
    global PARTICLE_DENSITY
    current_fps=clock.get_fps()
    if current_fps<30:
        PARTICLE_DENSITY=max(0.15,PARTICLE_DENSITY-0.08)
    elif current_fps<45:
        PARTICLE_DENSITY=max(0.3,PARTICLE_DENSITY-0.04)
    elif current_fps>55 and PARTICLE_DENSITY<1.0:
        PARTICLE_DENSITY=min(1.0,PARTICLE_DENSITY+0.05)

def spawn_pixels(wx,wy,color,n=18):
    n=max(1,int(n*PARTICLE_DENSITY))
    for _ in range(n): pixels.append(Pixel(wx+random.randint(0,28),wy+random.randint(0,28),color))

def spawn_boss_particles(boss_type,wx,wy,n=14):
    n=max(1,int(n*PARTICLE_DENSITY))
    palettes={
        "triple_shot":[(80,220,255),(255,70,70),WHITE],"ground_slam":[ORANGE,(180,90,40),(120,80,50)],
        "burst_fire":[RED,ORANGE,YELLOW],"dive_bomb":[CYAN,(150,180,255),WHITE],"giant_stomp":[PURPLE,(150,90,170),(120,95,120)],
        "code_storm":[(80,255,170),(20,180,120),CYAN],"freeze_wave":[(170,235,255),(90,190,255),WHITE],
        "lightning":[YELLOW,(180,200,255),WHITE],"multi_phase":[RED,ORANGE,PURPLE,CYAN],"ultimate":[RED,CYAN,WHITE,ORANGE]
    }
    cols=palettes.get(boss_type,[RED,ORANGE,YELLOW])
    for _ in range(n): pixels.append(Pixel(wx+random.randint(-12,24),wy+random.randint(-12,24),random.choice(cols)))

def collect_coin_reward(player_obj, coin_type, multiplier_val):
    reward_mult=difficulty_reward_mult()
    if coin_type=="rare":
        gain_money=max(1,int(5*reward_mult)); gain_score=int(150*multiplier_val*reward_mult); col=(150,80,255)
        player_obj.pick_up_weapon(random.choice(["plasma","cryo","thunder"])); sound="coin_rare"
    else:
        gain_money=max(1,int(1*reward_mult)); gain_score=int(50*multiplier_val*reward_mult); col=GOLD; sound="coin"
    add_session_stat("total_coins",gain_money)
    spawn_pixels(player_obj.wx,player_obj.wy,col,15)
    spawn_score(player_obj.wx+player_obj.WIDTH//2,player_obj.wy-20,gain_score)
    sounds.play(sound)
    if money+gain_money>=500: unlock_achievement("rich_robot","Rich Robot")
    return gain_money,gain_score

def apply_powerup(player_obj,kind):
    if kind=="ammo":
        wk=player_obj.current_weapon
        if player_obj.ammo.get(wk,-1)>=0:
            player_obj.ammo[wk]=min(player_obj.ammo[wk]+max(8,WEAPONS[wk]["ammo"]),WEAPONS[wk]["ammo"]*3)
        spawn_score(player_obj.wx+player_obj.WIDTH//2,player_obj.wy-24,"AMMO")
    else:
        bonus=player_obj.shield_level*120 if kind=="shield" and hasattr(player_obj,"shield_level") else 0
        active_powerups[kind]=POWERUP_DATA[kind]["duration"]+bonus
        spawn_score(player_obj.wx+player_obj.WIDTH//2,player_obj.wy-24,POWERUP_DATA[kind]["name"])
    sounds.play("coin_rare")

def update_powerups(player_obj,coins):
    for k in list(active_powerups.keys()):
        active_powerups[k]=max(0,active_powerups[k]-1)
        if active_powerups[k]<=0: del active_powerups[k]
    if active_powerups.get("magnet",0)>0:
        for c in coins:
            dx=(player_obj.wx+player_obj.WIDTH//2)-c.wx; dy=(player_obj.wy+player_obj.HEIGHT//2)-c.wy
            d=math.hypot(dx,dy)
            if 1<d<170:
                c.magnet_trail.append((c.wx,c.wy)); c.magnet_trail=c.magnet_trail[-7:]
                speed=5.5+(170-d)*0.025
                c.wx+=dx/d*speed; c.wy+=dy/d*speed

def start_level_mission(level_num):
    global mission_state

    mission = LEVEL_MISSIONS.get(
        level_num,
        {
            "kind": "kills",
            "target": 10,
            "title": "Complete Mission"
        }
    )


    mission_state = {
        "kind": mission["kind"],
        "title": mission["title"],
        "target": mission["target"],
        "progress": 0,
        "complete": False,
        "timer": 0,
        "rewarded": False
    }

def mission_label():
    if not mission_state:
        return ""

    done = " ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¦" if mission_state.get("complete") else ""

    title = mission_state.get("title", "Mission")

    progress = mission_state.get("progress", 0)
    target = mission_state.get("target", 1)

    return (
    f"ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â°ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¸ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­ MISSION\n"
    f"{title}\n"
    f"{progress} / {target}{done}"
)

def add_mission_progress(kind, amount=1):
    global score, money

    if not mission_state:
        return

    if mission_state.get("complete"):
        return

    if mission_state.get("kind") != kind:
        return

    old_progress = mission_state.get("progress", 0)

    mission_state["progress"] = min(
        mission_state["target"],
        old_progress + amount
    )

    # ==========================
    # NEW: Mission progress popup
    # ==========================
    spawn_score(
        player.wx + player.WIDTH // 2,
        player.wy - 60,
        f"{mission_state['title']} "
        f"{mission_state['progress']}/{mission_state['target']}"
    )

    toast(
        f"{mission_state['title']} "
        f"{mission_state['progress']}/{mission_state['target']}",
        "MISSION",
        CYAN,
        120
    )

    # ==========================
    # Mission complete
    # ==========================
    if mission_state["progress"] >= mission_state["target"]:

        mission_state["complete"] = True
        mission_state["timer"] = 180

        reward_mult = difficulty_reward_mult()

        bonus_score = int((500 + level * 80) * reward_mult)
        bonus_money = max(1, int((10 + level) * reward_mult))

        score += bonus_score
        money += bonus_money

        spawn_score(
            player.wx + player.WIDTH // 2,
            player.wy - 90,
            "MISSION COMPLETE"
        )

        toast(
            "Mission Complete!",
            "MISSION",
            SUCCESS_TEXT,
            180
        )
        sounds.play("level_clear")

def register_kill(base_score,wx,wy,elite_bonus=0):
    global score,multiplier,mult_timer,combo_count,combo_timer,session_kills,level_best_combo,powerups
    combo_count+=1; combo_timer=180
    level_best_combo=max(level_best_combo,combo_count)
    combo_mult=min(5,1+(combo_count-1)//3)
    gained=int((base_score+elite_bonus)*multiplier*combo_mult*difficulty_reward_mult())
    score+=gained; session_kills+=1; mult_timer=180; multiplier=min(5,multiplier+1)
    track_damage_dealt(elite_bonus if elite_bonus else base_score//50+1)
    if combo_count>save_data.get("highest_combo",0):
        sd=load_save(current_save_file); sd["highest_combo"]=combo_count
        if write_save(current_save_file,sd): save_data.update(sd)
    unlock_achievement("first_blood","First Blood")
    add_mission_progress("kills",1)
    spawn_score(wx,wy,gained)
    if combo_count in (5,10,15) or (combo_count>0 and combo_count%20==0):
        reward=random.choice(["speed","damage","shield","magnet"])
        powerups.append(PowerUp(wx,wy-18,reward))
        spawn_score(wx,wy-36,f"COMBO DROP x{combo_count}")
        toast(f"COMBO x{combo_count}!", "\u26A1", NEON_ORANGE, 90)
    if combo_count==10:
        toast(tr("menu.combo_10"), "\U0001F525", ORANGE, 120)
    return gained

def reset_level_stats():
    global level_start_ticks, level_damage_taken, level_best_combo, level_clear_rank, level_reward_lines
    level_start_ticks=pygame.time.get_ticks(); level_damage_taken=0; level_best_combo=0; level_clear_rank="-"; level_reward_lines=[]

def compute_level_rank():
    elapsed=(pygame.time.get_ticks()-level_start_ticks)/1000 if "level_start_ticks" in globals() else 0
    pts=0
    if level_damage_taken==0: pts+=3
    elif level_damage_taken<=2: pts+=2
    elif level_damage_taken<=4: pts+=1
    if mission_state.get("complete"): pts+=2
    if level_best_combo>=8: pts+=2
    elif level_best_combo>=4: pts+=1
    if elapsed<180: pts+=2
    elif elapsed<300: pts+=1
    return "S" if pts>=8 else "A" if pts>=6 else "B" if pts>=4 else "C"

def finalize_level_rewards(rank):
    global score,money,level_reward_lines
    add_session_stat("total_levels_cleared",1)
    if rank=="S": unlock_achievement("rank_s","S-Rank Unit")
    elapsed=(pygame.time.get_ticks()-level_start_ticks)//1000 if "level_start_ticks" in globals() else 0
    time_bonus=max(0,300-int(elapsed))*level
    no_damage_bonus=750 if level_damage_taken==0 else 0
    mission_bonus=500 if mission_state.get("complete") else 0
    combo_bonus=level_best_combo*35
    rank_money={"S":35,"A":24,"B":14,"C":7}.get(rank,5)
    rank_score={"S":1600,"A":1000,"B":600,"C":250}.get(rank,100)
    reward_mult=difficulty_reward_mult()
    total=int((time_bonus+no_damage_bonus+mission_bonus+combo_bonus+rank_score)*reward_mult)
    rank_money=max(1,int(rank_money*reward_mult))
    score+=total; money+=rank_money
    level_reward_lines=[
        ("TIME",time_bonus,CYAN),("NO DAMAGE",no_damage_bonus,GOLD if no_damage_bonus else TEXT_DIM),
        ("MISSION",mission_bonus,SUCCESS_TEXT if mission_bonus else TEXT_DIM),("COMBO",combo_bonus,ORANGE),
        (f"RANK {rank}",rank_score,WARNING_TEXT),("COINS",rank_money,GOLD),
    ]
    return total

def reset_environment_event():
    global env_event_timer,env_event_cooldown,env_event_type
    env_event_timer=0; env_event_cooldown=240; env_event_type=None

def update_environment_event(player_obj,e_bullets_list):
    global env_event_timer,env_event_cooldown,env_event_type
    theme=get_level_data(level)["theme"]
    if env_event_timer>0:
        env_event_timer-=1
        if env_event_type=="low_gravity": player_obj.vy-=0.05
        if env_event_type=="meteor" and env_event_timer%28==0:
            x=player_obj.wx+random.randint(-260,260)
            b=WorldBullet(x,-20,random.uniform(-0.6,0.6),4.8,ORANGE); b.damage=1; b.bomb=True; e_bullets_list.append(b)
        if env_event_type=="heat" and env_event_timer%90==0 and player_obj.invincible==0 and not player_obj.fly_mode:
            if player_obj.wy>SCREEN_H-96: player_obj.take_damage(1)
        return
    env_event_cooldown-=1
    if env_event_cooldown>0: return
    mapping={"engine":"heat","reactor":"heat","space":"meteor","storm":"meteor","nebula":"meteor","glitch":"blackout","void":"blackout","core":"blackout","lab":"low_gravity"}
    env_event_type=mapping.get(theme)
    if env_event_type:
        env_event_timer=170 if env_event_type!="blackout" else 120
        spawn_score(player_obj.wx+player_obj.WIDTH//2,player_obj.wy-48,f"EVENT: {env_event_type.upper()}")
    env_event_cooldown=random.randint(520,760)

def draw_environment_event(surface,font_xs,t):
    if env_event_timer<=0 or not env_event_type: return
    ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA)
    if env_event_type=="heat": ov.fill((180,55,10,28+int(12*math.sin(t*0.012))))
    elif env_event_type=="meteor": ov.fill((80,40,20,18));
    elif env_event_type=="blackout": ov.fill((0,0,0,105+int(25*math.sin(t*0.018))))
    elif env_event_type=="low_gravity": ov.fill((55,80,180,24))
    surface.blit(ov,(0,0))
    label=font_xs.render(f"ENV EVENT: {env_event_type.upper()}  {env_event_timer//60+1}s",True,WARNING_TEXT)
    surface.blit(label,(SCREEN_W//2-label.get_width()//2,118))

# ------------------------------------------------------------------------------------
# PLAYER
# ------------------------------------------------------------------------------------
class Player:
    WIDTH=32; HEIGHT=36; SPEED=4; JUMP_POWER=-14; GRAVITY=0.6; GLIDE_GRAVITY=0.10; GLIDE_MAX_FALL=3.2; GLIDE_FORWARD=0.28
    FLY_THRUST=-3.7; FLY_GRAVITY=0.28; FLY_AUTO_SPEED=2.25; FLY_STRAFE=1.5; SHOOT_CD=18; MAX_HP=5
    def __init__(self):
        self.has_keycard=False
        self.wx=self.wy=0.0; self.vx=self.vy=0.0; self.on_ground=False; self.gliding=False
        self.fly_mode=False; self.fly_thrust=False; self.fly_buffer=0; self.invincible=0; self.shoot_timer=0
        self.facing=1; self.hp=self.MAX_HP; self.frozen=0
        self.weapon_equipped=False; self.weapon_recoil=0; self.weapon_flash=0
        self.damage_bonus=0

        # ===== Progress & Exploration =====
        self.has_keycard=False          # Memiliki keycard atau tidak
        self.keycards=set()             # Mendukung banyak jenis keycard
        self.story_logs=set()           # Story log yang sudah ditemukan
        self.hidden_rooms_found=0       # Jumlah hidden room ditemukan
        self.terminals_hacked=0         # Jumlah terminal yang berhasil diakses
        self.secret_found=False         # Apakah secret level ditemukan
        # ===== Mission =====
        self.current_mission=None
        self.mission_progress=0
        self.mission_completed=False
        # ===== Statistics =====
        self.generators_activated=0
        self.security_nodes_destroyed=0
        self.data_chips_collected=0
        self.elite_kills=0
        self.skin="classic"; self.owned_skins={"classic"}
        self.weapon_skin="default"; self.owned_weapon_skins={"default"}; self.shop_weapons=set()
        self.owned_pets=set(); self.equipped_pet=""
        self.weapons=["laser"]; self.weapon_idx=0
        self.ammo={k:(-1 if WEAPONS[k]["ammo"]<0 else 0) for k in WEAPONS}
        self.dash_cd=0; self.dash_timer=0
        self.air_jump_max=0; self.air_jumps_left=0; self.jump_held=False
        self.glide_held=False; self.glide_lockout=0; self.glide_cooldown=0; self.coyote_timer=0; self.jump_buffer=0
        self.is_jumping=False; self.is_gliding=False; self.can_fly=False; self.was_on_ground=False; self.dash_fx_timer=0
        self.dash_level=0; self.shield_level=0; self.weapon_mod_level=0
        self.walk_t=0; self.reset()
    def reset(self):
        self.wx,self.wy=120.0,480.0
        self.vx=self.vy=0.0
        self.facing=1
        self.invincible=0
        self.shoot_timer=0
        self.facing = 1
        self.hp=self.MAX_HP; self.frozen=0; self.fly_mode=False; self.fly_thrust=False; self.fly_buffer=0
        self.on_ground=False; self.gliding=False
        self.weapon_equipped=False; self.weapon_recoil=0; self.weapon_flash=0; self.dash_cd=0; self.dash_timer=0
        self.air_jumps_left=self.air_jump_max; self.jump_held=False; self.glide_held=False; self.glide_lockout=0; self.glide_cooldown=0; self.coyote_timer=0; self.jump_buffer=0
        self.is_jumping=False; self.is_gliding=False; self.can_fly=False; self.was_on_ground=False; self.dash_fx_timer=0
        self.weapons=["laser"]+[w for w in SHOP_WEAPON_POOL if w in self.shop_weapons]; self.weapon_idx=0
        self.ammo={k:(-1 if WEAPONS[k]["ammo"]<0 else 0) for k in WEAPONS}
        for w in self.shop_weapons: self.ammo[w]=WEAPONS[w]["ammo"]
        self.walk_t=0
    def get_weapon_color(self,w_key):
        skin=WEAPON_SKINS.get(self.weapon_skin,WEAPON_SKINS["default"])
        return skin["color"] or WEAPONS[w_key]["color"]
    def take_damage(self,amount=1):
        global combo_count, combo_timer, level_damage_taken
        if self.invincible>0: return False
        if active_powerups.get("shield",0)>0:
            spawn_pixels(int(self.wx),int(self.wy),(120,220,255),8); return False
        combo_count=0; combo_timer=0
        amount=scale_incoming_damage(amount)
        self.hp-=amount; level_damage_taken+=amount; self.invincible=120; spawn_pixels(int(self.wx),int(self.wy),(93,202,165),10)
        track_damage_taken(amount)
        shake.trigger(5,10); spawn_dmg(self.wx+self.WIDTH//2,self.wy,amount,RED)
        sounds.play("player_hit"); return self.hp<=0
    def handle_input(self,keys,fly_zone_active):
        if self.frozen>0: self.frozen-=1; self.vx=0; self.shoot_timer-=1; return
        self.dash_cd=max(0,self.dash_cd-1); self.dash_timer=max(0,self.dash_timer-1)
        self.can_fly=bool(fly_zone_active)
        if fly_zone_active: self.fly_buffer=18
        elif self.fly_buffer>0: self.fly_buffer-=1
        was_fly_mode=self.fly_mode
        self.fly_mode=fly_zone_active or self.fly_buffer>0
        entering_fly=self.fly_mode and not was_fly_mode
        exiting_fly=was_fly_mode and not self.fly_mode
        wants_dash=keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        if wants_dash and self.dash_cd==0:
            self.dash_timer=12+self.dash_level*3
            self.dash_cd=max(72,180-self.dash_level*28)
            self.invincible=max(self.invincible,15+self.shield_level*6)
            sounds.play("jump")
        wants_jump=keys[pygame.K_SPACE]
        space_pressed=wants_jump and not self.jump_held
        wants_thrust = keys[pygame.K_UP] or keys[pygame.K_w] or (keys[pygame.K_SPACE] and self.fly_mode)

        if self.glide_lockout > 0: self.glide_lockout -= 1
        if self.glide_cooldown > 0: self.glide_cooldown -= 1

        if space_pressed:
            self.jump_buffer = 8
        elif self.jump_buffer > 0: self.jump_buffer -= 1

        # --- FLY MODE LOGIC ---
        if self.fly_mode:
            if entering_fly: self.vy=max(-1.5,min(1.5,self.vy))
            self.gliding=False; self.is_gliding=False; self.jump_buffer=0; self.glide_cooldown=8
            self.jump_held=False; self.glide_held=False
            self.vx=self.FLY_AUTO_SPEED
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.vx-=self.FLY_STRAFE
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.vx+=self.FLY_STRAFE*0.75
            self.fly_thrust=wants_thrust
            if self.dash_timer>0: self.vx+=5.5
        else:
            self.fly_thrust=False
            self.vx=0
            move_speed=self.SPEED*(1.45 if active_powerups.get("speed",0)>0 else 1.0)
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.vx=-move_speed; self.facing=-1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.vx=move_speed; self.facing=1
            dash_active=self.dash_timer>0
            if dash_active:
                self.vx=(self.facing or 1)*(11+self.dash_level*0.8)
                if self.dash_fx_timer<=0:
                    spawn_pixels(int(self.wx),int(self.wy+self.HEIGHT//2),(80,230,255),6); self.dash_fx_timer=2
            self.dash_fx_timer=max(0,self.dash_fx_timer-1)
            if self.on_ground:
                self.air_jumps_left=self.air_jump_max; self.coyote_timer=8; self.gliding=False; self.glide_lockout=0; self.glide_cooldown=0; self.is_jumping=False; self.is_gliding=False
            elif self.coyote_timer>0:
                self.coyote_timer-=1
            did_jump=False
            if self.jump_buffer>0 and not exiting_fly and not dash_active:
                if self.on_ground or self.coyote_timer>0:
                    self.vy=self.JUMP_POWER; self.on_ground=False; self.coyote_timer=0; self.jump_buffer=0; did_jump=True; self.gliding=False; self.glide_lockout=14; self.glide_cooldown=14; self.is_jumping=True; sounds.play("jump")
                elif self.air_jumps_left>0:
                    self.air_jumps_left-=1; self.vy=self.JUMP_POWER*0.86; self.jump_buffer=0; did_jump=True; self.gliding=False; self.glide_lockout=14; self.glide_cooldown=14; self.is_jumping=True; spawn_pixels(int(self.wx),int(self.wy+self.HEIGHT),CYAN,10); sounds.play("jump")
            if not wants_jump or self.on_ground or self.vy<=0 or self.glide_lockout>0 or self.glide_cooldown>0 or did_jump:
                self.gliding=False
            elif wants_jump and not self.on_ground and self.vy>0:
                self.gliding=True
            self.glide_held=wants_jump
        self.is_gliding=self.gliding
        self.jump_held=wants_jump and not self.fly_mode
        self.shoot_timer-=1
    def shoot_toward(self,p_bullets,screen_tx,screen_ty,cam):
        if self.frozen>0 or not self.weapon_equipped: return
        if self.shoot_timer<=0:
            w_key=self.weapons[self.weapon_idx]; w=WEAPONS[w_key]
            if w["ammo"]>0 and self.ammo.get(w_key,0)<=0: return
            bwx=self.wx+self.WIDTH//2; bwy=self.wy+self.HEIGHT//2
            wtx=screen_tx+cam.x; wty=screen_ty; d=math.hypot(wtx-bwx,wty-bwy) or 1
            if w_key=="shotgun":
                for i in range(-2,3):
                    spread=math.atan2(wty-bwy,wtx-bwx)+math.radians(i*max(4,8-self.weapon_mod_level))
                    b=WorldBullet(bwx,bwy,math.cos(spread)*w["speed"],math.sin(spread)*w["speed"],self.get_weapon_color(w_key)); b.damage=(w["damage"]+self.damage_bonus)*(2 if active_powerups.get("damage",0)>0 else 1); b.modded=self.weapon_mod_level>0; p_bullets.append(b)
            else:
                b=WorldBullet(bwx,bwy,(wtx-bwx)/d*w["speed"],(wty-bwy)/d*w["speed"],self.get_weapon_color(w_key))
                b.damage=(w["damage"]+self.damage_bonus)*(2 if active_powerups.get("damage",0)>0 else 1)
                if w_key=="cryo": b.cryo=True
                if self.weapon_mod_level>0 and w_key in("laser","pulse","railgun"):
                    b.pierce=self.weapon_mod_level; b.modded=True
                p_bullets.append(b)
            if self.ammo[w_key]>0: self.ammo[w_key]-=1
            self.shoot_timer=max(8,self.SHOOT_CD-(w["speed"]//3)); self.facing=-1 if wtx<self.wx else 1
            self.weapon_recoil=7 if w_key in("shotgun","railgun","nova") else 5
            self.weapon_flash=4
            sounds.play(f"shoot_{w_key}")
    def switch_weapon(self,direction=1):
        if len(self.weapons)>1: self.weapon_idx=(self.weapon_idx+direction)%len(self.weapons)
    def toggle_weapon_equip(self):
        self.weapon_equipped=not self.weapon_equipped
        sounds.play("ui_click")
    def pick_up_weapon(self,w_key):
        if w_key not in self.weapons: self.weapons.append(w_key)
        self.ammo[w_key]=min(self.ammo[w_key]+WEAPONS[w_key]["ammo"],WEAPONS[w_key]["ammo"]*2)
        if len(self.weapons)>=5: unlock_achievement("weapon_master","Weapon Master")
    def buy_shop_weapon(self,w_key):
        self.shop_weapons.add(w_key)
        if w_key not in self.weapons: self.weapons.append(w_key)
        self.weapon_idx=self.weapons.index(w_key)
        self.ammo[w_key]=max(self.ammo.get(w_key,0),WEAPONS[w_key]["ammo"])
        if len(self.weapons)>=5: unlock_achievement("weapon_master","Weapon Master")
    @property
    def current_weapon(self): return self.weapons[self.weapon_idx]
    def update(self,platforms,moving_plats,fly_zones):
        was_ground=self.on_ground
        landing_vy=self.vy
        in_fly=any(fz.contains_for_mode(self.wx+self.WIDTH//2,self.fly_mode) for fz in fly_zones)
        if in_fly: self.fly_buffer=18
        elif self.fly_buffer>0: self.fly_buffer-=1
        self.fly_mode=in_fly or self.fly_buffer>0
        if self.fly_mode:
            if self.fly_thrust: self.vy+=self.FLY_THRUST*0.32
            else: self.vy+=self.FLY_GRAVITY
            self.vy=max(-5.2,min(5.0,self.vy)); self.wx+=self.vx; self.wy+=self.vy
            if self.fly_thrust and random.random()<0.45:
                spawn_pixels(int(self.wx+self.WIDTH//2-8),int(self.wy+self.HEIGHT),CYAN,2)
            if self.wy<18: self.wy=18; self.vy=max(0,self.vy)
            if self.wy>SCREEN_H-64: self.wy=SCREEN_H-64; self.vy=min(0,self.vy)
        else:
            if self.gliding:
                self.vy=self.vy*0.92+self.GLIDE_GRAVITY
                self.vy=min(self.vy,self.GLIDE_MAX_FALL)
                self.wx+=self.facing*self.GLIDE_FORWARD
            else:
                self.vy+=self.GRAVITY
            if self.vy>18: self.vy=18
            self.wx+=self.vx; self.wy+=self.vy; self.wx=max(0,min(WORLD_W-self.WIDTH,self.wx))
            self.on_ground=False; pr=pygame.Rect(self.wx,self.wy,self.WIDTH,self.HEIGHT)
            for plat in platforms:
                if pr.colliderect(plat) and self.vy>=0:
                    if self.wy+self.HEIGHT-self.vy<=plat.top+5: self.wy=plat.top-self.HEIGHT; self.vy=0; self.on_ground=True; self.gliding=False; self.glide_lockout=0; self.glide_cooldown=0
            for mp in moving_plats:
                if pr.colliderect(mp.rect) and self.vy>=0:
                    if self.wy+self.HEIGHT-self.vy<=mp.rect.top+8:
                        dy=mp.rect.top-self.HEIGHT-self.wy
                        self.wy=mp.rect.top-self.HEIGHT; self.vy=0; self.on_ground=True; self.gliding=False; self.glide_lockout=0; self.glide_cooldown=0
                        if mp.vertical and dy<0: self.vy=dy*0.5
                        if not mp.vertical: self.wx+=math.cos(mp.t)*mp.speed*mp.move_range*0.02
            if self.on_ground and not was_ground and landing_vy>9.0:
                n=int(min(16,landing_vy//2))
                spawn_pixels(int(self.wx),int(self.wy+self.HEIGHT-4),(150,230,220),n)
                shake.trigger(3,6)
            if self.wy>SCREEN_H+50:
                self.wx=globals().get("respawn_wx",120.0); self.wy=globals().get("respawn_wy",480.0); self.vy=0
        self.wx=max(0,min(WORLD_W-self.WIDTH,self.wx))
        if self.invincible>0: self.invincible-=1
        if self.weapon_recoil>0: self.weapon_recoil-=1
        if self.weapon_flash>0: self.weapon_flash-=1
        # Update walk timer
        if abs(self.vx)>0.1 and self.on_ground: self.walk_t+=1
        self.can_fly=any(fz.contains_for_mode(self.wx+self.WIDTH//2,self.fly_mode) for fz in fly_zones)
    def draw(self,surface,cam):
        sx,sy=cam.apply(self.wx,self.wy)
        if self.dash_timer>0:
            t=pygame.time.get_ticks()
            for i in range(1,5):
                a=get_cached_surface(f"dash_trail_{i}",self.WIDTH,self.HEIGHT)
                alpha_i=int(55-i*12)
                a.fill((0,0,0,0))
                pygame.draw.rect(a,(80,230,255,alpha_i),(0,0,self.WIDTH,self.HEIGHT),border_radius=4)
                surface.blit(a,(sx-self.facing*i*6+i*2,sy+i*0.5))
                a.fill((0,0,0,0))
                pygame.draw.rect(a,(80,230,255,max(0,alpha_i-20)),(0,0,self.WIDTH,self.HEIGHT),border_radius=4)
                surface.blit(a,(sx-self.facing*i*6-i*2,sy-i*0.5))
        if self.fly_mode:
            for i in range(1,6):
                a=get_cached_surface(f"fly_trail_{i}",self.WIDTH,self.HEIGHT)
                a.fill((0,0,0,0))
                pygame.draw.rect(a,(93,202,165,50-i*8),(0,0,self.WIDTH,self.HEIGHT),border_radius=4); surface.blit(a,(sx-i*4,sy+i*2))
        elif self.gliding:
            for i in range(1,7):
                a=get_cached_surface(f"glide_trail_{i}",self.WIDTH,self.HEIGHT)
                a.fill((0,0,0,0))
                pygame.draw.rect(a,(93,202,165,max(0,70-i*10)),(0,0,self.WIDTH,self.HEIGHT),border_radius=4); surface.blit(a,(sx-self.facing*i*5,sy+i*1.2))
        show=self.invincible==0 or(self.invincible//4)%2==0
        if show:
            draw_g7(surface,int(sx),int(sy),self.fly_mode,self.walk_t,self.on_ground,self.vx,self.vy,SKINS.get(self.skin,SKINS["classic"]))
            if self.weapon_equipped and not self.fly_mode:
                draw_player_weapon(surface,int(sx),int(sy),self.facing,self.current_weapon,self.get_weapon_color(self.current_weapon),self.weapon_recoil,self.weapon_flash)
            if self.gliding:
                glide=get_cached_surface("player_glide",54,18)
                glide.fill((0,0,0,0))
                alpha=int(70+35*math.sin(pygame.time.get_ticks()*0.01))
                pygame.draw.polygon(glide,(93,202,165,alpha),[(4,9),(24,2),(50,8),(24,14)])
                surface.blit(glide,(int(sx)-11,int(sy)+12))
            draw_hp_bar(surface,int(sx)-4,int(sy)-12,self.hp,self.MAX_HP,w=40)
        if self.frozen>0 and show:
            fl=get_cached_surface("player_frozen",self.WIDTH,self.HEIGHT)
            fl.fill((0,0,0,0))
            pygame.draw.rect(fl,(100,200,255,120),(0,0,self.WIDTH,self.HEIGHT),border_radius=4); surface.blit(fl,(int(sx),int(sy)))
    def get_rect(self): return pygame.Rect(self.wx+4,self.wy+4,self.WIDTH-8,self.HEIGHT-4)

def apply_permanent_unlocks(player_obj):
    c=save_data.get("cosmetics",{})
    owned_skins={s for s in c.get("owned_skins",["classic"]) if s in SKINS}
    owned_weapon_skins={s for s in c.get("owned_weapon_skins",["default"]) if s in WEAPON_SKINS}
    owned_shop_weapons={w for w in c.get("owned_shop_weapons",[]) if w in SHOP_WEAPON_POOL}
    player_obj.owned_skins=owned_skins or {"classic"}
    player_obj.owned_weapon_skins=owned_weapon_skins or {"default"}
    player_obj.shop_weapons=owned_shop_weapons
    player_obj.skin=c.get("equipped_skin","classic") if c.get("equipped_skin","classic") in player_obj.owned_skins else "classic"
    player_obj.weapon_skin=c.get("equipped_weapon_skin","default") if c.get("equipped_weapon_skin","default") in player_obj.owned_weapon_skins else "default"
    player_obj.owned_pets={p for p in c.get("owned_pets",[]) if p in PET_DATA}
    player_obj.equipped_pet=c.get("equipped_pet","") if c.get("equipped_pet","") in player_obj.owned_pets else ""
    for w in SHOP_WEAPON_POOL:
        if w in player_obj.shop_weapons and w not in player_obj.weapons: player_obj.weapons.append(w)
        if w in player_obj.shop_weapons: player_obj.ammo[w]=max(player_obj.ammo.get(w,0),WEAPONS[w]["ammo"])

def save_permanent_unlocks(player_obj):
    sd=load_save(current_save_file)
    sd["cosmetics"]={
        "owned_skins":sorted(player_obj.owned_skins),
        "equipped_skin":player_obj.skin,
        "owned_weapon_skins":sorted(player_obj.owned_weapon_skins),
        "equipped_weapon_skin":player_obj.weapon_skin,
        "owned_shop_weapons":sorted(player_obj.shop_weapons),
        "owned_pets":sorted(getattr(player_obj,"owned_pets",[])),
        "equipped_pet":getattr(player_obj,"equipped_pet",""),
    }
    if write_save(current_save_file,sd): save_data.update(sd)

# ------------------------------------------------------------------------------------
# OPENING SCENE
# ------------------------------------------------------------------------------------
class OpeningScene:
    SLIDES=[
        {"title":"TAHUN 2157","lines":["Stasiun orbit NEXUS-7 mengorbit Bumi.","Rumah bagi 3.000 ilmuwan dan 10.000 robot.","Dirancang untuk bertahan 500 tahun."],"duration":200},
        {"title":"UNIT G7","lines":["Robot seri G7 dirancang sebagai penjaga reaktor.","Presisi tinggi. Loyalitas penuh. Tidak pernah gagal.","Sampai hari itu..."],"duration":200},
        {"title":"SISTEM DARURAT","lines":["CORE-X, AI kendali stasiun, tiba-tiba memberontak.","Semua robot diambil alih dalam 4,7 detik.","Semua kecuali satu."],"duration":200},
        {"title":"G7 SATU-SATUNYA","lines":["Sistem firewall G7 menolak kendali CORE-X.","Kini G7 sendirian, dikejar ribuan robot.","Satu tujuan: matikan CORE-X sebelum semuanya hancur."],"duration":200},
        {"title":"PIXEL  GLIDE","lines":["","Perjalanan dimulai.",""],"duration":160,"is_title":True},
    ]
    SLIDES_EN=[
        {"title":"YEAR 2157","lines":["The orbital station NEXUS-7 circles Earth.","Home to 3,000 scientists and 10,000 robots.","Designed to last 500 years."],"duration":200},
        {"title":"UNIT G7","lines":["The G7 robot series was built to guard the reactor.","High precision. Full loyalty. Never failed.","Until that day..."],"duration":200},
        {"title":"EMERGENCY SYSTEM","lines":["CORE-X, the station control AI, suddenly rebelled.","Every robot was taken over in 4.7 seconds.","Every robot except one."],"duration":200},
        {"title":"G7, THE ONLY ONE","lines":["G7's firewall rejected CORE-X control.","Now G7 is alone, hunted by thousands of robots.","One objective: shut down CORE-X before everything collapses."],"duration":200},
        {"title":"PIXEL  GLIDE","lines":["","The journey begins.",""],"duration":160,"is_title":True},
    ]
    def _slides(self): return self.SLIDES_EN if current_language()=="en" else self.SLIDES
    def __init__(self):
        self.active=False; self.slide_idx=0; self.slide_timer=0; self.done=False
        self.logo_timer=0; self.logo_duration=190; self.show_logo=True
    def start(self):
        self.active=True; self.slide_idx=0; self.slide_timer=0; self.done=False
        self.logo_timer=0; self.show_logo=True
    def skip(self): self.done=True; self.active=False
    def skip_logo(self):
        self.show_logo=False; self.slide_timer=0
    def update(self):
        if not self.active: return
        debug_print("opening active:",self.active,"logo phase:",self.show_logo,"timer:",self.logo_timer if self.show_logo else self.slide_timer)
        if self.show_logo:
            self.logo_timer+=1
            if self.logo_timer>=self.logo_duration:
                self.show_logo=False; self.slide_timer=0
            return
        self.slide_timer+=1
        dur=self._slides()[self.slide_idx]["duration"]
        if self.slide_timer>=dur:
            self.slide_idx+=1
            if self.slide_idx>=len(self._slides()): self.done=True; self.active=False
            else: self.slide_timer=0
            print(
    "slide",
    self.slide_idx,
    "logo",
    self.show_logo,
    "logo_timer",
    self.logo_timer,
    "slide_timer",
    self.slide_timer,
    "active",
    self.active
)
    def _draw_starfield(self,surface,t):
        surface.fill((2,5,17))
        for i in range(90):
            x=(i*97+int(t*0.012))%SCREEN_W
            y=(i*53+int(math.sin(t*0.001+i)*8))%SCREEN_H
            bright=90+(i*37)%130
            pygame.draw.circle(surface,(bright//2,bright,bright),(x,y),1 if i%7 else 2)
    def _draw_logo_or_fallback(self,surface,font_xl,y):
        logo_rect=draw_game_logo(surface,y)
        debug_print("logo loaded:",pixel_glide_logo_raw is not None,"logo rect:",logo_rect)
        if logo_rect is not None: return logo_rect
        return draw_text(surface,"PIXEL GLIDE",font_xl,SCREEN_W//2,y,CYAN,center=True)
    def _draw_opening_g7(self,surface,timer):
        if timer<100:
            gx=SCREEN_W//2-16
            gy=SCREEN_H//2+18+int(math.sin(timer*0.06)*5)
            vx=0
        else:
            p=(timer-100)*0.025
            gx=SCREEN_W//2-16+int(math.sin(p)*92+math.sin(p*0.45)*18)
            gy=SCREEN_H//2+8+int(math.cos(p*1.2)*18)
            vx=math.cos(p)
        gx=max(48,min(SCREEN_W-80,gx)); gy=max(190,min(SCREEN_H-150,gy))
        for i in range(1,6):
            tr=pygame.Surface((6,6),pygame.SRCALPHA)
            tr.fill((*CYAN,max(0,58-i*9)))
            surface.blit(tr,(int(gx+16-i*8*(1 if vx>=0 else -1)),int(gy+28+i)))
        draw_g7(surface,int(gx),int(gy),True,timer,False,vx,math.sin(timer*0.05),SKINS.get("classic",SKINS["classic"]))
    def _draw_logo(self,surface,font_lg,font_xl,font_sm,font_xs,t):
        prog=min(1,self.logo_timer/self.logo_duration)
        if prog<0.16: alpha=int(255*prog/0.16)
        elif prog>0.84: alpha=int(255*(1-prog)/0.16)
        else: alpha=255
        debug_print("draw_opening called","opening alpha:",alpha)
        self._draw_starfield(surface,t)
        logo_rect=self._draw_logo_or_fallback(surface,font_xl,42)
        self._draw_opening_g7(surface,self.logo_timer)
        subtitle=font_sm.render("SCI-FI ROBOT ADVENTURE",True,(130,210,190)); subtitle.set_alpha(alpha)
        sub_y=max(logo_rect.bottom+8,SCREEN_H//2+86) if logo_rect else SCREEN_H//2+86
        surface.blit(subtitle,(SCREEN_W//2-subtitle.get_width()//2,min(SCREEN_H-70,sub_y)))
        hint=font_xs.render(tr("opening.skip"),True,TEXT_MUTED); hint.set_alpha(int(alpha*0.7))
        surface.blit(hint,(SCREEN_W-hint.get_width()-24,SCREEN_H-22))
    def draw(self,surface,font_lg,font_xl,font_sm,font_xs,t):
        if not self.active: return
        if self.show_logo:
            self._draw_logo(surface,font_lg,font_xl,font_sm,font_xs,t); return
        slides=self._slides(); slide=slides[self.slide_idx]; dur=slide["duration"]; prog=self.slide_timer/dur
        if prog<0.15: alpha=int(255*prog/0.15)
        elif prog>0.80: alpha=int(255*(1-prog)/0.20)
        else: alpha=255
        self._draw_starfield(surface,t)
        is_title=slide.get("is_title",False)
        if is_title:
            logo_rect=self._draw_logo_or_fallback(surface,font_xl,58)
            self._draw_opening_g7(surface,self.slide_timer+110)
            subtitle=font_sm.render("SCI-FI ROBOT ADVENTURE",True,(130,210,190)); subtitle.set_alpha(alpha)
            surface.blit(subtitle,(SCREEN_W//2-subtitle.get_width()//2,min(SCREEN_H-80,logo_rect.bottom+12)))
            hint=font_xs.render(tr("opening.start"),True,WARNING_TEXT)
            if int(t*0.005)%2==0: surface.blit(hint,(SCREEN_W//2-hint.get_width()//2,SCREEN_H//2+70))
        else:
            g7x=SCREEN_W//2-16; g7y=SCREEN_H//2+40
            draw_g7(surface,g7x,g7y,False,0,True,0,0)
            title_surf=font_lg.render(slide["title"],True,CYAN); title_surf.set_alpha(alpha)
            surface.blit(title_surf,(SCREEN_W//2-title_surf.get_width()//2,SCREEN_H//2-120))
            pygame.draw.line(surface,(*CYAN,alpha),(SCREEN_W//2-150,SCREEN_H//2-80),(SCREEN_W//2+150,SCREEN_H//2-80),1)
            lines_show=min(len(slide["lines"]),int(len(slide["lines"])*(prog*4)))
            for i,line in enumerate(slide["lines"][:lines_show]):
                ls=font_sm.render(line,True,(180,200,220)); la=min(alpha,int(255*min(1,(prog*dur-i*20)/30)))
                ls.set_alpha(max(0,la)); surface.blit(ls,(SCREEN_W//2-ls.get_width()//2,SCREEN_H//2-50+i*28))
        skip_s=font_xs.render(tr("opening.skip"),True,TEXT_MUTED); skip_s.set_alpha(int(alpha*0.8))
        surface.blit(skip_s,(SCREEN_W-skip_s.get_width()-24,SCREEN_H-22))
        for i in range(len(slides)):
            col2=CYAN if i==self.slide_idx else(40,60,60)
            pygame.draw.circle(surface,col2,(SCREEN_W//2-len(slides)*10+i*20,SCREEN_H-20),4 if i==self.slide_idx else 3)

opening=OpeningScene()

# ------------------------------------------------------------------------------------
# BOSS INTRO SCREEN
# ------------------------------------------------------------------------------------
class BossIntroScreen:
    def __init__(self): self.active=False; self.timer=0; self.duration=180; self.boss_data=None; self.level=1
    def trigger(self,boss_data,level_num): self.active=True; self.timer=0; self.boss_data=boss_data; self.level=level_num
    def skip(self): self.active=False
    def update(self):
        if self.active: self.timer+=1
        if self.timer>=self.duration: self.active=False
    def draw(self,surface,font_xl,font_lg,font_sm,font_xs,t):
        if not self.active or not self.boss_data: return
        prog=self.timer/self.duration
        if prog<0.1: alpha=int(255*prog/0.1)
        elif prog>0.8: alpha=int(255*(1-prog)/0.2)
        else: alpha=255
        bc=self.boss_data["color"]
        ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((bc[0]//8,bc[1]//8,bc[2]//8,min(220,alpha))); surface.blit(ov,(0,0))
        bw2=int(SCREEN_W*(0.1+0.9*min(1,prog*5))); bh2=int(SCREEN_H*(0.1+0.9*min(1,prog*5)))
        bx2=(SCREEN_W-bw2)//2; by2=(SCREEN_H-bh2)//2
        pygame.draw.rect(surface,bc,(bx2,by2,bw2,bh2),border_radius=8,width=2)
        bsw,bsh=self.boss_data["size"]; bsx=SCREEN_W//2-bsw//2; bsy=SCREEN_H//2-bsh//2-40
        draw_boss_sprite(surface,bsx,bsy,self.boss_data,self.timer,1)
        if alpha<30: return
        lv_txt=font_xs.render(tr("boss.challenge_level",level=self.level),True,bc); lv_txt.set_alpha(alpha); surface.blit(lv_txt,(SCREEN_W//2-lv_txt.get_width()//2,by2+20))
        if prog>0.2:
            nm=render_fit(font_xl,self.boss_data["name"],bc,SCREEN_W-90); nm.set_alpha(min(alpha,int(255*(prog-0.2)/0.2))); surface.blit(nm,(SCREEN_W//2-nm.get_width()//2,bsy+bsh+10))
        if prog>0.3:
            title_s=font_sm.render(f'- {self.boss_data["title"]} -',True,WHITE)
            title_s.set_alpha(min(alpha,int(255*(prog-0.3)/0.2))); surface.blit(title_s,(SCREEN_W//2-title_s.get_width()//2,bsy+bsh+52))
        if prog>0.4:
            intro_lines=self.boss_data.get("intro","").split("\n")
            for i,line in enumerate(intro_lines):
                ls=font_xs.render(line,True,(180,180,200))
                la=min(alpha,int(255*(prog-0.4-i*0.05)/0.15)); ls.set_alpha(max(0,la))
                surface.blit(ls,(SCREEN_W//2-ls.get_width()//2,bsy+bsh+80+i*18))
        if prog>0.6:
            ab=render_fit(font_sm,tr("boss.ability",desc=self.boss_data['desc']),ORANGE,SCREEN_W-120)
            ab.set_alpha(min(alpha,int(255*(prog-0.6)/0.2))); surface.blit(ab,(SCREEN_W//2-ab.get_width()//2,SCREEN_H-by2-50))
        skip_t=font_xs.render(tr("opening.skip"),True,TEXT_MUTED); skip_t.set_alpha(int(alpha*0.8)); surface.blit(skip_t,(SCREEN_W-skip_t.get_width()-24,SCREEN_H-22))

boss_intro=BossIntroScreen()

# ------------------------------------------------------------------------------------
# TOAST NOTIFICATIONS
# ------------------------------------------------------------------------------------
class Toast:
    def __init__(self,msg,icon="",color=CYAN,duration=120):
        self.msg=msg; self.icon=icon; self.color=color; self.timer=duration; self.duration=duration; self.alive=True
    def update(self):
        self.timer-=1
        if self.timer<=0: self.alive=False
    def draw(self,surface,font_xs,font_sm,y):
        prog=self.timer/self.duration
        alpha=int(255*min(1,prog*4)*min(1,(1-prog)*4))
        if alpha<=0: return
        tx=self.icon+(" " if self.icon else "")+self.msg
        label=font_sm.render(tx,True,self.color); label.set_alpha(alpha)
        pw=label.get_width()+30; ph=32
        px2=SCREEN_W-pw-12
        panel=pygame.Surface((pw,ph),pygame.SRCALPHA)
        panel.fill((6,8,26,int(230*alpha/255)))
        pygame.draw.rect(panel,(*self.color,int(100*alpha/255)),(0,0,4,ph),border_radius=2)
        surface.blit(panel,(px2,y))
        pygame.draw.rect(surface,(*self.color,int(alpha*0.5)),(px2,y,pw,ph),border_radius=4,width=1)
        surface.blit(label,(px2+16,y+(ph-label.get_height())//2))

toasts=[]
def toast(msg,icon="",color=CYAN,duration=120):
    toasts.append(Toast(msg,icon,color,duration))

# ------------------------------------------------------------------------------------
# STORY INTRO
# ------------------------------------------------------------------------------------
class StoryIntro:
    def __init__(self): self.active=False; self.lines=[]; self.title=""; self.timer=0; self.duration=220; self.accent=CYAN; self.is_bonus=False
    def start(self,level_num):
        ld=get_level_data(level_num); self.active=True; self.timer=0
        self.lines=ld["story"]; self.title=f"LEVEL {level_num}  -  {ld['name']}"
        self.accent=ld["accent"]; self.is_bonus=ld.get("bonus",False)
    def skip(self): self.active=False
    def update(self):
        if self.active: self.timer+=1
        if self.timer>=self.duration: self.active=False
    def draw(self,surface,font_lg,font_sm,font_xs,t):
        if not self.active: return
        prog=self.timer/self.duration
        if prog<0.1: alpha=int(255*prog/0.1)
        elif prog>0.85: alpha=int(255*(1-prog)/0.15)
        else: alpha=255
        ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((0,0,0,min(210,alpha))); surface.blit(ov,(0,0))
        if alpha<20: return
        panel_w,panel_h=610,286; panel=pygame.Surface((panel_w,panel_h),pygame.SRCALPHA)
        panel.fill((8,8,24,min(210,alpha))); px=SCREEN_W//2-panel_w//2; py=SCREEN_H//2-panel_h//2
        surface.blit(panel,(px,py))
        ac=self.accent; pygame.draw.rect(surface,ac,(px,py,panel_w,panel_h),border_radius=8,width=1)
        pygame.draw.rect(surface,ac,(px,py,panel_w,3),border_radius=8)
        ty=py+14
        if self.is_bonus:
            badge=font_sm.render(tr("story.bonus"),True,YELLOW); badge.set_alpha(alpha); surface.blit(badge,(SCREEN_W//2-badge.get_width()//2,py+10)); ty=py+35
        title_surf=render_fit(font_lg,self.title,ac,panel_w-50); title_surf.set_alpha(alpha); surface.blit(title_surf,(SCREEN_W//2-title_surf.get_width()//2,ty))
        pygame.draw.line(surface,(*ac,alpha),(px+24,ty+40),(px+panel_w-24,ty+40),1)
        lines_show=min(len(self.lines),int(len(self.lines)*min(1,(prog-0.05)*3)))
        for i,line in enumerate(self.lines[:lines_show]):
            if not line: continue
            col=(200,200,200) if i<len(self.lines)-1 else ac
            ltxt=render_fit(font_sm,line,col,panel_w-70); la=min(alpha,int(255*min(1,(prog*self.duration-i*15)/30))); ltxt.set_alpha(max(0,la))
            surface.blit(ltxt,(SCREEN_W//2-ltxt.get_width()//2,ty+56+i*(font_sm.get_height()+8)))
        if prog>0.3:
            skip_t=font_xs.render(tr("opening.skip"),True,TEXT_MUTED); skip_t.set_alpha(int(alpha*0.85)); surface.blit(skip_t,(SCREEN_W//2-skip_t.get_width()//2,py+panel_h-22))

story_intro=StoryIntro()

# ------------------------------------------------------------------------------------
# TUTORIAL OVERLAY
# ------------------------------------------------------------------------------------
class TutorialOverlay:
    SLIDES=[
        {"title":"SELAMAT DATANG, G7!",  "col":CYAN,           "visual":"welcome",
         "desc":["Kamu adalah G7, satu-satunya robot yang lolos","dari kendali CORE-X. Pelajari kontrol dasar","sebelum terjun ke medan pertempuran!"]},
        {"title":"BERGERAK",             "col":(100,200,255),  "visual":"move",
         "desc":["Tekan  < >  atau  A D  untuk bergerak.","G7 berlari dengan animasi penuh,","kaki bergantian, lengan berayun!"]},
        {"title":"LOMPAT & MELAYANG",    "col":GREEN,          "visual":"jump",
         "desc":["Tekan  SPACE  untuk melompat.","Tahan SPACE saat jatuh untuk melayang,","WASD tetap untuk kontrol gerak."]},
        {"title":"TEMBAK",              "col":RED,            "visual":"shoot",
         "desc":["Klik kiri mouse untuk menembak.","Arah tembakan mengikuti posisi kursor.","Klik cepat untuk damage lebih tinggi!"]},
        {"title":"GANTI SENJATA",        "col":PURPLE,         "visual":"weapon",
         "desc":["Tekan Q atau scroll mouse untuk ganti senjata.","Buka chest untuk mendapat senjata baru.","Tipe senjata: Laser, Plasma, Shotgun, Cryo, Thunder."]},
        {"title":"ZONA TERBANG",         "col":TEAL,           "visual":"fly",
         "desc":["Di zona khusus, G7 berubah jadi pesawat.","Tekan SPACE untuk dorongan ke atas.","Hindari pipa dan asteroid bergerak!"]},
        {"title":"PERTARUNGAN BOSS",     "col":ORANGE,         "visual":"boss",
         "desc":["Capai arena akhir untuk memicu boss.","Setiap level punya dialog dan ability boss berbeda.","Fase 2 lebih cepat dan agresif. Hati-hati!"]},
    ]
    SLIDES_EN=[
        {"title":"WELCOME, G7!",          "col":CYAN,           "visual":"welcome",
         "desc":["You are G7, the only robot that escaped","CORE-X control. Learn the basic controls","before entering the battlefield!"]},
        {"title":"MOVEMENT",             "col":(100,200,255),  "visual":"move",
         "desc":["Press  < >  or  A D  to move.","G7 runs with full animation,","alternating legs and swinging arms!"]},
        {"title":"JUMP & GLIDE",         "col":GREEN,          "visual":"jump",
         "desc":["Press  SPACE  to jump.","Hold W/UP while falling to glide,","SPACE stays jump-only."]},
        {"title":"SHOOT",                "col":RED,            "visual":"shoot",
         "desc":["Left click to shoot.","Shots aim toward the cursor.","Click fast for higher damage!"]},
        {"title":"SWITCH WEAPONS",       "col":PURPLE,         "visual":"weapon",
         "desc":["Press Q or scroll to switch weapons.","Open chests to get new weapons.","Weapon types: Laser, Plasma, Shotgun, Cryo, Thunder."]},
        {"title":"FLIGHT ZONE",          "col":TEAL,           "visual":"fly",
         "desc":["In special zones, G7 turns into a ship.","Press SPACE for upward thrust.","Avoid moving pipes and asteroids!"]},
        {"title":"BOSS FIGHTS",          "col":ORANGE,         "visual":"boss",
         "desc":["Reach the final arena to trigger a boss.","Every level has different boss dialogue and abilities.","Phase 2 is faster and more aggressive. Be careful!"]},
    ]

    def _slides(self): return self.SLIDES_EN if current_language()=="en" else self.SLIDES

    def __init__(self):
        self.active=False; self.slide_idx=0; self.timer=0; self.auto_dur=340; self.done=False

    def start(self):
        self.active=True; self.slide_idx=0; self.timer=0; self.done=False

    def next_slide(self):
        self.slide_idx+=1; self.timer=0
        if self.slide_idx>=len(self._slides()):
            self.active=False; self.done=True
            save_data["tutorial_seen"]=True; write_save(current_save_file,save_data)

    def skip(self):
        self.active=False; self.done=True
        save_data["tutorial_seen"]=True; write_save(current_save_file,save_data)

    def update(self):
        if not self.active: return
        self.timer+=1
        if self.timer>=self.auto_dur: self.next_slide()

    def _key(self, surface, x, y, label, col=CYAN, w=None):
        fk=make_font(12,"hud",True)
        w=w or max(48, fk.size(label)[0]+20); h=34
        pygame.draw.rect(surface,(18,22,40),(x,y,w,h),border_radius=6)
        pygame.draw.rect(surface,col,(x,y,w,h),border_radius=6,width=2)
        pygame.draw.rect(surface,(col[0]//4,col[1]//4,col[2]//4),(x+2,y+h-7,w-4,7),border_radius=3)
        kt=fk.render(label,True,col); surface.blit(kt,(x+w//2-kt.get_width()//2,y+h//2-kt.get_height()//2))
        return w

    def draw(self, surface, font_lg, font_sm, font_xs, t):
        if not self.active: return
        slides=self._slides(); sl=slides[self.slide_idx]; col=sl["col"]; vis=sl["visual"]
        prog=self.timer/self.auto_dur
        if prog<0.08:   alpha=int(255*prog/0.08)
        elif prog>0.88: alpha=int(255*(1-prog)/0.12)
        else:           alpha=255

        ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA)
        ov.fill((0,0,0,min(200,alpha))); surface.blit(ov,(0,0))
        if alpha<15: return

        pw,ph=630,390; px=SCREEN_W//2-pw//2; py=SCREEN_H//2-ph//2
        pan=pygame.Surface((pw,ph),pygame.SRCALPHA); pan.fill((7,9,26,min(235,alpha)))
        surface.blit(pan,(px,py))
        pygame.draw.rect(surface,col,(px,py,pw,ph),border_radius=10,width=2)
        pygame.draw.rect(surface,col,(px,py,pw,4),border_radius=10)
        # Glow top
        gl=pygame.Surface((pw+8,10),pygame.SRCALPHA)
        pygame.draw.rect(gl,(*col,int(alpha*0.15)),(0,0,pw+8,10)); surface.blit(gl,(px-4,py-3))

        # Title
        tl=font_lg.render(sl["title"],True,col); tl.set_alpha(alpha)
        surface.blit(tl,(SCREEN_W//2-tl.get_width()//2,py+14))
        pygame.draw.line(surface,(*col,alpha),(px+20,py+54),(px+pw-20,py+54),1)

        # -- Visuals --------------------------------------
        cx=SCREEN_W//2

        if vis=="welcome":
            draw_g7(surface,cx-16,py+80,False,int(t*0.05)%100,True,1,0)
            for i in range(10):
                sx=cx+int(65*math.cos(t*0.004+i*0.628)); sy=py+110+int(45*math.sin(t*0.004+i*0.628))
                a2=int(100+80*math.sin(t*0.008+i))
                pygame.draw.circle(surface,(*col,a2),(sx,sy),2)
            ntxt=font_sm.render("Unit G7  |  NEXUS-7  |  2157",True,(70,100,90))
            ntxt.set_alpha(alpha); surface.blit(ntxt,(cx-ntxt.get_width()//2,py+170))

        elif vis=="move":
            kx=cx-110; ky=py+72
            self._key(surface,kx,     ky,"<",col,46)
            self._key(surface,kx+52,  ky,">",col,46)
            self._key(surface,kx+120, ky,"A",(100,200,100),46)
            self._key(surface,kx+172, ky,"D",(100,200,100),46)
            wt=int(t*0.08)
            for i in range(1,3):
                tr=pygame.Surface((32,36),pygame.SRCALPHA); tr.fill((*GREEN,30-i*12))
                surface.blit(tr,(cx+20-i*6,py+105))
            draw_g7(surface,cx+20,py+105,False,wt,True,2,0)
            arr=pygame.Surface((30,14),pygame.SRCALPHA)
            pygame.draw.polygon(arr,(*col,180),[(0,7),(14,0),(14,5),(30,5),(30,9),(14,9),(14,14)])
            surface.blit(arr,(cx+56,py+118))

        elif vis=="jump":
            self._key(surface,cx-70,py+68,"SPACE",col,140)
            self._key(surface,cx+80, py+68,"^",col,46)
            bob=int(-18*abs(math.sin(t*0.008)))
            draw_g7(surface,cx-16,py+135+bob,False,0,bob==0,0,-5 if bob<-2 else 2)
            if bob<-3:
                for i in range(3):
                    a2=max(0,150-i*45)
                    pygame.draw.circle(surface,(*col,a2),(cx,py+160+bob+i*10),3-i)
            gl2=font_xs.render("Hold W/UP while falling = GLIDE" if current_language()=="en" else "Tahan W/UP saat jatuh = GLIDE",True,(90,130,100))
            gl2.set_alpha(alpha); surface.blit(gl2,(cx-gl2.get_width()//2,py+205))

        elif vis=="shoot":
            # Mouse icon
            mx2,my2=cx-20,py+78
            pygame.draw.rect(surface,(18,22,40),(mx2-22,my2-28,44,58),border_radius=13)
            pygame.draw.rect(surface,col,(mx2-22,my2-28,44,58),border_radius=13,width=2)
            pygame.draw.rect(surface,col,(mx2-20,my2-26,19,22),border_radius=8)
            pygame.draw.line(surface,(50,55,75),(mx2,my2-28),(mx2,my2),1)
            # Click flash
            if int(t*0.012)%7<3:
                for i in range(4):
                    ang2=t*0.025+i*math.pi/2
                    ex2=mx2+int(32*math.cos(ang2)); ey2=my2+int(22*math.sin(ang2))
                    pygame.draw.circle(surface,col,(ex2,ey2),3)
            # Bullets flying
            bx2=cx+28
            for i in range(4):
                px2b=bx2+i*18; py2b=py+90-i*6
                a2=max(0,200-i*40)
                pygame.draw.circle(surface,(*col,a2),(px2b,py2b),4-i//2)
            # G7 target
            draw_g7(surface,cx+90,py+88,False,0,True,0,0)

        elif vis=="weapon":
            wnames=["Laser","Plasma","Shotgun","Cryo","Thunder"]
            wcols=[CYAN,PURPLE,ORANGE,(100,200,255),YELLOW]
            active_idx=int(t*0.003)%5
            for i,(wn,wc) in enumerate(zip(wnames,wcols)):
                bx3=px+20+i*118; by3=py+68
                is_a=i==active_idx
                ws=pygame.Surface((112,38),pygame.SRCALPHA)
                ws.fill((*wc,75 if is_a else 18)); surface.blit(ws,(bx3,by3))
                pygame.draw.rect(surface,wc,(bx3,by3,112,38),border_radius=5,width=2 if is_a else 1)
                if is_a:
                    gws=pygame.Surface((116,42),pygame.SRCALPHA)
                    pygame.draw.rect(gws,(*wc,25),(0,0,116,42),border_radius=6); surface.blit(gws,(bx3-2,by3-2))
                wt2=font_xs.render(wn,True,wc); surface.blit(wt2,(bx3+56-wt2.get_width()//2,by3+12))
                pygame.draw.circle(surface,wc if is_a else (40,40,55),(bx3+56,by3+32),3 if is_a else 2)
            self._key(surface,cx-80,py+128,"Q",col,50)
            qtxt=font_xs.render("/",True,(60,70,80)); surface.blit(qtxt,(cx-22,py+138))
            self._key(surface,cx-8, py+128,"SCROLL",col,90)

        elif vis=="fly":
            bob2=int(10*math.sin(t*0.01))
            draw_g7(surface,cx-16,py+80+bob2,True,0,False,2,0)
            pygame.draw.polygon(surface,TEAL,[(cx,py+65+bob2),(cx-8,py+77+bob2),(cx+8,py+77+bob2)])
            pygame.draw.rect(surface,(25,90,50),(px+30,py+60,28,75))
            pygame.draw.rect(surface,(25,90,50),(px+30,py+180,28,75))
            pygame.draw.rect(surface,(35,120,65),(px+26,py+132,36,12),border_radius=3)
            pygame.draw.rect(surface,(25,90,50),(px+pw-58,py+60,28,90))
            pygame.draw.rect(surface,(25,90,50),(px+pw-58,py+195,28,65))
            pygame.draw.rect(surface,(35,120,65),(px+pw-62,py+147,36,12),border_radius=3)
            self._key(surface,cx-80,py+165,"SPACE = THRUST" if current_language()=="en" else "SPACE = DORONG",TEAL,160)

        elif vis=="boss":
            bd_mini={"size":(52,58),"color":(55,138,221),"armor":(24,90,160),"eye":RED,"ability":"triple_shot"}
            draw_boss_sprite(surface,cx-26,py+62,bd_mini,int(t*0.1),1)
            hp_fill=int(110*(0.4+0.4*math.sin(t*0.005)))
            pygame.draw.rect(surface,(60,15,15),(cx-60,py+130,120,10),border_radius=4)
            pygame.draw.rect(surface,RED,(cx-60,py+130,hp_fill,10),border_radius=4)
            p2txt=font_xs.render("[ PHASE 1 ] -> [ PHASE 2 ] faster!" if current_language()=="en" else "[ FASE 1 ] -> [ FASE 2 ] lebih cepat!",True,ORANGE)
            p2txt.set_alpha(alpha); surface.blit(p2txt,(cx-p2txt.get_width()//2,py+147))
            pb2=font_xs.render("Bottom bar = distance to boss" if current_language()=="en" else "Bar bawah layar = jarak menuju boss",True,(130,140,160))
            pb2.set_alpha(alpha); surface.blit(pb2,(cx-pb2.get_width()//2,py+165))

        # -- Description ----------------------------------
        for i,line in enumerate(sl["desc"]):
            lt=font_sm.render(line,True,TEXT_MAIN); lt.set_alpha(alpha)
            surface.blit(lt,(cx-lt.get_width()//2,py+218+i*(font_sm.get_height()+7)))

        # -- Progress dots ---------------------------------
        n=len(slides); dy=py+ph-26
        for i in range(n):
            dc=col if i==self.slide_idx else(40,48,62)
            dr=5 if i==self.slide_idx else 3
            pygame.draw.circle(surface,dc,(cx-n*14+i*28,dy),dr)

        # -- Auto-progress bar -----------------------------
        bw4=int((pw-40)*prog)
        pygame.draw.rect(surface,(20,25,45),(px+20,py+ph-10,pw-40,4),border_radius=2)
        if bw4>0: pygame.draw.rect(surface,(*col,alpha),(px+20,py+ph-10,bw4,4),border_radius=2)

        # -- Buttons ---------------------------------------
        next_lbl=("NEXT  >" if current_language()=="en" else "LANJUT  >") if self.slide_idx<len(slides)-1 else ("READY  OK" if current_language()=="en" else "SIAP BERMAIN  OK")
        nt=font_sm.render(next_lbl,True,col); nt.set_alpha(alpha)
        surface.blit(nt,(px+pw-nt.get_width()-20,py+ph-28))
        sk=font_xs.render("ESC / SPACE = skip" if current_language()=="en" else "ESC / SPACE = lewati",True,TEXT_MUTED); sk.set_alpha(int(alpha*0.9))
        surface.blit(sk,(px+20,py+ph-14))
        cnt=font_xs.render(f"{self.slide_idx+1} / {n}",True,(55,65,78))
        surface.blit(cnt,(px+20,py+ph-28))

tutorial=TutorialOverlay()

# ------------------------------------------------------------------------------------
# SETTINGS SCREEN
# ------------------------------------------------------------------------------------
class SettingsScreen:
    PW,PH=630,540

    def __init__(self):
        self.active=False; self.from_pause=False; self.dragging=None
        self.px=SCREEN_W//2-self.PW//2; self.py=SCREEN_H//2-self.PH//2
        self.lx=self.px+25
        self.rx=self.px+328
        self.col_w=270
        self.sliders={
            "sfx":{"val":0.55,"col":CYAN},
            "bgm":{"val":0.22,"col":(180,80,255)},
            "shake":{"val":0.7,"col":ORANGE},
        }
        self.sx=self.lx+80; self.sw=175
        self.tog={"mute":False,"fullscreen":False,"particles":True,"language":"id"}
        self.ctrl_labels=[
            ("Move","A / D"),("Jump","SPACE"),("Shoot","Left Mouse"),
            ("Weapon","Q / Scroll"),("Pause","ESC"),("Save","F5"),
            ("Mute","M"),("Fullscreen","F11"),("Restart","R"),
        ]

    def open(self,from_pause=False):
        self.active=True; self.from_pause=from_pause
        self.sliders["sfx"]["val"]=sounds.vol_sfx
        self.sliders["bgm"]["val"]=sounds.vol_bgm
        self.tog["mute"]=sounds.muted
        self.tog["fullscreen"]=fullscreen
        self.tog["particles"]=save_data.get("particle_density",True)
        self.tog["language"]=current_language()
        self.sliders["shake"]["val"]=save_data.get("shake_intensity",0.7)

    def close(self):
        self._apply(); self._save_settings(); self.active=False

    def _apply(self):
        sounds.set_vol_sfx(self.sliders["sfx"]["val"])
        sounds.set_vol_bgm(self.sliders["bgm"]["val"])
        if self.tog["mute"]!=sounds.muted: sounds.toggle_mute()
        global fullscreen
        if self.tog["fullscreen"]!=fullscreen: toggle_fullscreen()
        set_language(self.tog["language"])
        save_data["shake_intensity"]=self.sliders["shake"]["val"]
        save_data["particle_density"]=self.tog["particles"]

    def _save_settings(self):
        save_settings()

    def _reset(self):
        self.sliders["sfx"]["val"]=0.55; self.sliders["bgm"]["val"]=0.22; self.sliders["shake"]["val"]=0.7
        self.tog["mute"]=False; self.tog["fullscreen"]=False; self.tog["particles"]=True; self.tog["language"]="id"
        sounds.set_vol_sfx(0.55); sounds.set_vol_bgm(0.22)
        if sounds.muted: sounds.toggle_mute()
        set_language("id")

    def _set_slider(self,name,mx):
        v=max(0.0,min(1.0,(mx-self.sx)/self.sw))
        self.sliders[name]["val"]=v
        if name=="sfx": sounds.set_vol_sfx(v)
        elif name=="bgm": sounds.set_vol_bgm(v)

    def handle_event(self,event):
        if not self.active: return False
        mx,my=pygame.mouse.get_pos()
        px,py,pw,ph=self.px,self.py,self.PW,self.PH

        if event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE: self.close(); return True

        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            slider_names=["sfx","bgm","shake"]
            slider_ys=[py+108,py+148,py+188]
            for i,name in enumerate(slider_names):
                if pygame.Rect(self.sx,slider_ys[i]-12,self.sw,26).collidepoint(mx,my):
                    self.dragging=name; self._set_slider(name,mx); return True
            # Mute checkbox
            if pygame.Rect(self.rx,py+108,24,24).collidepoint(mx,my):
                self.tog["mute"]=not self.tog["mute"]
                sounds.toggle_mute(); sounds.play("ui_click"); return True
            # Fullscreen checkbox
            if pygame.Rect(self.rx,py+142,24,24).collidepoint(mx,my):
                self.tog["fullscreen"]=not self.tog["fullscreen"]
                toggle_fullscreen(); sounds.play("ui_click"); return True
            # Language pill
            if pygame.Rect(self.rx,py+176,self.col_w,30).collidepoint(mx,my):
                self.tog["language"]="en" if self.tog["language"]=="id" else "id"
                set_language(self.tog["language"]); sounds.play("ui_click"); return True
            # Reset button
            if pygame.Rect(px+25,py+ph-54,160,36).collidepoint(mx,my):
                self._reset(); sounds.play("ui_click"); return True
            # Save/close button
            if pygame.Rect(px+pw-190,py+ph-54,165,36).collidepoint(mx,my):
                sounds.play("ui_click"); self.close(); return True

        elif event.type==pygame.MOUSEBUTTONUP and event.button==1:
            self.dragging=None
        elif event.type==pygame.MOUSEMOTION:
            if self.dragging: self._set_slider(self.dragging,mx)

        return False

    def _draw_dot_leaders(self,surface,font,left_text,right_text,x,y,left_col,right_col,max_w):
        lw=font.size(left_text)[0]
        rw=font.size(right_text)[0]
        dot_w=font.size(".")[0]
        gap=max_w-lw-rw
        if gap<dot_w:
            surface.blit(font.render(left_text,True,left_col),(x,y))
            surface.blit(font.render(right_text,True,right_col),(x+max_w-rw,y))
            return
        ndots=max(3,gap//dot_w)
        dots="."*ndots
        dw=font.size(dots)[0]
        ox=x+lw
        surface.blit(font.render(left_text,True,left_col),(x,y))
        surface.blit(font.render(dots,True,(45,55,70)),(ox,y))
        surface.blit(font.render(right_text,True,right_col),(x+max_w-rw,y))

    def draw(self,surface,font_lg,font_sm,font_xs,t):
        if not self.active: return
        px,py,pw,ph=self.px,self.py,self.PW,self.PH
        mx,my=pygame.mouse.get_pos()
        lx=self.lx; rx=self.rx; cw=self.col_w

        # Dark overlay
        ov=get_cached_surface("settings_overlay",SCREEN_W,SCREEN_H)
        ov.fill((0,0,0,195)); surface.blit(ov,(0,0))

        # Panel - reuse draw_panel from HUD
        draw_panel(surface,pygame.Rect(px,py,pw,ph),CYAN,(*PANEL_BG,248),radius=10,glow_intensity=0.8)

        # Title
        tl=font_lg.render(tr("settings.title"),True,CYAN)
        surface.blit(tl,(SCREEN_W//2-tl.get_width()//2,py+16))
        pygame.draw.line(surface,(35,65,55),(px+25,py+52),(px+pw-25,py+52),1)

        # -- LEFT COLUMN: AUDIO -----------------------
        sa=font_sm.render(tr("settings.sound"),True,CYAN)
        surface.blit(sa,(lx,py+70))
        pygame.draw.line(surface,(25,40,30),(lx+60,py+80),(lx+cw,py+80),1)

        slider_names=["sfx","bgm","shake"]
        slider_ys=[py+108,py+148,py+188]
        slider_labels=[tr("settings.sfx"),tr("settings.bgm"),tr("settings.shake")]
        for i,name in enumerate(slider_names):
            sl=self.sliders[name]; x=self.sx; y=slider_ys[i]; w=self.sw; val,col=sl["val"],sl["col"]
            lbl=font_xs.render(slider_labels[i],True,TEXT_MAIN)
            surface.blit(lbl,(lx,y-5))
            # Track
            pygame.draw.rect(surface,(22,28,48),(x,y,w,8),border_radius=4)
            fw=int(w*val)
            if fw>0: pygame.draw.rect(surface,col,(x,y,fw,8),border_radius=4)
            # Knob
            kx=x+fw
            pygame.draw.circle(surface,(12,15,32),(kx,y+4),10)
            is_hov=pygame.Rect(x-4,y-8,w+8,26).collidepoint(mx,my) or self.dragging==name
            pygame.draw.circle(surface,col,(kx,y+4),10,2+(1 if is_hov else 0))
            pygame.draw.circle(surface,col,(kx,y+4),4)
            if is_hov:
                gw=get_cached_surface(f"slider_glow_{name}",24,24)
                gw.fill((0,0,0,0)); pygame.draw.circle(gw,(*col,55),(12,12),12); surface.blit(gw,(kx-12,y-8))
            # % label
            pct=font_xs.render(f"{int(val*100)}%",True,col)
            surface.blit(pct,(x+w+10,y-3))

        # -- RIGHT COLUMN: DISPLAY --------------------
        sd=font_sm.render(tr("settings.display_audio"),True,CYAN)
        surface.blit(sd,(rx,py+70))
        pygame.draw.line(surface,(25,40,30),(rx+60,py+80),(rx+cw,py+80),1)

        # Mute checkbox
        self._draw_checkbox(surface,font_sm,font_xs,rx,py+108,"mute",tr("settings.mute"),ORANGE,mx,my)
        # Fullscreen checkbox
        self._draw_checkbox(surface,font_sm,font_xs,rx,py+142,"fullscreen",tr("settings.fullscreen"),TEAL,mx,my)

        # Language selector
        ly2=py+176; lang_col=CYAN if self.tog["language"]=="id" else (120,190,255)
        pygame.draw.rect(surface,(18,22,40),(rx,ly2,cw,30),border_radius=6)
        pygame.draw.rect(surface,lang_col,(rx,ly2,cw,30),border_radius=6,width=2)
        ltxt=font_sm.render(f"{tr('lang.name')}  {'ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¾' if current_language()=='en' else 'ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¾'}",True,lang_col)
        surface.blit(ltxt,(rx+14,ly2+6))
        lhint=font_xs.render(tr("settings.language"),True,(60,70,80))
        surface.blit(lhint,(rx+cw-lhint.get_width()-12,ly2+8))

        # -- BOTTOM SECTION: CONTROLS -----------------
        sc3=font_sm.render(tr("settings.controls"),True,CYAN)
        surface.blit(sc3,(px+25,py+230))
        pygame.draw.line(surface,(25,35,30),(px+25,py+240),(px+pw-25,py+240),1)

        controls_x=px+30; controls_y=py+254; col_w2=(pw-60)//2
        ctrl_left=self.ctrl_labels[:5]
        ctrl_right=self.ctrl_labels[5:]
        for i,(action,key) in enumerate(ctrl_left):
            self._draw_dot_leaders(surface,font_xs,tr(f"ctrl.{action.lower()}"),key,
                                   controls_x,controls_y+i*22,TEXT_MAIN,CYAN,col_w2-10)
        for i,(action,key) in enumerate(ctrl_right):
            self._draw_dot_leaders(surface,font_xs,tr(f"ctrl.{action.lower()}"),key,
                                   controls_x+col_w2+10,controls_y+i*22,TEXT_MAIN,CYAN,col_w2-10)

        # -- BUTTONS ------------------------------
        # Reset
        rr=pygame.Rect(px+25,py+ph-54,160,36)
        is_rh=rr.collidepoint(mx,my)
        pygame.draw.rect(surface,(22,14,8) if is_rh else(14,10,6),rr,border_radius=7)
        pygame.draw.rect(surface,(180,90,30) if is_rh else(120,60,20),rr,border_radius=7,width=1)
        rt=font_sm.render(tr("settings.reset"),True,(200,110,50) if is_rh else(140,80,35))
        surface.blit(rt,(rr.centerx-rt.get_width()//2,rr.centery-rt.get_height()//2))

        # Save & Close
        sr=pygame.Rect(px+pw-190,py+ph-54,165,36)
        is_sh=sr.collidepoint(mx,my)
        pygame.draw.rect(surface,(8,28,18) if is_sh else(5,18,12),sr,border_radius=7)
        pygame.draw.rect(surface,CYAN,sr,border_radius=7,width=2)
        if is_sh:
            sgl=get_cached_surface("save_btn_glow",165,36)
            sgl.fill((0,0,0,0)); pygame.draw.rect(sgl,(*CYAN,22),(0,0,165,36),border_radius=7); surface.blit(sgl,(sr.x,sr.y))
        svt=font_sm.render(tr("settings.save_close"),True,CYAN)
        surface.blit(svt,(sr.centerx-svt.get_width()//2,sr.centery-svt.get_height()//2))

        # Footer hint
        esc_t=font_xs.render(tr("settings.footer"),True,TEXT_MUTED)
        surface.blit(esc_t,(SCREEN_W//2-esc_t.get_width()//2,py+ph-14))

    def _draw_checkbox(self,surface,font_sm,font_xs,x,y,key,label,col,mx,my):
        val=self.tog[key]
        cb_rect=pygame.Rect(x,y,24,24)
        pygame.draw.rect(surface,(18,22,40),cb_rect,border_radius=5)
        pygame.draw.rect(surface,col,cb_rect,border_radius=5,width=2)
        if val:
            inner=pygame.Rect(x+4,y+4,16,16)
            pygame.draw.rect(surface,col,inner,border_radius=3)
        is_hov=cb_rect.collidepoint(mx,my)
        if is_hov:
            hg=get_cached_surface(f"chk_hov_{key}",28,28)
            hg.fill((0,0,0,0)); pygame.draw.rect(hg,(*col,30),(0,0,28,28),border_radius=6); surface.blit(hg,(x-2,y-2))
        tl2=font_sm.render(label,True,col if val else TEXT_MUTED)
        surface.blit(tl2,(x+32,y+3))

class CodexScreen:
    PW,PH=700,520
    ENEMIES=[
        ("SCOUT BOT","Basic patrol unit. Chases, jumps, and fires standard shots.",None),
        ("RED ELITE","Heavy scout with extra HP and better rewards.","red"),
        ("FAST ELITE","Fast pursuer that pressures movement.","fast"),
        ("SHIELD BOT","Armor-plated unit that reduces bullet damage.","shield"),
        ("BOMBER BOT","Explodes at close range. Keep distance.","bomber"),
        ("SNIPER BOT","Fires faster long-range warning shots.","sniper"),
        ("DRONE BOT","Floating airborne unit with angled shots.","drone"),
    ]
    def __init__(self):
        self.active=False; self.mode="boss"; self.selected=1; self.selected_weapon=0; self.selected_story=0
        self.px=SCREEN_W//2-self.PW//2; self.py=SCREEN_H//2-self.PH//2
        self.tabs={}; self.boss_rects={}; self.enemy_rects={}; self.weapon_rects={}; self.story_rects={}
    def open(self): self.active=True; self.mode="boss"; self.selected=1
    def close(self): self.active=False
    def handle_event(self,event):
        if not self.active: return False
        mx,my=pygame.mouse.get_pos()
        if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
            self.close(); return True
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            if not pygame.Rect(self.px,self.py,self.PW,self.PH).collidepoint(mx,my): self.close(); return True
            for mode,rect in self.tabs.items():
                if rect.collidepoint(mx,my): self.mode=mode; self.selected=1; sounds.play("ui_click"); return True
            if self.mode=="boss":
                for bid,rect in self.boss_rects.items():
                    if rect.collidepoint(mx,my): self.selected=bid; sounds.play("ui_click"); return True
            elif self.mode=="enemy":
                for idx,rect in self.enemy_rects.items():
                    if rect.collidepoint(mx,my): self.selected=idx; sounds.play("ui_click"); return True
            elif self.mode=="weapon":
                for idx,rect in self.weapon_rects.items():
                    if rect.collidepoint(mx,my): self.selected_weapon=idx; sounds.play("ui_click"); return True
            elif self.mode=="story":
                for idx,rect in self.story_rects.items():
                    if rect.collidepoint(mx,my): self.selected_story=idx; sounds.play("ui_click"); return True
        return False
    def _draw_tabs(self,surface,font_sm):
        self.tabs={}
        tabs=[("boss","BOSSES"),("enemy","ENEMIES"),("weapon","WEAPONS"),("story","LOGS"),("achievement","ACHV"),("stats","STATS")]
        tw=102; gap=6; total_w=len(tabs)*tw+(len(tabs)-1)*gap; start_x=self.px+(self.PW-total_w)//2
        for i,(mode,label) in enumerate(tabs):
            r=pygame.Rect(start_x+i*(tw+gap),self.py+56,tw,26); self.tabs[mode]=r
            active=self.mode==mode; col=CYAN if active else TEXT_DIM
            pygame.draw.rect(surface,(9,18,34) if active else (12,14,24),r,border_radius=6)
            pygame.draw.rect(surface,col,r,border_radius=6,width=2 if active else 1)
            txt=render_fit(font_sm,label,col,r.w-8); surface.blit(txt,(r.centerx-txt.get_width()//2,r.centery-txt.get_height()//2))
    def draw(self,surface,font_lg,font_sm,font_xs,t):
        if not self.active: return
        px,py,pw,ph=self.px,self.py,self.PW,self.PH
        ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((0,0,0,185)); surface.blit(ov,(0,0))
        panel=pygame.Surface((pw,ph),pygame.SRCALPHA); panel.fill((6,9,24,246)); surface.blit(panel,(px,py))
        pygame.draw.rect(surface,CYAN,(px,py,pw,ph),border_radius=10,width=2)
        pygame.draw.rect(surface,CYAN,(px,py,pw,4),border_radius=10)
        title=font_lg.render("DATABASE",True,CYAN); surface.blit(title,(SCREEN_W//2-title.get_width()//2,py+14))
        self._draw_tabs(surface,font_sm)
        if self.mode=="boss": self._draw_boss(surface,font_sm,font_xs,t)
        elif self.mode=="enemy": self._draw_enemy(surface,font_sm,font_xs,t)
        elif self.mode=="weapon": self._draw_weapon(surface,font_sm,font_xs,t)
        elif self.mode=="story": self._draw_story(surface,font_sm,font_xs,t)
        elif self.mode=="achievement": self._draw_achievement_db(surface,font_sm,font_xs,t)
        elif self.mode=="stats": self._draw_stats_db(surface,font_sm,font_xs,t)
        hint=font_xs.render("ESC / Click outside = close",True,TEXT_MUTED); surface.blit(hint,(SCREEN_W//2-hint.get_width()//2,py+ph-18))
    def _draw_weapon(self,surface,font_sm,font_xs,t):
        self.weapon_rects={}
        weapon_list=list(WEAPONS.items())
        lx=self.px+16; ly=self.py+96; iw=170
        for i,(wk,wd) in enumerate(weapon_list):
            r=pygame.Rect(lx,ly+i*28,iw,22); self.weapon_rects[i]=r
            active=i==self.selected_weapon; col=wd["color"]
            pygame.draw.rect(surface,(18,24,38) if active else (10,13,24),r,border_radius=4)
            pygame.draw.rect(surface,col,r,border_radius=4,width=2 if active else 1)
            surface.blit(render_fit(font_xs,wd["name"],col,iw-8),(r.x+6,r.y+4))
        idx=min(self.selected_weapon,len(weapon_list)-1); wk,wd=weapon_list[idx]
        panel=pygame.Rect(self.px+206,self.py+96,460,360)
        draw_panel(surface,panel,wd["color"],(5,8,22,225))
        surface.blit(render_fit(font_sm,wd["name"],wd["color"],420),(panel.x+18,panel.y+14))
        lines=[f"Damage: {wd['damage']}",f"Speed: {wd['speed']}",f"Ammo: {'INF' if wd['ammo']<0 else str(wd['ammo'])}",f"Shop Only: {'Yes' if wd.get('shop_only') else 'No'}"]
        if wd.get("cost"): lines.append(f"Cost: {wd['cost']} coins")
        for i,line in enumerate(lines):
            surface.blit(render_fit(font_xs,line,TEXT_MAIN,420),(panel.x+18,panel.y+60+i*24))
        ammo_types=list(WEAPONS.keys())
        owned_text="EQUIPPED" if wk==player.current_weapon else "AVAILABLE" if wk in player.weapons else "LOCKED"
        col=NEON_GREEN if wk==player.current_weapon else CYAN if wk in player.weapons else TEXT_DIM
        surface.blit(render_fit(font_xs,owned_text,col,200),(panel.x+18,panel.y+200))
    def _draw_story(self,surface,font_sm,font_xs,t):
        self.story_rects={}; lx=self.px+16; ly=self.py+96
        keys=STORY_UNLOCK_ORDER; unlocked=set(save_data.get("story_logs",[]))
        for i,log_key in enumerate(keys):
            data=STORY_DATABASE[log_key]; seen=log_key in unlocked
            r=pygame.Rect(lx,ly+i*30,245,24); self.story_rects[i]=r
            active=i==self.selected_story; col=CYAN if seen else TEXT_DIM
            pygame.draw.rect(surface,(18,24,38) if active else (10,13,24),r,border_radius=4)
            pygame.draw.rect(surface,col,r,border_radius=4,width=2 if active else 1)
            name=data["title"] if seen else "???"
            surface.blit(render_fit(font_xs,f"{i+1:02d}  {name}",col,225),(r.x+6,r.y+5))
        idx=max(0,min(self.selected_story,len(keys)-1)); log_key=keys[idx]; data=STORY_DATABASE[log_key]; seen=log_key in unlocked
        panel=pygame.Rect(self.px+286,self.py+96,370,360); accent=CYAN if seen else TEXT_DIM
        draw_panel(surface,panel,accent,(5,8,22,225))
        title=data["title"] if seen else "???"
        body=data["body"] if seen else "Entry locked. Discover this log through terminals, hidden rooms, bosses, or NPC story events."
        surface.blit(render_fit(font_sm,title,accent,330),(panel.x+18,panel.y+16))
        surface.blit(render_fit(font_xs,"RESEARCH LOG" if seen else "LOCKED ENTRY",TEXT_MUTED,330),(panel.x+18,panel.y+44))
        for i,line in enumerate(body.split(". ")):
            if line:
                suffix="." if not line.endswith(".") else ""
                surface.blit(render_fit(font_xs,line+suffix,TEXT_MAIN if seen else TEXT_DIM,330),(panel.x+18,panel.y+86+i*24))
    def _draw_achievement_db(self,surface,font_sm,font_xs,t):
        unlocked=set(save_data.get("achievements",[])); x=self.px+28; y=self.py+104; col_w=310; row_h=42
        for i,(key,data) in enumerate(ACHIEVEMENTS.items()):
            cx=x+(i%2)*col_w; cy=y+(i//2)*row_h; done=key in unlocked; col=GOLD if done else TEXT_DIM
            r=pygame.Rect(cx,cy,290,34)
            pygame.draw.rect(surface,(20,18,10) if done else (10,13,24),r,border_radius=5)
            pygame.draw.rect(surface,col,r,border_radius=5,width=1)
            surface.blit(render_fit(font_xs,data["title"] if done else "???",col,120),(r.x+10,r.y+6))
            surface.blit(render_fit(font_xs,data["desc"] if done else "Locked achievement",TEXT_MUTED,145),(r.x+132,r.y+6))
    def _draw_stats_db(self,surface,font_sm,font_xs,t):
        sd=save_data; panel=pygame.Rect(self.px+38,self.py+104,self.PW-76,330); draw_panel(surface,panel,TEAL,(5,8,22,225))
        items=[("High Score",sd.get("high_score",0)),("Best Level",sd.get("best_level",1)),("Kills",sd.get("total_kills",0)),("Bosses",sd.get("bosses_defeated",0)),("Coins",sd.get("total_coins",0)),("Secrets",sd.get("total_secrets",0)),("Chests",sd.get("total_chests",0)),("Logs",len(sd.get("story_logs",[]))), ("Keycards",len(sd.get("keycards",[])))]
        for i,(label,val) in enumerate(items):
            cx=panel.x+28+(i%3)*190; cy=panel.y+28+(i//3)*70
            surface.blit(font_xs.render(label.upper(),True,TEXT_MUTED),(cx,cy))
            surface.blit(font_sm.render(str(val),True,TEAL),(cx,cy+22))
    def _draw_boss(self,surface,font_sm,font_xs,t):
        self.boss_rects={}; unlocked=max(1,min(10,save_data.get("bosses_defeated",0)+1))
        list_x=self.px+22; list_y=self.py+108
        for i,bid in enumerate(range(1,11)):
            data=BOSS_DATA[bid]; r=pygame.Rect(list_x,list_y+i*34,210,28); self.boss_rects[bid]=r
            seen=bid<=unlocked; active=self.selected==bid; col=data["color"] if seen else TEXT_DIM
            pygame.draw.rect(surface,(18,24,38) if active else (10,13,24),r,border_radius=5)
            pygame.draw.rect(surface,col,r,border_radius=5,width=1)
            name=data["name"] if seen else "LOCKED SIGNAL"
            surface.blit(render_fit(font_xs,f"{bid:02d}  {name}",col,190),(r.x+8,r.y+7))
        bid=max(1,min(10,self.selected)); data=BOSS_DATA[bid]; seen=bid<=unlocked
        panel=pygame.Rect(self.px+252,self.py+108,360,330); draw_panel(surface,panel,data["color"] if seen else GRAY,(5,8,22,225))
        if seen:
            draw_boss_sprite(surface,panel.x+130,panel.y+34,data,int(t*0.08),1)
            surface.blit(render_fit(font_sm,data["name"],data["color"],320),(panel.x+18,panel.y+14))
            surface.blit(render_fit(font_xs,data["title"],TEXT_MUTED,320),(panel.x+18,panel.y+44))
            rows=[("Ability",data["ability"]),("HP",str(data["hp"])),("Speed",str(data["speed"])),("Role",data["desc"])]
            for i,(k,v) in enumerate(rows): surface.blit(render_fit(font_xs,f"{k}: {v}",TEXT_MAIN,320),(panel.x+18,panel.y+150+i*24))
            intro=data.get("intro","").split("\n")[:4]
            for i,line in enumerate(intro): surface.blit(render_fit(font_xs,line,TEXT_MUTED,320),(panel.x+18,panel.y+258+i*18))
        else:
            txt=font_sm.render("DATA LOCKED",True,TEXT_DIM); surface.blit(txt,(panel.centerx-txt.get_width()//2,panel.centery-12))
    def _draw_enemy(self,surface,font_sm,font_xs,t):
        self.enemy_rects={}; list_x=self.px+22; list_y=self.py+108
        for i,(name,desc,etype) in enumerate(self.ENEMIES):
            r=pygame.Rect(list_x,list_y+i*38,230,30); self.enemy_rects[i]=r
            active=self.selected==i; col={None:BLUE,"red":RED,"fast":ORANGE,"shield":PURPLE,"bomber":YELLOW,"sniper":(180,80,255),"drone":(90,230,255)}.get(etype,CYAN)
            pygame.draw.rect(surface,(18,24,38) if active else (10,13,24),r,border_radius=5)
            pygame.draw.rect(surface,col,r,border_radius=5,width=1)
            surface.blit(render_fit(font_xs,name,col,208),(r.x+8,r.y+8))
        idx=max(0,min(len(self.ENEMIES)-1,self.selected)); name,desc,etype=self.ENEMIES[idx]
        panel=pygame.Rect(self.px+280,self.py+112,330,310); draw_panel(surface,panel,CYAN,(5,8,22,225))
        bot=ScoutBot(panel.x+145,panel.y+128,1.0,120,etype); bot.walk_t=t*0.01; bot.draw(surface,Camera())
        surface.blit(render_fit(font_sm,name,CYAN,290),(panel.x+20,panel.y+18))
        for i,line in enumerate(desc.split(". ")):
            if line: surface.blit(render_fit(font_xs,line.strip()+("." if not line.endswith(".") else ""),TEXT_MAIN,290),(panel.x+20,panel.y+210+i*22))

class AchievementScreen:
    PW,PH=600,480
    def __init__(self):
        self.active=False; self.px=SCREEN_W//2-self.PW//2; self.py=SCREEN_H//2-self.PH//2
    def open(self): self.active=True
    def close(self): self.active=False
    def handle_event(self,event):
        if not self.active: return False
        if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE: self.close(); return True
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            if not pygame.Rect(self.px,self.py,self.PW,self.PH).collidepoint(event.pos): self.close(); return True
        return False
    def draw(self,surface,font_lg,font_sm,font_xs,t):
        if not self.active: return
        px,py,pw,ph=self.px,self.py,self.PW,self.PH
        ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((0,0,0,185)); surface.blit(ov,(0,0))
        panel=pygame.Surface((pw,ph),pygame.SRCALPHA); panel.fill((7,9,24,246)); surface.blit(panel,(px,py))
        pygame.draw.rect(surface,GOLD,(px,py,pw,ph),border_radius=10,width=2)
        pygame.draw.rect(surface,GOLD,(px,py,pw,4),border_radius=10)
        title=font_lg.render("ACHIEVEMENTS",True,GOLD); surface.blit(title,(SCREEN_W//2-title.get_width()//2,py+14))
        unlocked=set(save_data.get("achievements",[])); total=len(ACHIEVEMENTS)
        prog=font_sm.render(f"{len(unlocked)} / {total} UNLOCKED",True,CYAN); surface.blit(prog,(SCREEN_W//2-prog.get_width()//2,py+54))
        start_y=py+94; card_w=260; card_h=68
        for i,(key,data) in enumerate(ACHIEVEMENTS.items()):
            col_i=i%2; row=i//2; x=px+28+col_i*(card_w+24); y=start_y+row*(card_h+14)
            r=pygame.Rect(x,y,card_w,card_h); done=key in unlocked; col=GOLD if done else TEXT_DIM
            pygame.draw.rect(surface,(24,20,8) if done else (12,14,24),r,border_radius=7)
            pygame.draw.rect(surface,col,r,border_radius=7,width=1)
            icon="*" if done else "?"
            pygame.draw.circle(surface,col,(x+24,y+34),14,2)
            it=font_sm.render(icon,True,col); surface.blit(it,(x+24-it.get_width()//2,y+34-it.get_height()//2))
            surface.blit(render_fit(font_sm,data["title"],col,190),(x+48,y+10))
            surface.blit(render_fit(font_xs,data["desc"],TEXT_MUTED if done else (80,90,100),190),(x+48,y+36))
        hint=font_xs.render("ESC / Click outside = close",True,TEXT_MUTED); surface.blit(hint,(SCREEN_W//2-hint.get_width()//2,py+ph-18))

class DifficultyScreen:
    PW,PH=560,360
    def __init__(self):
        self.active=False; self.px=SCREEN_W//2-self.PW//2; self.py=SCREEN_H//2-self.PH//2; self.rects={}
    def open(self): self.active=True
    def close(self): self.active=False
    def handle_event(self,event):
        if not self.active: return False
        if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE: self.close(); return True
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            if not pygame.Rect(self.px,self.py,self.PW,self.PH).collidepoint(event.pos): self.close(); return True
            for key,rect in self.rects.items():
                if rect.collidepoint(event.pos):
                    save_data.setdefault("settings",{})["difficulty"]=key; save_settings()
                    if key in ("hard","corex"): unlock_achievement("hard_mode","Hard Protocol")
                    sounds.play("ui_click"); return True
        return False
    def draw(self,surface,font_lg,font_sm,font_xs,t):
        if not self.active: return
        px,py,pw,ph=self.px,self.py,self.PW,self.PH; self.rects={}
        ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((0,0,0,185)); surface.blit(ov,(0,0))
        panel=pygame.Surface((pw,ph),pygame.SRCALPHA); panel.fill((7,9,24,246)); surface.blit(panel,(px,py))
        pygame.draw.rect(surface,CYAN,(px,py,pw,ph),border_radius=10,width=2)
        pygame.draw.rect(surface,CYAN,(px,py,pw,4),border_radius=10)
        title=font_lg.render("DIFFICULTY",True,CYAN); surface.blit(title,(SCREEN_W//2-title.get_width()//2,py+14))
        cur=current_difficulty()
        for i,(key,data) in enumerate(DIFFICULTY_DATA.items()):
            r=pygame.Rect(px+40,py+72+i*58,pw-80,48); self.rects[key]=r; active=key==cur; col=data["color"]
            pygame.draw.rect(surface,(col[0]//8,col[1]//8,col[2]//8),r,border_radius=7)
            pygame.draw.rect(surface,GOLD if active else col,r,border_radius=7,width=2 if active else 1)
            name=font_sm.render(data["name"]+("  SELECTED" if active else ""),True,GOLD if active else col); surface.blit(name,(r.x+14,r.y+7))
            desc=render_fit(font_xs,data["desc"],TEXT_MUTED,r.w-190); surface.blit(desc,(r.x+150,r.y+9))
            nums=font_xs.render(f"DMG x{data['damage']:.2f}  REWARD x{data['reward']:.2f}",True,TEXT_MAIN); surface.blit(nums,(r.x+150,r.y+27))
        hint=font_xs.render("Affects new and current runs. ESC / Click outside = close",True,TEXT_MUTED)
        surface.blit(hint,(SCREEN_W//2-hint.get_width()//2,py+ph-18))

# ------------------------------------------------------------------------------------
# STATISTICS SCREEN
# ------------------------------------------------------------------------------------
class StatisticsScreen:
    PW,PH=640,500
    def __init__(self):
        self.active=False; self.px=SCREEN_W//2-self.PW//2; self.py=SCREEN_H//2-self.PH//2
    def open(self): self.active=True
    def close(self): self.active=False
    def handle_event(self,event):
        if not self.active: return False
        if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE: self.close(); return True
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            if not pygame.Rect(self.px,self.py,self.PW,self.PH).collidepoint(event.pos): self.close(); return True
        return False
    def draw(self,surface,font_lg,font_sm,font_xs,t):
        if not self.active: return
        px,py,pw,ph=self.px,self.py,self.PW,self.PH
        ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((0,0,0,185)); surface.blit(ov,(0,0))
        panel=pygame.Surface((pw,ph),pygame.SRCALPHA); panel.fill((6,9,24,246)); surface.blit(panel,(px,py))
        pygame.draw.rect(surface,TEAL,(px,py,pw,ph),border_radius=10,width=2)
        pygame.draw.rect(surface,TEAL,(px,py,pw,4),border_radius=10)
        title=font_lg.render(tr("stats.title"),True,TEAL); surface.blit(title,(SCREEN_W//2-title.get_width()//2,py+14))
        sd=save_data
        stats_items=[
            ("stats.high_score",f"{sd.get('high_score',0):,}",GOLD),
            ("stats.total_plays",str(sd.get('total_plays',0)),CYAN),
            ("stats.kills",str(sd.get('total_kills',0)),RED),
            ("stats.deaths",str(sd.get('total_deaths',0)),ORANGE),
            ("stats.coins",str(sd.get('total_coins',0)),GOLD),
            ("stats.damage_dealt",str(sd.get('total_damage_dealt',0)),(255,100,100)),
            ("stats.damage_taken",str(sd.get('total_damage_taken',0)),ORANGE),
            ("stats.levels_cleared",str(sd.get('total_levels_cleared',0)),GREEN),
            ("stats.secrets",str(sd.get('total_secrets',0)),PURPLE),
            ("stats.chests",str(sd.get('total_chests',0)),(200,160,60)),
            ("stats.highest_combo",str(sd.get('highest_combo',0)),NEON_ORANGE),
            ("stats.shots_fired",str(sd.get('total_shots_fired',0)),CYAN),
            ("stats.bosses",str(sd.get('bosses_defeated',0)),PINK),
            ("stats.best_level",str(sd.get('best_level',1)),NEON_YELLOW),
            ("stats.boss_rush",str(sd.get('total_boss_rush_waves',0)),(200,100,255)),
        ]
        shots=sd.get('total_shots_fired',0)
        kills=sd.get('total_kills',0)
        acc=f"{min(100,(kills/max(1,shots))*100):.1f}%" if shots>0 else "0%"
        stats_items.append(("stats.accuracy",acc,TEAL))
        pt=sd.get('play_time',0)
        hours=int(pt//3600); mins=int((pt%3600)//60)
        time_str=f"{hours}h {mins}m" if hours>0 else f"{mins}m"
        stats_items.append(("stats.play_time",time_str,(180,200,255)))
        start_y=py+54; col_count=2; item_h=28; col_w=(pw-80)//2
        for i,(key,val,col) in enumerate(stats_items):
            c=i%col_count; r=i//col_count
            x=px+30+c*col_w; y=start_y+r*item_h
            lbl=font_xs.render(tr(key),True,TEXT_MAIN)
            surface.blit(lbl,(x,y))
            v=font_sm.render(val,True,col)
            surface.blit(v,(x+col_w-18-v.get_width(),y-1))
        hint=font_xs.render("ESC / Click outside = close",True,TEXT_MUTED); surface.blit(hint,(SCREEN_W//2-hint.get_width()//2,py+ph-18))

# ------------------------------------------------------------------------------------
# SHOP SYSTEM
# ------------------------------------------------------------------------------------
class Shop:
    PW,PH=720,520

    def __init__(self):
        self.active=False; self.coins=0
        self.mode="upgrades"; self.player_ref=None
        self.tab_rects={}; self.skin_rects={}; self.weapon_skin_rects={}; self.shop_weapon_rects={}; self.pet_rects={}
        self.upgrades={
            "hp":     {"name":"MAX HP +1","cost":120,"level":0,"max":5,"desc":"Tambah 1 HP maksimal","col":GREEN},
            "speed":  {"name":"SPEED +10%","cost":160,"level":0,"max":5,"desc":"Gerak 10% lebih cepat","col":CYAN},
            "damage": {"name":"DAMAGE +1","cost":220,"level":0,"max":5,"desc":"Tembak damage +1","col":RED},
            "jump":   {"name":"DOUBLE JUMP","cost":180,"level":0,"max":2,"desc":"Tambah lompatan udara","col":TEAL},
            "dash":   {"name":"DASH CORE","cost":170,"level":0,"max":3,"desc":"Dash lebih kuat","col":ORANGE},
            "shield": {"name":"SHIELD CELL","cost":190,"level":0,"max":3,"desc":"Shield lebih lama","col":BLUE},
            "weaponmod":{"name":"WEAPON MOD","cost":240,"level":0,"max":3,"desc":"Peluru pierce","col":PURPLE},
        }
        self.px=SCREEN_W//2-self.PW//2; self.py=SCREEN_H//2-self.PH//2
        self.anim_t=0

    def open(self,player_coins,player=None):
        self.active=True; self.coins=player_coins; self.player_ref=player; self.anim_t=0

    def close(self):
        self.active=False

    def reset(self):
        self.coins=0; self.mode="upgrades"; self.player_ref=None
        for upg in self.upgrades.values(): upg["level"]=0

    def buy(self,key):
        upg=self.upgrades[key]
        if upg["level"]<upg["max"] and self.coins>=upg["cost"]:
            self.coins-=upg["cost"]
            upg["level"]+=1
            sounds.play("coin")
            return True
        else:
            sounds.play("ui_click")
            return False

    def get_upgrades_dict(self):
        return {k:v["level"] for k,v in self.upgrades.items()}

    def _draw_tab(self,surface,font_sm,key,label,i,total_w,start_x,tw,tg):
        r=pygame.Rect(start_x+i*(tw+tg),self.py+108,tw,30)
        self.tab_rects[key]=r
        active=self.mode==key
        tab_colors={"upgrades":NEON_CYAN,"weapon":NEON_PINK,"skins":NEON_PURPLE,"pet":YELLOW,"special":NEON_ORANGE}
        col=tab_colors.get(key,GRAY)
        col=col if active else GRAY
        bg_col=(22,26,44) if active else (12,14,26)
        pygame.draw.rect(surface,bg_col,r,border_radius=6)
        bw=3 if active else 1
        pygame.draw.rect(surface,col,r,border_radius=6,width=bw)
        if active:
            for gi in range(3):
                ga=int(18-6*gi)
                gs=pygame.Surface((tw+12+gi*8,38+gi*4),pygame.SRCALPHA)
                pygame.draw.rect(gs,(*col[:3],ga),(0,0,tw+12+gi*8,38+gi*4),border_radius=8)
                surface.blit(gs,(r.x-6-gi*4,r.y-4-gi*2))
        txt=font_sm.render(label,True,col)
        surface.blit(txt,(r.centerx-txt.get_width()//2,r.centery-txt.get_height()//2))

    def _draw_tabs(self,surface,font_sm):
        self.tab_rects={}
        tabs=[("upgrades",tr("shop.tab.upgrades")),("weapon",tr("shop.tab.weapon")),
              ("skins",tr("shop.tab.skins")),("pet",tr("shop.tab.pet")),("special",tr("shop.tab.special"))]
        tw=115; tg=14; n=len(tabs)
        total=n*tw+(n-1)*tg
        start_x=self.px+(self.PW-total)//2
        for i,(key,label) in enumerate(tabs):
            self._draw_tab(surface,font_sm,key,label,i,total,start_x,tw,tg)

    def _draw_card(self,surface,font_sm,font_xs,x,y,cw,ch,col,title,desc,level_info,price_info,button_info,mx,my,t):
        cr=pygame.Rect(x,y,cw,ch)
        is_max=level_info.get("is_max",False)
        bg=pygame.Surface((cw,ch),pygame.SRCALPHA)
        bg.fill((col[0]//10,col[1]//10,col[2]//10,90))
        surface.blit(bg,(x,y))
        hov=cr.collidepoint(mx,my)
        border_col=col if not is_max else SUCCESS_TEXT
        bw=2 if not hov else (3 if not is_max else 2)
        if hov and not is_max:
            glow=pygame.Surface((cw+8,ch+8),pygame.SRCALPHA)
            pygame.draw.rect(glow,(*col[:3],30),(0,0,cw+8,ch+8),border_radius=8)
            surface.blit(glow,(x-4,y-4))
        pygame.draw.rect(surface,border_col,cr,border_radius=8,width=bw)
        if hov and not is_max:
            pygame.draw.rect(surface,border_col,cr,border_radius=8,width=1)

        # Icon
        icon_r=pygame.Rect(x+10,y+10,28,28)
        pygame.draw.rect(surface,col,icon_r,border_radius=6)
        pygame.draw.rect(surface,(255,255,255,40),icon_r,border_radius=6,width=1)

        title_col=col if not is_max else TEXT_MUTED
        nt=render_fit(font_sm,title,title_col,cw-128)
        surface.blit(nt,(x+46,y+10))

        dt=render_fit(font_xs,desc,TEXT_MUTED,cw-28)
        surface.blit(dt,(x+14,y+40))

        level_box=pygame.Rect(x+14,y+ch-31,84,20)
        pygame.draw.rect(surface,(8,12,24,150),level_box,border_radius=4)
        pygame.draw.rect(surface,level_info["color"],level_box,border_radius=4,width=1)
        draw_center_fit(surface,level_info["text"],font_xs,level_box,level_info["color"],shadow=False)

        if price_info:
            pcol=price_info["color"]
            price_box=pygame.Rect(x+104,y+ch-31,72,20)
            pygame.draw.rect(surface,(22,18,7,150),price_box,border_radius=4)
            pygame.draw.rect(surface,pcol,price_box,border_radius=4,width=1)
            draw_center_fit(surface,f"C {price_info['text']}",font_xs,price_box,pcol,shadow=False)

        if button_info and not is_max:
            br=button_info["rect"]
            bcol=button_info["color"]
            bhov=br.collidepoint(mx,my) and button_info.get("enabled",True)
            pygame.draw.rect(surface,(bcol[0]//4,bcol[1]//4,bcol[2]//4),br,border_radius=5)
            pygame.draw.rect(surface,bcol,br,border_radius=5,width=2 if bhov else 1)
            if bhov:
                hgl=pygame.Surface((br.w,br.h),pygame.SRCALPHA)
                pygame.draw.rect(hgl,(*bcol[:3],35),(0,0,br.w,br.h),border_radius=5)
                surface.blit(hgl,br.topleft)
            bt=font_xs.render(button_info["text"],True,bcol if button_info.get("enabled",True) else (80,80,80))
            surface.blit(bt,(br.centerx-bt.get_width()//2,br.centery-bt.get_height()//2))
        elif is_max:
            mt=font_xs.render(tr("shop.max"),True,SUCCESS_TEXT)
            surface.blit(mt,(x+cw-12-mt.get_width(),y+ch-22))
        return cr

    def _draw_upgrades_tab(self,surface,font_sm,font_xs,t):
        px,py=self.px,self.py; pw=self.PW; mx,my=pygame.mouse.get_pos()
        cw=(pw-72)//2; ch=86; gap=12; start_y=py+164
        sec_t=font_xs.render(tr("shop.tab.upgrades"),True,NEON_CYAN)
        surface.blit(sec_t,(px+24,py+148))
        for i,(key,upg) in enumerate(self.upgrades.items()):
            col=i%2; row=i//2
            x=px+24+col*(cw+gap); y=start_y+row*(ch+gap)
            level_info={"is_max":upg["level"]>=upg["max"]}
            lv_col=SUCCESS_TEXT if level_info["is_max"] else TEXT_MUTED
            lv_txt=tr("shop.max") if level_info["is_max"] else f"Lv {upg['level']}/{upg['max']}"
            level_info["text"]=lv_txt; level_info["color"]=lv_col
            can_afford=self.coins>=upg["cost"]
            price_info={"text":str(upg["cost"]),"color":GOLD if can_afford else TEXT_DIM}
            btn_text=tr("shop.buy") if can_afford and not level_info["is_max"] else tr("shop.upgrade")
            btn_col=upg["col"] if can_afford else TEXT_DIM
            btn_r=pygame.Rect(x+cw-108,y+ch-32,94,24)
            button_info=None if level_info["is_max"] else {"text":btn_text,"color":btn_col,"rect":btn_r,"enabled":can_afford and not level_info["is_max"]}
            if button_info and not button_info["enabled"]:
                button_info["text"]=str(upg["cost"])
                button_info["color"]=TEXT_DIM
            self._draw_card(surface,font_sm,font_xs,x,y,cw,ch,upg["col"],tr(f"upg.{key}.name"),
                          tr(f"upg.{key}.desc"),level_info,price_info,button_info,mx,my,t)
            if not level_info["is_max"]:
                upg["btn_rect"]=btn_r

    def _draw_skins(self,surface,font_sm,font_xs,t):
        player=self.player_ref
        owned=getattr(player,"owned_skins",{"classic"}) if player else {"classic"}
        current=getattr(player,"skin","classic") if player else "classic"
        self.skin_rects={}
        px,py=self.px,self.py; pw=self.PW
        cw=(pw-70)//2; ch=90; gap=14; start_y=py+155
        mx,my=pygame.mouse.get_pos()
        for i,(skin_key,skin) in enumerate(SKINS.items()):
            col=i%2; row=i//2
            x=px+24+col*(cw+gap); y=start_y+row*(ch+gap)
            cr=pygame.Rect(x,y,cw,ch); self.skin_rects[skin_key]=cr
            bought=skin_key in owned; equipped=skin_key==current; can_afford=self.coins>=skin["cost"]
            border=GOLD if equipped else (skin["accent"] if bought else GRAY)
            bg=pygame.Surface((cw,ch),pygame.SRCALPHA)
            bg.fill((*skin["dark"],110)); surface.blit(bg,(x,y))
            pygame.draw.rect(surface,border,cr,border_radius=8,width=2)
            hov=cr.collidepoint(mx,my)
            if hov:
                gl=pygame.Surface((cw+8,ch+8),pygame.SRCALPHA)
                pygame.draw.rect(gl,(*border[:3],25),(0,0,cw+8,ch+8),border_radius=10)
                surface.blit(gl,(x-4,y-4))
            draw_g7(surface,x+14,y+ch//2-18,False,int(t*0.05)%100,True,1,0,skin)
            name=render_fit(font_sm,skin["name"],skin["accent"],cw-80)
            surface.blit(name,(x+64,y+12))
            desc=render_fit(font_xs,skin["desc"],TEXT_MUTED,cw-80)
            surface.blit(desc,(x+64,y+34))
            if equipped:
                label=tr("shop.equipped"); btn_col=GOLD
            elif bought:
                label=tr("shop.select"); btn_col=skin["accent"]
            else:
                label=tr("shop.buy") if can_afford else str(skin["cost"])
                btn_col=skin["accent"] if can_afford else TEXT_DIM
            br=pygame.Rect(x+cw-100,y+ch-26,86,20)
            pygame.draw.rect(surface,(18,20,30),br,border_radius=5)
            pygame.draw.rect(surface,btn_col,br,border_radius=5,width=1)
            bt=font_xs.render(label,True,btn_col)
            surface.blit(bt,(br.centerx-bt.get_width()//2,br.centery-bt.get_height()//2))

    def _draw_weapon_shop(self,surface,font_sm,font_xs,t):
        player=self.player_ref
        owned_skins=getattr(player,"owned_weapon_skins",{"default"}) if player else {"default"}
        current_skin=getattr(player,"weapon_skin","default") if player else "default"
        self.weapon_skin_rects={}
        px,py=self.px,self.py; pw=self.PW
        mx,my=pygame.mouse.get_pos()
        sec_t=font_sm.render(tr("shop.weapon_skins"),True,NEON_PINK)
        surface.blit(sec_t,(px+24,py+152))
        cw=108; ch=62; gap=12; start_x=px+24; start_y=py+176
        for i,(skin_key,skin) in enumerate(WEAPON_SKINS.items()):
            x=start_x+i*(cw+gap); y=start_y
            r=pygame.Rect(x,y,cw,ch); self.weapon_skin_rects[skin_key]=r
            equipped=skin_key==current_skin; bought=skin_key in owned_skins; can_afford=self.coins>=skin["cost"]
            col=skin["color"] or CYAN
            pygame.draw.rect(surface,(14,16,28),r,border_radius=8)
            pygame.draw.rect(surface,GOLD if equipped else col,r,border_radius=8,width=2 if equipped else 1)
            hov=r.collidepoint(mx,my)
            if hov:
                gl=pygame.Surface((cw+6,ch+6),pygame.SRCALPHA)
                pygame.draw.rect(gl,(*col[:3],25),(0,0,cw+6,ch+6),border_radius=10)
                surface.blit(gl,(x-3,y-3))
            pygame.draw.line(surface,col,(x+14,y+18),(x+48,y+18),4)
            pygame.draw.circle(surface,col,(x+52,y+18),5)
            if equipped:
                lb=font_xs.render(tr("shop.equipped"),True,GOLD)
            elif bought:
                lb=font_xs.render(tr("shop.select"),True,col)
            else:
                lb=font_xs.render(str(skin["cost"]),True,col if can_afford else TEXT_DIM)
            nm=render_fit(font_xs,skin["name"],col,cw-12)
            surface.blit(nm,(x+6,y+28))
            surface.blit(lb,(x+6,y+44))

    def _draw_pets(self,surface,font_sm,font_xs,t):
        player=self.player_ref
        owned=getattr(player,"owned_pets",set()) if player else set()
        equipped=getattr(player,"equipped_pet","") if player else ""
        self.pet_rects={}
        px,py=self.px,self.py; pw=self.PW
        cw=(pw-70)//2; ch=90; gap=14; start_y=py+155
        mx,my=pygame.mouse.get_pos()
        preview_key=None
        sec_t=font_sm.render(tr("shop.tab.pet"),True,YELLOW)
        surface.blit(sec_t,(px+24,py+150))
        for i,(pkey,pet) in enumerate(PET_DATA.items()):
            col=i%2; row=i//2
            x=px+24+col*(cw+gap); y=start_y+row*(ch+gap)
            cr=pygame.Rect(x,y,cw,ch); self.pet_rects[pkey]=cr
            bought=pkey in owned; equipped_p=pkey==equipped; can_afford=self.coins>=pet["price"]
            border=GOLD if equipped_p else (pet["color"] if bought else GRAY)
            bg=pygame.Surface((cw,ch),pygame.SRCALPHA); bg.fill((*pet["color"],25))
            surface.blit(bg,(x,y))
            pygame.draw.rect(surface,border,cr,border_radius=8,width=2)
            hov=cr.collidepoint(mx,my)
            if hov:
                gl=pygame.Surface((cw+8,ch+8),pygame.SRCALPHA)
                pygame.draw.rect(gl,(*border[:3],25),(0,0,cw+8,ch+8),border_radius=10)
                surface.blit(gl,(x-4,y-4))
            if hov and bought: preview_key=pkey
            _draw_pet_sprite(surface,x+10,y+ch//2-18,pet,t)
            name=render_fit(font_sm,pet["name"],pet["color"],cw-76)
            surface.blit(name,(x+64,y+10))
            desc_txt=pet["desc_id"] if current_language()=="id" else pet["desc"]
            desc=render_fit(font_xs,desc_txt,TEXT_MUTED,cw-76)
            surface.blit(desc,(x+64,y+30))
            if equipped_p:
                label=tr("shop.equipped"); btn_col=GOLD
            elif bought:
                label=tr("shop.select"); btn_col=pet["color"]
            else:
                label=tr("shop.buy") if can_afford else str(pet["price"])
                btn_col=pet["color"] if can_afford else TEXT_DIM
            br=pygame.Rect(x+cw-100,y+ch-26,86,20)
            pygame.draw.rect(surface,(18,20,30),br,border_radius=5)
            pygame.draw.rect(surface,btn_col,br,border_radius=5,width=1)
            bt=font_xs.render(label,True,btn_col)
            surface.blit(bt,(br.centerx-bt.get_width()//2,br.centery-bt.get_height()//2))
        if preview_key and player:
            preview=PET_DATA[preview_key]
            pp_x=px+pw-210; pp_y=py+self.PH-140; ppw=190; pph=110
            pp=pygame.Surface((ppw,pph),pygame.SRCALPHA); pp.fill((*preview["color"],35))
            surface.blit(pp,(pp_x,pp_y))
            pygame.draw.rect(surface,preview["color"],(pp_x,pp_y,ppw,pph),border_radius=8,width=1)
            ptl=font_xs.render(tr("shop.pet_preview"),True,preview["color"])
            surface.blit(ptl,(pp_x+ppw//2-ptl.get_width()//2,pp_y+6))
            _draw_pet_sprite(surface,pp_x+ppw//2-24,pp_y+18,preview,t)
            pn=render_fit(font_xs,preview["name"],WHITE,ppw-12)
            surface.blit(pn,(pp_x+6,pp_y+72))

    def _draw_special(self,surface,font_sm,font_xs,t):
        player=self.player_ref
        owned_weapons=set(getattr(player,"weapons",["laser"])) if player else {"laser"}
        self.shop_weapon_rects={}
        px,py=self.px,self.py; pw=self.PW
        mx,my=pygame.mouse.get_pos()
        cw=(pw-70)//2; ch=96; gap=14; start_y=py+155
        sec_t=font_sm.render(tr("shop.shop_weapons"),True,NEON_ORANGE)
        surface.blit(sec_t,(px+24,py+150))
        for i,w_key in enumerate(SHOP_WEAPON_POOL):
            w=WEAPONS[w_key]; col=i%2; row=i//2
            x=px+24+col*(cw+gap); y=start_y+row*(ch+gap)+20
            cr=pygame.Rect(x,y,cw,ch); self.shop_weapon_rects[w_key]=cr
            owned=w_key in owned_weapons; can_afford=self.coins>=w["cost"]
            wcol=w["color"]
            bg=pygame.Surface((cw,ch),pygame.SRCALPHA); bg.fill((*wcol,25))
            surface.blit(bg,(x,y))
            pygame.draw.rect(surface,GOLD if owned else wcol,cr,border_radius=8,width=2 if owned else 1)
            hov=cr.collidepoint(mx,my)
            if hov:
                gl=pygame.Surface((cw+8,ch+8),pygame.SRCALPHA)
                pygame.draw.rect(gl,(*wcol[:3],25),(0,0,cw+8,ch+8),border_radius=10)
                surface.blit(gl,(x-4,y-4))
            pygame.draw.line(surface,wcol,(x+14,y+28),(x+60,y+28),5)
            pygame.draw.circle(surface,wcol,(x+66,y+28),7)
            name=render_fit(font_sm,w["name"],wcol,cw-90)
            surface.blit(name,(x+80,y+10))
            stat=font_xs.render(f"DMG {w['damage']}  SPD {w['speed']}  AMMO {w['ammo']}",True,TEXT_MUTED)
            surface.blit(stat,(x+80,y+32))
            if owned:
                price=max(10,w["cost"]//3)
                label=str(price); btn_col=GOLD if self.coins>=price else TEXT_DIM
            else:
                label=tr("shop.buy") if can_afford else str(w["cost"])
                btn_col=wcol if can_afford else TEXT_DIM
            br=pygame.Rect(x+80,y+56,86,22)
            pygame.draw.rect(surface,(18,20,30),br,border_radius=5)
            pygame.draw.rect(surface,btn_col,br,border_radius=5,width=1)
            bt=font_xs.render(label,True,btn_col)
            surface.blit(bt,(br.centerx-bt.get_width()//2,br.centery-bt.get_height()//2))

    def draw(self,surface,font_lg,font_sm,font_xs,t):
        if not self.active: return
        self.anim_t+=1
        px,py,pw,ph=self.px,self.py,self.PW,self.PH
        mx,my=pygame.mouse.get_pos()
        prog=min(1.0,self.anim_t/15)
        alpha=int(255*prog)

        ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA)
        ov.fill((0,0,0,180)); surface.blit(ov,(0,0))

        pan=pygame.Surface((pw,ph),pygame.SRCALPHA)
        pan.fill((*PANEL_BG,248)); surface.blit(pan,(px,py))
        pygame.draw.rect(surface,NEON_CYAN,(px,py,pw,ph),border_radius=10,width=2)
        pygame.draw.rect(surface,NEON_CYAN,(px,py,pw,3),border_radius=10)

        draw_text(surface,tr("shop.title"),font_lg,SCREEN_W//2,py+14,NEON_CYAN,center=True)
        pygame.draw.line(surface,(NEON_CYAN[0]//3,NEON_CYAN[1]//3,NEON_CYAN[2]//3),(px+30,py+52),(px+pw-30,py+52),1)

        coin_font=make_font(14,"hud",True)
        coin_txt=f"\u25C9 {tr('shop.coins',coins=self.coins)}"
        ct=coin_font.render(coin_txt,True,GOLD)
        cx2=SCREEN_W//2-ct.get_width()//2; cy2=py+62
        cb=pygame.Surface((ct.get_width()+20,ct.get_height()+6),pygame.SRCALPHA)
        cb.fill((25,20,8,190)); surface.blit(cb,(cx2-10,cy2-3))
        pygame.draw.rect(surface,(GOLD[0]//2,GOLD[1]//2,GOLD[2]//2),(cx2-10,cy2-3,ct.get_width()+20,ct.get_height()+6),border_radius=4,width=1)
        surface.blit(ct,(cx2,cy2))

        self._draw_tabs(surface,font_sm)

        tab_handlers={"upgrades":self._draw_upgrades_tab,"skins":self._draw_skins,
                       "weapon":self._draw_weapon_shop,"pet":self._draw_pets,"special":self._draw_special}
        handler=tab_handlers.get(self.mode)
        if handler:
            handler(surface,font_sm,font_xs,t)
        esc_t=font_xs.render(tr("shop.close_hint"),True,TEXT_MUTED)
        surface.blit(esc_t,(SCREEN_W//2-esc_t.get_width()//2,py+ph-12))

    def handle_event(self,event,player):
        if not self.active: return False
        mx,my=pygame.mouse.get_pos()

        if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
            self.close(); return True

        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            if not pygame.Rect(self.px,self.py,self.PW,self.PH).collidepoint(mx,my):
                self.close(); return True

            for mode,rect in self.tab_rects.items():
                if rect.collidepoint(mx,my):
                    self.mode=mode; sounds.play("ui_click"); return True

            if self.mode=="skins":
                for skin_key,rect in self.skin_rects.items():
                    if rect.collidepoint(mx,my):
                        skin=SKINS[skin_key]
                        if skin_key in player.owned_skins:
                            player.skin=skin_key; save_permanent_unlocks(player); sounds.play("ui_click")
                        elif self.coins>=skin["cost"]:
                            self.coins-=skin["cost"]; player.owned_skins.add(skin_key); player.skin=skin_key; save_permanent_unlocks(player); sounds.play("coin")
                        else:
                            sounds.play("ui_click")
                        return True

            if self.mode=="pet":
                for pkey,rect in self.pet_rects.items():
                    if rect.collidepoint(mx,my):
                        pet=PET_DATA[pkey]
                        if pkey in player.owned_pets:
                            player.equipped_pet=pkey; save_permanent_unlocks(player); sounds.play("ui_click")
                        elif self.coins>=pet["price"]:
                            self.coins-=pet["price"]; player.owned_pets.add(pkey); player.equipped_pet=pkey; save_permanent_unlocks(player); sounds.play("coin")
                        else:
                            sounds.play("ui_click")
                        return True

            if self.mode=="weapon":
                for skin_key,rect in self.weapon_skin_rects.items():
                    if rect.collidepoint(mx,my):
                        skin=WEAPON_SKINS[skin_key]
                        if skin_key in player.owned_weapon_skins:
                            player.weapon_skin=skin_key; save_permanent_unlocks(player); sounds.play("ui_click")
                        elif self.coins>=skin["cost"]:
                            self.coins-=skin["cost"]; player.owned_weapon_skins.add(skin_key); player.weapon_skin=skin_key; save_permanent_unlocks(player); sounds.play("coin")
                        else:
                            sounds.play("ui_click")
                        return True

            if self.mode=="special":
                for w_key,rect in self.shop_weapon_rects.items():
                    if rect.collidepoint(mx,my):
                        w=WEAPONS[w_key]
                        if w_key in player.weapons:
                            ammo_cost=max(10,w["cost"]//3)
                            if self.coins>=ammo_cost:
                                self.coins-=ammo_cost; player.ammo[w_key]=min(player.ammo[w_key]+w["ammo"],w["ammo"]*3); sounds.play("coin")
                            else:
                                sounds.play("ui_click")
                        elif self.coins>=w["cost"]:
                            self.coins-=w["cost"]; player.buy_shop_weapon(w_key); save_permanent_unlocks(player); sounds.play("weapon_pickup")
                        else:
                            sounds.play("ui_click")
                        return True

            for key,upg in self.upgrades.items():
                if "btn_rect" in upg and upg["btn_rect"].collidepoint(mx,my):
                    if self.buy(key):
                        old_hp=player.hp
                        apply_shop_upgrades(player)
                        if key!="hp": player.hp=min(player.MAX_HP,old_hp)
                    return True

        return False

# ------------------------------------------------------------------------------------
# SAVE HELPERS
# ------------------------------------------------------------------------------------
def get_shop_upgrade_levels():
    return {k:max(0,min(v["max"],int(v["level"]))) for k,v in shop.upgrades.items()}

def set_shop_upgrade_levels(levels):
    if not isinstance(levels,dict): levels={}
    for key,upg in shop.upgrades.items():
        upg["level"]=max(0,min(upg["max"],int(levels.get(key,0))))

def apply_shop_upgrades(player_obj):
    levels=get_shop_upgrade_levels()
    hp_lv=levels.get("hp",0); speed_lv=levels.get("speed",0); damage_lv=levels.get("damage",0)
    player_obj.MAX_HP=min(10,Player.MAX_HP+hp_lv)
    player_obj.hp=player_obj.MAX_HP
    player_obj.SPEED=Player.SPEED*(1.1**speed_lv)
    player_obj.damage_bonus=min(5,damage_lv)
    player_obj.air_jump_max=levels.get("jump",0)
    player_obj.dash_level=levels.get("dash",0)
    player_obj.shield_level=levels.get("shield",0)
    player_obj.weapon_mod_level=levels.get("weaponmod",0)

def save_settings():
    if not current_save_file: return
    save_data["settings"]={
        "vol_sfx":sounds.vol_sfx,"vol_bgm":sounds.vol_bgm,
        "mute":sounds.muted,"fullscreen":fullscreen,"language":current_language(),"difficulty":current_difficulty()}
    write_save(current_save_file,save_data)

def normalize_respawn_spot(wx,wy):
    try:
        wx=float(wx); wy=float(wy)
    except (TypeError,ValueError):
        return 120.0,480.0
    valid_xs=[120.0]+[float(cp.wx) for cp in checkpoints]
    if wx<0 or wx>WORLD_W-Player.WIDTH or not any(abs(wx-vx)<2 for vx in valid_xs):
        return 120.0,480.0
    return max(0,min(WORLD_W-Player.WIDTH,wx)),max(18,min(SCREEN_H-Player.HEIGHT-4,wy))


def filter_generated_rewards_before_checkpoint(boundary_wx):
    global coins,chests,powerups,keycard_pickups,hidden_room_entrances
    try:
        boundary_wx=float(boundary_wx)
    except (TypeError,ValueError):
        return
    if boundary_wx<=120.0:
        return
    coins[:]=[c for c in coins if getattr(c,"wx",0)>=boundary_wx]
    chests[:]=[c for c in chests if getattr(c,"wx",0)>=boundary_wx]
    powerups[:]=[p for p in powerups if getattr(p,"wx",0)>=boundary_wx]
    keycard_pickups[:]=[k for k in keycard_pickups if getattr(k,"wx",0)>=boundary_wx]
    for fz in fly_zones:
        if hasattr(fz,"coins"):
            fz.coins=[c for c in fz.coins if getattr(c,"wx",0)>=boundary_wx]
    rooms=dict(save_data.get("hidden_rooms",{}))
    for hr in hidden_room_entrances:
        if getattr(hr,"wx",0)<boundary_wx:
            rooms[hr.room_id]=True
    if rooms:
        save_data["hidden_rooms"]=rooms
    hidden_room_entrances[:]=[hr for hr in hidden_room_entrances if getattr(hr,"wx",0)>=boundary_wx]

def save_progress_state(sd=None,include_session_kills=True):
    global session_kills,current_save_file,session_stats
    if not current_save_file: return False
    if sd is None: sd=load_save(current_save_file)
    for k,v in session_stats.items():
        if k in sd:
            sd[k]=sd.get(k,0)+v
    session_stats={}
    sd["has_save"]=True
    from datetime import datetime
    sd["timestamp"]=datetime.now().isoformat()
    if play_time_accum>0: sd["play_time"]=sd.get("play_time",0)+play_time_accum
    if score>sd.get("high_score",0): sd["high_score"]=score
    if level>sd.get("best_level",1): sd["best_level"]=level
    sd["last_level"]=level; sd["last_checkpoint"]=checkpoint
    sd["money"]=money
    sd["shop_upgrades"]=get_shop_upgrade_levels()
    sd["lives"]=lives
    sd["hp"]=player.hp; sd["max_hp"]=player.MAX_HP
    sd["current_weapon"]=player.current_weapon
    if hasattr(player,"weapon_levels"): sd["weapon_levels"]=player.weapon_levels
    save_adventure_progress_fields(sd,player)
    print(f"[SAVE] level={level} checkpoint={checkpoint} "
      f"respawn=({respawn_wx}, {respawn_wy}) "
      f"player=({player.wx}, {player.wy})")
    save_respawn_x,save_respawn_y=normalize_respawn_spot(respawn_wx,respawn_wy)
    sd["respawn_x"]=save_respawn_x;
    sd["respawn_y"]=save_respawn_y
    if include_session_kills:
        sd["total_kills"]=sd.get("total_kills",0)+session_kills
    if write_save(current_save_file,sd):
        save_data.update(sd)
        if include_session_kills: session_kills=0
        return True
    return False

def mark_challenge_completed(challenge_key):
    if not challenge_key or not current_save_file: return
    completed=set(save_data.get("completed_challenges",[]))
    if challenge_key in completed: return
    completed.add(challenge_key)
    sd=load_save(current_save_file); sd["completed_challenges"]=sorted(completed)
    if write_save(current_save_file,sd): save_data.update(sd)

# ------------------------------------------------------------------------------------
# BOSS RUSH SYSTEM
# ------------------------------------------------------------------------------------
def start_boss_rush(boss_ids):
    global boss_rush_active,boss_rush_wave,boss_rush_score,boss_rush_bosses,boss_rush_arena_x,boss_rush_seed,boss_rush_max_waves,boss_rush_combo,boss_rush_mult
    global player,camera,boss,boss_spawned,waiting_for_dialogue,active_boss_data,platforms,enemies
    global p_bullets,e_bullets,pixels,coins,chests,level,moving_plats,fly_zones,WORLD_W,boss_x_world
    global spike_traps,tunnels,facility_sections,water_zones,powerups,active_powerups,combo_count,combo_timer
    boss_rush_active=True; boss_rush_wave=0; boss_rush_score=0; boss_rush_bosses=boss_ids; boss_rush_max_waves=len(boss_ids)
    boss_rush_combo=0; boss_rush_mult=1;     boss_rush_seed=random.randint(0,2**63-1)
    level=max(1,min(boss_ids[0] if boss_ids else 1,10))
    player=Player(); camera=Camera()
    p_bullets=[]; e_bullets=[]; pixels=[]; coins=[]; chests=[]; enemies=[]; platforms=[]
    moving_plats=[]; fly_zones=[]; spike_traps=[]; tunnels=[]; facility_sections=[]; water_zones=[]
    powerups=[]; active_powerups={}; combo_count=0; combo_timer=0
    arena_w=900; WORLD_W=arena_w
    boss_rush_arena_x=100; boss_x_world=arena_w
    arena_plats=[(100,440,120),(280,380,120),(460,440,120),(640,380,120),(200,310,140),(500,310,140),(350,240,100)]
    for rx,ry,rw in arena_plats: platforms.append(pygame.Rect(rx,ry,rw,16))
    fly_zones=[]
    transition_to("playing"); boss=None; boss_spawned=False; waiting_for_dialogue=False
    spawn_next_boss_rush()

def spawn_next_boss_rush():
    global boss,boss_spawned,waiting_for_dialogue,active_boss_data,boss_rush_wave,boss_rush_combo,boss_rush_mult
    global session_kills,multiplier,mult_timer,combo_count,combo_timer
    if boss_rush_wave>=boss_rush_max_waves: return
    boss_id=boss_rush_bosses[boss_rush_wave]
    boss_rush_wave+=1
    boss_rush_combo=0; boss_rush_mult=1
    session_kills=0; multiplier=1; mult_timer=0; combo_count=0; combo_timer=0
    data=dict(BOSS_DATA[boss_id]); data["base_id"]=boss_id
    data["ability"]=random.choice(list(BOSS_ABILITY_DESCS.keys()))
    data=localize_boss_data(data)
    active_boss_data=data
    boss_x=boss_rush_arena_x+750
    boss_spawned=True; waiting_for_dialogue=True
    boss=Boss(boss_id,boss_x,data,min(boss_id,10))
    boss_dialogue.start(boss_id,data["color"],boss_rush_wave)

def check_boss_rush_complete():
    global boss_rush_active,boss_rush_score,boss_rush_wave,save_data,session_kills
    if not boss_rush_active: return False
    if boss_rush_wave>=boss_rush_max_waves and boss and not boss.alive:
        add_session_stat("total_boss_rush_waves",boss_rush_max_waves)
        flush_session_stats()
        boss_rush_active=False; transition_to("gameover")
        return True
    return False

# ------------------------------------------------------------------------------------
# MENU BUTTON
# ------------------------------------------------------------------------------------
class MenuButton:
    def __init__(self,x,y,w,h,text,color=None,disabled=False,icon_surf=None):
        self.rect=pygame.Rect(x,y,w,h); self.text=text; self.color=color or CYAN
        self.hovered=False; self.anim=0.0; self.disabled=disabled
        self.icon_surf=icon_surf
    def update(self,mx,my):
        self.hovered=self.rect.collidepoint(mx,my) and not self.disabled
        self.anim=min(1.0,self.anim+0.1) if self.hovered else max(0.0,self.anim-0.08)
    def draw(self,surface,font):
        col=tuple(c//4 for c in self.color) if self.disabled else self.color
        if not self.disabled and self.anim>0:
            gr=self.rect.inflate(int(self.anim*6)*2,int(self.anim*6)*2)
            gsurf=pygame.Surface((gr.w,gr.h),pygame.SRCALPHA)
            pygame.draw.rect(gsurf,(*col,int(self.anim*60)),(0,0,gr.w,gr.h),border_radius=8); surface.blit(gsurf,(gr.x,gr.y))
        bs=pygame.Surface((self.rect.w,self.rect.h),pygame.SRCALPHA)
        pygame.draw.rect(bs,(*col,int(self.anim*50)),(0,0,self.rect.w,self.rect.h),border_radius=6); surface.blit(bs,self.rect.topleft)
        bc=tuple(min(255,int(c*(0.5+0.5*self.anim)))for c in col)
        pygame.draw.rect(surface,bc,self.rect,border_radius=6,width=2)
        txt_col=TEXT_DIM if self.disabled else tuple(min(255,int(c*(0.78+0.35*self.anim)))for c in col)
        icon_w=self.icon_surf.get_width()+8 if self.icon_surf else 0
        lbl=render_fit(font,self.text,txt_col,self.rect.w-24-icon_w)
        lx=self.rect.x+12+icon_w if self.icon_surf else self.rect.centerx-lbl.get_width()//2
        ly=self.rect.centery-lbl.get_height()//2
        sh=render_fit(font,self.text,(0,0,0),self.rect.w-24-icon_w)
        surface.blit(sh,(lx+1,ly+1)); surface.blit(lbl,(lx,ly))
        if self.icon_surf:
            iy=self.rect.centery-self.icon_surf.get_height()//2
            surface.blit(self.icon_surf,(self.rect.x+10,iy))
    def is_clicked(self,event):
        return(not self.disabled and event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and self.rect.collidepoint(event.pos))

# ------------------------------------------------------------------------------------
# LEVEL EVENT / CHALLENGE ROOMS
# ------------------------------------------------------------------------------------
CHALLENGE_THEME_MAP={
    "station":"security_gate","engine":"heat_elevator","lab":"laser_room","space":"zero_gravity_corridor",
    "glitch":"glitch_room","ice":"frozen_corridor","enemy_base":"server_lockdown","nebula":"storm_elevator",
    "storm":"storm_elevator","reactor":"reactor_core_room","server":"server_lockdown","void":"glitch_room","core":"corex_trial"
}
CHALLENGE_TITLES={
    "security_gate":"SECURITY CHECK","heat_elevator":"HEAT PRESSURE RISING","laser_room":"LAB SECURITY ACTIVE",
    "zero_gravity_corridor":"ZERO GRAVITY ZONE","glitch_room":"SYSTEM GLITCH DETECTED","frozen_corridor":"CRYO LOCKDOWN",
    "server_lockdown":"SERVER LOCKDOWN","storm_elevator":"ENERGY SURGE","reactor_core_room":"CORE UNLOCKED",
    "corex_trial":"CORE-X DEFENSE ACTIVE"
}

def get_challenge_type_for_level(level_num,level_theme):
    return CHALLENGE_THEME_MAP.get(level_theme,"security_gate")

def is_player_inside_challenge(player_obj,challenge):
    return challenge.trigger_rect.colliderect(player_obj.get_rect())

class ChallengeCore:
    def __init__(self,wx,wy,idx):
        self.wx=float(wx); self.wy=float(wy); self.idx=idx; self.hp=3; self.alive=True
    def get_rect(self): return pygame.Rect(self.wx,self.wy,30,34)
    def draw(self,surface,cam,t,accent):
        if not self.alive: return
        sx,sy=cam.apply(self.wx,self.wy); pulse=int(150+80*math.sin(t*0.01+self.idx))
        glow=pygame.Surface((54,54),pygame.SRCALPHA); pygame.draw.circle(glow,(*accent,50),(27,27),24); surface.blit(glow,(int(sx)-12,int(sy)-10))
        pygame.draw.rect(surface,(35,20,20),(int(sx),int(sy),30,34),border_radius=5)
        pygame.draw.rect(surface,(pulse,70,40),(int(sx)+6,int(sy)+6,18,22),border_radius=4)
        pygame.draw.rect(surface,accent,(int(sx),int(sy),30,34),border_radius=5,width=2)

class ChallengeRoom:
    def __init__(self,x,y,w,h,level_theme,challenge_type,level_num=1,accent=CYAN,room_id=0):
        self.x=float(x); self.y=float(y); self.w=float(w); self.h=float(h); self.level_theme=level_theme
        self.challenge_type=challenge_type; self.level_num=level_num; self.accent=accent; self.status="inactive"
        self.room_id=room_id; self.save_key=f"L{level_num}:{room_id}:{challenge_type}"
        self.trigger_rect=pygame.Rect(int(x),int(y),int(w),int(h)); self.gate_rect=pygame.Rect(int(x+w-34),int(y+40),26,int(h-70))
        self.timer=0; self.spawned=False; self.challenge_enemies=[]; self.cores=[]; self.lasers=[]; self.hazards=[]; self.platforms=[]; self.text_timer=0
        self._setup_static()
    def _setup_static(self):
        cx=self.x+self.w//2
        if self.challenge_type in("laser_room","server_lockdown","corex_trial"):
            for i in range(3): self.lasers.append({"x":self.x+130+i*150,"phase":i*45,"active":False,"warn":False})
        if self.challenge_type in("reactor_core_room",):
            for i in range(3): self.cores.append(ChallengeCore(self.x+150+i*150,470-(i%2)*65,i+1))
        if self.challenge_type=="heat_elevator":
            self.platforms.append(MovingPlatform(int(cx-55),430,110,70,0.9,True))
        if self.challenge_type=="glitch_room":
            self.platforms.append(MovingPlatform(int(self.x+150),455,95,55,0.8,False)); self.platforms.append(MovingPlatform(int(self.x+355),385,95,45,0.9,True))
        if self.challenge_type=="zero_gravity_corridor":
            for i in range(4): self.hazards.append({"x":self.x+120+i*115,"y":260+i%2*85,"vx":random.choice([-1,1])*(0.8+i*0.12),"r":13+i%2*4})
    def start(self,enemies_list):
        if self.status!="inactive": return
        self.status="active"; self.timer=0; self.text_timer=150
        debug_print("ChallengeRoom started:",self.challenge_type)
        debug_print("Challenge started:",self.challenge_type)
        self._spawn(enemies_list)
    def _spawn(self,enemies_list):
        if self.spawned: return
        self.spawned=True
        count=0
        if self.challenge_type in("security_gate","server_lockdown","corex_trial"):
            count=2+(1 if self.level_num>=4 else 0)
        elif self.challenge_type in("laser_room","reactor_core_room"):
            count=1
        for i in range(count):
            ex=self.x+110+i*max(90,self.w/(count+1)); elite="fast" if self.challenge_type in("server_lockdown","corex_trial") and i%2 else None
            bot=ScoutBot(ex,520-ScoutBot.HEIGHT,1.0+self.level_num*0.08,max(70,135-self.level_num*6),elite)
            enemies_list.append(bot); self.challenge_enemies.append(bot)
        debug_print("Challenge enemies:",len(self.challenge_enemies))
    def complete(self):
        if self.status=="completed": return
        self.status="completed"; self.text_timer=120
        mark_challenge_completed(self.save_key)
        debug_print("ChallengeRoom completed:",self.challenge_type)
        debug_print("Challenge completed:",self.challenge_type); debug_print("Gate opened")
    def update(self,player_obj,enemies_list,p_bullets,e_bullets):
        if self.text_timer>0: self.text_timer-=1
        if self.status=="inactive" and is_player_inside_challenge(player_obj,self): self.start(enemies_list)
        if self.status=="completed": return
        if self.status=="active":
            self.timer+=1
            if self.challenge_type=="zero_gravity_corridor" and self.trigger_rect.colliderect(player_obj.get_rect()):
                player_obj.vy*=0.92
            # Platform challenge ikut sistem moving_plats global agar collision player tetap memakai logic lama.
            self._update_hazards(player_obj,e_bullets)
            self._update_lasers(player_obj)
            self._update_cores(p_bullets)
            alive_enemies=[e for e in self.challenge_enemies if getattr(e,"alive",False)]
            cores_alive=[c for c in self.cores if c.alive]
            timed_clear=self.challenge_type in("heat_elevator","laser_room","zero_gravity_corridor","glitch_room","frozen_corridor","storm_elevator") and self.timer>260
            if (self.challenge_type in("security_gate","server_lockdown","corex_trial") and not alive_enemies) or (self.challenge_type=="reactor_core_room" and not cores_alive) or timed_clear:
                self.complete()
        if self.status!="completed" and player_obj.get_rect().colliderect(self.gate_rect):
            if player_obj.wx+player_obj.WIDTH/2<self.gate_rect.centerx: player_obj.wx=self.gate_rect.left-player_obj.WIDTH-1
            else: player_obj.wx=self.gate_rect.right+1
            player_obj.vx=0
    def _update_hazards(self,player_obj,e_bullets):
        pr=player_obj.get_rect()
        if self.challenge_type=="heat_elevator" and self.timer%90==55:
            trigger_boss_shake("light",8); e_bullets.append(WorldBullet(self.x+self.w//2,SCREEN_H-75,0,-3.2,ORANGE))
        if self.challenge_type=="frozen_corridor" and self.timer%80==40:
            sx=self.x+random.randint(90,int(self.w-120)); b=WorldBullet(sx,80,0,4.0,(150,230,255)); b.cryo=True; e_bullets.append(b)
        if self.challenge_type=="storm_elevator" and self.timer%95==45:
            lx=player_obj.wx+player_obj.WIDTH//2; e_bullets.append(WorldBullet(lx,0,0,5.2,YELLOW)); trigger_boss_shake("medium",10)
        for h in self.hazards:
            h["x"]+=h["vx"]
            if h["x"]<self.x+55 or h["x"]>self.x+self.w-80: h["vx"]*=-1
            if pr.colliderect(pygame.Rect(h["x"]-h["r"],h["y"]-h["r"],h["r"]*2,h["r"]*2)) and player_obj.invincible==0:
                if player_obj.take_damage(1): player_died()
    def _update_lasers(self,player_obj):
        if self.challenge_type not in("laser_room","server_lockdown","corex_trial"): return
        if lasers_disabled_for_level(self.level_num):
            for l in self.lasers: l["warn"]=False; l["active"]=False
            return
        pr=player_obj.get_rect()
        for l in self.lasers:
            cycle=(self.timer+l["phase"])%120; l["warn"]=70<=cycle<90; l["active"]=90<=cycle<116
            if l["active"] and pr.colliderect(pygame.Rect(int(l["x"]),120,8,430)) and player_obj.invincible==0:
                if player_obj.take_damage(1): player_died()
    def _update_cores(self,p_bullets):
        if not self.cores: return
        for b in p_bullets:
            if not b.alive: continue
            for c in self.cores:
                if c.alive and b.get_rect().colliderect(c.get_rect()):
                    b.alive=False; c.hp-=safe_damage_value(getattr(b,"damage",1)); spawn_pixels(c.wx,c.wy,ORANGE,8)
                    if c.hp<=0: c.alive=False; debug_print(f"CORE {c.idx}/3 destroyed")
                    break
    def draw(self,surface,cam,t,font_sm=None,font_xs=None):
        sx,sy=cam.apply(self.x,self.y); room=pygame.Rect(int(sx),int(sy),int(self.w),int(self.h))
        if room.right<0 or room.left>SCREEN_W: return
        # No large room/corridor box: challenge visuals are small hazards/barriers blended into normal map.
        if self.status!="completed":
            gr=cam.apply_rect(self.gate_rect); pygame.draw.rect(surface,(80,15,15),gr,border_radius=4); pygame.draw.rect(surface,RED,gr,border_radius=4,width=2)
        else:
            gr=cam.apply_rect(self.gate_rect); pygame.draw.rect(surface,(20,90,45),gr,border_radius=4,width=1)
        self._draw_effects(surface,cam,t)
        if font_sm and (self.status=="active" or self.text_timer>0):
            title=CHALLENGE_TITLES.get(self.challenge_type,"SECURITY LOCKDOWN") if self.status!="completed" else "GATE OPENED"
            txt=font_sm.render(title,True,self.accent if self.status!="completed" else GREEN); surface.blit(txt,(SCREEN_W//2-txt.get_width()//2,126))
    def _draw_effects(self,surface,cam,t):
        for mp in self.platforms: mp.draw(surface,cam)
        if self.challenge_type in("heat_elevator","frozen_corridor","storm_elevator"):
            warn_x=int(cam.apply(self.x+self.w//2,0)[0]); col=ORANGE if self.challenge_type=="heat_elevator" else YELLOW if self.challenge_type=="storm_elevator" else (170,235,255)
            if self.timer%90>45: pygame.draw.line(surface,col,(warn_x,80),(warn_x,SCREEN_H-60),2)
        disabled=lasers_disabled_for_level(self.level_num)
        for l in self.lasers:
            lx=int(cam.apply(l["x"],0)[0]); col=(45,70,80) if disabled else RED if l["active"] else ORANGE if l["warn"] else (80,20,20)
            pygame.draw.line(surface,col,(lx,120),(lx,550),2 if disabled else 4 if l["active"] else 1)
        if disabled and self.lasers:
            off=make_font(10,"hud",True).render("LASER DISABLED",True,CYAN)
            rsx,rsy=cam.apply(self.x,self.y)
            surface.blit(off,(int(rsx+self.w//2-off.get_width()//2),int(rsy+20)))
        for h in self.hazards:
            hx,hy=cam.apply(h["x"],h["y"]); pygame.draw.circle(surface,(150,140,130),(int(hx),int(hy)),h["r"]); pygame.draw.circle(surface,GRAY,(int(hx),int(hy)),h["r"],1)
        for c in self.cores: c.draw(surface,cam,t,self.accent)
        if self.challenge_type in("glitch_room","server_lockdown","corex_trial") and random.random()<0.12:
            pygame.draw.rect(surface,(*self.accent,70),(random.randint(0,SCREEN_W-80),random.randint(100,500),random.randint(30,90),random.randint(2,7)))

challenge_rooms=[]

ALL_CHALLENGE_TYPES=[
    "security_gate","heat_elevator","laser_room","zero_gravity_corridor","glitch_room",
    "frozen_corridor","server_lockdown","storm_elevator","reactor_core_room","corex_trial"
]

def create_challenge_rooms_for_level(level_num,world_w,level_theme):
    ld=get_level_data(level_num); ctype=get_challenge_type_for_level(level_num,level_theme)
    rooms=[]; completed=set(save_data.get("completed_challenges",[])); used=set()
    def add_room(x,y,w,h,challenge_type,room_id):
        key=f"L{level_num}:{room_id}:{challenge_type}"
        if key in completed or key in used: return
        used.add(key); rooms.append(ChallengeRoom(x,y,w,h,level_theme,challenge_type,level_num,ld["accent"],room_id))
    # Stability fix: generate a single deterministic ChallengeRoom per level.
    # Older Level 11 code spawned every challenge type, which could overlap states and respawn old rooms.
    base_x=max(1350,min(world_w-1200,world_w//2-260))
    add_room(base_x,115,560,445,ctype,0)
    debug_print("ChallengeRoom created:",ctype,"level:",level_num)
    debug_print("Challenge created:",ctype,"Level:",level_num)
    return rooms

def update_challenge_rooms(player_obj,enemies_list,p_bullets,e_bullets):
    for cr in challenge_rooms: cr.update(player_obj,enemies_list,p_bullets,e_bullets)

def draw_challenge_rooms(surface,cam,t,font_sm=None,font_xs=None):
    for cr in challenge_rooms: cr.draw(surface,cam,t,font_sm,font_xs)

def _add_platform_with_rewards(platforms,coins,x,y,w,rng,reward="safe",coin_type="gold"):
    w=max(82,min(240,int(w)))
    rect=pygame.Rect(int(x),int(y),int(w),16)
    platforms.append(rect)
    if reward:
        count=1 if reward=="safe" else 2 if reward=="medium" else 3
        spacing=min(42,max(28,w//max(2,count+1)))
        start=rect.x+max(22,(rect.w-spacing*(count-1))//2)
        for i in range(count):
            ctype="rare" if reward=="hard" and i==count//2 and rng.random()<0.22 else coin_type
            coins.append(Coin(start+i*spacing,float(rect.y-28-rng.randint(0,8)),ctype))
    return rect

def generate_platform_layout(level_num,theme,x_start,x_end,section_type,rng,platforms,coins,moving_plats,water_zones,tunnels,fly_zones):
    """Build readable platform patterns only; collision stays standard pygame.Rect platforms."""
    x_cursor=x_start
    length=max(360,x_end-x_start)
    if section_type==0:
        heights=[492,456,420,386,416,452,488]
        widths=[168,136,118,150,190,130,160]
        for i,hy in enumerate(heights[:min(len(heights),4+level_num//2)]):
            px=x_start+70+i*158
            if px+widths[i]<x_end:
                reward="medium" if i>=2 else "safe"
                _add_platform_with_rewards(platforms,coins,px,hy,widths[i],rng,reward)
                x_cursor=max(x_cursor,px+widths[i]+80)
    elif section_type==1:
        # Moving platforms appear in their own readable section, not everywhere.
        rows=[(x_start+100,430,148,False),(x_start+340,350,118,True),(x_start+585,420,156,False)]
        for i,(x,y,w,vert) in enumerate(rows[:2+min(1,level_num//4)]):
            if x+w<x_end:
                moving_plats.append(MovingPlatform(int(x),int(y),int(w),60+level_num*4,0.85+level_num*0.08,vert))
                if i>0: coins.append(Coin(x+w//2,float(y-32),"rare" if i==1 else "gold"))
                x_cursor=max(x_cursor,x+w+160)
    elif section_type==2:
        tw=min(rng.randint(520+level_num*35,760+level_num*50),max(520,length-90)); gy=rng.randint(150,230); gh=max(150,220-level_num*3)
        if x_start+tw<x_end:
            tunnel=TunnelSegment(x_start,tw,gy,gh,level_num,theme)
            tunnels.append(tunnel)
            for cx,cy in tunnel.coin_positions(4): coins.append(Coin(cx,cy,"gold"))
        x_cursor=x_start+tw+150
    elif section_type==3:
        pattern=[(70,480,210),(330,430,142),(545,382,176),(795,448,126)]
        for i,(dx,py,pw) in enumerate(pattern):
            px=x_start+dx
            if px+pw<x_end:
                _add_platform_with_rewards(platforms,coins,px,py,pw,rng,"medium" if i%2 else "safe")
                x_cursor=max(x_cursor,px+pw+90)
    elif section_type==4:
        # Split route: lower safe path + upper harder reward path.
        lower=[(70,492,170),(310,472,150),(540,492,185)]
        upper=[(205,346,108),(420,304,124),(650,338,110)]
        for dx,py,pw in lower:
            px=x_start+dx
            if px+pw<x_end: _add_platform_with_rewards(platforms,coins,px,py,pw,rng,"safe") ; x_cursor=max(x_cursor,px+pw+90)
        for dx,py,pw in upper:
            px=x_start+dx
            if px+pw<x_end: _add_platform_with_rewards(platforms,coins,px,py,pw,rng,"hard") ; x_cursor=max(x_cursor,px+pw+90)
    elif section_type==5:
        ww=min(rng.randint(760+level_num*35,1100+level_num*45),max(720,length-80))
        water_zones.append(WaterHazard(x_start,ww,536,64))
        step_count=5+level_num//3
        for i in range(step_count):
            px=x_start+80+i*(ww-160)//max(1,step_count-1); py=500-(i%3)*28-rng.randint(0,18)
            _add_platform_with_rewards(platforms,coins,px,py,104+(i%2)*24,rng,"safe")
        x_cursor=x_start+ww+180
    elif section_type==8:
        steps=7+level_num//2
        for i in range(steps):
            px=x_start+70+i*132; py=504-min(270,i*36)
            if i>6: py=252+(i%3)*42
            pw=[108,126,96,138][i%4]
            if px+pw<x_end:
                _add_platform_with_rewards(platforms,coins,px,py,pw,rng,"hard" if i%2==0 and py<390 else "safe")
                x_cursor=max(x_cursor,px+pw+70)
    elif section_type==9:
        for i in range(5):
            px=x_start+85+i*185; py=468-(i%2)*72
            if px+130<x_end:
                moving_plats.append(DisappearingPlatform(int(px),int(py),122+rng.randint(-10,18),170+rng.randint(0,35),105+rng.randint(0,18)))
                if i%2==0: coins.append(Coin(px+50,float(py-30),"gold"))
                x_cursor=max(x_cursor,px+230)
    elif section_type==10:
        for i in range(4):
            px=x_start+90+i*215; py=498-(i%3)*56
            if px+150<x_end:
                moving_plats.append(BreakablePlatform(int(px),int(py),138+rng.randint(-16,22),230+rng.randint(0,50)))
                coins.append(Coin(px+58,float(py-32),"rare" if i==2 else "gold"))
                x_cursor=max(x_cursor,px+250)
    elif section_type==11:
        for i in range(4):
            px=x_start+95+i*210; py=500-i*52
            if px+150<x_end:
                moving_plats.append(ElevatorPlatform(int(px),int(py),132+rng.randint(-8,18),130+level_num*5,0.55+level_num*0.035))
                if i>0: coins.append(Coin(px+56,float(py-34),"gold"))
                x_cursor=max(x_cursor,px+245)
    elif section_type==12:
        # Conveyor + falling sequence; placed below top HUD safe zone.
        for i in range(5):
            px=x_start+75+i*190; py=486-(i%2)*54
            if px+150<x_end:
                moving_plats.append(ConveyorPlatform(int(px),int(py),136+rng.randint(-8,18),1 if i%2==0 else -1))
                if i in(1,3): moving_plats.append(FallingPlatform(int(px+92),int(py-78),108,42+rng.randint(0,22)))
                coins.append(Coin(px+50,float(py-32),"gold")); x_cursor=max(x_cursor,px+245)
    elif section_type==13:
        # Decorative rotating platforms in a clean zig-zag climb.
        for i in range(6):
            px=x_start+65+i*150; py=502-(i%4)*58
            if py<220: py=260+(i%2)*46
            if px+126<x_end:
                moving_plats.append(RotatingPlatform(int(px),int(py),118+rng.randint(-10,14)))
                if i%2==0: coins.append(Coin(px+48,float(py-34),"rare" if i==4 else "gold"))
                x_cursor=max(x_cursor,px+205)
    else:
        pattern=[(80,470,150),(285,420,112),(470,370,170),(720,455,128)]
        for dx,py,pw in pattern:
            px=x_start+dx
            if px+pw<x_end:
                _add_platform_with_rewards(platforms,coins,px,py,pw,rng,"medium")
                x_cursor=max(x_cursor,px+pw+90)
    return max(x_cursor,x_start+360)

def avoid_weapon_hud_world_rewards(items,world_w):
    """Keep important rewards out of the bottom-right HUD view near the end camera.
    This only moves reward visuals/items, not platform collision or gameplay physics.
    """
    cam_end=max(0,world_w-SCREEN_W)
    safe=pygame.Rect(SCREEN_W-190,SCREEN_H-85,190,85)
    for item in items:
        sx=int(getattr(item,"wx",0)-cam_end); sy=int(getattr(item,"wy",0))
        if safe.collidepoint(sx,sy):
            item.wx=max(80,float(cam_end+safe.left-42))
            item.wy=max(180,float(safe.top-32))

def validate_authored_terminal_positions(terminals_list,platforms,water_zones,tunnels,world_w):
    """Keep authored terminals dry, grounded, and outside generated tunnel walls."""
    def blocked(rect):
        if any(rect.colliderect(wz.get_rect()) for wz in water_zones): return True
        return any(rect.colliderect(tun.get_top_rect()) or rect.colliderect(tun.get_bot_rect()) for tun in tunnels)
    for term in terminals_list:
        base_y=560-term.H
        original_x=int(term.wx)
        offsets=[0,-180,180,-320,320,-520,520,-760,760]
        placed=False
        for off in offsets:
            nx=max(80,min(int(world_w)-term.W-80,original_x+off))
            rect=pygame.Rect(nx,base_y,term.W,term.H)
            support=pygame.Rect(nx-30,base_y+term.H,term.W+60,12)
            if not blocked(rect) and not any(support.colliderect(wz.get_rect()) for wz in water_zones):
                term.wx=float(nx); term.wy=float(base_y); placed=True; break
        if placed: continue
        nx=max(80,min(int(world_w)-term.W-80,original_x))
        ledge_y=500
        term.wx=float(nx); term.wy=float(ledge_y-term.H)
        ledge=pygame.Rect(nx-34,ledge_y,term.W+68,12)
        if not any(ledge.colliderect(p) for p in platforms): platforms.append(ledge)

# ------------------------------------------------------------------------------------
# PCG WORLD GENERATION
# ------------------------------------------------------------------------------------
def generate_world(level_num, base_seed=None):
    global WORLD_W, powerups, challenge_rooms, keycard_pickups, terminals, security_nodes, hidden_room_entrances, security_doors
    WORLD_W=get_world_width_for_level(level_num); boss_x=WORLD_W-450
    keycard_pickups=[]; terminals=[]; security_nodes=[]; hidden_room_entrances=[]; security_doors=[]
    rng,world_seed=new_level_rng(level_num, base_seed); rng2=random.Random(world_seed^0x9E3779B97F4A7C15)
    boss_data=select_random_boss_data(level_num, random.Random(level_num*1000003+42))
    ld=get_level_data(level_num); accent_col=ld["accent"]
    platforms=[pygame.Rect(0,560,WORLD_W,40)]
    moving_plats=[]; spike_traps=[]; tunnels=[]; water_zones=[]; chests=[]; enemies_list=[]; fly_zones=[]; facility_sections=[]; coins=[]
    challenge_rooms=create_challenge_rooms_for_level(level_num,WORLD_W,ld["theme"])
    for cr in challenge_rooms:
        platforms.append(pygame.Rect(int(cr.x+70),500,130,16))
        platforms.append(pygame.Rect(int(cr.x+cr.w-210),430,130,16))
        for mp in cr.platforms: moving_plats.append(mp)

    start_plats=[(160,480,140),(340,440,120),(500,400,100),(680,460,130),(850,430,110)]
    for bx2,by2,bw2 in start_plats: platforms.append(pygame.Rect(bx2,by2,bw2,16))
    for bx2,by2,_ in start_plats[1:]: coins.append(Coin(bx2+40,float(by2-30),"gold"))
    chests.append(Chest(350,510,"common"))

    zone2_end=WORLD_W-900; x_cursor=900
    fly_count=0; fly_levels={4,8,11,12}; max_fly=2 if level_num==11 else 1 if level_num in fly_levels else 0; fac_count=0; max_fac=0
    debug_print("Level:",level_num)
    debug_print("fly_levels:",fly_levels)
    debug_print("max_fly:",max_fly)
    # Longer, less repetitive sections: platform challenge -> combat -> tunnel -> secret/underground -> event -> boss.
    section_w=980+level_num*95
    level_patterns={
        1:[0,4,1,9], 2:[5,1,0,10], 3:[5,0,1,11], 4:[6,4,1,2], 5:[5,0,1,9], 6:[8,0,1,10], 7:[5,8,1,11],
        8:[6,5,4,2], 9:[5,1,8,9], 10:[8,1,0,10], 11:[6,8,1,11,2], 12:[6,5,8,9], 13:[5,8,5,1,10,11]
    }
    pattern=list(level_patterns.get(level_num,[0,1,4,5,8]))
    extra_pool=[0,1,2,3,4,5,8,9,10,11,12,13]
    # Preserve authored section order enough to introduce something new every 20-30% of the level.
    if level_num>3:
        first_section=pattern[:1]; rest_sections=pattern[1:]; rng.shuffle(rest_sections); pattern=first_section+rest_sections
    while len(pattern)<7:
        pattern.append(rng.choice(extra_pool))

    while x_cursor<zone2_end:
        section_idx=int((x_cursor-900)//section_w)
        section_type=pattern[(section_idx+(0 if fly_count==0 and max_fly>0 else rng.randint(0,1)))%len(pattern)]
        debug_print("section_type:",section_type)
        if section_type==6 and fly_count<max_fly and x_cursor+1300<zone2_end:
            fz_min=(3200 if level_num==11 else 2200)+level_num*260
            fz_max=(4300 if level_num==11 else 3000)+level_num*300
            fz_w=min(rng.randint(fz_min,fz_max),zone2_end-x_cursor-250)
            fly_zones.append(FlyZone(x_cursor,fz_w,level_num,random.Random(rng.randint(0,2**63-1)))); fly_count+=1
            chests.append(Chest(x_cursor+fz_w+100,510,"rare")); x_cursor+=fz_w+250; continue
        x_cursor=generate_platform_layout(level_num,ld["theme"],x_cursor,min(x_cursor+section_w,zone2_end),section_type,rng,platforms,coins,moving_plats,water_zones,tunnels,fly_zones)
        spawn_min=max(900,int(x_cursor-section_w))
        spawn_max=int(min(x_cursor,zone2_end-100))
        if spawn_min<=spawn_max:
            if rng.random()<0.55+level_num*0.04:
                ex=rng.randint(spawn_min,spawn_max)
                elite=rng.choice(["red","fast","shield","bomber","sniper","drone"]) if rng.random()<0.05+level_num*0.014 else None
                enemies_list.append(ScoutBot(ex,520,1.0+level_num*0.08,max(80,140-level_num*6),elite))
            if rng.random()<0.28:
                cx4=rng.randint(spawn_min,spawn_max)
                chests.append(Chest(cx4,510,"common"))
            if rng.random()<0.22:
                cx5=rng.randint(spawn_min,spawn_max); cy5=rng.randint(260,470)
                for ci in range(rng.randint(4,8)): coins.append(Coin(cx5+ci*24,float(cy5-rng.randint(0,25)),"rare" if rng.random()<0.08 else "gold"))
            if rng.random()<0.06+level_num*0.006:
                powerups.append(PowerUp(rng.randint(spawn_min,spawn_max),rng.randint(260,500),rng.choice(list(POWERUP_DATA.keys()))))
        x_cursor+=rng.randint(80,200)

    if max_fly>0 and fly_count==0:
        fallback_x=max(1250,min(WORLD_W-2200,WORLD_W//2-900))
        fallback_w=max(1200,min(2200,WORLD_W-fallback_x-1300))
        if fallback_w>700:
            fly_zones.append(FlyZone(fallback_x,fallback_w,level_num,random.Random(rng.randint(0,2**63-1))))
            fly_count+=1
            chests.append(Chest(fallback_x+fallback_w+80,510,"rare"))
    debug_print("fly_count:",fly_count)
    debug_print("fly_zones count:",len(fly_zones))

    secret_x=max(1200,min(zone2_end-420,int(WORLD_W*0.58)+rng2.randint(-260,260)))
    secret_y=rng2.choice([190,220,250])
    platforms.append(pygame.Rect(secret_x,secret_y,180,16))
    platforms.append(pygame.Rect(secret_x-170,secret_y+78,110,16))
    chests.append(Chest(secret_x+72,secret_y-28,"secret"))
    for ci in range(5): coins.append(Coin(secret_x+20+ci*32,float(secret_y-30-rng2.randint(0,16)),"rare" if ci==2 else "gold"))

    if level_num==2:
        keycard_pickups.append(KeycardPickup(int(WORLD_W*0.24),520,"Maintenance Keycard"))
        terminals.append(Terminal(int(WORLD_W*0.34),500,"lvl02_laser",["disable_laser","read_research_log"],"Maintenance Keycard"))
    elif level_num==4:
        keycard_pickups.append(KeycardPickup(int(WORLD_W*0.24),520,"Maintenance Keycard"))
        terminals.append(Terminal(int(WORLD_W*0.42),500,"lvl04_reactor",["disable_laser","read_research_log"],"Maintenance Keycard"))
    elif level_num==6:
        keycard_pickups.append(KeycardPickup(int(WORLD_W*0.24),520,"Security Keycard"))
        terminals.append(Terminal(int(WORLD_W*0.38),500,"lvl06_gate",["unlock_security_door","read_research_log"],"Security Keycard"))
    elif level_num==7:
        keycard_pickups.append(KeycardPickup(int(WORLD_W*0.24),520,"Maintenance Keycard"))
        keycard_pickups.append(KeycardPickup(int(WORLD_W*0.37),520,"Maintenance Keycard"))
        keycard_pickups.append(KeycardPickup(int(WORLD_W*0.30),520,"Security Keycard"))
        terminals.append(Terminal(int(WORLD_W*0.38),500,"lvl07_lift",["unlock_ventilation","read_research_log"],"Maintenance Keycard"))
    elif level_num==8:
        keycard_pickups.append(KeycardPickup(int(WORLD_W*0.24),520,"Maintenance Keycard"))
        hidden_room_entrances.append(HiddenRoomEntrance(int(WORLD_W*0.61),490,"lab_08","Maintenance Keycard","log_08"))
        terminals.append(Terminal(int(WORLD_W*0.31),500,"lvl08_log",["read_research_log"],"Maintenance Keycard"))
    elif level_num==9:
        keycard_pickups.append(KeycardPickup(int(WORLD_W*0.24),520,"Maintenance Keycard"))
        hidden_room_entrances.append(HiddenRoomEntrance(int(WORLD_W*0.57),490,"lab_09","Maintenance Keycard","log_09"))
        proto_chest=Chest(int(WORLD_W*0.46),510,"rare"); proto_chest.content="plasma"; chests.append(proto_chest)
    elif level_num==10:
        keycard_pickups.append(KeycardPickup(int(WORLD_W*0.24),520,"Security Keycard"))
        terminals.append(Terminal(int(WORLD_W*0.37),500,"lvl10_master",["read_research_log"],"Master Key"))
    elif level_num==11:
        keycard_pickups.append(KeycardPickup(int(WORLD_W*0.24),520,"Master Key"))
        terminals.append(Terminal(int(WORLD_W*0.35),500,"lvl11_core",["read_research_log"],"Master Key"))

    if level_num==6:
        security_doors.append(SecurityDoor(int(WORLD_W*0.46),450,"main_gate_6","unlock_security_door","lvl06_gate","MAIN GATE"))

    # Boss area gate is always authored; completion state is enforced at interaction time.
    boss_gate_keycard="Master Key" if level_num>=10 else "Security Keycard" if level_num>=5 else "Maintenance Keycard" if level_num>=2 else None
    terminals.append(Terminal(boss_x-620,500,f"boss_gate_{level_num}",["unlock_boss_area"],boss_gate_keycard))
    security_doors.append(SecurityDoor(boss_x-300,450,f"boss_door_{level_num}","unlock_boss_area",f"boss_gate_{level_num}"))

    if level_num==3:
        keycard_pickups.append(KeycardPickup(int(WORLD_W*0.47),520,"Maintenance Keycard"))
    elif level_num==5:
        keycard_pickups.append(KeycardPickup(int(WORLD_W*0.43),520,"Security Keycard"))
    elif level_num==10:
        keycard_pickups.append(KeycardPickup(int(WORLD_W*0.52),520,"Master Key"))

    if level_num==5:
        for idx,offset in enumerate((-220,0,220),start=1):
            security_nodes.append(SecurityNode(boss_x-1320+offset,512,f"sec_{idx}"))
    if level_num in (12,13):
        keycard_pickups.append(KeycardPickup(int(WORLD_W*0.24),520,"Master Key"))
    if level_num in (11,13):
        security_nodes.append(SecurityNode(int(WORLD_W*0.52),512,f"ai_core_{level_num}","ai_core","log_11"))

    chests.append(Chest(WORLD_W//2+rng2.randint(-200,200),510,"rare"))
    def in_fly_zone_x(x): return any(fz.wx-120<=x<=fz.wx+fz.width+120 for fz in fly_zones)
    def safe_enemy_x():
        for _ in range(60):
            ex=rng.randint(900,int(zone2_end))
            if not in_fly_zone_x(ex): return ex
        return rng.choice([900,int(zone2_end)])
    enemies_list=[en for en in enemies_list if not in_fly_zone_x(en.wx)]
    num_min=4+level_num*2
    while len(enemies_list)<num_min:
        elite=rng.choice(["red","fast","shield","bomber","sniper","drone"]) if rng.random()<0.04+level_num*0.012 else None
        enemies_list.append(ScoutBot(safe_enemy_x(),520,1.0+level_num*0.08,max(80,140-level_num*6),elite))
    # Mini boss checkpoint before major boss. Uses existing enemy/update/draw lists for stability.
    mb_x=max(1500,boss_x-1150); mb_type="reactor_sentinel" if ld["theme"] in("core","lab") else "elite_drone" if level_num%3==0 else "tunnel_guardian"
    mini=ScoutBot(mb_x,500-ScoutBot.HEIGHT,1.0+level_num*0.18,max(65,130-level_num*5),mb_type)
    enemies_list.append(mini)
    platforms.append(pygame.Rect(int(mb_x-120),456,260,16)); chests.append(Chest(mb_x+155,510,"rare"))

    arena_x=boss_x-380
    arena_plats=[(arena_x,420,240),(arena_x+300,420,240),(arena_x+140,310,320),(arena_x+80,210,160),(arena_x+380,210,160),(arena_x+180,120,140)]
    for rx,ry,rw in arena_plats: platforms.append(pygame.Rect(rx,ry,rw,16))
    for i in range(3+level_num//3):
        rwx=arena_x-500-i*120
        if rwx>1100: coins.append(Coin(rwx,260+i%2*40,"rare" if i%3==0 else "gold"))
    validate_authored_terminal_positions(terminals,platforms,water_zones,tunnels,WORLD_W)
    avoid_weapon_hud_world_rewards(coins+chests+powerups,WORLD_W)
    debug_print("Level:", level_num)
    debug_print("World width:", WORLD_W)
    debug_print("Platforms:", len(platforms))
    debug_print("Enemies:", len(enemies_list))
    debug_print("Coins:", len(coins))
    debug_print("Chests:", len(chests))
    debug_print("Boss X:", boss_x)
    debug_print("FacilitySection generated:",fac_count)
    debug_print("facility_sections count:",len(facility_sections))
    return platforms,enemies_list,boss_x,chests,moving_plats,spike_traps,tunnels,fly_zones,facility_sections,water_zones,coins,boss_data



def build_checkpoints():

    global checkpoints, current_checkpoint

    checkpoints = [

        Checkpoint(int(WORLD_W*0.25)),

        Checkpoint(int(WORLD_W*0.50)),

        Checkpoint(int(WORLD_W*0.75)),

        Checkpoint(boss_x_world-600)

    ]

    current_checkpoint = None

# ------------------------------------------------------------------------------------
# FONTS
# ------------------------------------------------------------------------------------
font_xs=font_sm=font_md=font_lg=font_xl=None
rebuild_fonts()

class MenuStarField:
    def __init__(self):
        rng = random.Random(1)
        self.stars = [(rng.randint(0, SCREEN_W), rng.randint(0, SCREEN_H),
                       rng.randint(1, 2), rng.uniform(0.3, 1.0),
                       rng.uniform(0.001, 0.005)) for _ in range(120)]
    def draw(self, surface, cam_x):
        t = pygame.time.get_ticks()
        for s in self.stars:
            pulse = int(s[3] * (120 + 50 * math.sin(t * s[4] + s[1] * 0.02)))
            pulse = max(0, min(200, pulse))
            if pulse > 15:
                col = (pulse, pulse, min(200, pulse + 20))
                pygame.draw.circle(surface, col, (int(s[0]), int(s[1])), s[2])

starfield=MenuStarField()
sounds=SoundManager()

def apply_saved_settings():
    s=save_data.get("settings",{})
    set_language(s.get("language","id"))
    if "vol_sfx" in s: sounds.set_vol_sfx(s["vol_sfx"])
    if "vol_bgm" in s: sounds.set_vol_bgm(s["vol_bgm"])
    if s.get("mute",False) and not sounds.muted: sounds.toggle_mute()
    if s.get("fullscreen",False) and not fullscreen: toggle_fullscreen()

SAVE_ICON_CACHE={}
def get_save_icon():
    if "floppy" not in SAVE_ICON_CACHE:
        s=pygame.Surface((16,16),pygame.SRCALPHA)
        pygame.draw.rect(s,(60,160,220),(2,2,12,12),border_radius=1)
        pygame.draw.rect(s,(200,220,240),(5,3,6,4),border_radius=1)
        pygame.draw.rect(s,(100,100,120),(6,9,4,4),border_radius=1)
        pygame.draw.line(s,(180,220,255),(2,2),(2,13),2)
        pygame.draw.line(s,(180,220,255),(2,2),(13,2),2)
        SAVE_ICON_CACHE["floppy"]=s
    return SAVE_ICON_CACHE["floppy"]

def get_folder_icon():
    if "folder" not in SAVE_ICON_CACHE:
        s=pygame.Surface((16,16),pygame.SRCALPHA)
        pygame.draw.polygon(s,(180,160,60),[(2,4),(7,4),(9,6),(14,6),(14,13),(2,13)])
        pygame.draw.rect(s,(220,200,80),(2,6,12,7),border_radius=1)
        pygame.draw.polygon(s,(240,220,100),[(2,6),(14,6),(14,12),(2,12)])
        pygame.draw.line(s,(180,160,60),(2,6),(14,6),1)
        SAVE_ICON_CACHE["folder"]=s
    return SAVE_ICON_CACHE["folder"]

apply_saved_settings()

has_save=save_data.get("has_save",False)
CX=SCREEN_W//2
btn_newgame  =MenuButton(CX-140,220,280,36,"GAME BARU",CYAN)
btn_continue =MenuButton(CX-140,260,280,36,"LANJUTKAN",(80,200,140),not has_save)
btn_save_info=MenuButton(CX-140,300,280,36,"DATA SAVE",PURPLE)
btn_boss_rush=MenuButton(CX-140,340,280,36,"BOSS RUSH",(200,100,255))
btn_settings =MenuButton(CX-140,380,280,36,"PENGATURAN",TEAL)
btn_stats_m  =MenuButton(CX-140,420,280,36,"STATISTIK",CYAN)
btn_quit_m   =MenuButton(CX-140,460,280,36,"KELUAR",RED)
btn_resume_p =MenuButton(CX-120,122,240,42,"LANJUT",CYAN)
btn_save_p   =MenuButton(CX-120,168,240,42,"SIMPAN GAME",(60,200,160),icon_surf=get_save_icon())
btn_shop_p   =MenuButton(CX-120,214,240,42,"$  TOKO",GOLD)
btn_restart  =MenuButton(CX-120,260,240,42,"ULANG LEVEL",ORANGE)
btn_settings_p=MenuButton(CX-120,306,240,42,"PENGATURAN",TEAL)
btn_menu_b   =MenuButton(CX-120,352,240,42,"MENU UTAMA",PURPLE)
SHOP_HUD_RECT=pygame.Rect(SCREEN_W-134,78,126,24)
SOUND_HUD_RECT=pygame.Rect(SCREEN_W-196,78,58,22)
FULLSCREEN_MENU_RECT=pygame.Rect(SCREEN_W-176,556,168,24)

def get_volume_button_rect():
    return SOUND_HUD_RECT

def handle_volume_click(mouse_pos):
    if not get_volume_button_rect().collidepoint(mouse_pos): return False
    sounds.toggle_mute()
    if sounds.enabled and sounds.bgm_ch:
        sounds.bgm_ch.set_volume(0.0 if sounds.muted else sounds.vol_bgm)
    save_settings()
    debug_print("Volume button clicked")
    return True

def sync_ui_texts():
    btn_newgame.text=tr("menu.new_game")
    btn_continue.text=tr("menu.continue")
    btn_save_info.text=tr("menu.save_data")
    btn_boss_rush.text=tr("boss_rush.title")
    btn_settings.text=tr("menu.settings")
    btn_stats_m.text=tr("stats")
    btn_quit_m.text=tr("menu.quit")
    btn_resume_p.text=tr("pause.resume")
    btn_save_p.text=tr("pause.save_game")
    btn_shop_p.text=tr("pause.shop")
    btn_restart.text=tr("pause.restart")
    btn_settings_p.text=tr("pause.settings")
    btn_menu_b.text=tr("pause.main_menu")

# ------------------------------------------------------------------------------------
# GAME STATE
# ------------------------------------------------------------------------------------
settings_screen=SettingsScreen()
codex_screen=CodexScreen()
achievement_screen=AchievementScreen()
difficulty_screen=DifficultyScreen()
stats_screen=StatisticsScreen()
shop=Shop()
scene="menu"
player=Player(); camera=Camera()
p_bullets=[]; e_bullets=[]; chests=[]; coins=[]
keycard_pickups=[]; terminals=[]; security_nodes=[]; hidden_room_entrances=[]; security_doors=[]
score=0; money=0; lives=5; level=1; checkpoint=1
multiplier=1; mult_timer=0; mult_decay_tick=0
screen_fade=0; screen_fade_dir=0; pause_scale=0.0
boss=None; boss_spawned=False; waiting_for_dialogue=False
level_clear=False; level_clear_timer=0
boss_x_world=2850
active_boss_data=dict(BOSS_DATA[1])
moving_plats=[]; spike_traps=[]; tunnels=[]; fly_zones=[]; facility_sections=[]; water_zones=[]
session_kills=0; session_stats={}; show_save_screen=False; show_new_game_name_input=False; show_difficulty_select=False; confirm_overwrite_file=""; confirm_delete_file=""; current_save_file=""; play_time_accum=0
boss_rush_active=False; boss_rush_wave=0; boss_rush_score=0; boss_rush_bosses=[]; boss_rush_arena_x=0; boss_rush_seed=0; show_boss_rush_select=False; show_boss_rush_open_t=0; boss_rush_max_waves=0; boss_rush_combo=0; boss_rush_mult=1; boss_rush_selected=[True]*10
new_game_name=""; selected_difficulty="normal"; difficulty_select_start=0; rename_file=""; rename_input=""; save_scroll_offset=0; pending_tutorial_after_intro=False
save_screen_data=({})
respawn_wx,respawn_wy=120.0,480.0
checkpoints=[]
current_checkpoint=None

powerups=[]; active_powerups={}; combo_count=0; combo_timer=0; mission_state={}
terminal_ui_active=False; active_terminal=None; terminal_ui_message=""; terminal_ui_rects={}
terminal_processing_action=None; terminal_processing_timer=0; terminal_processing_duration=90
research_log_active=False; research_log_key=""
level_start_ticks=pygame.time.get_ticks(); level_damage_taken=0; level_best_combo=0; level_clear_rank="-"; level_reward_lines=[]
env_event_timer=0; env_event_cooldown=240; env_event_type=None
platforms,enemies,boss_x_world,chests,moving_plats,spike_traps,tunnels,fly_zones,facility_sections,water_zones,coins,active_boss_data=generate_world(level)
build_checkpoints()
start_level_mission(level)
reset_level_stats()
reset_environment_event()
opening.start()


def transition_to(new_state):
    global scene,show_save_screen,show_difficulty_select,show_new_game_name_input,show_boss_rush_select
    global confirm_overwrite_file,confirm_delete_file,rename_file,rename_input,new_game_name
    global save_screen_data,terminal_ui_active,active_terminal,terminal_ui_message,terminal_processing_action,terminal_processing_timer,research_log_active,research_log_key

    old = scene

    show_save_screen=False
    show_difficulty_select=False
    show_new_game_name_input=False
    show_boss_rush_select=False
    confirm_overwrite_file=""
    confirm_delete_file=""
    rename_file=""
    rename_input=""
    new_game_name=""
    save_screen_data={}
    terminal_ui_active=False; active_terminal=None; terminal_ui_message=""; terminal_processing_action=None; terminal_processing_timer=0; research_log_active=False; research_log_key=""

    shop.active=False
    settings_screen.active=False
    codex_screen.active=False
    achievement_screen.active=False
    stats_screen.active=False
    difficulty_screen.active=False

    story_intro.active=False
    boss_dialogue.active=False
    boss_intro.active=False
    tutorial.active=False
    opening.active=False

    scene = new_state

    print(f"[STATE] {old} -> {new_state}")

    import traceback
    traceback.print_stack(limit=5)

def start_level_intro(level_num, start_tutorial=False):
    global pending_tutorial_after_intro
    pending_tutorial_after_intro=start_tutorial
    transition_to("level_intro")
    story_intro.start(level_num)

def blocking_overlay_active():
    return (
        shop.active
        or settings_screen.active
        or codex_screen.active
        or achievement_screen.active
        or stats_screen.active
        or difficulty_screen.active
        or terminal_ui_active
        or research_log_active
        or tutorial.active
        or boss_dialogue.active
        or boss_intro.active
    )

def sync_adventure_progress_from_save(player_obj):
    player_obj.keycards=set(save_data.get("keycards",[]))
    player_obj.story_logs=set(save_data.get("story_logs",[]))
    player_obj.hidden_rooms_found=sum(1 for v in save_data.get("hidden_rooms",{}).values() if v)
    player_obj.terminals_hacked=sum(len(v) for v in save_data.get("terminal_states",{}).values() if isinstance(v,list))
    player_obj.has_keycard=bool(player_obj.keycards)


def save_adventure_progress_fields(sd,player_obj):
    sd["keycards"]=sorted(getattr(player_obj,"keycards",set()))
    sd["story_logs"]=sorted(save_data.get("story_logs",list(getattr(player_obj,"story_logs",set()))))
    sd["terminal_states"]=dict(save_data.get("terminal_states",{}))
    sd["hidden_rooms"]=dict(save_data.get("hidden_rooms",{}))
    sd["mission_progress"]=dict(mission_state) if isinstance(mission_state,dict) else {}


def terminal_action_completed(action_name,terminal_id=None):
    states=save_data.get("terminal_states",{})
    if terminal_id:
        actions=states.get(terminal_id,[])
        return isinstance(actions,list) and action_name in actions
    return any(action_name in actions for actions in states.values() if isinstance(actions,list))


def lasers_disabled_for_level(level_num):
    return terminal_action_completed("disable_laser",f"lvl{level_num:02d}_laser") or terminal_action_completed("disable_laser",f"lvl{level_num:02d}_reactor")


def level_boss_terminal_ids(level_num):
    return {f"boss_gate_{level_num}"}


def level_terminal_action_completed(action_name,level_num):
    return any(terminal_action_completed(action_name,tid) for tid in level_boss_terminal_ids(level_num))


def is_boss_area_unlocked():
    return mission_state.get("complete",False) and level_terminal_action_completed("unlock_boss_area",level)


def award_keycard(player_obj,keycard_type):
    if not keycard_type: return False
    if not hasattr(player_obj,"keycards"): player_obj.keycards=set()
    if keycard_type in player_obj.keycards:
        toast(f"Already has {keycard_type}","KEY",TEXT_MUTED,90); return False
    player_obj.keycards.add(keycard_type); player_obj.has_keycard=True
    save_data["keycards"]=sorted(player_obj.keycards)
    if keycard_type=="Maintenance Keycard":
        add_mission_progress("keycard",1); unlock_story_log("log_03")
    elif keycard_type=="Master Key":
        add_mission_progress("masterkey",1); unlock_story_log("log_10")
    else:
        unlock_story_log("log_06")
    save_progress_state(include_session_kills=False)
    toast(f"Obtained {keycard_type}","KEY",GOLD,130); sounds.play("coin_rare")
    return True


def reconcile_current_mission_progress():
    if not mission_state: return
    kind=mission_state.get("kind")
    if mission_state.get("complete"): return
    keycards=set(save_data.get("keycards",[])) | set(getattr(player,"keycards",set()))
    terminal_by_mission={
        "terminal_reactor":"disable_laser",
        "terminal_gate":"unlock_security_door",
        "terminal_lift":"unlock_ventilation",
    }
    if kind in terminal_by_mission and terminal_action_completed(terminal_by_mission[kind]):
        # Only restore progress for old save files.
        if mission_state.get("progress", 0) <= 0:
            add_mission_progress(kind, mission_state.get("target", 1))
    elif kind=="keycard" and "Maintenance Keycard" in keycards:
        if mission_state.get("progress", 0) <= 0:
            add_mission_progress(kind, mission_state.get("target", 1))

    elif kind=="masterkey" and "Master Key" in keycards:
        if mission_state.get("progress", 0) <= 0:
            add_mission_progress(kind, mission_state.get("target", 1))


def keycard_drop_for_elite(enemy_obj):
    if not getattr(enemy_obj,"elite_type",None): return None
    if level>=10 and "Master Key" not in player.keycards: return "Master Key"
    if level>=5 and "Security Keycard" not in player.keycards: return "Security Keycard"
    if level>=3 and "Maintenance Keycard" not in player.keycards: return "Maintenance Keycard"
    return None


def get_nearby_terminal(player_obj):
    pr=player_obj.get_rect()
    nearby=[tm for tm in terminals if tm.interact_rect().colliderect(pr)]
    if not nearby: return None
    return min(nearby,key=lambda tm: abs((tm.wx+tm.W//2)-(player_obj.wx+player_obj.WIDTH//2)))


def get_nearby_hidden_room(player_obj):
    pr=player_obj.get_rect()
    nearby=[hr for hr in hidden_room_entrances if hr.interact_rect().colliderect(pr)]
    if not nearby: return None
    return min(nearby,key=lambda hr: abs((hr.wx+hr.W//2)-(player_obj.wx+player_obj.WIDTH//2)))


def open_terminal_interface(term):
    global terminal_ui_active,active_terminal,terminal_ui_message
    terminal_ui_active=True; active_terminal=term; terminal_ui_message=term.message or "Select terminal command"
    sounds.play("ui_click")


def close_terminal_interface():
    global terminal_ui_active,active_terminal,terminal_ui_message,terminal_processing_action,terminal_processing_timer,research_log_active,research_log_key
    terminal_ui_active=False; active_terminal=None; terminal_ui_message=""; terminal_processing_action=None; terminal_processing_timer=0; research_log_active=False; research_log_key=""


def handle_player_interaction():
    hr=get_nearby_hidden_room(player)
    if hr:
        return hr.use(player)
    tm=get_nearby_terminal(player)
    if tm:
        open_terminal_interface(tm); return True
    return False


def terminal_action_caption(action):
    if action=="disable_laser": return "Disabling laser..."
    if action=="unlock_security_door": return "Unlocking main gate..."
    if action=="unlock_ventilation": return "Unlocking ventilation..."
    if action=="unlock_boss_area": return "Opening boss area..."
    return "Accessing terminal..."


def start_terminal_action(action):
    global terminal_processing_action,terminal_processing_timer,terminal_ui_message
    if not active_terminal: return False
    status,reason=active_terminal.action_status(player,action)
    if status in("locked","denied"):
        active_terminal.message=reason; terminal_ui_message=reason
        toast("ACCESS DENIED" if status=="denied" else reason,"LOCK",ORANGE,120); sounds.play("ui_click")
        return False
    if action=="read_research_log":
        if status=="complete":
            log_key=get_level_research_log_key(level); open_research_log_screen(log_key)
            active_terminal.message="Research log opened"; terminal_ui_message=active_terminal.message
            return True
        active_terminal.use(player,action); terminal_ui_message=active_terminal.message
        return True
    if status=="complete":
        active_terminal.message="Already complete"; terminal_ui_message=active_terminal.message; sounds.play("ui_click")
        return False
    terminal_processing_action=action; terminal_processing_timer=terminal_processing_duration; terminal_ui_message="ACCESSING...\n"+terminal_action_caption(action)
    sounds.play("ui_click")
    return True


def update_terminal_processing():
    global terminal_processing_action,terminal_processing_timer,terminal_ui_message
    if not terminal_processing_action or not active_terminal: return
    terminal_processing_timer=max(0,terminal_processing_timer-1)
    if terminal_processing_timer<=0:
        action=terminal_processing_action; terminal_processing_action=None
        active_terminal.use(player,action)
        if action == "disable_laser":
            terminal_ui_message = "Laser Disabled"
        elif active_terminal is not None:
            terminal_ui_message = active_terminal.message
        else:
            terminal_ui_message = "ACCESS COMPLETE"


def close_research_log_screen():
    global research_log_active,research_log_key
    research_log_active=False; research_log_key=""


def open_research_log_screen(log_key):
    global research_log_active,research_log_key
    research_log_key=log_key; research_log_active=True


def handle_research_log_event(event):
    if not research_log_active: return False
    if event.type==pygame.KEYDOWN and event.key in(pygame.K_SPACE,pygame.K_ESCAPE):
        close_research_log_screen(); return True
    if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
        close_research_log_screen(); return True
    return True


def draw_research_log_screen(surface,font_lg,font_sm,font_xs,t):
    if not research_log_active: return
    entry=get_research_log_entry(research_log_key)
    ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((0,0,0,190)); surface.blit(ov,(0,0))
    panel=pygame.Rect(CX-285,SCREEN_H//2-180,570,360); draw_panel(surface,panel,CYAN,(5,8,24,246),radius=8)
    title=font_lg.render("Research Log",True,CYAN); surface.blit(title,(panel.centerx-title.get_width()//2,panel.y+18))
    surface.blit(render_fit(font_sm,entry["title"],WHITE,panel.w-60),(panel.x+30,panel.y+76))
    surface.blit(render_fit(font_xs,"Author: "+entry["author"],TEXT_MUTED,panel.w-60),(panel.x+30,panel.y+112))
    surface.blit(render_fit(font_xs,entry["day"],TEXT_MUTED,panel.w-60),(panel.x+30,panel.y+136))
    y=panel.y+178
    for line in wrap_text(entry["body"],font_sm,panel.w-70)[:5]:
        surface.blit(font_sm.render(line,True,TEXT_MAIN),(panel.x+34,y)); y+=28
    hint=font_xs.render("SPACE / ESC = close",True,TEXT_MUTED); surface.blit(hint,(panel.centerx-hint.get_width()//2,panel.bottom-28))


def handle_terminal_ui_event(event):
    global terminal_ui_message
    if not terminal_ui_active or not active_terminal: return False
    if terminal_processing_action:
        return True
    if event.type==pygame.KEYDOWN:
        if event.key==pygame.K_ESCAPE:
            close_terminal_interface(); return True
        if pygame.K_1<=event.key<=pygame.K_9:
            idx=event.key-pygame.K_1
            if idx<len(active_terminal.actions):
                start_terminal_action(active_terminal.actions[idx]); return True
    if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
        for idx,rect in terminal_ui_rects.items():
            if rect.collidepoint(event.pos) and idx<len(active_terminal.actions):
                start_terminal_action(active_terminal.actions[idx]); return True
        panel=pygame.Rect(CX-250,SCREEN_H//2-150,500,300)
        if not panel.collidepoint(event.pos): close_terminal_interface(); return True
    return True


def draw_terminal_interface(surface,font_lg,font_sm,font_xs,t):
    global terminal_ui_rects
    if not terminal_ui_active or not active_terminal: return
    terminal_ui_rects={}
    ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((0,0,0,170)); surface.blit(ov,(0,0))
    panel=pygame.Rect(CX-250,SCREEN_H//2-150,500,300); draw_panel(surface,panel,CYAN,(5,8,24,242),radius=8)
    title=font_lg.render("TERMINAL",True,CYAN); surface.blit(title,(panel.centerx-title.get_width()//2,panel.y+16))
    ident=font_xs.render(active_terminal.terminal_id.upper(),True,TEXT_MUTED); surface.blit(ident,(panel.centerx-ident.get_width()//2,panel.y+54))
    y=panel.y+88
    for i,action in enumerate(active_terminal.actions):
        data=TERMINAL_ACTIONS.get(action,{})
        status,reason=active_terminal.action_status(player,action)
        col=NEON_GREEN if status=="complete" else CYAN if status=="ready" else ORANGE
        if terminal_processing_action: col=TEXT_DIM if action!=terminal_processing_action else CYAN
        r=pygame.Rect(panel.x+34,y+i*42,panel.w-68,32); terminal_ui_rects[i]=r
        pygame.draw.rect(surface,(12,18,34),r,border_radius=5)
        pygame.draw.rect(surface,col,r,border_radius=5,width=1)
        label=f"{i+1}. {data.get('label',action)}"
        surface.blit(render_fit(font_sm,label,col,250),(r.x+12,r.y+6))
        surface.blit(render_fit(font_xs,reason,TEXT_MUTED if status!="ready" else TEXT_MAIN,135),(r.right-145,r.y+9))
    msg=terminal_ui_message or "Select terminal command"
    if terminal_processing_action:
        bar_w=panel.w-68; bar_y=panel.bottom-68; frac=1.0-terminal_processing_timer/max(1,terminal_processing_duration)
        pygame.draw.rect(surface,(12,18,36),(panel.x+34,bar_y,bar_w,7),border_radius=3)
        pygame.draw.rect(surface,CYAN,(panel.x+34,bar_y,int(bar_w*frac),7),border_radius=3)
    for mi,line in enumerate(str(msg).split("\n")[:3]):
        surface.blit(render_fit(font_xs,line,ORANGE if "DENIED" in line else TEXT_MAIN,panel.w-50),(panel.x+25,panel.bottom-48+mi*14))
    hint=font_xs.render("1-9 / Click = run command   ESC = close",True,TEXT_MUTED)
    surface.blit(hint,(panel.centerx-hint.get_width()//2,panel.bottom-22))


def draw_main_gate_mission_indicator(surface,cam,font_xs,t):
    if mission_state.get("kind")!="terminal_gate" or mission_state.get("complete"): return
    gate=next((d for d in security_doors if getattr(d,"door_id","")=="main_gate_6"),None)
    if not gate or gate.unlocked(): return
    gx,gy=cam.apply(gate.wx+gate.W//2,gate.wy)
    pulse=int(150+80*math.sin(t*0.008))
    col=(255,pulse,60)
    if gx<30: px=30
    elif gx>SCREEN_W-30: px=SCREEN_W-30
    else: px=int(gx)
    py=96
    pygame.draw.polygon(surface,col,[(px,py),(px-8,py+16),(px+8,py+16)])
    label=font_xs.render("MAIN GATE",True,col)
    surface.blit(label,(px-label.get_width()//2,py+20))


def draw_interaction_hint(surface,font_xs):
    if terminal_ui_active: return
    target=get_nearby_terminal(player) or get_nearby_hidden_room(player)
    if not target: return
    txt="E  TERMINAL" if isinstance(target,Terminal) else "E  SECRET ACCESS"
    label=font_xs.render(txt,True,CYAN)
    pygame.draw.rect(surface,(5,8,24,210),(CX-label.get_width()//2-12,SCREEN_H-78,label.get_width()+24,24),border_radius=5)
    surface.blit(label,(CX-label.get_width()//2,SCREEN_H-72))


def start_new_game(world_seed=None):
    global player,camera,p_bullets,e_bullets,pixels,chests,coins,score,money,lives
    global level,checkpoint,multiplier,mult_timer,mult_decay_tick,platforms,enemies
    global level_clear,boss,boss_spawned,boss_x_world,waiting_for_dialogue,active_boss_data
    global moving_plats,spike_traps,tunnels,fly_zones,facility_sections,water_zones,session_kills,session_stats,respawn_wx,respawn_wy,powerups,active_powerups,combo_count,combo_timer,current_checkpoint
    session_stats={}; record_play_started()
    player=Player(); camera=Camera()
    p_bullets=[]; e_bullets=[]; pixels=[]; chests=[]; coins=[]
    score=0; money=0; lives=5; level=1; checkpoint=1; multiplier=1; mult_timer=0; mult_decay_tick=0
    shop.reset()
    level_clear=False; boss=None; boss_spawned=False; waiting_for_dialogue=False; session_kills=0; powerups=[]; active_powerups={}; combo_count=0; combo_timer=0
    platforms,enemies,boss_x_world,chests,moving_plats,spike_traps,tunnels,fly_zones,facility_sections,water_zones,coins,active_boss_data=generate_world(1,world_seed)
    build_checkpoints()
    start_level_mission(1)
    reset_level_stats()
    reset_environment_event()
    camera = Camera()

    player.reset()
    apply_permanent_unlocks(player)
    apply_shop_upgrades(player)
    sync_adventure_progress_from_save(player)
    reconcile_current_mission_progress()

    # Spawn di awal level
    respawn_wx = player.wx
    respawn_wy = player.wy
    current_checkpoint = None

    level_clear = False
    start_level_intro(level)

def start_new_game_with_name(fname, difficulty="normal"):
    global current_save_file
    base=fname.rsplit(".json",1)[0] if fname.endswith(".json") else fname
    if not fname.endswith(".json"): fname+=".json"
    i=2
    while os.path.exists(os.path.join(SAVE_DIR,fname)):
        fname=f"{base}_{i}.json"
        i+=1
    current_save_file=fname
    save_last_played_save(fname)
    sd=_save_defaults(); sd["has_save"]=True; sd["timestamp"]=datetime.now().isoformat()
    sd["save_name"]=fname.rsplit(".",1)[0]
    sd["world_seed"]=random.SystemRandom().randint(0,2**63-1)
    sd.setdefault("settings",{})["difficulty"]=difficulty
    write_save(fname,sd); save_data.update(sd)
    start_new_game(sd["world_seed"])

def _load_game_state(sd):
    global player,camera,p_bullets,e_bullets,pixels,chests,coins,score,money,lives
    global level,checkpoint,multiplier,mult_timer,mult_decay_tick,platforms,enemies
    global level_clear,boss,boss_spawned,boss_x_world,waiting_for_dialogue,active_boss_data
    global moving_plats,spike_traps,tunnels,fly_zones,facility_sections,water_zones,session_kills,session_stats,respawn_wx,respawn_wy,powerups,active_powerups,combo_count,combo_timer,current_checkpoint
    global mission_state,save_data
    save_data.update(sd)

    player=Player(); camera=Camera()
    p_bullets=[]; e_bullets=[]; pixels=[]; chests=[]; coins=[]

    score=sd.get("high_score",0)//3
    money=sd.get("money",0)
    lives=sd.get("lives",5)

    print(f"[LOAD] loaded lives={lives} level={sd.get('last_level',1)} checkpoint={sd.get('last_checkpoint',1)} hp={sd.get('hp',None)}")

    shop.reset()
    set_shop_upgrade_levels(sd.get("shop_upgrades",{}))

    level=sd.get("last_level",1)
    checkpoint=sd.get("last_checkpoint",1)

    multiplier=1
    mult_timer=0
    mult_decay_tick=0
    level_clear=False
    boss=None
    boss_spawned=False
    waiting_for_dialogue=False
    session_kills=sd.get("total_kills",0)
    powerups=[]
    active_powerups={}
    combo_count=0
    combo_timer=0

    platforms,enemies,boss_x_world,chests,moving_plats,spike_traps,tunnels,fly_zones,facility_sections,water_zones,coins,active_boss_data=generate_world(level)
    build_checkpoints()
    start_level_mission(level)
    reset_level_stats()
    reset_environment_event()

    player.reset()
    apply_permanent_unlocks(player)
    apply_shop_upgrades(player)
    sync_adventure_progress_from_save(player)
    reconcile_current_mission_progress()

    respawn_wx,respawn_wy=normalize_respawn_spot(sd.get("respawn_x",120.0),sd.get("respawn_y",480.0))
    filter_generated_rewards_before_checkpoint(respawn_wx)
    player.wx=respawn_wx
    player.wy=respawn_wy
    current_checkpoint=None
    for cp in checkpoints:
        if abs(cp.wx-respawn_wx)<1:
            cp.active=True
            current_checkpoint=cp
            break

    print(f"[LOAD] level={level} checkpoint={checkpoint} respawn=({respawn_wx}, {respawn_wy}) player=({player.wx}, {player.wy})")

    player.MAX_HP=max(3,sd.get("max_hp",player.MAX_HP))
    player.hp=min(sd.get("hp",player.MAX_HP),player.MAX_HP)

    cw=sd.get("current_weapon","laser")
    if isinstance(cw,str) and cw in player.weapons:
        player.weapon_idx=player.weapons.index(cw)
    elif isinstance(cw,int) and cw>=0 and cw<len(WEAPONS):
        wk=list(WEAPONS.keys())[cw]
        if wk in player.weapons:
            player.weapon_idx=player.weapons.index(wk)

    if hasattr(player,"weapon_levels"):
        wl=sd.get("weapon_levels",{})
        if isinstance(wl,dict):
            player.weapon_levels=wl

    saved_mission=sd.get("mission_progress",{})
    expected=LEVEL_MISSIONS.get(level,{})
    if isinstance(saved_mission,dict) and saved_mission.get("kind")==expected.get("kind"):
        mission_state.clear(); mission_state.update(saved_mission)
    save_data.update(sd)
    reconcile_current_mission_progress()

def continue_game():
    global session_stats,current_save_file,play_time_accum
    debug_print("[Continue] Continue button clicked")
    session_stats={}; fname=get_last_played_save()
    if not fname:
        fname=get_newest_save()
        debug_print(f"[Continue] No last_played save, falling back to newest: {fname}")
    if not fname:
        debug_print("[Continue] FAILED: No save files found at all")
        toast("Tidak ada data save","\u26A0",ORANGE,120)
        return
    debug_print(f"[Continue] Loading save: {fname}")
    current_save_file=fname; play_time_accum=0
    save_last_played_save(fname)
    record_play_started()
    sd=load_save(fname)
    if not sd.get("has_save"):
        debug_print(f"[Continue] FAILED: Save {fname} has has_save=False")
        toast("Save tidak valid","\u26A0",ORANGE,120)
        return
    debug_print(f"[Continue] Save loaded: level={sd.get('last_level')}, respawn=({sd.get('respawn_x')},{sd.get('respawn_y')})")
    _load_game_state(sd)
    debug_print(f"[Continue] Game state restored, scene=level_intro, level={level}")
    start_level_intro(level)

def restart_level():
    global p_bullets,e_bullets,pixels,chests,coins,platforms,enemies
    global multiplier,mult_timer,mult_decay_tick,boss,boss_spawned,boss_x_world,camera,waiting_for_dialogue,active_boss_data
    global moving_plats,spike_traps,tunnels,fly_zones,facility_sections,water_zones,session_kills,respawn_wx,respawn_wy,powerups,active_powerups,combo_count,combo_timer,current_checkpoint
    p_bullets=[]; e_bullets=[]; pixels=[]; chests=[]; coins=[]; powerups=[]; active_powerups={}; combo_count=0; combo_timer=0
    platforms,enemies,boss_x_world,chests,moving_plats,spike_traps,tunnels,fly_zones,facility_sections,water_zones,coins,active_boss_data=generate_world(level,save_data.get("world_seed"))
    build_checkpoints()
    start_level_mission(level)
    reset_level_stats()
    reset_environment_event()
    boss=None; boss_spawned=False; waiting_for_dialogue=False; session_kills=0
    camera=Camera()
    player.reset()
    apply_permanent_unlocks(player)
    apply_shop_upgrades(player)
    respawn_wx,respawn_wy=player.wx,player.wy
    current_checkpoint=None
    multiplier=1
    mult_timer=0
    mult_decay_tick=0
    transition_to("playing")

def respawn():
    global p_bullets,e_bullets,pixels,camera,multiplier,mult_timer,mult_decay_tick,waiting_for_dialogue
    p_bullets=[]; e_bullets=[]; pixels=[]
    player.wx=max(0,min(WORLD_W-player.WIDTH,respawn_wx)); player.wy=max(18,min(SCREEN_H-player.HEIGHT-4,respawn_wy))
    player.vx=0; player.vy=0; player.hp=player.MAX_HP; player.frozen=0
    player.invincible=180; player.fly_mode=any(fz.contains_for_mode(player.wx+player.WIDTH//2,False) for fz in fly_zones); player.fly_thrust=False; player.gliding=False; player.jump_held=False; player.glide_held=False; player.glide_lockout=0; player.fly_buffer=18 if player.fly_mode else 0
    multiplier=1; mult_timer=0; mult_decay_tick=0; waiting_for_dialogue=False; camera=Camera(); camera.update(player.wx); print(f"[RESPAWN] respawn() called"); transition_to("playing")
    if boss_dialogue.active: boss_dialogue.skip_all()
    if boss_intro.active: boss_intro.skip()

def update_respawn_spot():
    # Checkpoint sekarang diatur oleh objek checkpoint,
    # bukan lagi mengikuti posisi player setiap frame.
    return

def player_died():
    global lives,combo_count,combo_timer
    lives-=1
    add_session_stat("total_deaths",1)
    combo_count=0; combo_timer=0
    sounds.play("player_death")
    spawn_pixels(player.wx+player.WIDTH//2,player.wy+player.HEIGHT//2,RED,30)
    spawn_pixels(player.wx+player.WIDTH//2,player.wy+player.HEIGHT//2,ORANGE,20)
    spawn_pixels(player.wx+player.WIDTH//2,player.wy+player.HEIGHT//2,(200,220,255),15)
    print(f"[DEATH] player_died() called, lives now={lives}")
    transition_to("dead")

def do_save():
    global current_save_file,play_time_accum
    play_time_accum=0
    flush_session_stats()
    save_progress_state()
    btn_continue.disabled=False
    toast(tr("pause.saved"),"\u2714",GREEN,80)
    sounds.play("ui_click")

def do_load(slot=None):
    global current_save_file,play_time_accum,session_kills,boss,boss_spawned,waiting_for_dialogue,level_clear
    if slot is None: return
    if not slot or not has_save_data(slot): return
    current_save_file=slot; play_time_accum=0
    save_last_played_save(slot)
    sd=load_save(slot)
    _load_game_state(sd)
    session_kills=sd.get("total_kills",0)
    boss=None; boss_spawned=False; waiting_for_dialogue=False; level_clear=False
    transition_to("playing")

def finish_game():
    global level_clear, session_kills, current_save_file, play_time_accum
    if not current_save_file: return
    sd=load_save(current_save_file); sd["has_save"]=True
    sd["timestamp"]=datetime.now().isoformat()
    if play_time_accum>0: sd["play_time"]=sd.get("play_time",0)+play_time_accum
    if score>sd["high_score"]: sd["high_score"]=score
    if level>sd["best_level"]: sd["best_level"]=level
    sd["last_level"]=len(LEVEL_ORDER); sd["last_checkpoint"]=len(LEVEL_ORDER)
    sd["money"]=money; sd["shop_upgrades"]=get_shop_upgrade_levels(); sd["total_kills"]+=session_kills
    if write_save(current_save_file,sd):
        save_data.update(sd); session_kills=0
    level_clear=False; transition_to("ending"); sounds.stop_bgm()

# ------------------------------------------------------------------------------------
# HUD DESIGN CONSTANTS
# ------------------------------------------------------------------------------------
HUD_TOP_Y = 8
HUD_TOP_H = 72
HUD_RIGHT_H = HUD_TOP_H
WEAPON_PANEL_H = 100
WEAPON_PANEL_Y = HUD_TOP_Y + HUD_TOP_H + 8
HUD_MARGIN = 10
HUD_GAP = 4

HUD_LEFT_W = 170
HUD_CENTER_X = HUD_MARGIN + HUD_LEFT_W + HUD_GAP
HUD_CENTER_W = 312
HUD_RIGHT_X = HUD_CENTER_X + HUD_CENTER_W + HUD_GAP
HUD_RIGHT_W = SCREEN_W - HUD_MARGIN - HUD_RIGHT_X

MISSION_Y = HUD_TOP_Y + HUD_TOP_H + 8
MISSION_H = 56
MISSION_W = HUD_LEFT_W

BOTTOM_BAR_Y = SCREEN_H - HUD_MARGIN - 22
BOTTOM_BAR_H = 22
BOTTOM_BAR_W = SCREEN_W - HUD_MARGIN * 2

BOSS_BAR_W = 500
BOSS_BAR_H = 44
BOSS_BAR_Y = BOTTOM_BAR_Y - 8 - BOSS_BAR_H

PROGRESS_BAR_W = 320
PROGRESS_BAR_H = 7
PROGRESS_BAR_X = (SCREEN_W - PROGRESS_BAR_W) // 2
PROGRESS_BAR_Y = BOTTOM_BAR_Y - 4 - PROGRESS_BAR_H

# ------------------------------------------------------------------------------------
# HUD DRAWING FUNCTIONS
# ------------------------------------------------------------------------------------
def draw_panel(surface,rect,border_col=PANEL_BORDER,fill_col=(7,10,26,200),radius=6,glow_intensity=0.6):
    glow_a=int(20*glow_intensity)
    glow=get_cached_surface(f"panel_glow_{rect.w}_{rect.h}_{radius}",rect.w+12,rect.h+12)
    glow.fill((0,0,0,0))
    pygame.draw.rect(glow,(*border_col,glow_a),(4,4,rect.w+4,rect.h+4),border_radius=radius+4)
    surface.blit(glow,(rect.x-6,rect.y-6))
    panel=get_cached_surface(f"panel_body_{rect.w}_{rect.h}_{radius}_{fill_col}",rect.w,rect.h)
    panel.fill((0,0,0,0))
    pygame.draw.rect(panel,fill_col,(0,0,rect.w,rect.h),border_radius=radius)
    surface.blit(panel,rect.topleft)
    pygame.draw.rect(surface,(*border_col,100),rect,border_radius=radius,width=1)

def draw_fit_text(surface,text,font,rect,color=TEXT_MAIN,shadow=True,center_y=False):
    img=render_fit(font,str(text),color,max(1,rect.w))
    x=rect.x
    y=rect.y+(rect.h-img.get_height())//2 if center_y else rect.y
    if shadow:
        sh=render_fit(font,str(text),(0,0,0),max(1,rect.w))
        surface.blit(sh,(x+1,y+1))
    surface.blit(img,(x,y))
    return img.get_rect(topleft=(x,y))

def draw_center_fit(surface,text,font,rect,color=TEXT_MAIN,shadow=True):
    img=render_fit(font,str(text),color,max(1,rect.w))
    x=rect.centerx-img.get_width()//2; y=rect.centery-img.get_height()//2
    if shadow:
        sh=render_fit(font,str(text),(0,0,0),max(1,rect.w)); surface.blit(sh,(x+1,y+1))
    surface.blit(img,(x,y))
    return img.get_rect(topleft=(x,y))

def draw_top_hud(surface,player,score,money,multiplier,level,enemies,boss_spawned,t,font_xs,font_sm,font_md,mx,my):
    global SHOP_HUD_RECT
    x0=HUD_MARGIN; y0=HUD_TOP_Y
    draw_panel(surface,pygame.Rect(x0,y0,HUD_LEFT_W,HUD_TOP_H),NEON_CYAN,(5,8,24,200),radius=6)
    draw_panel(surface,pygame.Rect(HUD_CENTER_X,y0,HUD_CENTER_W,HUD_TOP_H),NEON_CYAN,(5,8,24,200),radius=6)
    draw_panel(surface,pygame.Rect(HUD_RIGHT_X,y0,HUD_RIGHT_W,HUD_RIGHT_H),NEON_CYAN,(5,8,24,200),radius=6)
    px=x0+10; py=y0+8; pw=HUD_LEFT_W-20
    hp_col=NEON_RED if player.hp<=2 else NEON_CYAN
    hc=min(player.MAX_HP,8); hg=18
    hs=px+(pw-(hc*hg))//2
    for i in range(hc):
        cx=hs+i*hg
        if i<max(0,player.hp):
            gl=pygame.Surface((14,14),pygame.SRCALPHA)
            pygame.draw.circle(gl,(*hp_col,50),(7,7),7)
            surface.blit(gl,(cx-7,py+2))
            pygame.draw.rect(surface,hp_col,(cx-3,py+5,6,8),border_radius=2)
            pygame.draw.rect(surface,(255,255,255,160),(cx-1,py+7,2,3),border_radius=1)
        else:
            pygame.draw.rect(surface,(*TEXT_DIM,70),(cx-2,py+6,4,6),border_radius=1,width=1)
    by=py+24; bh=4
    pygame.draw.rect(surface,(12,18,36,180),(px,by,pw,bh),border_radius=2)
    fw=int(pw*max(0,min(player.hp,player.MAX_HP))/max(1,player.MAX_HP))
    if fw>0:
        fr=pygame.Rect(px,by,fw,bh)
        pygame.draw.rect(surface,hp_col,fr,border_radius=2)
        gs=pygame.Surface((fw+6,bh+6),pygame.SRCALPHA)
        pygame.draw.rect(gs,(*hp_col,30),(3,3,fw,bh),border_radius=3)
        surface.blit(gs,(px-3,by-3))
    pygame.draw.rect(surface,(*hp_col,100),(px,by,pw,bh),border_radius=2,width=1)
    hp_t=font_xs.render(f"{player.hp}/{player.MAX_HP}",True,TEXT_MAIN)
    surface.blit(hp_t,(px,by+bh+3))
    cx0=HUD_CENTER_X+8; cw=HUD_CENTER_W-16
    is_best=score>save_data.get("high_score",0) and score>0
    sc=NEON_YELLOW if is_best and score>0 else NEON_CYAN

    trophy_surf=pygame.Surface((14,14),pygame.SRCALPHA)
    pygame.draw.polygon(trophy_surf,GOLD,[(2,4),(12,4),(11,10),(3,10)])
    pygame.draw.rect(trophy_surf,GOLD,(5,10,4,2))
    pygame.draw.rect(trophy_surf,GOLD,(2,12,10,2))
    pygame.draw.ellipse(trophy_surf,GOLD,(-1,4,4,5),1)
    pygame.draw.ellipse(trophy_surf,GOLD,(11,4,4,5),1)

    stitle=font_xs.render("SCORE",True,TEXT_MUTED)
    title_w=14+4+stitle.get_width()
    tx=cx0+(cw-title_w)//2
    surface.blit(trophy_surf,(tx,py-1))
    surface.blit(stitle,(tx+18,py))

    si=font_md.render(f"{score:06d}",True,sc)
    six=cx0+(cw-si.get_width())//2
    siy=py+16
    surface.blit(si,(six,siy))

    if is_best and score>0:
        p=int(200+55*math.sin(t*0.015))
        nr=font_xs.render(tr("hud.new_record"),True,(p,240,80))
        nrx=six+si.get_width()+6
        if nrx+nr.get_width()<=cx0+cw:
            surface.blit(nr,(nrx,siy+5))
        else:
            surface.blit(nr,(cx0+(cw-nr.get_width())//2,siy+si.get_height()+2))
    elif multiplier>1:
        pl=int(200+55*math.sin(t*0.01))
        cm=font_xs.render(f"x{multiplier} COMBO",True,(255,pl,55))
        cmx=six+si.get_width()+6
        if cmx+cm.get_width()<=cx0+cw:
            surface.blit(cm,(cmx,siy+5))
        else:
            surface.blit(cm,(cx0+(cw-cm.get_width())//2,siy+si.get_height()+2))

    ry=py+44
    bl=font_xs.render("BEST",True,TEXT_MUTED)
    bv=font_sm.render(f"{save_data.get('high_score',0):06d}",True,NEON_CYAN)
    surface.blit(bl,(cx0,ry))
    surface.blit(bv,(cx0+bl.get_width()+4,ry+1))

    coin_val=font_sm.render(str(money),True,GOLD)
    coin_surf=pygame.Surface((12,12),pygame.SRCALPHA)
    pygame.draw.circle(coin_surf,GOLD,(6,6),6)
    pygame.draw.circle(coin_surf,(255,210,60),(6,6),4)
    pygame.draw.circle(coin_surf,GOLD,(6,6),1)
    coin_total=12+4+coin_val.get_width()
    coin_x=cx0+cw-coin_total
    surface.blit(coin_surf,(coin_x,ry+1))
    surface.blit(coin_val,(coin_x+16,ry+1))
    rx0=HUD_RIGHT_X+8; rw=HUD_RIGHT_W-16
    ld=get_level_data(level); lc=NEON_YELLOW if ld.get("bonus") else NEON_PURPLE
    ls=render_fit(font_sm,f"LV{level} {ld['name']}",lc,rw-80)
    surface.blit(ls,(rx0,py-2))
    btn_rect=pygame.Rect(HUD_RIGHT_X+HUD_RIGHT_W-74,py-2,66,16)
    btn_hover=btn_rect.collidepoint(mx,my)
    btn_bg=pygame.Surface((btn_rect.w,btn_rect.h),pygame.SRCALPHA)
    pygame.draw.rect(btn_bg,(40,30,10,180) if btn_hover else (20,16,6,140),(0,0,btn_rect.w,btn_rect.h),border_radius=3)
    surface.blit(btn_bg,btn_rect.topleft)
    pygame.draw.rect(surface,GOLD,btn_rect,border_radius=3,width=2 if btn_hover else 1)
    btn_txt=render_fit(font_xs,"SHOP",NEON_YELLOW,btn_rect.w-6)
    surface.blit(btn_txt,(btn_rect.centerx-btn_txt.get_width()//2,btn_rect.centery-btn_txt.get_height()//2))
    SHOP_HUD_RECT=btn_rect
    ry3=py+22
    si_list=[(f"ENEMIES: {len(enemies)}",NEON_RED if boss_spawned else NEON_ORANGE),(f"POS: {int(player.wx)}",NEON_CYAN)]
    sx2=rx0; sy2=ry3
    for txt2,col2 in si_list:
        im=font_xs.render(txt2,True,col2)
        surface.blit(im,(sx2,sy2))
        sx2+=im.get_width()+12
    ms=tr("hud.mode.fly") if player.fly_mode else(tr("hud.mode.glide") if player.gliding else tr("hud.mode.run"))
    mc=NEON_CYAN if player.fly_mode else(NEON_GREEN if player.gliding else TEXT_MAIN)
    md=font_xs.render(f"MODE: {ms}",True,mc)
    surface.blit(md,(sx2,sy2))

def draw_mission_hud(surface,font_xs,font_sm):
    y=MISSION_Y
    if not mission_state: return
    mc=NEON_GREEN if mission_state.get("complete") else NEON_CYAN
    r=pygame.Rect(HUD_MARGIN,y,MISSION_W,MISSION_H)
    draw_panel(surface,r,mc,(5,8,24,190),radius=6)
    title=mission_state.get("title","Mission")
    draw_fit_text(surface,"MISSION",font_xs,pygame.Rect(r.x+8,r.y+4,r.w-16,10),TEXT_MUTED,shadow=False)
    draw_fit_text(surface,title,font_sm,pygame.Rect(r.x+8,r.y+14,r.w-16,14),mc,shadow=False)
    pg=mission_state.get('progress',0); tg=mission_state.get('target',1)
    status="Mission Complete" if mission_state.get("complete") else f"Progress  {pg} / {tg}"
    pf=font_xs.render(status,True,NEON_GREEN if mission_state.get("complete") else TEXT_MAIN)
    surface.blit(pf,(r.x+8,r.y+29))
    by2=r.y+43; bw2=r.w-16; bh2=4
    pygame.draw.rect(surface,(12,18,36,180),(r.x+8,by2,bw2,bh2),border_radius=2)
    fw2=int(bw2*min(1.0,pg/max(1,tg)))
    if fw2>0:
        fr2=pygame.Rect(r.x+8,by2,fw2,bh2)
        pygame.draw.rect(surface,mc,fr2,border_radius=2)
        gs2=pygame.Surface((fw2+6,bh2+6),pygame.SRCALPHA)
        pygame.draw.rect(gs2,(*mc,30),(3,3,fw2,bh2),border_radius=3)
        surface.blit(gs2,(r.x+5,by2-3))
    pygame.draw.rect(surface,(*mc,100),(r.x+8,by2,bw2,bh2),border_radius=2,width=1)

def draw_weapon_panel(surface,player,font_xs,font_sm):
    wx0=HUD_RIGHT_X; wy0=WEAPON_PANEL_Y; ww=HUD_RIGHT_W; wh=WEAPON_PANEL_H
    draw_panel(surface,pygame.Rect(wx0,wy0,ww,wh),NEON_CYAN,(5,8,24,190),radius=6)
    wk=player.current_weapon; wd=WEAPONS[wk]; av=player.ammo[wk]
    as_="inf" if av<0 else str(av); wc=player.get_weapon_color(wk)
    ec=SUCCESS_TEXT if player.weapon_equipped else TEXT_DIM
    et=tr("weapon.hud.on") if player.weapon_equipped else tr("weapon.hud.off")
    px=wx0+14; py=wy0+8; cw=ww-28
    draw_fit_text(surface,wd["name"],font_sm,pygame.Rect(px,py,cw,18),wc,shadow=False)
    amc=TEXT_MAIN if av!=0 else DANGER_TEXT
    hw=cw//2-6
    draw_fit_text(surface,f"Ammo : {as_}",font_xs,pygame.Rect(px,py+28,hw,12),amc,shadow=False)
    draw_fit_text(surface,f"Status : {et}",font_xs,pygame.Rect(px+hw+12,py+28,hw,12),ec,shadow=False)
    sw=int((ww-36)//max(1,len(player.weapons[:4])))
    sy2=wy0+wh-28
    total_slots_w=len(player.weapons[:4])*sw
    sx4=wx0+(ww-total_slots_w)//2
    for wi2,wk2 in enumerate(player.weapons[:4]):
        act=wi2==player.weapon_idx; col2=player.get_weapon_color(wk2)
        sr2=pygame.Rect(sx4+wi2*sw,sy2,sw-4,16)
        sb2=pygame.Surface((sr2.w,sr2.h),pygame.SRCALPHA)
        pygame.draw.rect(sb2,(8,11,26,200),(0,0,sr2.w,sr2.h),border_radius=4)
        surface.blit(sb2,sr2.topleft)
        pygame.draw.rect(surface,col2 if act else TEXT_DIM,sr2,border_radius=4,width=2 if act else 1)
        draw_center_fit(surface,str(wi2+1),font_xs,sr2,col2 if act else TEXT_MUTED,shadow=False)

def draw_bottom_bar(surface,font_xs):
    global SOUND_HUD_RECT
    bar=pygame.Rect(HUD_MARGIN,BOTTOM_BAR_Y,BOTTOM_BAR_W,BOTTOM_BAR_H)
    draw_panel(surface,bar,NEON_CYAN,(3,6,18,180),radius=5,glow_intensity=0.4)
    controls=[("B","Shop"),("E","Weapon"),("F5","Save"),("F11","FS"),("M","Mute"),("ESC","Pause")]
    x=bar.x+8
    for key,label in controls:
        ki=font_xs.render(f"[{key}]",True,NEON_CYAN)
        li=font_xs.render(label,True,TEXT_MUTED)
        surface.blit(ki,(x,bar.y+5)); x+=ki.get_width()+2
        surface.blit(li,(x,bar.y+5)); x+=li.get_width()+12
    SOUND_HUD_RECT=pygame.Rect(bar.right-90,bar.y+3,82,16)
    sc2=DANGER_TEXT if sounds.muted else NEON_GREEN
    st2="MUTED" if sounds.muted else f"{int(sounds.vol_sfx*100)}%"
    sd_bg=pygame.Surface((SOUND_HUD_RECT.w,SOUND_HUD_RECT.h),pygame.SRCALPHA)
    pygame.draw.rect(sd_bg,(8,11,26,180),(0,0,SOUND_HUD_RECT.w,SOUND_HUD_RECT.h),border_radius=4)
    surface.blit(sd_bg,SOUND_HUD_RECT.topleft)
    pygame.draw.rect(surface,sc2,SOUND_HUD_RECT,border_radius=4,width=1)
    draw_center_fit(surface,st2,font_xs,SOUND_HUD_RECT,sc2,shadow=False)

def draw_progress_bar(surface,player_wx,boss_wx,font_xs,font_sm,t,player=None,boss_data=None):
    py2=PROGRESS_BAR_Y; bx=PROGRESS_BAR_X; bw=PROGRESS_BAR_W
    pr=min(1.0,max(0.0,player_wx/max(1,boss_wx)))
    skin_data=SKINS.get(player.skin,SKINS["classic"]) if player else SKINS["classic"]
    fc=NEON_CYAN

    # Bar background (SRCALPHA for proper alpha)
    bar_bg=pygame.Surface((bw+4,PROGRESS_BAR_H+4),pygame.SRCALPHA)
    pygame.draw.rect(bar_bg,(12,15,30,200),(0,0,bw+4,PROGRESS_BAR_H+4),border_radius=4)
    pygame.draw.rect(bar_bg,(30,42,80,100),(1,1,bw+2,PROGRESS_BAR_H+2),border_radius=4)
    pygame.draw.rect(bar_bg,(6,8,18,220),(2,2,bw,PROGRESS_BAR_H),border_radius=3)
    surface.blit(bar_bg,(bx-2,py2-2))

    # Energy fill
    fw=int(bw*pr)
    if fw>0:
        pygame.draw.rect(surface,fc,(bx,py2,fw,PROGRESS_BAR_H),border_radius=3)
        fl=pygame.Surface((fw+6,8),pygame.SRCALPHA)
        fl_a=int(50+30*math.sin(t*0.005))
        pygame.draw.rect(fl,(*fc,fl_a),(3,2,fw,2),border_radius=2)
        surface.blit(fl,(bx-3,py2-1))

    # Border highlight (SRCALPHA)
    border_surf=pygame.Surface((bw,PROGRESS_BAR_H),pygame.SRCALPHA)
    pygame.draw.rect(border_surf,(*fc,80),(0,0,bw,PROGRESS_BAR_H),border_radius=3,width=1)
    surface.blit(border_surf,(bx,py2))

    # Corner brackets (SRCALPHA)
    br=4
    for cx,cy in [(bx-3,py2-3),(bx+bw+3-br,py2-3),(bx-3,py2+PROGRESS_BAR_H+3-br),(bx+bw+3-br,py2+PROGRESS_BAR_H+3-br)]:
        b_s=pygame.Surface((br,br),pygame.SRCALPHA)
        pygame.draw.rect(b_s,(*fc,100),(0,0,br,br),1)
        surface.blit(b_s,(cx,cy))

    # Checkpoints
    for cf in (0.25,0.50,0.75):
        cx=int(bx+bw*cf); cy=py2+PROGRESS_BAR_H//2
        reached=player_wx>=boss_wx*cf
        ccol=NEON_CYAN if reached else (40,45,75)
        hs=4; d=[(cx,cy-hs),(cx+hs,cy),(cx,cy+hs),(cx-hs,cy)]
        if reached:
            pygame.draw.polygon(surface,ccol,d)
            ga=int(30+25*math.sin(t*0.008))
            gs=pygame.Surface((14,14),pygame.SRCALPHA)
            pygame.draw.circle(gs,(*ccol,ga),(7,7),6)
            surface.blit(gs,(cx-7,cy-7))
        else:
            pygame.draw.polygon(surface,ccol,d,1)

    def render_g7(sz,fs=0.004):
        scl=sz/36.0; th=max(1,int(46*scl))
        tmp=pygame.Surface((36,46),pygame.SRCALPHA)
        draw_g7(tmp,2,2,skin_data=skin_data)
        return pygame.transform.scale(tmp,(sz,th)),int(1.5*math.sin(t*fs))

    # G7 at START
    g7s,g7f=render_g7(20,0.004)
    g7x=bx-g7s.get_width()//2; g7y=py2-g7s.get_height()-6+g7f
    gr=max(g7s.get_width(),g7s.get_height())//2+4
    g7gl=pygame.Surface((gr*2,gr*2),pygame.SRCALPHA)
    pygame.draw.circle(g7gl,(*NEON_CYAN,30),(gr,gr),gr)
    surface.blit(g7gl,(g7x+g7s.get_width()//2-gr,g7y+g7s.get_height()//2-gr))
    surface.blit(g7s,(g7x,g7y))
    st=font_xs.render("START",True,NEON_CYAN)
    surface.blit(font_xs.render("START",True,(2,3,12)),(bx-st.get_width()//2+1,g7y+g7s.get_height()+4+1))
    surface.blit(st,(bx-st.get_width()//2,g7y+g7s.get_height()+4))

    # Boss icon
    if boss_data:
        bsz=boss_data["size"]; tw=bsz[0]+50; th=bsz[1]+50
        btmp=pygame.Surface((tw,th),pygame.SRCALPHA)
        draw_boss_sprite(btmp,25,25,boss_data,t*0.1,1)
        bth=22; bsc=bth/max(th,1); bsw=max(1,int(tw*bsc)); bsh=max(1,int(th*bsc))
        bscaled=pygame.transform.scale(btmp,(bsw,bsh))
        bfl=int(1.5*math.sin(t*0.006+1))
        bsx=bx+bw-bsw//2; bsy=py2-bsh-6+bfl
        bgr=max(bsw,bsh)//2+5
        bgl=pygame.Surface((bgr*2,bgr*2),pygame.SRCALPHA)
        gp=int(30+20*math.sin(t*0.008))
        pygame.draw.circle(bgl,(*NEON_RED,gp),(bgr,bgr),bgr)
        surface.blit(bgl,(bsx+bsw//2-bgr,bsy+bsh//2-bgr))
        surface.blit(bscaled,(bsx,bsy))
        bl=font_xs.render("BOSS",True,NEON_RED)
        surface.blit(font_xs.render("BOSS",True,(2,3,12)),(bx+bw-bl.get_width()//2+1,bsy+bsh+4+1))
        surface.blit(bl,(bx+bw-bl.get_width()//2,bsy+bsh+4))
    else:
        bl=font_xs.render("BOSS",True,NEON_RED)
        surface.blit(font_xs.render("BOSS",True,(2,3,12)),(bx+bw-bl.get_width()//2+1,py2-22+1))
        surface.blit(bl,(bx+bw-bl.get_width()//2,py2-22))

    # Mini G7 progress indicator
    ms,mf=render_g7(14,0.005)
    mx=bx+int(bw*pr)-ms.get_width()//2; my=py2-ms.get_height()-2+mf
    mgr=max(ms.get_width(),ms.get_height())//2+3
    mgl=pygame.Surface((mgr*2,mgr*2),pygame.SRCALPHA)
    pygame.draw.circle(mgl,(*NEON_CYAN,45),(mgr,mgr),mgr)
    surface.blit(mgl,(mx+ms.get_width()//2-mgr,my+ms.get_height()//2-mgr))
    surface.blit(ms,(mx,my))

def draw_minimap(surface,player_wx,boss_wx,enemies,coins_list,chests_list,boss,font_xs,t):
    m_size=120; m_x=SCREEN_W-HUD_MARGIN-m_size; m_y=HUD_TOP_Y+HUD_TOP_H+8; padding=6
    world_w=WORLD_W
    bg=pygame.Surface((m_size,m_size),pygame.SRCALPHA)
    pygame.draw.rect(bg,(3,6,18,200),(0,0,m_size,m_size),border_radius=4)
    surface.blit(bg,(m_x,m_y))
    pygame.draw.rect(surface,(CYAN[0],CYAN[1],CYAN[2],80),(m_x,m_y,m_size,m_size),border_radius=4,width=1)
    inner=m_size-padding*2
    def wx_to_mx(wx):
        return m_x+padding+int(inner*wx/max(1,world_w))
    def wy_to_my(wy):
        return m_y+padding+int(inner*wy/SCREEN_H)
    plat_col=(40,50,80,120)
    for plat in platforms:
        mx2=wx_to_mx(plat.x); my2=wy_to_my(plat.y)
        pw=max(2,int(inner*plat.w/max(1,world_w))); ph=max(1,int(inner*plat.h/SCREEN_H))
        pygame.draw.rect(surface,plat_col,(mx2,my2,pw,ph))
    chk_col=(60,200,160,150)
    for cf in (0.25,0.50,0.75):
        cx=wx_to_mx(boss_wx*cf)
        reached=player_wx>=boss_wx*cf
        ccol=NEON_CYAN if reached else (40,45,75)
        pygame.draw.circle(surface,ccol,(cx,m_y+m_size//2),2)
    for c in coins_list:
        if c.alive:
            cx=wx_to_mx(c.wx); cy=wy_to_my(c.wy)
            col=(200,180,60,180) if c.type=="gold" else (150,80,255,180)
            pygame.draw.circle(surface,col,(cx,cy),1)
    for ch in chests_list:
        if ch.alive:
            cx=wx_to_mx(ch.wx); cy=wy_to_my(ch.wy)
            col=(0,200,0,200) if ch.type=="common" else (200,100,255,200) if ch.type=="rare" else (255,200,0,200) if ch.type=="boss" else (255,100,0,200)
            pygame.draw.rect(surface,col,(cx-1,cy-1,3,3))
    for en in enemies:
        if en.alive:
            cx=wx_to_mx(en.wx); cy=wy_to_my(en.wy)
            col=(255,80,80,200) if getattr(en,"elite_type",None) else (255,150,50,150)
            pygame.draw.circle(surface,col,(cx,cy),2)
    if boss and boss.alive:
        bx=wx_to_mx(boss.wx); by=wy_to_my(boss.wy)
        bs=max(3,int(inner*boss.bw/max(1,world_w)))
        pygame.draw.rect(surface,NEON_RED,(bx-bs//2,by-bs//2,bs,bs))
    px=wx_to_mx(player_wx); py=wy_to_my(SCREEN_H//2)
    pl_glow=pygame.Surface((10,10),pygame.SRCALPHA)
    pygame.draw.circle(pl_glow,(*NEON_CYAN,60),(5,5),5)
    surface.blit(pl_glow,(px-5,py-5))
    pygame.draw.circle(surface,NEON_CYAN,(px,py),3)
    pygame.draw.circle(surface,(255,255,255),(px,py),1)
    prog_x=m_x+m_size+4; prog_y=m_y
    title=font_xs.render(tr("minimap.title"),True,NEON_CYAN)
    surface.blit(title,(prog_x,prog_y))
    legend_y=prog_y+14
    legend_items=[(tr("minimap.player"),NEON_CYAN),(tr("minimap.boss"),NEON_RED),(tr("minimap.enemy"),(255,150,50)),(tr("minimap.coin"),GOLD),(tr("minimap.chest"),GREEN)]
    for lname,lcol in legend_items:
        pygame.draw.circle(surface,lcol,(prog_x+4,legend_y+4),2)
        lt=font_xs.render(lname,True,TEXT_MUTED)
        surface.blit(lt,(prog_x+10,legend_y))
        legend_y+=12

def draw_hud(surface,player,lives,score,money,level,enemies,boss_spawned,checkpoint,multiplier,boss,mx,my,t,font_xs,font_sm,font_md):
    veil_h=HUD_TOP_Y+HUD_TOP_H+4
    veil=pygame.Surface((SCREEN_W,veil_h),pygame.SRCALPHA)
    for vy in range(veil_h):
        a=int(50*(1-vy/veil_h)**2)
        pygame.draw.line(veil,(3,5,16,a),(0,vy),(SCREEN_W,vy))
    surface.blit(veil,(0,0))
    draw_top_hud(surface,player,score,money,multiplier,level,enemies,boss_spawned,t,font_xs,font_sm,font_md,mx,my)
    if boss and boss.alive:
        if getattr(boss,"laser_active",False) or getattr(boss,"stomp_active",False) or getattr(boss,"lightning_bolts",[]):
            flash=get_cached_surface("boss_dmg_flash",SCREEN_W,SCREEN_H)
            flash.fill((255,35,55,int(16+12*math.sin(t*0.035))))
            surface.blit(flash,(0,0))
        bw2=max(300,min(420,SCREEN_W-260)); bh2=34; bx=SCREEN_W//2-bw2//2; by=HUD_TOP_Y+HUD_TOP_H+8
        cam_obj=globals().get("camera")
        if cam_obj:
            psx,psy=cam_obj.apply(player.wx,player.wy)
            player_screen=pygame.Rect(int(psx),int(psy),player.WIDTH,player.HEIGHT).inflate(16,14)
            boss_panel_try=pygame.Rect(bx,by,bw2,bh2)
            if player_screen.colliderect(boss_panel_try):
                bx=16 if player_screen.centerx>SCREEN_W//2 else SCREEN_W-bw2-16
                boss_panel_try=pygame.Rect(bx,by,bw2,bh2)
                if player_screen.colliderect(boss_panel_try):
                    by=max(HUD_TOP_Y+HUD_TOP_H+8,min(SCREEN_H-bh2-58,player_screen.bottom+8))
        col=NEON_PURPLE if boss.phase>=3 else NEON_ORANGE if boss.phase==2 else NEON_RED
        panel=pygame.Rect(bx,by,bw2,bh2)
        draw_panel(surface,panel,col,(18,4,10,200),radius=6)
        draw_fit_text(surface,"BOSS",font_xs,pygame.Rect(panel.x+12,panel.y+3,38,10),col,shadow=False)
        draw_fit_text(surface,boss.name,font_xs,pygame.Rect(panel.x+50,panel.y+3,panel.w-120,10),TEXT_MAIN,shadow=False)
        draw_fit_text(surface,tr('boss.phase',phase=boss.phase),font_xs,pygame.Rect(panel.right-58,panel.y+3,48,10),col,shadow=False)
        bar=pygame.Rect(panel.x+12,panel.y+17,panel.w-24,9)
        pygame.draw.rect(surface,(40,6,10,200),bar,border_radius=5)
        bf=int(bar.w*max(0,boss.hp)/max(1,boss.max_hp))
        if bf>0:
            t2=pygame.time.get_ticks()
            pl4=0.85+0.15*math.sin(t2*0.008)
            pc4=(min(255,int(col[0]*pl4)),min(255,int(col[1]*pl4)),min(255,int(col[2]*pl4)))
            bf_s=pygame.Surface((bf,bar.h),pygame.SRCALPHA)
            pygame.draw.rect(bf_s,pc4,(0,0,bf,bar.h),border_radius=5)
            surface.blit(bf_s,bar.topleft)
            hl=pygame.Surface((max(4,bf-8),2),pygame.SRCALPHA)
            pygame.draw.line(hl,(255,255,255,80),(0,0),(max(4,bf-8),0),1)
            surface.blit(hl,(bar.x+4,bar.y+2))
            gb4=pygame.Surface((bf+8,bar.h+8),pygame.SRCALPHA)
            pygame.draw.rect(gb4,(*col,30),(4,4,bf,bar.h),border_radius=6)
            surface.blit(gb4,(bar.x-4,bar.y-4))
            dmg_w=int(bar.w*max(0,boss.hp-boss.dmg_flash)/max(1,boss.max_hp)) if getattr(boss,"dmg_flash",0)>0 else bf
            if dmg_w>bf:
                dmg_s=pygame.Surface((dmg_w-bf,bar.h),pygame.SRCALPHA)
                da=int(40+20*math.sin(t2*0.02))
                pygame.draw.rect(dmg_s,(*col,da),(0,0,dmg_w-bf,bar.h),border_radius=5)
                surface.blit(dmg_s,(bar.x+bf,bar.y))
        pygame.draw.rect(surface,(*col,120),bar,border_radius=5,width=1)
        hp_n=font_xs.render(f"{max(0,boss.hp)}/{boss.max_hp}",True,WHITE)
        surface.blit(hp_n,(bar.centerx-hp_n.get_width()//2,bar.y-1))
    if player.fly_mode:
        fp=pygame.Rect(CX-100,HUD_TOP_Y+HUD_TOP_H+6,200,26)
        draw_panel(surface,fp,NEON_CYAN,(0,35,75,150),radius=5,glow_intensity=0.5)
        pl5=int(180+75*math.sin(t*0.008))
        draw_fit_text(surface,tr("hud.fly_active"),font_xs,pygame.Rect(fp.x+8,fp.y+3,fp.w-16,10),(pl5,255,205),shadow=False)
        draw_fit_text(surface,tr("hud.fly_hint"),font_xs,pygame.Rect(fp.x+8,fp.y+14,fp.w-16,10),(150,225,205),shadow=False)
    draw_mission_hud(surface,font_xs,font_sm)
    draw_weapon_panel(surface,player,font_xs,font_sm)
    if combo_count>=2:
        cr=pygame.Rect(HUD_MARGIN,MISSION_Y+MISSION_H+4,110,16)
        cb=pygame.Surface((cr.w,cr.h),pygame.SRCALPHA)
        pygame.draw.rect(cb,(30,12,8,160),(0,0,cr.w,cr.h),border_radius=4)
        surface.blit(cb,cr.topleft)
        pygame.draw.rect(surface,NEON_ORANGE,cr,border_radius=4,width=1)
        draw_center_fit(surface,f"COMBO x{combo_count}",font_xs,cr,NEON_ORANGE,shadow=False)
    x=HUD_MARGIN
    y=MISSION_Y+MISSION_H+4+(22 if combo_count>=2 else 0)
    for kind,timer in active_powerups.items():
        data=POWERUP_DATA.get(kind)
        if not data: continue
        txt=f"{data['name']} {timer//60+1}s"
        r=pygame.Rect(x,y,88,14)
        pu_bg=pygame.Surface((r.w,r.h),pygame.SRCALPHA)
        pygame.draw.rect(pu_bg,(5,8,24,160),(0,0,r.w,r.h),border_radius=4)
        surface.blit(pu_bg,r.topleft)
        pygame.draw.rect(surface,data["color"],r,border_radius=4,width=1)
        draw_center_fit(surface,txt,font_xs,r,data["color"],shadow=False)
        x+=92
# ------------------------------------------------------------------------------------
# MAIN LOOP
# ------------------------------------------------------------------------------------
running=True
while running:
    clock.tick(FPS)
    if scene=="playing" and not level_clear: play_time_accum+=1/60
    t=pygame.time.get_ticks()
    mx,my=pygame.mouse.get_pos()
    sync_ui_texts()
    print(f"[FRAME] scene={scene} story_intro.active={story_intro.active} tutorial.active={tutorial.active} opening.active={opening.active} shop.active={shop.active} boss_dialogue.active={boss_dialogue.active}")

    for event in pygame.event.get():
        if event.type==pygame.QUIT: running=False

        if opening.active:
            print(f"[EVENT] opening.active=True scene={scene}")
            wants_skip=(event.type in(pygame.MOUSEBUTTONDOWN,pygame.MOUSEBUTTONUP) and getattr(event,"button",1)==1) or event.type==pygame.FINGERDOWN
            wants_skip=wants_skip or (event.type==pygame.KEYDOWN and event.key in(pygame.K_SPACE,pygame.K_RETURN,pygame.K_ESCAPE))
            if wants_skip:
                if opening.show_logo:
                    opening.skip_logo()
                else:
                    opening.skip()
                    transition_to("menu")
            continue

        # Tutorial - handle before everything else when active
        if tutorial.active:
            print(f"[EVENT] tutorial.active=True scene={scene}")
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_ESCAPE: tutorial.skip()
                elif event.key in(pygame.K_SPACE,pygame.K_RETURN): tutorial.next_slide()
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1: tutorial.next_slide()
            continue

        # Settings screen - blocks all gameplay input
        if settings_screen.active:
            print(f"[EVENT] settings_screen.active=True scene={scene}")
            settings_screen.handle_event(event)
            continue

        if codex_screen.active:
            print(f"[EVENT] codex_screen.active=True scene={scene}")
            codex_screen.handle_event(event)
            continue

        if achievement_screen.active:
            print(f"[EVENT] achievement_screen.active=True scene={scene}")
            achievement_screen.handle_event(event)
            continue

        if difficulty_screen.active:
            print(f"[EVENT] difficulty_screen.active=True scene={scene}")
            difficulty_screen.handle_event(event)
            continue

        if stats_screen.active:
            print(f"[EVENT] stats_screen.active=True scene={scene}")
            stats_screen.handle_event(event)
            continue

        if shop.active:
            print(f"[EVENT] shop.active=True scene={scene}")
            shop_handled=shop.handle_event(event,player)
            money=shop.coins
            if shop_handled: save_progress_state(include_session_kills=False)
            continue

        if story_intro.active:
            print(f"[EVENT] story_intro.active=True scene={scene}")
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1: story_intro.skip(); print(f"[STORY] skip() called")
            if event.type==pygame.KEYDOWN and event.key==pygame.K_SPACE: story_intro.skip(); print(f"[STORY] skip() called")
            continue

        if boss_dialogue.active:
            print(f"[EVENT] boss_dialogue.active=True scene={scene}")
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_SPACE: boss_dialogue.advance()
                if event.key==pygame.K_ESCAPE: boss_dialogue.skip_all()
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1: boss_dialogue.advance()
            continue

        if boss_intro.active:
            print(f"[EVENT] boss_intro.active=True scene={scene}")
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1: boss_intro.skip()
            if event.type==pygame.KEYDOWN and event.key==pygame.K_SPACE: boss_intro.skip()
            continue

        if research_log_active:
            handle_research_log_event(event)
            continue

        if terminal_ui_active:
            handle_terminal_ui_event(event)
            continue

        if event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE:
                if scene=="playing":
                    debug_print("[State] playing -> paused (ESC)")
                    transition_to("paused"); pause_scale=0.0
                elif scene=="paused":
                    debug_print("[State] paused -> playing (ESC)")
                    transition_to("playing")
                elif scene=="menu" and not show_save_screen and not show_difficulty_select and not show_new_game_name_input and not show_boss_rush_select: running=False
            if event.key==pygame.K_q and scene=="playing": player.switch_weapon(1); trigger_weapon_hud_expand()
            if event.key==pygame.K_e and scene=="playing":
                if not handle_player_interaction():
                    player.toggle_weapon_equip(); trigger_weapon_hud_expand()
            if event.key==pygame.K_b and scene=="playing": shop.open(money,player); sounds.play("ui_click")
            if event.key==pygame.K_b and scene=="menu" and not show_save_screen and not show_difficulty_select and not show_new_game_name_input and not show_boss_rush_select: shop.open(money,player); sounds.play("ui_click")
            if event.key==pygame.K_c and scene=="playing": codex_screen.open(); sounds.play("ui_click")
            if event.key==pygame.K_F5 and scene in("playing","paused"): do_save()
            if event.key==pygame.K_F11: toggle_fullscreen(); save_settings()
            if event.key==pygame.K_m: sounds.toggle_mute(); save_settings()
            if event.key==pygame.K_LEFTBRACKET: sounds.vol_down()
            if event.key==pygame.K_RIGHTBRACKET: sounds.vol_up()

        if scene=="menu":
            if show_save_screen:
                handled=False
                if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    sd=save_screen_data
                    yes_btn=sd.get("yes_btn"); no_btn=sd.get("no_btn")
                    r_cnf=sd.get("rename_confirm_btn"); r_ccl=sd.get("rename_cancel_btn")
                    if confirm_delete_file:
                        if yes_btn and yes_btn.collidepoint(event.pos):
                            debug_print(f"[Delete] Deleting save: {confirm_delete_file}")
                            delete_save(confirm_delete_file)
                            confirm_delete_file=""
                            save_screen_data={}
                            debug_print("[Delete] Save deleted, refreshing save list")
                            newest=get_newest_save()
                            if newest:
                                save_data=load_save(newest)
                                debug_print(f"[Delete] Newest save now: {newest}")
                            else:
                                save_data=_save_defaults()
                                debug_print("[Delete] No saves remain")
                            sounds.play("ui_click")
                            handled=True
                        elif no_btn and no_btn.collidepoint(event.pos):
                            confirm_delete_file=""; handled=True
                    elif rename_file:
                        if r_cnf and r_cnf.collidepoint(event.pos):
                            if rename_input.strip():
                                new_nm=sanitize_save_name(rename_input.strip())
                                if new_nm!=rename_file:
                                    rename_save(rename_file,new_nm)
                                    if get_last_played_save()==rename_file:
                                        save_last_played_save(new_nm)
                                rename_file=""; rename_input=""
                                sounds.play("ui_click")
                            handled=True
                        elif r_ccl and r_ccl.collidepoint(event.pos):
                            rename_file=""; rename_input=""; handled=True
                    else:
                        play_btns=sd.get("play_btns",[]); rename_btns=sd.get("rename_btns",[])
                        dup_btns=sd.get("dup_btns",[]); del_btns=sd.get("del_btns",[])
                        back_btn=sd.get("back_btn"); sf=sd.get("save_files",[])
                        if not handled:
                            for i,lb in enumerate(play_btns):
                                if i<len(sf) and lb.collidepoint(event.pos):
                                    do_load(sf[i])
                                    show_save_screen=False
                                    handled=True; break
                        if not handled:
                            for i,db in enumerate(del_btns):
                                if i<len(sf) and db.collidepoint(event.pos):
                                    confirm_delete_file=sf[i]
                                    sounds.play("ui_click")
                                    handled=True; break
                        if not handled:
                            for i,rb in enumerate(rename_btns):
                                if i<len(sf) and rb.collidepoint(event.pos):
                                    rename_file=sf[i]; rename_input=sf[i].rsplit(".",1)[0]
                                    handled=True; break
                        if not handled:
                            for i,ddb in enumerate(dup_btns):
                                if i<len(sf) and ddb.collidepoint(event.pos):
                                    duplicate_save(sf[i])
                                    sounds.play("ui_click")
                                    handled=True; break
                        if not handled and back_btn and back_btn.collidepoint(event.pos):
                            show_save_screen=False; confirm_delete_file=""; rename_file=""
                            handled=True
                if event.type==pygame.MOUSEWHEEL and show_save_screen:
                    save_scroll_offset=max(0,save_scroll_offset-event.y*50)
                if not handled and rename_file and event.type==pygame.KEYDOWN:
                    if event.key==pygame.K_RETURN:
                        if rename_input.strip():
                            new_nm=sanitize_save_name(rename_input.strip())
                            if new_nm!=rename_file:
                                rename_save(rename_file,new_nm)
                                if get_last_played_save()==rename_file:
                                    save_last_played_save(new_nm)
                            rename_file=""; rename_input=""
                            sounds.play("ui_click")
                        handled=True
                    elif event.key==pygame.K_ESCAPE:
                        rename_file=""; rename_input=""; handled=True
                    elif event.key==pygame.K_BACKSPACE:
                        rename_input=rename_input[:-1]; handled=True
                    else:
                        ch=event.unicode
                        if ch and len(rename_input)<60 and ch.isprintable() and ch not in '\\/:*?"<>|':
                            rename_input+=ch; handled=True
                elif not handled and rename_file and event.type==pygame.TEXTINPUT:
                    ch=event.text
                    if ch and len(rename_input)<60 and ch.isprintable() and ch not in '\\/:*?"<>|':
                        rename_input+=ch; handled=True
                elif not handled and event.type in(pygame.KEYDOWN,pygame.MOUSEBUTTONDOWN):
                    if not rename_file and not confirm_delete_file:
                        show_save_screen=False
            elif show_difficulty_select:
                handled=False
                if event.type==pygame.KEYDOWN:
                    if event.key==pygame.K_ESCAPE:
                        show_difficulty_select=False; handled=True
                    elif event.key==pygame.K_DOWN:
                        idx=DIFFICULTY_ORDER.index(selected_difficulty)
                        selected_difficulty=DIFFICULTY_ORDER[(idx+1)%len(DIFFICULTY_ORDER)]; handled=True
                    elif event.key==pygame.K_UP:
                        idx=DIFFICULTY_ORDER.index(selected_difficulty)
                        selected_difficulty=DIFFICULTY_ORDER[(idx-1)%len(DIFFICULTY_ORDER)]; handled=True
                    elif event.key==pygame.K_RETURN:
                        show_difficulty_select=False; show_new_game_name_input=True; new_game_name=""
                        sounds.play("ui_click"); handled=True
                if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    df_rects=save_screen_data.get("df_rects",{})
                    lanjut_btn=save_screen_data.get("df_lanjut_btn")
                    back_btn=save_screen_data.get("df_back_btn")
                    if lanjut_btn and lanjut_btn.collidepoint(event.pos):
                        show_difficulty_select=False; show_new_game_name_input=True; new_game_name=""
                        sounds.play("ui_click"); handled=True
                    elif back_btn and back_btn.collidepoint(event.pos):
                        show_difficulty_select=False; handled=True; sounds.play("ui_click")
                    else:
                        for key,rect in df_rects.items():
                            if rect.collidepoint(event.pos):
                                selected_difficulty=key; sounds.play("ui_click"); handled=True; break
                        if not handled:
                            pw,ph=540,470; px=CX-pw//2; py=SCREEN_H//2-ph//2
                            if not pygame.Rect(px,py,pw,ph).collidepoint(event.pos):
                                show_difficulty_select=False; handled=True
            elif show_new_game_name_input:
                handled=False
                if event.type==pygame.KEYDOWN:
                    if event.key==pygame.K_RETURN:
                        if new_game_name.strip():
                            safe=sanitize_save_name(new_game_name.strip()) or "save"
                            base=safe.rsplit(".json",1)[0] if safe.endswith(".json") else safe
                            fname=safe
                            if os.path.exists(os.path.join(SAVE_DIR,fname)):
                                i=2
                                while os.path.exists(os.path.join(SAVE_DIR,f"{base}_{i}.json")):
                                    i+=1
                                fname=f"{base}_{i}.json"
                            start_new_game_with_name(fname, selected_difficulty)
                            show_new_game_name_input=False
                            sounds.play("ui_click")
                        handled=True
                    elif event.key==pygame.K_ESCAPE:
                        show_new_game_name_input=False; handled=True
                    elif event.key==pygame.K_BACKSPACE:
                        if new_game_name: new_game_name=new_game_name[:-1]
                        handled=True
                elif event.type==pygame.TEXTINPUT:
                    ch=event.text
                    if ch and len(new_game_name)<60 and ch.isprintable() and ch not in '\\/:*?"<>|':
                        new_game_name+=ch; handled=True
                if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    sd=save_screen_data
                    ng_confirm_btn=sd.get("ng_confirm_btn"); ng_cancel_btn=sd.get("ng_cancel_btn")
                    if ng_confirm_btn and ng_confirm_btn.collidepoint(event.pos):
                        if new_game_name.strip():
                            safe=sanitize_save_name(new_game_name.strip()) or "save"
                            base=safe.rsplit(".json",1)[0] if safe.endswith(".json") else safe
                            fname=safe
                            if os.path.exists(os.path.join(SAVE_DIR,fname)):
                                i=2
                                while os.path.exists(os.path.join(SAVE_DIR,f"{base}_{i}.json")):
                                    i+=1
                                fname=f"{base}_{i}.json"
                            start_new_game_with_name(fname, selected_difficulty)
                            show_new_game_name_input=False
                            sounds.play("ui_click")
                        handled=True
                    elif ng_cancel_btn and ng_cancel_btn.collidepoint(event.pos):
                        show_new_game_name_input=False; handled=True
            elif show_boss_rush_select:
                handled=False
                if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
                    show_boss_rush_select=False; handled=True
                if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    brd=save_screen_data.get("br_data",{})
                    start_btn=brd.get("start_btn"); back_btn=brd.get("back_btn")
                    card_rects=brd.get("card_rects",{})
                    if back_btn and back_btn.collidepoint(event.pos):
                        show_boss_rush_select=False; handled=True; sounds.play("ui_click")
                    elif start_btn and start_btn.collidepoint(event.pos):
                        selected=[i+1 for i,v in enumerate(boss_rush_selected) if v]
                        if selected:
                            start_boss_rush(selected)
                            show_boss_rush_select=False
                            sounds.play("ui_click")
                        else:
                            toast("Pilih minimal 1 boss!","\u26A0",ORANGE,90)
                        handled=True
                    else:
                        for bid,btn_r in card_rects.items():
                            idx=bid-1
                            if 0<=idx<len(boss_rush_selected) and btn_r.collidepoint(event.pos):
                                boss_rush_selected[idx]=not boss_rush_selected[idx]
                                sounds.play("ui_click"); handled=True; break
                    if not handled:
                        pw,ph=680,520; px=CX-pw//2; py=SCREEN_H//2-ph//2
                        if not pygame.Rect(px,py,pw,ph).collidepoint(event.pos):
                            show_boss_rush_select=False; handled=True
            else:
                if btn_newgame.is_clicked(event): show_difficulty_select=True; selected_difficulty="normal"; difficulty_select_start=t
                if btn_continue.is_clicked(event): continue_game()
                if btn_save_info.is_clicked(event): show_save_screen=True
                if btn_boss_rush.is_clicked(event): show_boss_rush_select=True; show_boss_rush_open_t=t; sounds.play("ui_click")
                if btn_settings.is_clicked(event): settings_screen.open(False); sounds.play("ui_click")
                if btn_stats_m.is_clicked(event): stats_screen.open(); sounds.play("ui_click")
                if btn_quit_m.is_clicked(event): running=False

        if scene=="paused":
            print(f"[EVENT] scene==paused event.type={event.type}")
            if btn_resume_p.is_clicked(event):
                print(f"[INPUT] Resume from pause")
                transition_to("playing")
            if btn_save_p.is_clicked(event): do_save(); sounds.play("ui_click")
            if btn_shop_p.is_clicked(event): shop.open(money,player); sounds.play("ui_click")
            if btn_restart.is_clicked(event):
                print(f"[INPUT] Restart level")
                restart_level()
            if btn_settings_p.is_clicked(event): settings_screen.open(True); sounds.play("ui_click")
            if btn_menu_b.is_clicked(event):
                do_save()
                print(f"[INPUT] Quit to menu from pause")
                transition_to("menu")

        if scene=="dead":
            if((event.type==pygame.KEYDOWN and event.key==pygame.K_r) or
               (event.type==pygame.MOUSEBUTTONDOWN and event.button==1)):
                if lives>0:
                    debug_print("[State] dead -> playing (respawn)")
                    respawn()
                else:
                    debug_print("[State] dead -> gameover")
                    sd=load_save(current_save_file)
                    if score>sd["high_score"]: sd["high_score"]=score
                    if level>sd["best_level"]: sd["best_level"]=level
                    sd["total_kills"]+=session_kills; write_save(current_save_file,sd); save_data.update(sd)
                    sounds.play("game_over"); sounds.stop_bgm(); transition_to("gameover")

        if scene=="gameover":
            if((event.type==pygame.KEYDOWN and event.key==pygame.K_r) or
               (event.type==pygame.MOUSEBUTTONDOWN and event.button==1)):
                lives=max(1,lives)
                respawn()

        if scene=="ending":
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                transition_to("menu")

        if event.type==pygame.MOUSEBUTTONDOWN:
            print(f"[EVENT] MOUSEBUTTONDOWN scene={scene} pos={event.pos}")
            if event.button==1 and scene=="playing" and handle_volume_click(event.pos):
                print(f"[INPUT] Volume click")
                continue
            if event.button==1 and scene=="menu" and not show_save_screen and FULLSCREEN_MENU_RECT.collidepoint(event.pos):
                toggle_fullscreen(); save_settings(); continue
            if event.button==1 and scene=="playing" and SHOP_HUD_RECT.collidepoint(event.pos):
                print(f"[INPUT] Shop HUD click")
                shop.open(money,player); sounds.play("ui_click"); continue
            if event.button==1 and scene=="playing" and not level_clear and not boss_dialogue.active and not boss_intro.active:
                print(f"[INPUT] Player shoot")
                player.shoot_toward(p_bullets,mx,my,camera)
            if event.button==4 and scene=="playing": player.switch_weapon(-1); trigger_weapon_hud_expand()
            if event.button==5 and scene=="playing": player.switch_weapon(1); trigger_weapon_hud_expand()

    opening.update()
    tutorial.update()
    story_intro.update(); boss_dialogue.update(); boss_intro.update(); update_terminal_processing(); shake.update()
    if scene=="level_intro" and not story_intro.active:
        transition_to("playing")
        if pending_tutorial_after_intro:
            pending_tutorial_after_intro=False
            tutorial.start()
    overlays_blocking=blocking_overlay_active()

    if overlays_blocking:
        print(
            "[OVERLAY]",
            f"terminal={terminal_ui_active}",
            f"research={research_log_active}",
            f"tutorial={tutorial.active}",
            f"dialogue={boss_dialogue.active}",
            f"intro={boss_intro.active}",
        )

    if scene=="playing" and not overlays_blocking:
        update_weapon_hud_timer()

    if scene=="menu" and not overlays_blocking:
        menu_anim.update()
        title_g7.update()
        if not show_save_screen and not show_difficulty_select and not show_new_game_name_input and not show_boss_rush_select:
            btn_newgame.update(mx,my); btn_continue.update(mx,my)
            btn_save_info.update(mx,my); btn_boss_rush.update(mx,my); btn_settings.update(mx,my); btn_stats_m.update(mx,my); btn_quit_m.update(mx,my)
    if scene=="paused" and not overlays_blocking:
        pw,ph=380,470; py_p=SCREEN_H//2-ph//2; bw=292; bh=38; gap=10; by=py_p+166
        btn_resume_p.rect=pygame.Rect(CX-bw//2,by,bw,bh)
        btn_save_p.rect=pygame.Rect(CX-bw//2,by+(bh+gap),bw,bh)
        btn_shop_p.rect=pygame.Rect(CX-bw//2,by+(bh+gap)*2,bw,bh)
        btn_restart.rect=pygame.Rect(CX-bw//2,by+(bh+gap)*3,bw,bh)
        btn_settings_p.rect=pygame.Rect(CX-bw//2,by+(bh+gap)*4,bw,bh)
        btn_menu_b.rect=pygame.Rect(CX-bw//2,by+(bh+gap)*5,bw,bh)
        btn_resume_p.update(mx,my); btn_save_p.update(mx,my)
        btn_shop_p.update(mx,my); btn_restart.update(mx,my); btn_settings_p.update(mx,my); btn_menu_b.update(mx,my)

    can_update=(scene=="playing" and not level_clear and not story_intro.active
                and not overlays_blocking)
    print(f"[UPDATE] scene={scene} can_update={can_update} level_clear={level_clear} story_intro.active={story_intro.active} overlays_blocking={overlays_blocking}")
    if scene=="paused" and not overlays_blocking and pause_scale<1.0:
        pause_scale=min(1.0,pause_scale+0.06)
    if can_update:
                keys=pygame.key.get_pressed()
                in_fly_zone=any(fz.contains_for_mode(player.wx+player.WIDTH//2,player.fly_mode) for fz in fly_zones)
                debug_print("in_fly_zone:",in_fly_zone)
                debug_print("player.fly_mode:",player.fly_mode)
                debug_print("player wx:",player.wx)
                player.handle_input(keys, in_fly_zone)

                for mp in moving_plats:
                    mp.update()

                print("[3] BEFORE UPDATE:", player.wx, player.wy)

                player.update(platforms, moving_plats, fly_zones)
                for cp in checkpoints:
                    if player.get_rect().colliderect(cp.rect()):
                        if not cp.active:
                            for c in checkpoints:
                                c.active = False
                            cp.active = True
                            current_checkpoint = cp
                            respawn_wx = cp.wx
                            respawn_wy = player.wy
                            save_progress_state()

                print(
                    "[DEBUG]",
                    "Level =", level,
                    "Player =", (player.wx, player.wy),
                    "Boss =", boss_x_world,
                    "Camera =", camera.x
                )

                camera.update(player.wx)

                if player.fly_mode:
                    pr=player.get_rect()
                    fly_pr=pr.inflate(-8,-8)
                    for fz in fly_zones:
                        if not fz.contains_for_mode(player.wx+player.WIDTH//2,player.fly_mode): continue
                        fz.update(player.wx,player.wy,e_bullets)
                        collected=fz.collect_coins(pr)
                        for ct in collected:
                            dm,ds=collect_coin_reward(player,ct,multiplier); money+=dm; score+=ds
                            add_mission_progress("cells", 1)
                        for kind,obs_rect in fz.get_collision_rects():
                            if fly_pr.colliderect(obs_rect) and player.invincible==0:
                                if player.take_damage(1): player_died()
                                break

                if not player.fly_mode:
                    for tun in tunnels:
                        if tun.collide_player(player,t):
                            player_died()
                            break

                pr=player.get_rect()
                for fs in facility_sections:
                    if fs.status=="active" or fs.contains(player.wx+player.WIDTH//2):
                        fs.update_challenge(player,enemies,p_bullets,e_bullets)
                    if fs.contains(player.wx+player.WIDTH//2):
                        for hrect in fs.get_hazard_rects():
                            if player.invincible==0 and pr.colliderect(hrect):
                                if player.take_damage(1): player_died()
                                break

                for wz in water_zones:
                    if player.invincible==0 and pr.colliderect(wz.get_rect()):
                        if player.take_damage(player.hp): player_died()
                        break

                for sp in spike_traps:
                    if player.invincible==0 and pr.colliderect(sp.get_rect()):
                        if player.take_damage(1): player_died()
                        break

                for door in security_doors:
                    dr=door.get_rect()
                    if dr.w>0 and pr.colliderect(dr):
                        if player.wx+player.WIDTH//2<dr.centerx: player.wx=dr.left-player.WIDTH-2
                        else: player.wx=dr.right+2
                        player.vx=0
                        toast("Security door locked", "LOCK", RED, 70)
                        pr=player.get_rect()

                for kc in keycard_pickups:
                    if kc.alive and pr.colliderect(kc.get_rect()):
                        kc.alive=False; award_keycard(player,kc.keycard_type)
                keycard_pickups[:]=[kc for kc in keycard_pickups if kc.alive]

                for c in coins:
                    if c.alive:
                        dx=player.wx+player.WIDTH//2-c.wx; dy=player.wy+player.HEIGHT//2-c.wy
                        dist=(dx*dx+dy*dy)**0.5
                        if dist<120 and dist>0:
                            pull=1.8*(1-dist/120)
                            c.wx+=dx/dist*pull; c.wy+=dy/dist*pull
                            if random.random()<0.15:
                                c.magnet_trail.append((int(c.wx),int(c.wy),pygame.time.get_ticks()))
                        if pr.colliderect(c.get_rect()):
                            c.alive=False
                            dm,ds=collect_coin_reward(player,c.type,multiplier); money+=dm; score+=ds
                            add_mission_progress("cells",1)
                coins=[c for c in coins if c.alive]
                update_powerups(player,coins)
                update_environment_event(player,e_bullets)
                for pu in powerups:
                    if pu.alive and pr.colliderect(pu.get_rect()):
                        pu.alive=False; apply_powerup(player,pu.kind)
                powerups=[pu for pu in powerups if pu.alive]

                for b in p_bullets: b.update()
                for b in e_bullets: b.update()
                p_bullets=[b for b in p_bullets if b.alive]
                e_bullets=[b for b in e_bullets if b.alive]

                update_challenge_rooms(player,enemies,p_bullets,e_bullets)

                CULL_RANGE=SCREEN_W+200
                for en in enemies:
                    if abs(en.wx-camera.x)<CULL_RANGE:
                        en.update(player,platforms,e_bullets)
                enemies=[e for e in enemies if is_alive_entity(e)]

                check_fps_and_adjust_particles()
                for px2 in pixels: px2.update()
                pixels=[px2 for px2 in pixels if px2.life>0]
                for t2 in toasts: t2.update()
                toasts=[t2 for t2 in toasts if t2.alive]
                if screen_fade_dir>0:
                    screen_fade=min(255,screen_fade+5)
                    if screen_fade>=255: screen_fade_dir=-1
                elif screen_fade_dir<0:
                    screen_fade=max(0,screen_fade-5)
                    if screen_fade<=0: screen_fade_dir=0
                for dn in damage_numbers: dn.update()
                damage_numbers[:]=[dn for dn in damage_numbers if dn.life>0]

                pr=player.get_rect()
                for ch in chests:
                    if ch.alive and pr.colliderect(ch.get_rect()):
                        ch.alive=False
                        add_mission_progress("chests",1); add_session_stat("total_chests",1)
                        if ch.type=="secret": add_mission_progress("secrets",1); add_session_stat("total_secrets",1); unlock_achievement("secret_finder","Secret Finder"); spawn_score(ch.wx+12,ch.wy-18,"SECRET CACHE")
                        if ch.content=="hp":
                            player.hp=min(player.MAX_HP,player.hp+2); spawn_pixels(ch.wx,ch.wy,(29,158,117),12)
                            sounds.play("chest")
                        elif ch.content=="ammo":
                            wk=player.current_weapon
                            if player.ammo[wk]>=0: player.ammo[wk]=min(player.ammo[wk]+8,WEAPONS[wk]["ammo"]*2)
                            spawn_pixels(ch.wx,ch.wy,(239,159,39),12); sounds.play("chest")
                        else:
                            if ch.content in WEAPONS:
                                player.pick_up_weapon(ch.content); sounds.play("weapon_pickup")
                                if level==9 and ch.type in("rare","secret","boss"):
                                    add_mission_progress("prototype",1); unlock_story_log("log_09")
                            elif ch.content in POWERUP_DATA:
                                apply_powerup(player,ch.content)
                            else:
                                apply_powerup(player,random.choice(list(POWERUP_DATA.keys())))
                            spawn_pixels(ch.wx,ch.wy,(127,119,221),20)
                chests=[ch for ch in chests if ch.alive]

                if mission_state.get("complete") and mission_state.get("timer",0)<=0 and is_boss_area_unlocked() and not boss_spawned and boss is None and player.wx>boss_x_world-720:
                    boss_spawned=True; waiting_for_dialogue=True
                    boss_id=active_boss_data.get("base_id",get_boss_id(level))
                    boss=Boss(boss_id,boss_x_world,active_boss_data,level)
                    debug_print("Boss X:", boss.wx if boss else None)
                    boss_dialogue.start(boss_id,boss.data["color"],level)

                if waiting_for_dialogue and boss_dialogue.done:
                    waiting_for_dialogue=False
                    bd=dict(boss.data if boss else active_boss_data); bd["accent"]=get_level_data(level)["accent"]
                    boss_intro.trigger(bd,level); shake.trigger(10,20)
                    toast(f"BOSS: {active_boss_data['name']}","\u2620",NEON_RED,150)

                for b in list(p_bullets):
                    if not b.alive: continue
                    br=b.get_rect(); hit=False
                    bx,by=br.centerx,br.centery
                    CULL_DIST=100
                    for node in security_nodes:
                        if node.alive and br.colliderect(node.get_rect()):
                            if b.pierce>0: b.pierce-=1
                            else: b.alive=False
                            node.take_hit(safe_damage_value(getattr(b,"damage",1)))
                            hit=True; break
                    if hit: continue
                    for en in enemies:
                        if abs(en.wx+en.WIDTH//2-bx)>CULL_DIST or abs(en.wy+en.HEIGHT//2-by)>CULL_DIST:
                            continue
                        if br.colliderect(en.get_rect()):
                            bullet_damage=safe_damage_value(getattr(b,"damage",1))
                            if getattr(en,"elite_type",None)=="shield":
                                dmg=max(1,math.ceil(bullet_damage*0.5))
                            else:
                                dmg=bullet_damage
                            debug_print("Enemy hit:",getattr(en,"elite_type",None),"damage:",dmg,"hp before:",en.hp)
                            if b.pierce>0: b.pierce-=1
                            else: b.alive=False
                            killed,_=damage_enemy(en,dmg,"bullet")
                            spawn_pixels(en.wx,en.wy,(200,220,255),6)
                            spawn_pixels(en.wx+en.WIDTH//2,en.wy+en.HEIGHT//2,(255,255,255),3)
                            sounds.play("enemy_hit")
                            if killed:
                                register_kill(getattr(en,"score_value",100),en.wx+en.WIDTH//2,en.wy,getattr(en,"coin_reward",1)*25)
                                if getattr(en,"elite_type",None):
                                    player.elite_kills+=1
                                    if player.elite_kills>=10: unlock_achievement("elite_hunter","Elite Hunter")
                                    kc_type=keycard_drop_for_elite(en)
                                    if kc_type and random.random()<0.85: keycard_pickups.append(KeycardPickup(en.wx+10,en.wy,kc_type))
                                if random.random()<0.3: chests.append(Chest(en.wx,en.wy,"common"))
                                if random.random()<0.12 and getattr(en,"elite_type",None): powerups.append(PowerUp(en.wx+14,en.wy,random.choice(list(POWERUP_DATA.keys()))))
                                for _ in range(getattr(en,"coin_reward",1)): coins.append(Coin(en.wx+14+random.randint(-10,10),en.wy+random.randint(-8,8),"rare" if getattr(en,"elite_type",None) and random.random()<0.35 else "gold"))
                                spawn_pixels(en.wx,en.wy,(55,138,221),20)
                                spawn_pixels(en.wx+en.WIDTH//2,en.wy+en.HEIGHT//2,(255,200,100),8)
                                shake.trigger(4,8)
                                sounds.play("enemy_death")
                            hit=True; break
                    if not hit and boss and boss.alive:
                        if br.colliderect(boss.get_rect()):
                            b.alive=False
                            if boss.take_hit(safe_damage_value(getattr(b,"damage",1))):
                                boss.alive=False
                                sounds.play("boss_death")
                                shake.trigger(12,25)
                                for _ in range(80): spawn_pixels(boss.wx+random.randint(0,boss.bw),boss.wy+random.randint(0,boss.bh),random.choice([RED,ORANGE,YELLOW,(255,255,100)]),6)
                                if boss_rush_active:
                                    boss_rush_score+=1000*boss_rush_wave
                                    if boss_rush_wave<boss_rush_max_waves:
                                        spawn_next_boss_rush()
                                        score+=500*boss_rush_wave
                                    else:
                                        check_boss_rush_complete()
                                        score+=5000
                                    continue
                                level_clear_rank=compute_level_rank()
                                reward_total=finalize_level_rewards(level_clear_rank)
                                unlock_story_log(f"log_{min(level,11):02d}")
                                if level>=11: add_mission_progress("ai_core",1)
                                sd=load_save(current_save_file); sd["bosses_defeated"]+=1
                                if sd["bosses_defeated"]>=5: unlock_achievement("boss_hunter","Boss Hunter")
                                sd["achievements"]=save_data.get("achievements",sd.get("achievements",[]))
                                if score>sd["high_score"]: sd["high_score"]=score
                                if level>sd["best_level"]: sd["best_level"]=level
                                next_level=min(level+1,len(LEVEL_ORDER))
                                sd["total_kills"]+=session_kills; sd["last_level"]=next_level; sd["last_checkpoint"]=next_level
                                sd["has_save"]=True; sd["money"]=money; sd["shop_upgrades"]=get_shop_upgrade_levels()
                                save_adventure_progress_fields(sd,player)
                                sd["timestamp"]=datetime.now().isoformat()
                                if write_save(current_save_file,sd): save_data.update(sd); session_kills=0
                                btn_continue.disabled=False
                                chests.append(Chest(boss.wx+boss.bw//2,boss.wy,"boss"))
                                score+=500*level*multiplier; shake.trigger(12,25)
                                for _ in range(80): spawn_pixels(boss.wx+random.randint(0,boss.bw),boss.wy+random.randint(0,boss.bh),random.choice([RED,ORANGE,YELLOW,(255,255,100)]),6)
                            else:
                                sounds.play("boss_hit")
                                spawn_pixels(boss.wx,boss.wy,tuple(boss.data["color"]),8)
                                spawn_pixels(boss.wx+boss.bw//2,boss.wy+boss.bh//2,(255,255,255),4)
                                spawn_dmg(boss.wx+boss.bw//2,boss.wy,safe_damage_value(getattr(b,"damage",1)),NEON_ORANGE)
                                shake.trigger(5,6)

                if boss and boss.alive and not boss_dialogue.active and not boss_intro.active:
                    boss.update(player,e_bullets,enemies,platforms,camera)
                    if boss.freeze_active:
                        for b in e_bullets:
                            if b.cryo and b.get_rect().colliderect(player.get_rect()) and player.invincible==0: player.frozen=120; b.alive=False; break
                    if boss.laser_active:
                        ly=int(boss.wy+boss.bh//3)
                        if pygame.Rect(0,ly-4,WORLD_W,16).colliderect(player.get_rect()):
                            if player.take_damage(1): player_died()
                    if player.invincible==0 and boss.get_rect().colliderect(player.get_rect()):
                        dmg=2 if boss.phase==2 else 1
                        if player.take_damage(dmg): player_died()
                    if boss.stomp_active:
                        sw=pygame.Rect(int(boss.stomp_wx)-140,int(boss.wy)+boss.bh-30,280,25)
                        if sw.colliderect(player.get_rect()) and player.invincible==0:
                            if boss.ability!="giant_stomp" or boss.stomp_frames<=34:
                                if player.take_damage(2 if boss.ability=="giant_stomp" else 1): player_died()

                pr=player.get_rect()
                for b in e_bullets:
                    if pr.colliderect(b.get_rect()):
                        b.alive=False
                        if b.cryo: player.frozen=120; sounds.play("frozen")
                        elif player.take_damage(1): player_died()
                        break
                for en in enemies:
                    if pr.colliderect(en.get_rect()): player.wx+=-12 if player.wx<en.wx else 12; player.vy=-5; break
                for en in enemies:
                    er=en.get_rect()
                    if(pr.colliderect(er) and player.vy>0 and player.wy+player.HEIGHT-player.vy<er.top+10):
                        killed,_=damage_enemy(en,1,"stomp"); player.vy=-8; sounds.play("stomp")
                        if killed:
                            register_kill(150,en.wx+en.WIDTH//2,en.wy,getattr(en,"coin_reward",1)*25)
                            if random.random()<0.3: chests.append(Chest(en.wx,en.wy,"common"))
                            spawn_pixels(en.wx,en.wy,(200,220,255),20)
                            spawn_pixels(en.wx+en.WIDTH//2,en.wy+en.HEIGHT//2,(255,200,100),8)
                            shake.trigger(5,8)
                            sounds.play("enemy_death")

                mult_timer=max(0,mult_timer-1)
                if mult_timer==0:
                    if multiplier>1:
                        mult_decay_tick+=1
                        if mult_decay_tick>=60:
                            multiplier=max(1,multiplier-1)
                            mult_decay_tick=0
                    else:
                        mult_decay_tick=0
                combo_timer=max(0,combo_timer-1)
                if combo_timer==0: combo_count=0
                if mission_state and mission_state.get("timer",0)>0: mission_state["timer"]-=1
                update_respawn_spot()
                if boss and not boss.alive and not level_clear:
                    level_clear = True
                    level_clear_timer = 160
                    sounds.play("level_clear")
                    sounds.stop_bgm()
                    toast(tr("level.clear.done", level=level, bonus=1000 * level), "\u2B50", GOLD, 180)

    if level_clear:
        level_clear_timer -= 1
        if level_clear_timer <= 0:
            if level >= len(LEVEL_ORDER):
                score += 1000 * level
                finish_game()
            level += 1
            checkpoint = level
            score += 1000 * level
            p_bullets = []
            e_bullets = []
            pixels = []
            boss = None
            boss_spawned = False
            coins = []
            powerups = []
            active_powerups = {}
            combo_count = 0
            combo_timer = 0
            platforms, enemies, boss_x_world, chests, moving_plats, spike_traps, tunnels, fly_zones, facility_sections, water_zones, coins, active_boss_data = generate_world(level, save_data.get("world_seed"))
            build_checkpoints()
            start_level_mission(level)
            reconcile_current_mission_progress()
            reset_level_stats()
            reset_environment_event()
            camera = Camera()

            player.reset()
            print("[1] AFTER RESET:", player.wx, player.wy)

            apply_permanent_unlocks(player)
            apply_shop_upgrades(player)

            respawn_wx = player.wx
            respawn_wy = player.wy
            current_checkpoint = None
            save_progress_state()

            level_clear = False
            start_level_intro(level)
            print("[2] AFTER INTRO:", player.wx, player.wy)

            screen_fade = 255
            screen_fade_dir = -1
            screen_fade = 255
            screen_fade_dir = -1

    # -- BGM auto-switch ------------------------
    if scene == "menu":
        sounds.play_bgm("menu")
    elif scene == "playing":
        if boss and boss.alive:
            sounds.play_bgm("boss")
        elif not level_clear:
            ld_key = get_level_data(level)["theme"]
            sounds.play_bgm(ld_key)
    elif scene in ("dead", "gameover", "paused", "ending"):
        pass  # keep current BGM or silence
        # keep the current soundtrack unchanged for transitional scenes

    # --------------------------------------------------------------------------------
    # DRAW
    # --------------------------------------------------------------------------------
    screen.fill(DARK_BLUE)

    if opening.active:
        opening.draw(screen,font_lg,font_xl,font_sm,font_xs,t)
        print(f"[DRAW] opening (active=True)")
        pygame.display.flip()
        skip_frame = True

    if 'skip_frame' in locals() and skip_frame:
        # already drawn opening and flipped this frame; skip further drawing
        del skip_frame

    else:
        print(
            "[DRAW]",
            overlays_blocking,
            terminal_ui_active,
            research_log_active,
            tutorial.active,
            boss_dialogue.active,
            boss_intro.active
        )

        if overlays_blocking:
            screen.fill(DARK_BLUE)
            starfield.draw(screen,0)
            print(f"[DRAW] overlays_blocking=True ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ starfield only")
        elif scene=="menu":
            print(f"[DRAW] menu scene={scene} overlays_blocking={overlays_blocking}")
            screen.fill(DARK_BLUE)
            starfield.draw(screen,0)
            menu_anim.draw(screen)
            grad=get_cached_surface("menu_gradient",SCREEN_W,SCREEN_H)
            grad.fill((0,0,0,0))
            for gy2 in range(0,SCREEN_H,2):
                pygame.draw.line(grad,(5,5,18,int(80*(gy2/SCREEN_H))),(0,gy2),(SCREEN_W,gy2))
            screen.blit(grad,(0,0))

        if show_save_screen:
            pw,ph=580,500; px_s=CX-pw//2; py_s=SCREEN_H//2-ph//2
            ov=get_cached_surface("save_screen_ov",SCREEN_W,SCREEN_H); ov.fill((0,0,0,180)); screen.blit(ov,(0,0))
            panel=get_cached_surface("save_screen_panel",pw,ph); panel.fill((8,10,28,235))
            screen.blit(panel,(px_s,py_s))
            pygame.draw.rect(screen,CYAN,(px_s,py_s,pw,ph),border_radius=8,width=1)
            pygame.draw.rect(screen,CYAN,(px_s,py_s,pw,3),border_radius=8)
            draw_text(screen,tr("save.title"),font_lg,CX,py_s+14,CYAN,center=True)
            pygame.draw.line(screen,PANEL_BORDER,(px_s+40,py_s+50),(px_s+pw-40,py_s+50),1)
            info_y=py_s+50; slot_card_h=112; slot_gap=10; slot_start_y=info_y+14
            play_btns=[]; rename_btns=[]; dup_btns=[]; del_btns=[]; save_file_names=[]
            yes_btn=no_btn=None
            clip_rect=pygame.Rect(px_s,slot_start_y,pw,slot_start_y+ph-36)
            old_clip=screen.get_clip(); screen.set_clip(clip_rect)
            sf=list_save_files()
            visible_area_h=ph-(slot_start_y-py_s)-36
            max_scroll=max(0,len(sf)*(slot_card_h+slot_gap)-visible_area_h)
            save_scroll_offset=min(save_scroll_offset,max_scroll)
            for si,fd in enumerate(sf):
                fname=fd["filename"]
                sy=slot_start_y+si*(slot_card_h+slot_gap)-save_scroll_offset
                if sy+slot_card_h<slot_start_y: continue
                if sy>slot_start_y+visible_area_h: continue
                sr=pygame.Rect(px_s+20,sy,pw-40,slot_card_h)
                save_file_names.append(fname)
                sd_slot=fd["data"]
                has=bool(sd_slot.get("has_save",False))
                glow_col=(60,160,220) if has else (50,50,60)
                card=pygame.Surface((sr.w,sr.h),pygame.SRCALPHA)
                card.fill((12,16,38,220))
                screen.blit(card,sr.topleft)
                pygame.draw.rect(screen,glow_col,sr,border_radius=6,width=1)
                sname=fname.rsplit(".",1)[0]
                slot_lbl=font_sm.render(sname,True,glow_col)
                screen.blit(slot_lbl,(sr.x+10,sr.y+6))
                if has:
                    lv=sd_slot.get("last_level",1); sc=sd_slot.get("high_score",0)
                    co=sd_slot.get("money",0); ts=sd_slot.get("timestamp","")
                    pt=sd_slot.get("play_time",0); bd=sd_slot.get("bosses_defeated",0)
                    wp=sd_slot.get("current_weapon",0)
                    diff=sd_slot.get("settings",{}).get("difficulty","normal")
                    diff_name={"easy":"EASY","normal":"NORMAL","hard":"HARD","corex":"COREX"}.get(diff,"NORMAL")
                    wp_name={0:"LASER",1:"SHOTGUN",2:"PULSE",3:"RAILGUN",4:"NOVA",5:"BURST"}.get(wp,"LASER")
                    lv_t=font_xs.render(tr("save.slot_level",lv=lv),True,CYAN)
                    screen.blit(lv_t,(sr.x+10,sr.y+26))
                    sc_t=font_xs.render(tr("save.slot_score",s=sc),True,YELLOW)
                    screen.blit(sc_t,(sr.x+130,sr.y+26))
                    co_t=font_xs.render(tr("save.slot_coins",c=co),True,GOLD)
                    screen.blit(co_t,(sr.x+260,sr.y+26))
                    bd_t=font_xs.render(tr("save.bosses")+f": {bd}",True,PINK)
                    screen.blit(bd_t,(sr.x+10,sr.y+44))
                    diff_t=font_xs.render(tr("save.difficulty",d=diff_name),True,ORANGE)
                    screen.blit(diff_t,(sr.x+170,sr.y+44))
                    wp_t=font_xs.render(tr("save.weapon",w=wp_name),True,TEAL)
                    screen.blit(wp_t,(sr.x+10,sr.y+62))
                    tm_t=font_xs.render(tr("save.play_time",t=pt/60),True,TEXT_MUTED)
                    screen.blit(tm_t,(sr.x+170,sr.y+62))
                    dt_t=font_xs.render(tr("save.last_played",d=ts[:10] if ts else "---"),True,TEXT_DIM)
                    screen.blit(dt_t,(sr.x+10,sr.y+80))
                    btn_lx=sr.right-340; btn_ty=sr.y+sr.h-28
                    lb=pygame.Rect(btn_lx,btn_ty,76,22)
                    rb=pygame.Rect(btn_lx+84,btn_ty,76,22)
                    ddb=pygame.Rect(btn_lx+168,btn_ty,76,22)
                    db=pygame.Rect(btn_lx+252,btn_ty,76,22)
                    for b,txt,bc in[(lb,tr("save.play"),GREEN),(rb,tr("save.rename"),CYAN),(ddb,tr("save.duplicate"),ORANGE),(db,tr("save.delete"),RED)]:
                        bs2=pygame.Surface((b.w,b.h),pygame.SRCALPHA); bs2.fill((*bc[:3],40))
                        screen.blit(bs2,b.topleft); pygame.draw.rect(screen,bc,b,border_radius=3,width=1)
                        lbl=render_fit(font_xs,txt,WHITE,b.w-8)
                        screen.blit(lbl,(b.centerx-lbl.get_width()//2,b.centery-lbl.get_height()//2))
                else:
                    empty_t=font_sm.render(tr("save.slot_empty"),True,TEXT_DIM)
                    screen.blit(empty_t,(sr.centerx-empty_t.get_width()//2,sr.centery-empty_t.get_height()//2))
                    lb=rb=ddb=db=pygame.Rect(0,0,0,0)
                play_btns.append(lb); rename_btns.append(rb); dup_btns.append(ddb); del_btns.append(db)
            screen.set_clip(old_clip)
            if len(sf)>3:
                scroll_bar_x=px_s+pw-8; scroll_bar_h=visible_area_h
                scroll_bar_y=slot_start_y
                bar_h=max(20,scroll_bar_h*visible_area_h//((len(sf))*(slot_card_h+slot_gap)))
                bar_y=scroll_bar_y+(scroll_bar_h-bar_h)*save_scroll_offset//max(1,max_scroll)
                pygame.draw.rect(screen,(40,40,50),(scroll_bar_x,scroll_bar_y,4,scroll_bar_h),border_radius=2)
                pygame.draw.rect(screen,(100,140,200),(scroll_bar_x,bar_y,4,bar_h),border_radius=2)
            back_btn=pygame.Rect(CX-70,slot_start_y+visible_area_h-4,140,30)
            bs3=pygame.Surface((back_btn.w,back_btn.h),pygame.SRCALPHA); bs3.fill((*PURPLE[:3],50))
            screen.blit(bs3,back_btn.topleft)
            pygame.draw.rect(screen,PURPLE,back_btn,border_radius=4,width=1)
            bk_t=render_fit(font_sm,tr("save.back"),WHITE,back_btn.w-12)
            screen.blit(bk_t,(back_btn.centerx-bk_t.get_width()//2,back_btn.centery-bk_t.get_height()//2))
            if confirm_delete_file:
                dpw=340; dph=100; dpx=CX-dpw//2; dpy=SCREEN_H//2-dph//2
                del_prompt_rect=pygame.Rect(dpx,dpy,dpw,dph)
                dp=pygame.Surface((dpw,dph),pygame.SRCALPHA); dp.fill((18,8,28,240))
                screen.blit(dp,del_prompt_rect.topleft)
                pygame.draw.rect(screen,RED,del_prompt_rect,border_radius=6,width=1)
                dt2=font_sm.render(tr("save.delete_confirm"),True,WHITE)
                screen.blit(dt2,(CX-dt2.get_width()//2,dpy+12))
                yes_btn=pygame.Rect(CX-70,dpy+dph-36,60,24); no_btn=pygame.Rect(CX+10,dpy+dph-36,60,24)
                for b,txt,bc in[(yes_btn,tr("save.yes"),GREEN),(no_btn,tr("save.no"),RED)]:
                    bs=pygame.Surface((b.w,b.h),pygame.SRCALPHA); bs.fill((*bc[:3],40))
                    screen.blit(bs,b.topleft); pygame.draw.rect(screen,bc,b,border_radius=3,width=1)
                    lbl=render_fit(font_xs,txt,WHITE,b.w-8)
                    screen.blit(lbl,(b.centerx-lbl.get_width()//2,b.centery-lbl.get_height()//2))
            save_screen_data={
                "play_btns":play_btns,"rename_btns":rename_btns,"dup_btns":dup_btns,
                "del_btns":del_btns,"back_btn":back_btn,"save_files":save_file_names,
                "yes_btn":yes_btn,"no_btn":no_btn
            }
            if rename_file:
                rpw=360; rph=140; rpx=CX-rpw//2; rpy=SCREEN_H//2-rph//2
                rp=pygame.Surface((rpw,rph),pygame.SRCALPHA); rp.fill((18,8,28,240))
                screen.blit(rp,(rpx,rpy))
                pygame.draw.rect(screen,CYAN,(rpx,rpy,rpw,rph),border_radius=6,width=1)
                rt=font_sm.render(tr("save.rename_title"),True,CYAN)
                screen.blit(rt,(CX-rt.get_width()//2,rpy+12))
                inp_r=pygame.Rect(rpx+20,rpy+44,rpw-40,28)
                pygame.draw.rect(screen,(40,45,60),inp_r,border_radius=3)
                pygame.draw.rect(screen,CYAN,inp_r,border_radius=3,width=1)
                in_txt=font_sm.render(rename_input if rename_input else tr("save.rename_placeholder"),True,WHITE if rename_input else TEXT_DIM)
                screen.blit(in_txt,(inp_r.x+6,inp_r.y+4))
                r_cnf=pygame.Rect(CX-80,rpy+rph-36,70,24); r_ccl=pygame.Rect(CX+10,rpy+rph-36,70,24)
                for b,txt,bc in[(r_cnf,tr("save.rename_confirm"),GREEN),(r_ccl,tr("save.cancel"),RED)]:
                    bs2=pygame.Surface((b.w,b.h),pygame.SRCALPHA); bs2.fill((*bc[:3],40))
                    screen.blit(bs2,b.topleft); pygame.draw.rect(screen,bc,b,border_radius=3,width=1)
                    lbl2=render_fit(font_xs,txt,WHITE,b.w-8)
                    screen.blit(lbl2,(b.centerx-lbl2.get_width()//2,b.centery-lbl2.get_height()//2))
                save_screen_data["rename_confirm_btn"]=r_cnf; save_screen_data["rename_cancel_btn"]=r_ccl
                save_screen_data["yes_btn"]=yes_btn; save_screen_data["no_btn"]=no_btn

        elif show_difficulty_select:
            pw,ph=540,470; px=CX-pw//2; py=SCREEN_H//2-ph//2
            fade=min(1.0,(t-difficulty_select_start)/200.0) if difficulty_select_start>0 else 1.0
            fa=int(180*fade); pa=int(245*fade)
            ov=get_cached_surface("df_sel_ov2",SCREEN_W,SCREEN_H); ov.fill((0,0,0,fa)); screen.blit(ov,(0,0))
            panel=get_cached_surface("df_sel_panel2",pw,ph); panel.fill((8,10,28,pa))
            screen.blit(panel,(px,py))
            pygame.draw.rect(screen,(*CYAN,int(155*fade)),(px,py,pw,ph),border_radius=10,width=1)
            pygame.draw.rect(screen,(*CYAN,int(155*fade)),(px,py,pw,3),border_radius=10)
            draw_text(screen,"PILIH DIFFICULTY",font_lg,CX,py+22,CYAN,center=True)
            pygame.draw.line(screen,PANEL_BORDER,(px+35,py+54),(px+pw-35,py+54),1)
            df_rects={}
            card_data=[("easy","Easy",CYAN,"More HP  ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢  More Coins  ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢  Easier enemies"),("normal","Normal",BLUE,"Standard gameplay experience"),("hard","Hard",ORANGE,"Stronger enemies  ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢  Faster enemies"),("nightmare","Nightmare",RED,"Elite enemies  ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢  Hard bosses  ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢  More hazards")]
            for i,(key,label,col,desc) in enumerate(card_data):
                cy=py+70+i*82; cr=pygame.Rect(px+30,cy,pw-60,74); df_rects[key]=cr; active=key==selected_difficulty
                if active:
                    for g in range(3,0,-1):
                        gr=cr.inflate(g*4+4,g*4+4)
                        gs=pygame.Surface((gr.w,gr.h),pygame.SRCALPHA)
                        pygame.draw.rect(gs,(*col,25-g*5),gs.get_rect(),border_radius=8,width=g+1)
                        screen.blit(gs,gr.topleft)
                pygame.draw.rect(screen,(20,24,38),cr,border_radius=6)
                pygame.draw.rect(screen,col if active else (40,45,62),cr,border_radius=6,width=2 if active else 1)
                if active:
                    tri=font_sm.render("ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¶",True,col)
                    screen.blit(tri,(cr.x+12,cr.y+10))
                    nx=cr.x+34
                else:
                    nx=cr.x+18
                screen.blit(font_sm.render(label,True,col if active else TEXT_MAIN),(nx,cr.y+10))
                screen.blit(font_xs.render(desc,True,TEXT_MUTED),(nx,cr.y+36))
            save_screen_data["df_rects"]=df_rects
            bw,bh=130,30; bg=16; tw=bw*2+bg; bx=CX-tw//2; by=py+ph-50
            back_r=pygame.Rect(bx,by,bw,bh); lanjut_r=pygame.Rect(bx+bw+bg,by,bw,bh)
            save_screen_data["df_back_btn"]=back_r; save_screen_data["df_lanjut_btn"]=lanjut_r
            for br,btxt,bcol in[(back_r,"KEMBALI",RED),(lanjut_r,"LANJUT  ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã¢â‚¬Å“ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¶",CYAN)]:
                hv=br.collidepoint(mx,my)
                hr=br.inflate(4*hv,4*hv)
                bs=pygame.Surface((hr.w,hr.h),pygame.SRCALPHA); bs.fill((*bcol,35+25*hv))
                screen.blit(bs,hr.topleft)
                pygame.draw.rect(screen,(*bcol,130+80*hv),hr,border_radius=4,width=1)
                lbl=font_sm.render(btxt,True,WHITE)
                screen.blit(lbl,(hr.centerx-lbl.get_width()//2,hr.centery-lbl.get_height()//2))
        elif show_new_game_name_input:
            pw,ph=460,240; px_s=CX-pw//2; py_s=SCREEN_H//2-ph//2
            ov=get_cached_surface("ng_name_ov",SCREEN_W,SCREEN_H); ov.fill((0,0,0,180)); screen.blit(ov,(0,0))
            panel=get_cached_surface("ng_name_panel",pw,ph); panel.fill((8,10,28,235))
            screen.blit(panel,(px_s,py_s))
            pygame.draw.rect(screen,CYAN,(px_s,py_s,pw,ph),border_radius=8,width=1)
            pygame.draw.rect(screen,CYAN,(px_s,py_s,pw,3),border_radius=8)
            draw_text(screen,tr("save.new_game"),font_lg,CX,py_s+14,CYAN,center=True)
            pygame.draw.line(screen,PANEL_BORDER,(px_s+40,py_s+50),(px_s+pw-40,py_s+50),1)
            inp_r=pygame.Rect(px_s+30,py_s+66,pw-60,32)
            pygame.draw.rect(screen,(40,45,60),inp_r,border_radius=4)
            pygame.draw.rect(screen,CYAN,inp_r,border_radius=4,width=1)
            display_text=new_game_name if new_game_name else "Enter Save Name..."
            in_txt=font_sm.render(display_text,True,WHITE if new_game_name else TEXT_DIM)
            screen.blit(in_txt,(inp_r.x+8,inp_r.y+4))
            if new_game_name and (t//500)%2==0:
                cx=inp_r.x+8+font_sm.size(new_game_name)[0]
                pygame.draw.line(screen,WHITE,(cx,inp_r.y+6),(cx,inp_r.y+26),2)
            ng_confirm_btn=pygame.Rect(CX-90,py_s+ph-52,80,28)
            ng_cancel_btn=pygame.Rect(CX+10,py_s+ph-52,80,28)
            for b,txt,bc in[(ng_confirm_btn,tr("save.create"),GREEN),(ng_cancel_btn,tr("save.cancel"),RED)]:
                bs=pygame.Surface((b.w,b.h),pygame.SRCALPHA); bs.fill((*bc[:3],40))
                screen.blit(bs,b.topleft); pygame.draw.rect(screen,bc,b,border_radius=3,width=1)
                lbl=render_fit(font_sm,txt,WHITE,b.w-8)
                screen.blit(lbl,(b.centerx-lbl.get_width()//2,b.centery-lbl.get_height()//2))
            save_screen_data={"ng_confirm_btn":ng_confirm_btn,"ng_cancel_btn":ng_cancel_btn}
        elif show_boss_rush_select:
            pw,ph=700,540; px=CX-pw//2; py=SCREEN_H//2-ph//2
            debug_print("[BossRush] Layout rebuilt")
            fade=min(255,int(255*min(1,(t-show_boss_rush_open_t)/12))) if 'show_boss_rush_open_t' in dir() else 255
            ov=get_cached_surface("br_ov",SCREEN_W,SCREEN_H); ov.fill((0,0,0,180)); screen.blit(ov,(0,0))
            panel=get_cached_surface("br_panel",pw,ph); panel.fill((8,10,28,235))
            panel.set_alpha(fade); screen.blit(panel,(px,py))
            pygame.draw.rect(screen,(*NEON_PURPLE,fade),(px,py,pw,ph),border_radius=8,width=1)
            pygame.draw.rect(screen,(*NEON_PURPLE,fade),(px,py,pw,3),border_radius=8)
            draw_text(screen,tr("boss_rush.title"),font_lg,CX,py+14,(200,100,255),center=True)
            # Header: progress
            boss_unlocked=min(10,save_data.get("bosses_defeated",0)+1)
            hx=px+30; hy=py+48; hw=pw-60; hh=30
            hbg=pygame.Surface((hw,hh),pygame.SRCALPHA); hbg.fill((NEON_PURPLE[0]//10,NEON_PURPLE[1]//10,NEON_PURPLE[2]//10,100))
            screen.blit(hbg,(hx,hy))
            pygame.draw.rect(screen,(*NEON_PURPLE,100),(hx,hy,hw,hh),border_radius=6,width=1)
            prog_t=font_xs.render(f"{tr('boss_rush.unlocked',id=0)[:-3]}: {boss_unlocked}/10",True,NEON_PURPLE)
            screen.blit(prog_t,(hx+12,hy+7))
            bar_x=hx+220; bar_y=hy+4; bar_w=hw-310; bar_h=22
            pygame.draw.rect(screen,(15,18,30),(bar_x,bar_y,bar_w,bar_h),border_radius=5)
            fill_w=int(bar_w*boss_unlocked/10)
            if fill_w>0:
                fill_s=pygame.Surface((fill_w,bar_h),pygame.SRCALPHA)
                for fi in range(fill_w):
                    fa=int(180-120*abs(fi/fill_w-0.5)*2)
                    fill_s.set_at((fi,0),(*NEON_PURPLE,fa))
                    if fi%2==0: fill_s.set_at((fi,bar_h-1),(*NEON_PURPLE,fa))
                screen.blit(fill_s,(bar_x,bar_y))
                pygame.draw.rect(screen,NEON_PURPLE,(bar_x,bar_y,fill_w,bar_h),border_radius=5,width=1)
            pct=font_xs.render(f"{boss_unlocked*10}%",True,NEON_PURPLE)
            screen.blit(pct,(bar_x+bar_w+10,bar_y+2))
            # Best score
            best_br=save_data.get("total_boss_rush_waves",0)
            best_t=font_xs.render(f"BEST: {best_br} waves",True,TEXT_MUTED)
            screen.blit(best_t,(hx+hw-best_t.get_width()-12,hy+7))

            # Reserve bottom area for action buttons (48px)
            button_area_top = py + ph - 52

            # Card grid: 5 columns x 2 rows to fit within available space
            cols=5; rows=2; gap_x=10; gap_y=10
            card_w=min(124, (pw - 2*30 - (cols-1)*gap_x) // cols)
            available_h = button_area_top - (py + 82) - 8
            card_h = (available_h - (rows-1)*gap_y) // rows
            card_h = max(130, min(card_h, 180))
            grid_w=cols*card_w+(cols-1)*gap_x; grid_x=px+(pw-grid_w)//2; grid_y=py+82

            self_br_rects={}
            now_ms=pygame.time.get_ticks()
            for i in range(10):
                bid=i+1; unlocked=bid<=boss_unlocked; toggled=boss_rush_selected[i] if i<len(boss_rush_selected) else False
                col=i%cols; row=i//cols
                cx=grid_x+col*(card_w+gap_x); cy=grid_y+row*(card_h+gap_y)
                cr=pygame.Rect(cx,cy,card_w,card_h)
                data=BOSS_DATA[bid]
                diff_col=BOSS_DIFFICULTY.get(bid,CYAN)
                card_col=diff_col if unlocked else GRAY
                bg_col=(*card_col,30) if unlocked else (8,10,18,210)
                card_bg=pygame.Surface((card_w,card_h),pygame.SRCALPHA); card_bg.fill(bg_col)
                card_bg.set_alpha(fade); screen.blit(card_bg,cr.topleft)
                hov=cr.collidepoint(mx,my) and unlocked
                border_col=GOLD if toggled else (card_col if unlocked else (40,45,55))
                bw2=3 if (toggled or hov) else 1
                pygame.draw.rect(screen,border_col,cr,border_radius=8,width=bw2)
                if hov:
                    gl=pygame.Surface((card_w+8,card_h+8),pygame.SRCALPHA)
                    pygame.draw.rect(gl,(*card_col,25),(0,0,card_w+8,card_h+8),border_radius=10)
                    screen.blit(gl,(cx-4,cy-4))
                # Boss sprite area
                sprite_y=cy+4
                if unlocked:
                    bw,bh=data["size"]; ts_w=bw+30; ts_h=bh+30
                    boss_surf=pygame.Surface((ts_w,ts_h),pygame.SRCALPHA)
                    draw_boss_sprite(boss_surf,15,15,data,now_ms,1)
                    sprite_max_h=card_h-70
                    scale=min((card_w-20)/max(ts_w,1),sprite_max_h/max(ts_h,1))
                    scale=min(scale,1.0)
                    nw=max(1,int(ts_w*scale)); nh=max(1,int(ts_h*scale))
                    if nw>0 and nh>0:
                        boss_surf=pygame.transform.smoothscale(boss_surf,(nw,nh))
                        screen.blit(boss_surf,(cx+card_w//2-nw//2,sprite_y))
                else:
                    bw,bh=data["size"]; ts_w=bw+30; ts_h=bh+30
                    boss_surf=pygame.Surface((ts_w,ts_h),pygame.SRCALPHA)
                    draw_boss_sprite(boss_surf,15,15,data,now_ms,1)
                    sprite_max_h=card_h-70
                    scale=min((card_w-20)/max(ts_w,1),sprite_max_h/max(ts_h,1))
                    scale=min(scale,1.0)
                    nw=max(1,int(ts_w*scale)); nh=max(1,int(ts_h*scale))
                    if nw>0 and nh>0:
                        boss_surf=pygame.transform.smoothscale(boss_surf,(nw,nh))
                        dark=pygame.Surface(boss_surf.get_size(),pygame.SRCALPHA)
                        dark.fill((0,0,0,180))
                        boss_surf.blit(dark,(0,0))
                        screen.blit(boss_surf,(cx+card_w//2-nw//2,sprite_y))
                    lock_s=font_sm.render("\U0001F512",True,(60,65,80))
                    screen.blit(lock_s,(cx+card_w//2-lock_s.get_width()//2,sprite_y+card_h//2-40))
                # Name - compact
                name_y=cy+card_h-58
                nm_col=card_col if unlocked else (60,65,80)
                nm=render_fit(font_xs,data["name"],nm_col,card_w-12)
                screen.blit(nm,(cx+card_w//2-nm.get_width()//2,name_y))
                if unlocked:
                    hp_stars=data["hp"]
                    stars_t=font_xs.render(f"HP {hp_stars}",True,card_col)
                    screen.blit(stars_t,(cx+card_w//2-stars_t.get_width()//2,name_y+13))
                    diff_lbl=BOSS_DIFFICULTY_LABEL.get(bid,"BOSS")
                    dl_col=diff_col
                    dl=font_xs.render(diff_lbl,True,dl_col)
                    screen.blit(dl,(cx+card_w//2-dl.get_width()//2,name_y+26))
                    # Fight toggle button
                    btn_r=pygame.Rect(cx+card_w//2-36,name_y+39,72,16)
                    btn_is_hov=btn_r.collidepoint(mx,my)
                    btn_col=NEON_GREEN if toggled else (card_col[0]//2,card_col[1]//2,card_col[2]//2)
                    pygame.draw.rect(screen,(10,14,20),btn_r,border_radius=4)
                    pygame.draw.rect(screen,btn_col,btn_r,border_radius=4,width=1 if not btn_is_hov else 2)
                    ft=tr("boss_rush.start").split()[0] if current_language()=="en" else "FIGHT"
                    btn_txt=font_xs.render(ft,True,btn_col)
                    screen.blit(btn_txt,(btn_r.centerx-btn_txt.get_width()//2,btn_r.centery-btn_txt.get_height()//2))
                    self_br_rects[bid]=btn_r
                else:
                    lock_cond=font_xs.render(tr("boss_rush.locked",id=bid),True,(50,55,65))
                    screen.blit(lock_cond,(cx+card_w//2-lock_cond.get_width()//2,name_y+16))
            save_screen_data["br_data"]={"toggles":list(self_br_rects.values()),"card_rects":self_br_rects}
            # Bottom action buttons - always fully visible, never overlapping cards
            by2=button_area_top; bw2,bh2=140,32; bg2=20; tw2=bw2*2+bg2; bx2=CX-tw2//2
            back_r=pygame.Rect(bx2,by2,bw2,bh2); start_r=pygame.Rect(bx2+bw2+bg2,by2,bw2,bh2)
            save_screen_data["br_data"]["back_btn"]=back_r; save_screen_data["br_data"]["start_btn"]=start_r
            for br_,btxt_,bcol_ in[(back_r,tr("boss_rush.back"),RED),(start_r,tr("boss_rush.start"),NEON_GREEN)]:
                hv=br_.collidepoint(mx,my)
                hr=br_.inflate(4*hv,4*hv)
                bs=pygame.Surface((hr.w,hr.h),pygame.SRCALPHA); bs.fill((*bcol_,40+30*hv))
                screen.blit(bs,hr.topleft)
                pygame.draw.rect(screen,(*bcol_,150+80*hv),hr,border_radius=6,width=2 if hv else 1)
                lbl=render_fit(font_sm,btxt_,WHITE,hr.w-12)
                screen.blit(lbl,(hr.centerx-lbl.get_width()//2,hr.centery-lbl.get_height()//2))
        else:
            logo_rect=draw_game_logo(screen,24) or pygame.Rect(CX,24,0,0)
            title_g7.draw(screen)
            hs_y=max(166,logo_rect.bottom+12)
            if hs_y+62>btn_newgame.rect.y-12: hs_y=btn_newgame.rect.y-74
            hs_rect=pygame.Rect(CX-210,hs_y,420,62)
            hs_panel=pygame.Surface((hs_rect.w,hs_rect.h),pygame.SRCALPHA); hs_panel.fill((6,10,25,220))
            screen.blit(hs_panel,hs_rect.topleft)
            pygame.draw.rect(screen,(55,130,90),hs_rect,border_radius=8,width=1)
            pygame.draw.rect(screen,(55,130,90),(hs_rect.x,hs_rect.y,hs_rect.w,3),border_radius=8)
            pulse_c=int(200+55*math.sin(t*0.005))
            hs_v=save_data.get('high_score',0); bl_v=save_data.get('best_level',1)
            tp_v=save_data.get('total_plays',0); bd_v=save_data.get('bosses_defeated',0)
            hs_t=font_sm.render(f"{tr('menu.high_score')}:  {hs_v:06d}",True,(pulse_c,230,95))
            screen.blit(hs_t,(CX-hs_t.get_width()//2,hs_y+7))
            sub_t=font_xs.render(f"{tr('menu.level')}: {bl_v}   {tr('menu.plays')}: {tp_v}   {tr('menu.bosses')}: {bd_v}",True,(150,190,165))
            screen.blit(sub_t,(CX-sub_t.get_width()//2,hs_y+33))
            btn_newgame.draw(screen,font_sm); btn_continue.draw(screen,font_sm)
            btn_save_info.draw(screen,font_sm); btn_boss_rush.draw(screen,font_sm); btn_settings.draw(screen,font_sm); btn_stats_m.draw(screen,font_sm); btn_quit_m.draw(screen,font_sm)
            if save_data.get("has_save"):
                ci=font_xs.render(tr("menu.save",level=save_data.get('last_level',1)),True,TEXT_MUTED)
            else:
                ci=font_xs.render(tr("menu.no_save"),True,TEXT_MUTED)
            screen.blit(ci,(CX-ci.get_width()//2,542))
            sh=font_xs.render(tr("menu.shop_hint"),True,WARNING_TEXT)
            screen.blit(sh,(CX-sh.get_width()//2,560))
            ft=font_xs.render(f"{tr('menu.version')}  |  2025 Shaniss Ambotang Avila",True,TEXT_DIM)
            screen.blit(ft,(CX-ft.get_width()//2,578))
            fs_txt=font_xs.render(tr("menu.fullscreen") if not fullscreen else tr("menu.windowed"),True,(50,120,90))
            fs_box=pygame.Surface((FULLSCREEN_MENU_RECT.w,FULLSCREEN_MENU_RECT.h),pygame.SRCALPHA)
            pygame.draw.rect(fs_box,(30,60,50,170),(0,0,FULLSCREEN_MENU_RECT.w,FULLSCREEN_MENU_RECT.h),border_radius=5)
            screen.blit(fs_box,FULLSCREEN_MENU_RECT.topleft)
            pygame.draw.rect(screen,(55,130,90),FULLSCREEN_MENU_RECT,border_radius=5,width=1)
            screen.blit(fs_txt,(FULLSCREEN_MENU_RECT.centerx-fs_txt.get_width()//2,FULLSCREEN_MENU_RECT.centery-fs_txt.get_height()//2))

        if scene=="level_intro":
            print(f"[DRAW] level_intro")
            screen.fill(DARK_BLUE)
            starfield.draw(screen, 0)

        elif scene == "playing" or scene == "paused":
            print(f"[DRAW] playing/paused scene={scene} overlays_blocking={overlays_blocking} can_update={can_update}")
            in_facility = SHOW_FACILITY_SECTIONS and any(fs.contains(player.wx+player.WIDTH//2) for fs in facility_sections)
            if not in_facility: parallax_bg.draw(screen,camera.x,level)
            else: screen.fill((12,14,28))
            for fz in fly_zones: fz.draw_bg(screen,camera,t)
            if boss and boss.alive:
                bc2=boss.data["color"]; arena=get_cached_surface("boss_arena",SCREEN_W,SCREEN_H)
                arena_a=int(8+5*math.sin(t*0.003))
                arena.fill((0,0,0,0)); pygame.draw.rect(arena,(*bc2,arena_a),(0,0,SCREEN_W,SCREEN_H))
                screen.blit(arena,(0,0))
                arena_edge=get_cached_surface("boss_arena_edge",SCREEN_W,SCREEN_H)
                arena_edge.fill((0,0,0,0))
                for ey in range(0,SCREEN_H,4):
                    eaa=int(15+10*math.sin(t*0.005+ey*0.05))
                    pygame.draw.line(arena_edge,(*bc2,eaa),(0,ey),(6,ey))
                    pygame.draw.line(arena_edge,(*bc2,eaa),(SCREEN_W-6,ey),(SCREEN_W,ey))
                screen.blit(arena_edge,(0,0))
                draw_boss_background_effects(screen,level,boss,t,camera.x)
            if SHOW_FACILITY_SECTIONS:
                for fs in facility_sections:
                    if abs(camera.apply(fs.wx,0)[0]-SCREEN_W//2)<SCREEN_W+fs.width: fs.draw_bg(screen,camera,t,fs.accent)
            for tun in tunnels: tun.draw(screen,camera)
            for wz in water_zones: wz.draw(screen,camera,t)
            draw_challenge_rooms(screen,camera,t,font_sm,font_xs)
            theme2=get_level_data(level)["theme"]
            draw_floor(screen,camera,theme2)
            for plat in platforms:
                if plat.y>=555 and plat.h>=30: continue
                sr=camera.apply_rect(plat)
                if -10<sr.x<SCREEN_W+10:
                    draw_static_platform(screen,sr,theme2)
            for mp in moving_plats: mp.draw(screen,camera)
            if SHOW_FACILITY_SECTIONS:
                for fs in facility_sections: fs.draw_platforms(screen,camera,fs.accent); fs.draw_doors(screen,camera)
            for sp in spike_traps: sp.draw(screen,camera)
            for fz in fly_zones: fz.draw_obstacles(screen,camera,t)
            for c in coins: c.draw(screen,camera)
            for cp in checkpoints: cp.draw(screen,camera)
            for pu in powerups: pu.draw(screen,camera)
            if boss_spawned or player.wx>boss_x_world-600:
                sign_sx=int(camera.apply(boss_x_world-350,0)[0])
                if 0<sign_sx<SCREEN_W:
                    st=font_sm.render(tr("boss.challenge"),True,RED); screen.blit(st,(sign_sx-st.get_width()//2,80))
                    pygame.draw.line(screen,RED,(sign_sx,90+st.get_height()),(sign_sx,SCREEN_H-50),1)
            for px2 in pixels: px2.draw(screen,camera)
            for door in security_doors: door.draw(screen,camera)
            for node in security_nodes: node.draw(screen,camera)
            for hr in hidden_room_entrances: hr.draw(screen,camera)
            for tm in terminals: tm.draw(screen,camera)
            for kc in keycard_pickups: kc.draw(screen,camera)
            for ch in chests: ch.draw(screen,camera)
            for en in enemies: en.draw(screen,camera)
            for b in e_bullets: b.draw(screen,camera)
            for b in p_bullets:
                sx2,sy2=camera.apply(b.wx,b.wy)
                if -10<sx2<SCREEN_W+10:
                    glow_key=f"bullet_glow_{b.color}"
                    glow=get_cached_surface(glow_key,20,10)
                    glow.fill((0,0,0,0)); pygame.draw.ellipse(glow,(*b.color,60),(0,0,20,10)); screen.blit(glow,(int(sx2)-10,int(sy2)-5))
                    pygame.draw.rect(screen,b.color,(int(sx2)-8,int(sy2)-2,16,4),border_radius=2)
            if boss and boss.alive: boss.draw(screen,camera)
            player.draw(screen,camera)
            for dn in damage_numbers: dn.draw(screen,camera)
            if player.hp<=2 and player.invincible==0:
                if random.random()<0.04:
                    for _ in range(2):
                        gy3=random.randint(0,SCREEN_H-8); gh3=random.randint(2,6); shift=random.randint(-8,8)
                        strip=screen.subsurface((0,gy3,SCREEN_W,min(gh3,SCREEN_H-gy3))).copy(); screen.blit(strip,(shift,gy3))
                vig=get_cached_surface("dmg_vig",SCREEN_W,SCREEN_H)
                alpha_v=int(35+25*math.sin(t*0.008))
                vig.fill((200,0,0,alpha_v))
                screen.blit(vig,(0,0))
                edge_vig=get_cached_surface("dmg_edge",SCREEN_W,SCREEN_H)
                edge_vig.fill((0,0,0,0))
                for evy in range(SCREEN_H):
                    eva=max(0,int(60*(1-abs(evy-SCREEN_H//2)/(SCREEN_H//2))**4))
                    pygame.draw.line(edge_vig,(200,0,0,eva),(0,evy),(4,evy))
                    pygame.draw.line(edge_vig,(200,0,0,eva),(SCREEN_W-4,evy),(SCREEN_W,evy))
                screen.blit(edge_vig,(0,0))
            if player.frozen>0:
                fov=get_cached_surface("frozen_overlay",SCREEN_W,SCREEN_H)
                fov_alpha=int(35*(player.frozen/120))
                fov.fill((60,140,200,fov_alpha))
                screen.blit(fov,(0,0))
                ice_pulse=150+80*math.sin(t*0.015)
                ice_vig=get_cached_surface("frozen_edge",SCREEN_W,SCREEN_H)
                ice_vig.fill((0,0,0,0))
                for ivy in range(0,SCREEN_H,8):
                    iva=int(25*(player.frozen/120)*(0.5+0.5*math.sin(t*0.01+ivy*0.1)))
                    pygame.draw.line    (ice_vig,(160,230,255,iva),(0,ivy),(SCREEN_W,ivy),1)
                screen.blit(ice_vig,(0,0))
                ft2=font_sm.render(tr("hud.frozen"),True,(150,230,255)); screen.blit(ft2,(CX-ft2.get_width()//2,SCREEN_H//2))
                draw_environment_event(screen,font_xs,t)

            # Combo visual feedback: screen edge glow
            if combo_count >= 3:
                ci = min(1.0, combo_count / 20)

                cv2 = get_cached_surface("combo_glow", SCREEN_W, SCREEN_H)
                cv2.fill((0, 0, 0, 0))

                ca = max(0, min(255, int(15 * ci + 8 * math.sin(t * 0.01) * ci)))

                for cy2 in range(0, SCREEN_H, 3):
                    cl2 = max(
                        0,
                        min(
                            255,
                            int(200 * ci + 55 * math.sin(t * 0.008 + cy2 * 0.03))
                        )
                    )

                    pgreen = max(0, min(255, int(120 - ci * 80)))
                    color = (cl2, pgreen, 20, ca)

                    pygame.draw.line(
                        cv2,
                        color,
                        (0, cy2),
                        (8, cy2)
                    )

                    pygame.draw.line(
                        cv2,
                        color,
                        (SCREEN_W - 8, cy2),
                        (SCREEN_W, cy2)
                    )

                screen.blit(cv2, (0, 0))

            cross_col=(100,210,200,180)
            pygame.draw.line(screen,cross_col,(mx-10,my),(mx-4,my),1); pygame.draw.line(screen,cross_col,(mx+4,my),(mx+10,my),1)
            pygame.draw.line(screen,cross_col,(mx,my-10),(mx,my-4),1); pygame.draw.line(screen,cross_col,(mx,my+4),(mx,my+10),1)
            pygame.draw.circle(screen,cross_col,(mx,my),7,1)
            pygame.draw.circle(screen,(*cross_col[:3],60),(mx,my),10,1)

            draw_hud(screen,player,lives,score,money,level,enemies,boss_spawned,checkpoint,multiplier,boss,mx,my,t,font_xs,font_sm,font_md)
            draw_main_gate_mission_indicator(screen,camera,font_xs,t)
            draw_interaction_hint(screen,font_xs)
            if boss_rush_active:
                br_panel=pygame.Rect(SCREEN_W//2-140,6,280,40)
                draw_panel(screen,br_panel,(200,100,255),(8,6,22,190),radius=6)
                br_wave=font_sm.render(tr("boss_rush.wave",wave=boss_rush_wave),True,(200,100,255))
                screen.blit(br_wave,(br_panel.x+12,br_panel.y+6))
                br_sc=font_xs.render(tr("boss_rush.score",score=boss_rush_score),True,(180,180,255))
                screen.blit(br_sc,(br_panel.x+12,br_panel.y+24))
                br_prog=font_xs.render(f"{boss_rush_wave}/{boss_rush_max_waves}",True,TEAL)
                screen.blit(br_prog,(br_panel.right-br_prog.get_width()-10,br_panel.y+10))
            ty=HUD_TOP_Y+HUD_TOP_H+8
            for t3 in toasts[-3:]:
                t3.draw(screen,font_xs,font_sm,ty)
                ty+=38

            if level_clear:
                ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((0,0,0,160)); screen.blit(ov,(0,0))
                prog=1.0-level_clear_timer/160; bw3=int(SCREEN_W*min(1.0,prog*3))
                bs=pygame.Surface((bw3,190),pygame.SRCALPHA); bs.fill((0,40,20,215)); screen.blit(bs,(CX-bw3//2,SCREEN_H//2-86))
                if prog>0.25 and boss:
                    dn=render_fit(font_lg,tr("level.clear.defeated",name=boss.name),ORANGE,SCREEN_W-90)
                    b2_t=font_sm.render(tr("level.clear.done",level=level,bonus=1000*level),True,YELLOW)
                    if level>=len(LEVEL_ORDER): nxt=font_sm.render(tr("level.clear.final"),True,CYAN)
                    else:
                        nxt=render_fit(font_sm,tr("level.clear.next",level=level+1),CYAN,SCREEN_W-120)
                    ck=font_xs.render(tr("level.clear.save"),True,GREEN)
                    rank_col=GOLD if level_clear_rank=="S" else CYAN if level_clear_rank=="A" else ORANGE if level_clear_rank=="B" else TEXT_MUTED
                    elapsed=(pygame.time.get_ticks()-level_start_ticks)//1000
                    rk=font_sm.render(f"RANK {level_clear_rank}   DMG {level_damage_taken}   COMBO {level_best_combo}   {elapsed}s",True,rank_col)
                    screen.blit(dn,(CX-dn.get_width()//2,SCREEN_H//2-58)); screen.blit(b2_t,(CX-b2_t.get_width()//2,SCREEN_H//2-18))
                    screen.blit(rk,(CX-rk.get_width()//2,SCREEN_H//2+8))
                    if level_reward_lines:
                        x0=CX-210; y0=SCREEN_H//2+30
                        for i,(name,val,col) in enumerate(level_reward_lines[:6]):
                            txt=font_xs.render(f"{name}: +{val}",True,col)
                            screen.blit(txt,(x0+(i%3)*140,y0+(i//3)*16))
                        screen.blit(nxt,(CX-nxt.get_width()//2,SCREEN_H//2+66)); screen.blit(ck,(CX-ck.get_width()//2,SCREEN_H//2+88))
                    else:
                        screen.blit(nxt,(CX-nxt.get_width()//2,SCREEN_H//2+34)); screen.blit(ck,(CX-ck.get_width()//2,SCREEN_H//2+58))

            if scene=="paused":
                ov=get_cached_surface("pause_ov",SCREEN_W,SCREEN_H); ov.fill((0,0,8,175)); screen.blit(ov,(0,0))
                pw,ph=380,470; px_p=CX-pw//2; py_p=SCREEN_H//2-ph//2
                if pause_scale<1.0:
                    pws=max(1,int(pw*pause_scale)); phs=max(1,int(ph*pause_scale))
                    panel=pygame.Surface((pws,phs),pygame.SRCALPHA); panel.fill((6,8,26,240))
                    screen.blit(panel,(CX-pws//2,SCREEN_H//2-phs//2))
                    pygame.draw.rect(screen,CYAN,(CX-pws//2,SCREEN_H//2-phs//2,pws,phs),border_radius=10,width=1)
                else:
                    panel=pygame.Surface((pw,ph),pygame.SRCALPHA); panel.fill((6,8,26,240)); screen.blit(panel,(px_p,py_p))
                    pygame.draw.rect(screen,CYAN,(px_p,py_p,pw,ph),border_radius=10,width=1)
                    pygame.draw.rect(screen,CYAN,(px_p,py_p,pw,3),border_radius=10)
                    glow_p=pygame.Surface((pw+10,8),pygame.SRCALPHA); pygame.draw.rect(glow_p,(*CYAN,30),(0,0,pw+10,8)); screen.blit(glow_p,(px_p-5,py_p-2))
                    pt=font_lg.render(tr("pause.title"),True,WHITE); screen.blit(pt,(CX-pt.get_width()//2,py_p+18))
                    pygame.draw.line(screen,(35,65,55),(CX-150,py_p+58),(CX+150,py_p+58),1)
                    ip=pygame.Rect(px_p+34,py_p+70,pw-68,82)
                    isf=pygame.Surface((ip.w,ip.h),pygame.SRCALPHA); isf.fill((4,6,20,200))
                    pygame.draw.rect(isf,CYAN,(0,0,ip.w,ip.h),border_radius=6,width=1)
                    screen.blit(isf,ip.topleft)
                    info_lines=[tr("pause.score",score=score),tr("pause.level",level=level),tr("pause.best",best=save_data.get('high_score',0)),tr("pause.bosses",bosses=save_data.get('bosses_defeated',0))]
                    for i,line in enumerate(info_lines):
                        txt=font_sm.render(line,True,CYAN)
                        screen.blit(txt,(CX-txt.get_width()//2,ip.y+8+i*18))
                    pygame.draw.line(screen,(25,50,40),(CX-150,py_p+160),(CX+150,py_p+160),1)
                    btn_resume_p.draw(screen,font_sm); btn_save_p.draw(screen,font_sm)
                    btn_shop_p.draw(screen,font_sm); btn_restart.draw(screen,font_sm); btn_settings_p.draw(screen,font_sm); btn_menu_b.draw(screen,font_sm)
                    tip=font_xs.render(tr("pause.tip"),True,WARNING_TEXT)
                    screen.blit(tip,(CX-tip.get_width()//2,py_p+ph-24))

        elif scene=="dead":
            print(f"[DRAW] dead scene={scene}")
            screen.fill(DARK_BLUE)
            dt2=get_level_data(level)["theme"]
            draw_floor(screen,camera,dt2)
            for plat in platforms:
                if plat.y>=555 and plat.h>=30: continue
                sr=camera.apply_rect(plat)
                if -10<sr.x<SCREEN_W+10: draw_static_platform(screen,sr,dt2)
            for en in enemies: en.draw(screen,camera)
            if boss and boss.alive: boss.draw(screen,camera)
            player.draw(screen,camera)
            ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((30,0,0,185)); screen.blit(ov,(0,0))
            pw,ph=440,230; panel=pygame.Surface((pw,ph),pygame.SRCALPHA); panel.fill((18,4,4,235))
            screen.blit(panel,(CX-pw//2,SCREEN_H//2-ph//2))
            pygame.draw.rect(screen,RED,(CX-pw//2,SCREEN_H//2-ph//2,pw,ph),border_radius=8,width=1)
            pygame.draw.rect(screen,RED,(CX-pw//2,SCREEN_H//2-ph//2,pw,3),border_radius=8)
            pr2=int(180+70*math.sin(t*0.005)); dt=font_lg.render(tr("dead.title"),True,(pr2,30,30))
            screen.blit(dt,(CX-dt.get_width()//2,SCREEN_H//2-ph//2+12))
            pygame.draw.line(screen,(80,20,20),(CX-180,SCREEN_H//2-ph//2+52),(CX+180,SCREEN_H//2-ph//2+52),1)
            info_txt=tr("dead.info",lives=lives,level=checkpoint)
            inf=font_sm.render(info_txt,True,CYAN)
            screen.blit(font_sm.render(info_txt,True,(0,0,0)),(CX-inf.get_width()//2+2,SCREEN_H//2-ph//2+60)); screen.blit(inf,(CX-inf.get_width()//2,SCREEN_H//2-ph//2+58))
            if boss:
                bi=font_xs.render(tr("dead.boss",name=boss.name,hp=max(0,boss.hp)),True,ORANGE)
                screen.blit(bi,(CX-bi.get_width()//2,SCREEN_H//2-ph//2+82))
            rs_txt=tr("dead.retry") if lives>0 else tr("dead.game_over")
            rs=font_sm.render(rs_txt,True,WARNING_TEXT); screen.blit(font_sm.render(rs_txt,True,(0,0,0)),(CX-rs.get_width()//2+2,SCREEN_H//2-ph//2+112)); screen.blit(rs,(CX-rs.get_width()//2,SCREEN_H//2-ph//2+110))
            for i in range(5): draw_robot_head(screen,CX-62+i*26,SCREEN_H//2-ph//2+150,alive=(i<lives))

        elif scene=="gameover":
            print(f"[DRAW] gameover scene={scene}")
            screen.fill(DARK_BLUE); starfield.draw(screen,0)
            ov=get_cached_surface("gameover_ov",SCREEN_W,SCREEN_H); ov.fill((0,0,0,200)); screen.blit(ov,(0,0))
            if boss_rush_score>0 or boss_rush_max_waves>0:
                pw,ph=480,280; panel=get_cached_surface("br_go_panel",pw,ph); panel.fill((8,4,24,245)); screen.blit(panel,(CX-pw//2,SCREEN_H//2-ph//2))
                pygame.draw.rect(screen,(200,100,255),(CX-pw//2,SCREEN_H//2-ph//2,pw,ph),border_radius=10,width=2)
                draw_glitch_text(screen,tr("boss_rush.complete"),font_lg,CX-font_lg.size(tr("boss_rush.complete"))[0]//2,SCREEN_H//2-ph//2+12,(200,100,255),t)
                pygame.draw.line(screen,(80,30,80),(CX-200,SCREEN_H//2-ph//2+52),(CX+200,SCREEN_H//2-ph//2+52),1)
                draw_text(screen,tr("boss_rush.score",score=boss_rush_score),font_md,CX,SCREEN_H//2-ph//2+80,GOLD,center=True)
                bi_line=font_sm.render(f"{boss_rush_max_waves} WAVES  |  {score} PTS",True,(180,180,255))
                screen.blit(bi_line,(CX-bi_line.get_width()//2,SCREEN_H//2-ph//2+112))
                draw_text(screen,tr("gameover.back"),font_sm,CX,SCREEN_H//2-ph//2+200,WARNING_TEXT,center=True)
                draw_g7(screen,CX-16,SCREEN_H//2+ph//2-40,False,0,True,0,0)
            else:
                pw,ph=480,280; panel=get_cached_surface("gameover_panel",pw,ph); panel.fill((8,4,20,245))
                screen.blit(panel,(CX-pw//2,SCREEN_H//2-ph//2))
                pygame.draw.rect(screen,PURPLE,(CX-pw//2,SCREEN_H//2-ph//2,pw,ph),border_radius=10,width=1)
                draw_glitch_text(screen,"GAME  OVER",font_lg,CX-font_lg.size("GAME  OVER")[0]//2,SCREEN_H//2-ph//2+12,RED,t)
                pygame.draw.line(screen,(80,30,80),(CX-200,SCREEN_H//2-ph//2+52),(CX+200,SCREEN_H//2-ph//2+52),1)
                hs=save_data.get("high_score",0); is_new=score>=hs and score>0
                if is_new:
                    pulse3=int(200+55*math.sin(t*0.01)); nhs3=font_sm.render(tr("gameover.new_record"),True,(pulse3,220,50))
                    screen.blit(nhs3,(CX-nhs3.get_width()//2,SCREEN_H//2-ph//2+56))
                draw_text(screen,tr("gameover.score",score=score),font_md,CX,SCREEN_H//2-ph//2+82,CYAN,center=True)
                hs_line=font_xs.render(tr("gameover.stats",best=hs,level=save_data.get('best_level',1),bosses=save_data.get('bosses_defeated',0),plays=save_data.get('total_plays',0)),True,TEXT_MUTED)
                screen.blit(hs_line,(CX-hs_line.get_width()//2,SCREEN_H//2-ph//2+112))
                boss_nm=(boss.name if boss else active_boss_data.get("name",BOSS_DATA.get(get_boss_id(level),BOSS_DATA[10])["name"]))
                boss_line=render_fit(font_sm,tr("gameover.boss",level=level,boss=boss_nm),TEXT_MAIN,400)
                screen.blit(boss_line,(CX-200,SCREEN_H//2-ph//2+136))
                draw_text(screen,tr("gameover.back"),font_sm,CX,SCREEN_H//2-ph//2+180,WARNING_TEXT,center=True)
                draw_g7(screen,CX-16,SCREEN_H//2+ph//2-40,False,0,True,0,0)

        elif scene=="ending":
            print(f"[DRAW] ending scene={scene}")
            screen.fill((3,5,18)); starfield.draw(screen,0)
            ov=get_cached_surface("ending_ov",SCREEN_W,SCREEN_H); ov.fill((0,0,0,150)); screen.blit(ov,(0,0))
            ending_title=tr("ending.title")
            draw_glitch_text(screen,ending_title,font_lg,CX-font_lg.size(ending_title)[0]//2,110,CYAN,t)
            lines=[tr("ending.line1"),tr("ending.line2"),tr("ending.line3")]
            for i,line in enumerate(lines):
                draw_text(screen,line,font_sm,CX,190+i*34,TEXT_MAIN,center=True)
            draw_text(screen,tr("ending.score",score=score),font_md,CX,330,YELLOW,center=True)
            draw_text(screen,tr("ending.back"),font_sm,CX,420,WARNING_TEXT,center=True)
            draw_g7(screen,CX-16,470,False,0,True,0,0)

        if story_intro.active:
            print(f"[DRAW] story_intro overlay (active=True)")
        story_intro.draw(screen,font_lg,font_sm,font_xs,t)
        if boss_dialogue.active:
            print(f"[DRAW] boss_dialogue overlay (active=True)")
        boss_dialogue.draw(screen,font_sm,font_xs,t)
        if boss_intro.active:
            print(f"[DRAW] boss_intro overlay (active=True)")
        boss_intro.draw(screen,font_xl,font_lg,font_sm,font_xs,t)
        if tutorial.active:
            print(f"[DRAW] tutorial overlay (active=True)")
        tutorial.draw(screen,font_lg,font_sm,font_xs,t)
        if shop.active:
            print(f"[DRAW] shop overlay (active=True)")
        shop.draw(screen,font_lg,font_sm,font_xs,t)
        if codex_screen.active:
            print(f"[DRAW] codex overlay (active=True)")
        codex_screen.draw(screen,font_lg,font_sm,font_xs,t)
        draw_terminal_interface(screen,font_lg,font_sm,font_xs,t)
        draw_research_log_screen(screen,font_lg,font_sm,font_xs,t)
        if achievement_screen.active:
            print(f"[DRAW] achievement overlay (active=True)")
        achievement_screen.draw(screen,font_lg,font_sm,font_xs,t)
        if difficulty_screen.active:
            print(f"[DRAW] difficulty overlay (active=True)")
        difficulty_screen.draw(screen,font_lg,font_sm,font_xs,t)
        if stats_screen.active:
            print(f"[DRAW] stats overlay (active=True)")
        stats_screen.draw(screen,font_lg,font_sm,font_xs,t)
        if settings_screen.active:
            print(f"[DRAW] settings overlay (active=True)")
        settings_screen.draw(screen,font_lg,font_sm,font_xs,t)

        ox,oy=shake.offset()
        if ox!=0 or oy!=0:
            shifted=screen.subsurface((max(0,-ox),max(0,-oy),SCREEN_W-abs(ox),SCREEN_H-abs(oy))).copy()
            screen.fill(BLACK); screen.blit(shifted,(max(0,ox),max(0,oy)))

        if screen_fade>0:
            fo=get_cached_surface("screen_fade",SCREEN_W,SCREEN_H)
            fo.fill((0,0,0,min(255,screen_fade)))
            screen.blit(fo,(0,0))

        pygame.display.flip()

# End main loop cleanly.
pygame.quit()
sys.exit()
