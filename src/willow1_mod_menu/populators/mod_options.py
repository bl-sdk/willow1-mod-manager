from dataclasses import dataclass

from mods_base import Mod

from .options import OptionPopulator


@dataclass
class ModOptionPopulator(OptionPopulator):
    mod: Mod
