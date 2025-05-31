import re
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field

from unrealsdk import logging
from unrealsdk.unreal import UObject

from mods_base import BaseOption, BoolOption, DropdownOption, SliderOption, SpinnerOption

type WillowGFxMenu = UObject
type WillowGFxLobbyTools = UObject


RE_INVALID_SPINNER_CHARS = re.compile("[:,]")


@dataclass
class Populator(ABC):
    title: str
    drawn_options: dict[str, BaseOption] = field(
        init=False,
        repr=False,
        default_factory=dict[str, BaseOption],
    )

    @abstractmethod
    def populate(self, tools: WillowGFxLobbyTools) -> None:
        """
        Populates the menu with the appropriate contents.

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

    # ==============================================================================================

    def _get_next_tag(self, option: BaseOption) -> str:
        return f"willow1-mod-menu:{len(self.drawn_options)}:{option.identifier}"

    def draw_text(self, tools: WillowGFxLobbyTools, text: str, option: BaseOption) -> None:
        """
        Adds a line of text to the menu.

        Args:
            tools: The lobby tools which may be used to add to the menu.
            text: The text to display.
            option: The option associated with this text, to be passed back to the callback.
        """
        tag = self._get_next_tag(option)
        tools.menuAddItem(0, text, tag, "extKeybinds")
        self.drawn_options[tag] = option

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

        tag = self._get_next_tag(option)
        tools.menuAddSpinner(
            name,
            tag,
            config_str,
            "Change:extSpinnerChanged",
        )
        self.drawn_options[tag] = option

    def draw_slider(
        self,
        tools: WillowGFxLobbyTools,
        name: str,
        value: float,
        min_value: float,
        max_value: float,
        step: float,
        option: BaseOption,
    ) -> None:
        """
        Adds a slider to the menu.

        Args:
            tools: The lobby tools which may be used to add to the menu.
            name: The name of the slider.
            value: The slider's current value.
            min_value: The slider's min allowed value.
            max_value: The slider's max allowed value.
            step: The slider's step.
            option: The option associated with this slider, to be passed back to the callback
        """
        tag = self._get_next_tag(option)
        tools.menuAddSlider(
            name,
            tag,
            f"Min:{min_value},Max:{max_value},Step:{step},Value:{value}",
            "Change:extSliderChanged",
        )
        self.drawn_options[tag] = option

    def on_activate(self, menu: WillowGFxMenu, tag: str) -> None:
        """
        Handles a raw menu item activation.

        Args:
            menu: The currently open menu.
            tag: The tag of the item which was activated.
        """
        if (option := self.drawn_options.get(tag)) is None:
            logging.error(f"Can't find option '{tag}' which was changed")
            return

        self.handle_activate(menu, option)

    def on_spinner_change(self, menu: WillowGFxMenu, tag: str, idx: int) -> None:
        """
        Handles a raw spinner change.

        Args:
            menu: The currently open menu.
            tag: The tag of the item which was activated.
            idx: The newly selected choice's index.
        """
        _ = menu

        if (option := self.drawn_options.get(tag)) is None:
            logging.error(f"Can't find option '{tag}' which was changed")
            return

        match option:
            case BoolOption():
                option.value = bool(idx)
            case DropdownOption() | SpinnerOption():
                option.value = option.choices[idx]
            case _:
                logging.error(
                    f"Option '{option.identifier}' got a spinner change event despite not being a"
                    " spinner",
                )

    def on_slider_change(self, menu: WillowGFxMenu, tag: str, value: float) -> None:
        """
        Handles a raw slider change.

        Args:
            menu: The currently open menu.
            tag: The tag of the item which was activated.
            value: The new value of the slider.
        """
        _ = menu

        if (option := self.drawn_options.get(tag)) is None:
            logging.error(f"Can't find option '{tag}' which was changed")
            return
        if not isinstance(option, SliderOption):
            logging.error(
                f"Option '{option.identifier}' got a spinner change event despite not being a"
                " spinner",
            )
            return

        option.value = value
