from collections.abc import Sequence
from dataclasses import dataclass

from unrealsdk import logging

from mods_base import (
    BaseOption,
    BoolOption,
    ButtonOption,
    DropdownOption,
    GroupedOption,
    KeybindOption,
    NestedOption,
    SliderOption,
    SpinnerOption,
)

try:
    from ui_utils import TrainingBox
except ImportError:
    TrainingBox = None
from typing import override

from willow1_mod_menu.options import create_nested_options_menu

from . import Populator, WillowGFxLobbyTools, WillowGFxMenu


@dataclass
class OptionPopulator(Populator):
    options: Sequence[BaseOption]

    @override
    def populate(self, tools: WillowGFxLobbyTools) -> None:
        self.drawn_options.clear()
        self.add_option_list(tools, self.options, [])

    @override
    def handle_activate(self, menu: WillowGFxMenu, option: BaseOption) -> None:
        match option:
            case ButtonOption():
                if option.on_press:
                    option.on_press(option)
            case NestedOption():
                create_nested_options_menu(menu, option)
            case GroupedOption():
                pass
            case _:
                logging.error(
                    f"Option '{option.identifier}' of unknown type {type(option)} was unexpectedly"
                    f" activated",
                )

    @staticmethod
    def any_option_visible(options: Sequence[BaseOption]) -> bool:
        """
        Recursively checks if any option in a sequence is visible.

        Recurses into grouped options, but not nested ones. A grouped option which is not explicitly
        hidden, but contains no visible children, does not count as visible.

        Keybind options are always treated as hidden.

        Args:
            options: The list of options to check.
        """
        return any(
            (
                isinstance(option, GroupedOption)
                and not option.is_hidden
                and OptionPopulator.any_option_visible(option.children)
            )
            or (not isinstance(option, KeybindOption) and not option.is_hidden)
            for option in options
        )

    def add_description_if_required(
        self,
        tools: WillowGFxLobbyTools,
        group_stack: list[GroupedOption],
        option: BaseOption,
    ) -> None:
        """
        Adds an extra option to hold the description of a previous one, if applicable.

        Args:
            tools: The lobby tools which may be used to add to the menu.
            group_stack: The stack of currently open grouped options.
            option: The option to add a description of.
        """
        if not option.description or TrainingBox is None:
            return

        # Indent if we're in the middle of a group, and not adding to a group header
        desc_name = (
            "  " if group_stack and not isinstance(option, GroupedOption) else ""
        ) + "(...)"

        self.draw_text(
            tools,
            desc_name,
            ButtonOption(
                desc_name,
                on_press=lambda _: (
                    None
                    if TrainingBox is None
                    else TrainingBox(
                        title=option.description_title,
                        message=option.description,
                    ).show()
                ),
            ),
        )

    def add_grouped_option(
        self,
        tools: WillowGFxLobbyTools,
        options: Sequence[BaseOption],
        group_stack: list[GroupedOption],
        option: GroupedOption,
        options_idx: int,
    ) -> None:
        """
        Adds a grouped option to the current menu.

        Args:
            tools: The lobby tools which may be used to add to the menu.
            options: The full options list this group is part of.
            group_stack: The stack of currently open grouped options.
            option: The specific grouped option to add.
            options_idx: The index of the specific grouped option being added.
        """
        if not self.any_option_visible(option.children):
            return

        group_stack.append(option)

        # If the first entry of the group is another group, don't draw a title, let the nested call
        # do it, so the first title is the most nested
        # If we're empty, or a different type, draw our own header
        if len(option.children) == 0 or not isinstance(option.children[0], GroupedOption):
            self.draw_text(tools, " - ".join(g.display_name for g in group_stack), option)
            self.add_description_if_required(tools, group_stack, option)

        self.add_option_list(tools, option.children, group_stack)

        group_stack.pop()

        # If we didn't just close the outermost group, the group above us still has extra visible
        # options, and the next one of those options is not another group, re-draw the outer group's
        # header
        if (
            group_stack
            and options_idx != len(options) - 1
            and self.any_option_visible(options[options_idx + 1 :])
            and not isinstance(options[options_idx + 1], GroupedOption)
        ):
            self.draw_text(tools, " - ".join(g.display_name for g in group_stack), group_stack[-1])
            self.add_description_if_required(tools, group_stack, group_stack[-1])

    def add_option_list(  # noqa: C901 - can't really simplify, each case is one statement
        self,
        tools: WillowGFxLobbyTools,
        options: Sequence[BaseOption],
        group_stack: list[GroupedOption],
    ) -> None:
        """
        Adds a list of options to the current menu.

        Args:
            tools: The lobby tools which may be used to add to the menu.
            options: The list of options to add.
            group_stack: The stack of currently open grouped options. Should start out empty.
        """
        for options_idx, option in enumerate(options):
            if option.is_hidden:
                continue

            # If we're in any group, we indent the names slightly to distinguish them from the
            # headers
            option_name = ("  " if group_stack else "") + option.display_name

            match option:
                case ButtonOption() | NestedOption():
                    self.draw_text(tools, option_name, option)

                case BoolOption():
                    self.draw_spinner(
                        tools,
                        option_name,
                        (choices := [option.false_text or "Off", option.true_text or "On"])[
                            option.value
                        ],
                        choices,
                        option,
                    )

                case DropdownOption() | SpinnerOption():
                    self.draw_spinner(
                        tools,
                        option_name,
                        option.value,
                        option.choices,
                        option,
                    )

                case SliderOption():
                    self.draw_slider(tools, option)

                case GroupedOption() if option in group_stack:
                    logging.dev_warning(f"Found recursive options group, not drawing: {option}")
                case GroupedOption():
                    self.add_grouped_option(
                        tools,
                        options,
                        group_stack,
                        option,
                        options_idx,
                    )

                case KeybindOption():
                    pass

                case _:
                    logging.dev_warning(f"Encountered unknown option type {type(option)}")

            # Again grouped options handle this themselves
            if not isinstance(option, GroupedOption):
                self.add_description_if_required(tools, group_stack, option)
