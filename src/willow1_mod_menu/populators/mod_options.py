from collections.abc import Iterator, Sequence
from dataclasses import KW_ONLY, dataclass, field
from typing import override

from mods_base import BaseOption, BoolOption, ButtonOption, Mod, html_to_plain_text
from ui_utils import TrainingBox

from . import WillowGFxMenu
from .options import OptionPopulator

try:
    from ui_utils import TrainingBox
except ImportError:
    TrainingBox = None


@dataclass
class KeybindMenuProxyOption(ButtonOption):
    pass


@dataclass
class ModOptionPopulator(OptionPopulator):
    options: Sequence[BaseOption] = field(default_factory=tuple, init=False)
    _: KW_ONLY
    mod: Mod

    def __post_init__(self) -> None:
        self.options = tuple(self.gen_options_list())

    def gen_options_list(self) -> Iterator[BaseOption]:
        """
        Generates the outermost set of options to display.

        Yields:
            The options to display.
        """
        description = html_to_plain_text(self.mod.description)
        if description and TrainingBox is not None:
            yield ButtonOption(
                "Description",
                on_press=lambda _: (
                    None
                    if TrainingBox is None
                    else TrainingBox(
                        title=html_to_plain_text(self.mod.name),
                        message=description,
                    ).show()
                ),
            )

        if not self.mod.enabling_locked:
            yield BoolOption(
                "Enabled",
                self.mod.is_enabled,
                on_change=lambda _, now_enabled: (
                    self.mod.enable() if now_enabled else self.mod.disable()
                ),
            )

        if self.mod.keybinds:
            option = KeybindMenuProxyOption("Keybinds")
            option.mod = self.mod
            yield option

        yield from self.mod.iter_display_options()

    @override
    def handle_activate(self, menu: WillowGFxMenu, option: BaseOption) -> None:
        match option:
            case KeybindMenuProxyOption():
                print("TODO keybinds menu")
            case _:
                super().handle_activate(menu, option)
