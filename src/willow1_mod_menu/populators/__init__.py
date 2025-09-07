import re
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field

from unrealsdk import logging
from unrealsdk.unreal import UObject

from mods_base import (
    BaseOption,
    BoolOption,
    DropdownOption,
    KeybindOption,
    SliderOption,
    SpinnerOption,
)
from willow1_mod_menu.util import WillowGFxMenu, find_focused_item

type WillowGFxLobbyTools = UObject
type WillowGFxMenuScreenFrameKeyBinds = UObject

LOCKED_KEY_PREFIX = "!LOCKED!"

RE_INVALID_SPINNER_CHARS = re.compile("[:,]")


@dataclass
class Populator(ABC):
    title: str
    drawn_options: list[BaseOption] = field(
        init=False,
        repr=False,
        default_factory=list[BaseOption],
    )
    drawn_keybinds: list[KeybindOption | None] = field(
        init=False,
        repr=False,
        default_factory=list[KeybindOption | None],
    )

    @abstractmethod
    def populate(self, tools: WillowGFxLobbyTools) -> None:
        """
        Populates the menu with the appropriate options.

        Args:
            tools: The lobby tools which may be used to add to the menu.
        """
        raise NotImplementedError

    @abstractmethod
    def handle_activate(self, menu: WillowGFxMenu, option: BaseOption) -> None:
        """
        Handles an option being activated.

        Args:
            menu: The currently open menu.
            option: The option which was activate.
        """
        raise NotImplementedError

    def populate_keybinds(self, kb_frame: WillowGFxMenuScreenFrameKeyBinds) -> None:
        """
        Populates the menu with the appropriate keybinds.

        Args:
            kb_frame: The keybinds frame object which may be used to add binds.
        """
        raise NotImplementedError

    def handle_reset_keybinds(self) -> None:
        """Handles the reset keybind menu being activated."""
        raise NotImplementedError

    # ==============================================================================================

    def draw_text(self, tools: WillowGFxLobbyTools, text: str, option: BaseOption) -> None:
        """
        Adds a line of text to the menu.

        Args:
            tools: The lobby tools which may be used to add to the menu.
            text: The text to display.
            option: The option associated with this text, to be passed back to the callback.
        """
        tools.menuAddItem(0, text)
        self.drawn_options.append(option)

    def draw_spinner(
        self,
        tools: WillowGFxLobbyTools,
        name: str,
        current_choice: str,
        choices: Sequence[str],
        option: BaseOption,
    ) -> None:
        """
        Adds a spinner to the menu.

        Args:
            tools: The lobby tools which may be used to add to the menu.
            name: The name of the spinner.
            current_choice: The choice that should be initially selected.
            choices: The list of all choices.
            option: The option associated with this spinner, to be passed back to the callback.
        """
        config_str = ""
        for idx, choice in enumerate(choices):
            cleaned_choice = RE_INVALID_SPINNER_CHARS.sub(" ", choice)
            if choice != cleaned_choice:
                logging.dev_warning(
                    f"'{choice}' contains characters which are invalid for a spinner choice in"
                    f" willow1-mod-menu",
                )

            config_str += f"{idx}:{cleaned_choice},"

        try:
            config_str += str(choices.index(current_choice))
        except ValueError:
            logging.warning(
                f"Cannot make spinner select value of '{current_choice}' since it's an invalid"
                f" choice!",
            )
            config_str += "0"

        tools.menuAddSpinner(
            name,
            "",
            config_str,
        )
        self.drawn_options.append(option)

    @staticmethod
    def format_slider_label(option: SliderOption) -> str:
        """
        Combines a slider name and value into a single label string.

        Args:
            option: The slider to format a label for.
        Returns:
            The formatted label.
        """
        value = option.value
        if option.is_integer:
            value = round(value)

        return f"{option.display_name}: {value:g}"

    def draw_slider(
        self,
        tools: WillowGFxLobbyTools,
        option: SliderOption,
    ) -> None:
        """
        Adds a slider to the menu.

        Args:
            tools: The lobby tools which may be used to add to the menu.
            option: The slider option to get all the details from, and to be passed to the callback.
        """
        tools.menuAddSlider(
            self.format_slider_label(option),
            "",
            f"Min:{option.min_value},Max:{option.max_value},Step:{option.step},Value:{option.value}",
        )
        self.drawn_options.append(option)

    def is_slider(self, idx: int) -> bool:
        """
        Checks if the option drawn at a given index is a slider.

        Args:
            idx: The index to check.
        Returns:
            True if the option is a slider.
        """
        try:
            return isinstance(self.drawn_options[idx], SliderOption)
        except IndexError:
            return False

    def on_activate(self, menu: WillowGFxMenu, idx: int) -> None:
        """
        Handles a raw menu item activation.

        Args:
            menu: The currently open menu.
            idx: The index of the item which was activated.
        """
        try:
            option = self.drawn_options[idx]
        except IndexError:
            logging.error(f"Can't find option which was changed at index {idx}")
            return

        self.handle_activate(menu, option)

    def on_spinner_change(self, menu: WillowGFxMenu, idx: int, choice_idx: int) -> None:
        """
        Handles a raw spinner change.

        Args:
            menu: The currently open menu.
            idx: The index of the item which was activated.
            choice_idx: The newly selected choice's index.
        """
        _ = menu
        try:
            option = self.drawn_options[idx]
        except IndexError:
            logging.error(f"Can't find option which was changed at index {idx}")
            return

        match option:
            case BoolOption():
                option.value = bool(choice_idx)
            case DropdownOption() | SpinnerOption():
                option.value = option.choices[choice_idx]
            case _:
                logging.error(
                    f"Option '{option.identifier}' got a spinner change event despite not being a"
                    " spinner",
                )

    def on_slider_change(self, menu: WillowGFxMenu, idx: int, value: float) -> None:
        """
        Handles a raw slider change.

        Args:
            menu: The currently open menu.
            idx: The index of the item which was activated.
            value: The new value of the slider.
        """
        _ = menu
        try:
            option = self.drawn_options[idx]
        except IndexError:
            logging.error(f"Can't find option which was changed at index {idx}")
            return

        if not isinstance(option, SliderOption):
            logging.error(
                f"Option '{option.identifier}' got a spinner change event despite not being a"
                " spinner",
            )
            return

        if option.is_integer:
            value = round(value)

        option.value = value

        menu.SetVariableString(
            find_focused_item(menu) + ".mLabel.text",
            self.format_slider_label(option),
        )

    def draw_keybind(
        self,
        kb_frame: WillowGFxMenuScreenFrameKeyBinds,
        name: str,
        key: str | None = None,
        is_rebindable: bool = True,
        option: KeybindOption | None = None,
    ) -> None:
        """
        Adds an individual keybind to the menu.

        Args:
            kb_frame: The keybinds frame object to add to.
            name: The name of the bind.
            key: The key the bind is bound to.
            is_rebindable: True if the key is rebindable.
            option: The option to use during the callback, or None.
        """
        kb_frame.ActiveItems.emplace_struct(Caption=name)

        key_list: list[str]
        if key is None:
            key_list = [] if is_rebindable else [LOCKED_KEY_PREFIX]
        else:
            key_list = [key] if is_rebindable else [LOCKED_KEY_PREFIX + key]

        kb_frame.Keybinds.emplace_struct(Keys=key_list)

        self.drawn_keybinds.append(option)

    def may_bind_key(self, idx: int) -> bool:
        """
        Checks if we're allowed to bind the given key.

        Args:
            idx: The index of the key to check.
        Returns:
            True if we're allowed to bind this key index.
        """
        try:
            option = self.drawn_keybinds[idx]
        except IndexError:
            return False

        if option is None:
            return False

        return option.is_rebindable

    def on_bind_key(self, kb_frame: WillowGFxMenuScreenFrameKeyBinds, idx: int, key: str) -> None:
        """
        Handles a raw key bind event.

        Args:
            kb_frame: The keybinds frame object to update with the new key.
            idx: The index of the key which was bound.
            key: The new value the key was requested to be set to.
        """
        try:
            option = self.drawn_keybinds[idx]
        except IndexError:
            return
        if option is None or not option.is_rebindable:
            return

        if key == option.value:
            option.value = None
        else:
            option.value = key

        kb_frame.Keybinds[idx].Keys = [] if option.value is None else [option.value]

    def on_reset_keybinds(self, kb_frame: WillowGFxMenuScreenFrameKeyBinds) -> None:
        """
        Handles a raw reset keybinds event.

        Args:
            kb_frame: The keybinds frame object to update with the new key.
        """
        self.handle_reset_keybinds()

        keybinds = kb_frame.Keybinds
        for idx, option in enumerate(self.drawn_keybinds):
            if option is None:
                continue
            keybinds[idx].Keys = [] if option.value is None else [option.value]

        kb_frame.ApplyPageContent()
