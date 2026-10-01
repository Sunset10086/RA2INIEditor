"""全局配置常量：显示参数、注册列表定义、说明文件名。"""

# ==================== 显示配置 ====================
UI_FONT_FAMILY   = "Microsoft YaHei"
UI_FONT_SIZE     = 11
LIST_FONT_FAMILY = "Consolas"
LIST_FONT_SIZE   = 11
DESC_FONT_FAMILY = "Microsoft YaHei"
DESC_FONT_SIZE   = 11
WINDOW_WIDTH     = 1400
WINDOW_HEIGHT    = 850
ROW_HEIGHT       = 22
# ==================================================
# ------------------------------------------------------------------
# INI 类型识别规则
# ------------------------------------------------------------------
# 每个规则：(类型名, 该类型独有的节名列表)
# 只要文件中出现了列表中任意一个节名，就判为该类型。
# 注意：节名比较时不区分大小写。
INI_TYPE_SIGNATURES = [
    
    # ---------------- 主题音乐文件（thememd.ini） ----------------
    # 核心特征节是 [Themes]，配合固定主题节 [INTRO]/[SCORE] 提高准确度
    ("theme", ["Themes"]),
    # ---------------- 地图文件（.map / .mpr / .yrm） ----------------
    # IsoMapPack5 / OverlayPack 是 RA2 地图独有节，几乎不会出现在其他文件里
    ("map", [
        "IsoMapPack5", "OverlayPack", "OverlayPack5",
        "PreviewPack", "IsoMapPack4",
    ]),
    # ---------------- 多人地图注册文件（.pkt） ----------------
    ("pkt", ["MultiMaps"]),
    # ---------------- 气候（Theater）文件 ----------------
    # 特征是每个文件都带有 [General] 且包含 RampBase / ClearTile / CliffSet 等
    # 但是 [General] 在 rules 里也有，所以优先用独有的 [TileSet0000] 等节识别。
    ("theater", [
        "TileSet0000", "TileSet0001",
    ]),

    # ---------------- 战役地图相关（battle/mapsel/mission） ----------------
    # battlemd.ini 有 [Battles]
    # mapselmd.ini 有 [GDI]、[Nod] 加 [ALL00]~[ALL07]、[Sov01]~[Sov07]
    # missionmd.ini 是 [*.MAP] 形式的节，用带 .MAP 后缀的节特征不好写在签名里，
    # 因此用几个共有特征节：[ALL01] / [Sov01] / [C1A01MD.MAP] 之类
    ("mission", [
        "Battles",     # battlemd.ini
        # mapselmd.ini
        "ALL00", "ALL01", "Sov01",
    ]),

    # ---------------- UI 文件 ----------------
    # uimd.ini 有 [AdvancedCommandBar]、[MultiplayerAdvancedCommandBar]
    ("ui", [
        "AdvancedCommandBar",
        "MultiplayerAdvancedCommandBar",
    ]),

    # rules.ini / rulesmd.ini 的核心特征
    ("rules", [
        "General", "AudioVisual", "CombatDamage", "CrateRules",
        "Radiation", "ElevationModel", "WallModel",
        "MultiplayerDialogSettings", "Maximums", "AI", "IQ",
        "InfantryTypes", "VehicleTypes", "AircraftTypes",
        "BuildingTypes", "TerrainTypes", "SmudgeTypes",
        "OverlayTypes", "Animations", "VoxelAnims",
        "Particles", "ParticleSystems",
        "SuperWeaponTypes", "Warheads",
        "Countries", "Sides", "Colors", "ColorAdd",
        "VariableNames",
        "JumpjetControls", "SpecialWeapons",
    ]),

    ("art", [
        "Movies",
    ]),

    ("ai", [
        "TaskForces", "TeamTypes", "ScriptTypes", "AITriggerTypes",
        "Actions", "Events", "Scripts"
    ]),

    ("eva", [
        "DialogList", "EVA_Base", "EVA_Allied", "EVA_Soviet", "EVA_Yuri"
    ]),

    ("sound", [
        "SoundList", "DialogList", "MusicList", "AmbientList"
    ]),
]

# 辅助判据：art.ini 里绝大多数节只有图像相关字段；
# 下面这些键只要出现在某一个节里，就强指向 art。
ART_ONLY_KEYS = {
    "cameo", "altcameo", "voxel", "remapable",
    "normalized", "theater", "newtheater",
    "rotcount", "shadowindex", "turretoffset",
    "fireangle", "barrellength",
    "primaryfireflh", "secondaryfireflh",
    "eliteprimaryfireflh", "elitesecondaryfireflh",
    "sequence", "crawls", "fireup", "fireprone",
    "visibleload", "useturretshadow",
    "foundation", "height", "occupyheight",
    "canhidthings", "canbehidden",
    "addoccupy1", "removeoccupy1",
    "primaryfirepixeloffset", "secondaryfirepixeloffset",
    "simpledamage", "buildup", "auxanim", "altimage",
    "chargeanim", "silodamage", "flat", "recoilless",
    "tooverlay", "damagelevels",
    "activeanim", "activeanimdamaged",
    "idleanim", "idleanimdamaged",
    "specialanim", "productionanim",
    "superanim", "superanimtwo",
    "layer", "loopstart", "loopend", "loopcount",
    "rate", "start", "end",
    "report",  # art 里的 Report 用于动画声音；rules 里武器也用 Report，所以仅当键很少时参考
}

# 辅助判据：rules.ini 里独有的键
RULES_ONLY_KEYS = {
    "cost", "strength", "armor", "sight", "speed",
    "owner", "prerequisite", "techlevel",
    "primary", "secondary",
    "veteranabilities", "eliteabilities",
    "locomotor", "movementzone",
    "crushsound", "dieSound",
    "pip", "pipscale", "pipwrap",
    "category", "points", "soylent",
    "power", "capturable", "factory",
    "harvester", "refinery",
    "voiceselect", "voicemove", "voiceattack",
}

# 注册列表定义: {节名: (显示名称, 值说明)}
REGISTRY_SECTIONS = {
    "Countries":        ("国家注册列表",   "国家/阵营"),
    "Sides":            ("阵营注册列表",   "阵营"),
    "InfantryTypes":    ("步兵注册列表",   "步兵"),
    "VehicleTypes":     ("载具注册列表",   "载具"),
    "AircraftTypes":    ("飞行器注册列表", "飞行器"),
    "BuildingTypes":    ("建筑注册列表",   "建筑"),
    "TerrainTypes":     ("地形对象注册列表", "地形对象"),
    "SmudgeTypes":      ("污染物注册列表", "污染物"),
    "OverlayTypes":     ("覆盖图注册列表", "覆盖图"),
    "Animations":       ("动画注册列表",   "动画"),
    "VoxelAnims":       ("模型动画注册列表", "模型动画"),
    "SuperWeaponTypes": ("超级武器注册列表", "超级武器"),
    "Warheads":         ("弹头注册列表",   "弹头"),
    "Particles":        ("粒子注册列表",   "粒子"),
    "ParticleSystems":  ("粒子系统注册列表",   "粒子系统"),
    "Colors":           ("所属色注册列表",   "所属色"),
    "ColorAdd":         ("物体变色注册列表", "变色效果"),
    "VariableNames":    ("全局变量注册列表", "全局变量"),
    "Movies":           ("过场视频注册列表", "过场视频"),
    "TaskForces":       ("特遣部队注册列表", "特遣部队"),
    "TeamTypes":        ("作战小队注册列表", "作战小队"),
    "SoundList":        ("音效注册列表",   "音效"),
    "DialogList":       ("语音注册列表",   "语音"),
    "Themes":           ("主题音乐注册列表", "主题音乐"),
    "MultiMaps":        ("多人地图注册列表", "地图文件"),
}

# 这些注册表用「键」代表节名（其余用「值」代表节名）
REGISTRY_KEY_AS_NAME = {"Sides", "Colors", "ColorAdd"}

# 说明文件名（放在脚本同目录下会被自动加载）
EXPLANATION_FILE = "rules_explanation.txt"
GENERAL_FILE     = "general_explanation.txt"
WEAPONS_FILE     = "weapons_explanation.txt"
SECTIONS_FILE    = "sections_explanation.txt"
OTHERS_FILE      = "others_explanation.txt"
ARTS_FILE        = "arts_explanation.txt"
AI_FILE          = "ai_explanation.txt"
ARES_FILE        = "ares_explanation.txt"

# ==================== 自动保存配置 ====================
AUTOSAVE_INTERVAL_MS = 3 * 60 * 1000     # 3 分钟
AUTOSAVE_MAX_FILES   = 5                 # 最多保留 5 个副本
AUTOSAVE_DIR_NAME    = "saves"           # 存放在项目根目录下的 saves/
AUTOSAVE_PREFIX      = "autosave_"       # 文件名前缀
