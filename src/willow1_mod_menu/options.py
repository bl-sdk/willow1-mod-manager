# ruff: noqa: D103
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import unrealsdk
from unrealsdk.hooks import Block, Type
from unrealsdk.unreal import BoundFunction, UFunction, UObject, WrappedStruct

from mods_base import Mod, NestedOption, hook, html_to_plain_text

from .lobby import open_lobby_mods_menu
from .util import find_focused_item

if TYPE_CHECKING:
    from .populators import Populator
    from .util import WillowGFxMenu

CUSTOM_OPTIONS_MENU_TAG = "willow1-mod-menu:custom-option"
RE_SELECTED_IDX = re.compile(r"^_level\d+\.(menu\.selections|content)\.mMenu\.mList\.item(\d+)$")

populator_stack: list[Populator] = []


def create_mod_list_options_menu(menu: WillowGFxMenu) -> None:
    """
    Creates a new menu holding the full mods list.

    Args:
        menu: The current menu to create the new one under.
    """
    populator_stack.append(ModListPopulator("Mods"))
    open_new_generic_menu(menu)


def create_mod_options_menu(menu: WillowGFxMenu, mod: Mod) -> None:
    """
    Creates a new menu holding a single mod's options.

    Args:
        menu: The current menu to create the new one under.
        mod: The mod to create the options menu for.
    """
    populator_stack.append(ModOptionPopulator(mod.name, mod=mod))
    open_new_generic_menu(menu)


def create_nested_options_menu(menu: WillowGFxMenu, option: NestedOption) -> None:
    """
    Creates a new menu holding a nested option's children.

    Args:
        menu: The current menu to create the new one under.
        option: The options whose children to create a menu for.
    """
    populator_stack.append(OptionPopulator(option.display_name, option.children))
    open_new_generic_menu(menu)


# ==================================================================================================

# Avoid circular imports
from .populators.mod_list import ModListPopulator  # noqa: E402
from .populators.mod_options import ModOptionPopulator  # noqa: E402
from .populators.options import OptionPopulator  # noqa: E402


def open_new_generic_menu(menu: WillowGFxMenu) -> None:
    """
    Creates a new generic menu with the populator on top of the stack.

    Args:
        menu: The current menu to open the generic one under.
    """
    if len(populator_stack) == 1:
        play_sound.enable()

    text = unrealsdk.construct_object("WillowGFxMenuScreenGeneric", outer=menu)
    text.MenuTag = CUSTOM_OPTIONS_MENU_TAG
    text.Init(menu, 0)

    menu.ScreenStack.append(text)
    menu.ActivateTopPage(0)
    menu.PlayUISound("Confirm")

    draw_custom_menu(menu)


def draw_custom_menu(menu: WillowGFxMenu) -> None:
    """
    Draws the populator on top of the stack to the current menu.

    Args:
        menu: The current menu to draw under.
    """
    tools = menu.GetLobbyTools()
    tools.menuStart(0)

    populator = populator_stack[-1]
    populator.populate(tools)

    tools.menuEnd()

    menu.SetVariableString("menu.selections.title.text", html_to_plain_text(populator.title))
    menu.SetVariableString(
        "menu.tooltips.htmlText",
        menu.ResolveDataStoreMarkup("<Strings:WillowMenu.TitleMenu.SelBackBar>"),
    )


def get_selected_idx(menu: WillowGFxMenu) -> int | None:
    """
    Gets the index of the currently selected option item.

    Args:
        menu: The current menu to read the selected item of.
    Returns:
        The selected index, or None if unable to find.
    """
    focused = find_focused_item(menu)
    match = RE_SELECTED_IDX.match(focused)
    if match is None:
        return None

    try:
        return int(match.group(2))
    except ValueError:
        return None


# Similarly to the lobby menu, we need to use sounds to detect when you click an option/adjust a
# slider, since we can't safely pass callback names to ActionScript
@hook("GearboxFramework.GearboxGFxMovie:PlaySpecialUISound")
def play_sound(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    if args.SoundString not in ("Confirm", "SliderMovement"):
        return

    try:
        populator = populator_stack[-1]
    except IndexError:
        return
    if (idx := get_selected_idx(obj)) is None:
        return

    if args.SoundString == "Confirm":
        populator.on_activate(obj, idx)
    else:
        value = obj.GetVariableNumber(find_focused_item(obj) + ".Value")
        populator.on_slider_spinner_change(obj, idx, value)


@hook("WillowGame.WillowGFxMenuScreenGeneric:Screen_Deactivate", immediately_enable=True)
def generic_screen_deactivate(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    if obj.MenuTag == CUSTOM_OPTIONS_MENU_TAG and populator_stack:
        last_populator = populator_stack.pop()
        if isinstance(last_populator, ModOptionPopulator):
            last_populator.mod.save_settings()

        if populator_stack:
            # If we have screens left, we can't immediately redraw them here, need to wait a little
            reactivate_upper_screen.enable()

    if not populator_stack:
        play_sound.disable()

        if (owner := obj.MenuOwner).Class.Name == "WillowGFxMenuFrontend":
            open_lobby_mods_menu(owner)


@hook("WillowGame.WillowGFxMenu:ActivateTopPage", hook_type=Type.POST)
def reactivate_upper_screen(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    reactivate_upper_screen.disable()
    draw_custom_menu(obj)


# ==================================================================================================
# experimental


def create_keybinds_menu(obj: WillowGFxMenu) -> None:
    keybinds_frame = unrealsdk.construct_object("WillowGFxMenuScreenFrameKeyBinds", outer=obj)
    keybinds_frame.FrameTag = "PCBindings"
    keybinds_frame.MenuTag = "PCBindings"
    keybinds_frame.CaptionMarkup = "My Mod"
    keybinds_frame.Tip = "<Strings:WillowMenu.TitleMenu.SelBackBar>"

    keybinds_frame.Init(obj, 0)

    obj.ScreenStack.append(keybinds_frame)
    obj.ActivateTopPage(0)
    obj.PlayUISound("Confirm")


@hook("WillowGame.WillowGFxMenuScreenFrameKeyBinds:InitFrame")
def init_keybinds_frame(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    func: BoundFunction,
) -> type[Block]:
    super_class = obj.Class.SuperField
    assert super_class is not None
    super_func = super_class._find(func.func.Name)
    assert isinstance(super_func, UFunction)
    BoundFunction(super_func, obj)(args.Frame)

    obj.ActiveItems.emplace_struct(
        Tag="action_mod_kb_0",
        Caption="kb caption",
        CaptionMarkup="kb markup",
    )
    obj.Keybinds.emplace_struct(Bind="kb bind", Keys=["P"])
    obj.Keybinds[-1].Keys.append("T")

    obj.ActiveItems.emplace_struct(
        Tag="action_mod_option_0",
        Caption="opt caption",
        CaptionMarkup="opt markup",
    )
    obj.Keybinds.emplace_struct()

    return Block


init_keybinds_frame.disable()
