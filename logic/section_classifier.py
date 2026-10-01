"""判断某个节是弹头 / 武器 / 抛射体。

判定规则：
- 弹头：出现在 [Warheads] 注册列表里
- 武器：节里同时有 Damage= 和 Range=
- 抛射体：被某个武器节的 Projectile= 指向
"""


class SectionClassifier:
    """节类别判定器。持有 IniParser 实例，内部对抛射体集合做缓存。"""

    WARHEAD    = 'warhead'
    WEAPON     = 'weapon'
    PROJECTILE = 'projectile'

    def __init__(self, parser):
        self.parser = parser
        self._projectile_set_cache = None
        self._particle_set_cache = None

    def invalidate(self):
        """数据变了之后清空缓存。"""
        self._projectile_set_cache = None

    def is_warhead(self, section_name):
        if "Warheads" not in self.parser.sections:
            return False
        for _, value in self.parser.get_items("Warheads"):
            if value.strip() == section_name:
                return True
        return False

    def is_weapon(self, section_name):
        items = self.parser.get_items(section_name)
        keys = {k.lower() for k, _ in items}
        return ('damage' in keys) and ('range' in keys)

    def get_weapon_projectile(self, section_name):
        for key, value in self.parser.get_items(section_name):
            if key.lower() == 'projectile':
                return value.strip()
        return None

    def _build_projectile_set(self):
        if self._projectile_set_cache is not None:
            return self._projectile_set_cache
        s = set()
        for sec in self.parser.get_sections():
            if not self.is_weapon(sec):
                continue
            proj = self.get_weapon_projectile(sec)
            if proj:
                s.add(proj)
        self._projectile_set_cache = s
        return s

    def is_projectile(self, section_name):
        return section_name in self._build_projectile_set()

    def classify(self, section_name):
        # 先判断粒子系统 / 粒子（这两类特征明确，优先）
        if self.is_particle_system(section_name):
            return 'particle_system'
        if self.is_particle(section_name):
            return 'particle'
        # 原有判断
        if self.is_warhead(section_name):
            return self.WARHEAD
        if self.is_weapon(section_name):
            return self.WEAPON
        if self.is_projectile(section_name):
            return self.PROJECTILE
        return None
    def is_particle_system(self, section_name):
        """有 HoldsWhat= 或 BehavesLike= 就是粒子系统。"""
        items = self.parser.get_items(section_name)
        keys = {k.lower() for k, _ in items}
        return ('holdswhat' in keys) or ('behaveslike' in keys)

    def is_particle(self, section_name):
        """节名被某个粒子系统节的 HoldsWhat= 引用，就是粒子。"""
        target = section_name
        for sec in self.parser.get_sections():
            items = self.parser.get_items(sec)
            keys = {k.lower() for k, _ in items}
            if 'holdswhat' not in keys:
                continue
            for k, v in items:
                if k.lower() == 'holdswhat':
                    # HoldsWhat 可能是 "A,B,C" 形式
                    names = [x.strip() for x in v.split(',') if x.strip()]
                    if target in names:
                        return True
        return False
