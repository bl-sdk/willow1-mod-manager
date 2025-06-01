from dataclasses import dataclass
from types import EllipsisType
from typing import override

from mods_base import JSON, BaseOption, get_ordered_mod_list, html_to_plain_text
from willow1_mod_menu.options import create_mod_options_menu

from . import Populator, WillowGFxLobbyTools, WillowGFxMenu


@dataclass
class ModProxyOption(BaseOption):
    @override
    def _to_json(self) -> EllipsisType:
        return ...

    @override
    def _from_json(self, value: JSON) -> None:
        pass


@dataclass
class ModListPopulator(Populator):
    @override
    def populate(self, tools: WillowGFxLobbyTools) -> None:
        self.drawn_options.clear()

        for mod in get_ordered_mod_list():
            opt = ModProxyOption(mod.name)
            opt.mod = mod
            self.draw_text(tools, html_to_plain_text(mod.name), opt)

    @override
    def handle_activate(self, menu: WillowGFxMenu, option: BaseOption) -> None:
        assert option.mod is not None
        create_mod_options_menu(menu, option.mod)
