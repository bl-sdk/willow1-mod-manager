from collections.abc import Iterator, Sequence
from dataclasses import KW_ONLY, dataclass, field
from typing import override

from mods_base import (
    BaseOption,
    BoolOption,
    ButtonOption,
    GroupedOption,
    KeybindOption,
    Mod,
    NestedOption,
    html_to_plain_text,
)
from ui_utils import TrainingBox
from willow1_mod_menu.options import create_keybinds_menu

from . import WillowGFxMenu, WillowGFxMenuScreenFrameKeyBinds
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

    @override
    def handle_activate(self, menu: WillowGFxMenu, option: BaseOption) -> None:
        match option:
            case KeybindMenuProxyOption():
                create_keybinds_menu(menu)
            case _:
                super().handle_activate(menu, option)

    @override
    def populate_keybinds(self, kb_frame: WillowGFxMenuScreenFrameKeyBinds) -> None:
        self.drawn_keybinds.clear()

        # A bunch of code assumes index 0 = rebind, so might as well follow that
        self.draw_keybind(
            kb_frame,
            kb_frame.Localize("MessageBox", "ResetToDefaults_Title", "WillowGame"),
        )
        self.add_keybinds_list(kb_frame, self.options, [])

    @override
    def handle_reset_keybinds(self) -> None:
        self.reset_keybinds_list(self.options)

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

        display_options = tuple(self.mod.iter_display_options())

        if self.any_keybind_visible(display_options):
            option = KeybindMenuProxyOption("Keybinds")
            option.mod = self.mod
            yield option

        yield from display_options

    @staticmethod
    def any_keybind_visible(options: Sequence[BaseOption]) -> bool:
        """
        Recursively checks if any keybind option in a sequence is visible.

        Recurses into grouped and nested options. A grouped or nested option which is not explicitly
        hidden, but contains no visible children, does not count as visible.

        Args:
            options: The list of options to check.
        """
        return any(
            (
                isinstance(option, GroupedOption | NestedOption)
                and not option.is_hidden
                and ModOptionPopulator.any_keybind_visible(option.children)
            )
            or (isinstance(option, KeybindOption) and not option.is_hidden)
            for option in options
        )

    def add_keybinds_list(
        self,
        kb_frame: WillowGFxMenuScreenFrameKeyBinds,
        options: Sequence[BaseOption],
        group_stack: list[GroupedOption | NestedOption],
    ) -> None:
        """
        Adds a list of keybinds to the current menu.

        Args:
            kb_frame: The keybinds frame object to add to.
            options: The list of options containing the keybinds to add.
            group_stack: The stack of currently open grouped/nested options. Should start out empty.
        """
        for options_idx, option in enumerate(options):
            if option.is_hidden:
                continue

            match option:
                case KeybindOption():
                    caption = ("  " if group_stack else "") + option.display_name
                    self.draw_keybind(kb_frame, caption, option.value, option.is_rebindable, option)

                # This is the same sort of logic as grouped options in add_options_list
                case GroupedOption() | NestedOption() if self.any_keybind_visible(option.children):
                    group_stack.append(option)

                    if len(option.children) == 0 or not (
                        isinstance(option.children[0], GroupedOption | NestedOption)
                    ):
                        caption = " - ".join(g.display_name for g in group_stack)
                        self.draw_keybind(kb_frame, caption)

                    self.add_keybinds_list(
                        kb_frame,
                        option.children,
                        group_stack,
                    )

                    group_stack.pop()

                    if (
                        group_stack
                        and options_idx != len(options) - 1
                        and self.any_keybind_visible(options[options_idx + 1 :])
                        and not isinstance(options[options_idx + 1], GroupedOption | NestedOption)
                    ):
                        caption = " - ".join(g.display_name for g in group_stack)
                        self.draw_keybind(kb_frame, caption)

                case _:
                    pass

    @staticmethod
    def reset_keybinds_list(options: Sequence[BaseOption]) -> None:
        """
        Recursively resets all keybinds in the given options list.

        Args:
            options: The options list to reset.
        """
        for option in options:
            match option:
                case KeybindOption():
                    option.value = option.default_value
                case GroupedOption() | NestedOption():
                    ModOptionPopulator.reset_keybinds_list(option.children)
                case _:
                    pass
