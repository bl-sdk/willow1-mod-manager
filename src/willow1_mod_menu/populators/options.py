import re
from collections.abc import Sequence
from dataclasses import dataclass, field

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

from . import Populator, WillowGFxLobbyTools

RE_INVALID_SPINNER_CHARS = re.compile("[:,]")


@dataclass
class OptionPopulator(Populator):
    options: Sequence[BaseOption]

    drawn_options: list[BaseOption] = field(
        init=False,
        repr=False,
        default_factory=list[BaseOption],
    )

    @override
    def populate(self, tools: WillowGFxLobbyTools) -> None:
        self.drawn_options.clear()
        self.add_option_list(tools, self.options, [])

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

        tools.menuAddItem(0, desc_name)
        self.drawn_options.append(
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
            tools.menuAddItem(0, " - ".join(g.display_name for g in group_stack))
            self.drawn_options.append(option)
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
            tools.menuAddItem(0, " - ".join(g.display_name for g in group_stack))
            self.drawn_options.append(group_stack[-1])
            self.add_description_if_required(tools, group_stack, group_stack[-1])

    def add_spinner_option(
        self,
        tools: WillowGFxLobbyTools,
        option_name: str,
        current_choice: str,
        choices: Sequence[str],
    ) -> None:
        """
        Adds a spinner option to the current menu.

        Args:
            tools: The lobby tools which may be used to add to the menu.
            option_name: The name to use for the spinner.
            current_choice: The choice which is currently selected.
            choices: The lis of allowed choices.
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

        tools.menuAddSpinner(option_name, "dummy_spinner_tag", config_str)

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

            # Grouped options are a little more complex, they handle this manually
            if not isinstance(option, GroupedOption):
                self.drawn_options.append(option)

            # If we're in any group, we indent the names slightly to distinguish them from the
            # headers
            option_name = ("  " if group_stack else "") + option.display_name

            match option:
                case ButtonOption() | NestedOption():
                    tools.menuAddItem(0, option_name)

                case BoolOption():
                    self.add_spinner_option(
                        tools,
                        option_name,
                        (choices := [option.false_text or "Off", option.true_text or "On"])[
                            option.value
                        ],
                        choices,
                    )

                case DropdownOption() | SpinnerOption():
                    self.add_spinner_option(
                        tools,
                        option_name,
                        option.value,
                        option.choices,
                    )

                case SliderOption():
                    tools.menuAddSlider(
                        option_name,
                        "dummy_slider_tag",
                        (
                            f"Min:{option.min_value},"
                            f"Max:{option.max_value},"
                            f"Step:{option.step},"
                            f"Value:{option.value}"
                        ),
                    )

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
