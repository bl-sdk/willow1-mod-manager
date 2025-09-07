# ruff: noqa: D103
from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, Any

import unrealsdk
from unrealsdk import logging
from unrealsdk.hooks import Block, Type
from unrealsdk.unreal import BoundFunction, UFunction, UObject, WeakPointer, WrappedStruct

from mods_base import Mod, NestedOption, hook, html_to_plain_text

from .lobby import open_lobby_mods_menu
from .util import ASType, find_focused_item

if TYPE_CHECKING:
    from .populators import Populator
    from .util import WillowGFxMenu

CUSTOM_OPTIONS_MENU_TAG = "willow1-mod-menu:custom-option"
CUSTOM_KEYBINDS_MENU_TAG = "willow1-mod-menu:custom-keybinds"

RE_SELECTED_IDX = re.compile(
    r"^(?P<list>_level\d+\.(?:menu\.selections|content)\.mMenu\.mList)\.item(?P<idx>\d+)$",
)

populator_stack: list[Populator] = []
nested_selection_stack: list[tuple[str, float]] = []


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
    if menu.Class.Name == "WillowGFxMenuPause":
        push_nested_selection(menu)
    open_new_generic_menu(menu)


def create_nested_options_menu(menu: WillowGFxMenu, option: NestedOption) -> None:
    """
    Creates a new menu holding a nested option's children.

    Args:
        menu: The current menu to create the new one under.
        option: The options whose children to create a menu for.
    """
    populator_stack.append(OptionPopulator(option.display_name, option.children))
    push_nested_selection(menu)
    open_new_generic_menu(menu)


def create_keybinds_menu(menu: WillowGFxMenu) -> None:
    """
    Creates a new menu holding a mod's keybinds.

    Args:
        menu: The current menu to create the new one under.
    """
    push_nested_selection(menu)
    create_keybinds_menu_impl(menu)


# ==================================================================================================


def push_nested_selection(menu: WillowGFxMenu) -> None:
    """
    Pushes the currently selected item to the stack, so it can be restored when this menu is closed.

    Args:
        menu: The current menu to retrieve the selected item from
    """
    item = find_focused_item(menu)
    if (match := RE_SELECTED_IDX.match(item)) is None:
        # Just default to 0
        y = 0
    else:
        y = menu.GetVariableNumber(match.group("list") + "._y")

    nested_selection_stack.append((item, y))


# Avoid circular imports
from .populators import LOCKED_KEY_PREFIX  # noqa: E402
from .populators.mod_list import ModListPopulator  # noqa: E402
from .populators.mod_options import ModOptionPopulator  # noqa: E402
from .populators.options import OptionPopulator  # noqa: E402

# Weirdly, we need to perform a delayed init once, the very first time you open a generic menu
# screen after starting the frontend. On subsequent calls we can initialize immediately, and we can
# always do so from the pause menu. This tracks that.
needs_delayed_init = False


@hook("WillowGame.WillowGFxMenuFrontend:extOpenInitialScreen", immediately_enable=True)
def trigger_delayed_init(*_: Any) -> None:
    global needs_delayed_init
    needs_delayed_init = True


@hook("WillowGame.WillowGFxMenuFrontend:OnClose", immediately_enable=True)
@hook("WillowGame.WillowGFxMenu:initGenericMenu")
def cancel_delayed_init(*_: Any) -> None:
    global needs_delayed_init
    needs_delayed_init = False


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

    original_needs_delayed_init = needs_delayed_init
    if original_needs_delayed_init:
        text.InitFunc = "extInitOptions_Game"
        delayed_mod_init.enable()

    # This call will clear the init flag if it's set, hence saving the original value earlier
    text.Init(menu, 0)

    menu.ScreenStack.append(text)
    menu.ActivateTopPage(0)

    if not original_needs_delayed_init:
        # Can draw immediately
        draw_custom_menu(menu)


@hook("WillowGame.WillowGFxMenu:extInitOptions_Game")
def delayed_mod_init(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> type[Block]:
    delayed_mod_init.disable()

    obj.ScreenStack[-1].InitFunc = ""
    draw_custom_menu(obj)

    return Block


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

    # There's a different variable for the title in the frontend vs pause menus, luckily we can just
    # try set both
    title = html_to_plain_text(populator.title)
    menu.SetVariableString("menu.selections.title.text", title)  # Frontend
    menu.SetVariableString("_level0.title.text", title)  # Pause

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
        return int(match.group("idx"))
    except ValueError:
        return None


slider_next_tick_info: tuple[WeakPointer, str, Populator, int] | None = None


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
        return

    # The same sound is used for both sliders and spinners.
    focused = find_focused_item(obj)
    if not populator.is_slider(idx):
        # We can do spinners more easily first
        choice: float = obj.GetVariableNumber(focused + ".mChoice")
        populator.on_spinner_change(obj, idx, int(choice))
        return

    # Sliders have the same problem as in the lobby movie, for kb input they plays the sound after
    # updating the value, and we could run our callbacks here, but for mouse input they play the
    # sound before.
    # Save a bunch of data we already have, then wait for next tick.

    global slider_next_tick_info
    slider_next_tick_info = (
        WeakPointer(obj),
        focused + ".mValue",
        populator,
        idx,
    )

    slider_next_tick.enable()


@hook("WillowGame.WillowUIInteraction:TickImp")
def slider_next_tick(*_: Any) -> None:
    slider_next_tick.disable()

    global slider_next_tick_info
    if slider_next_tick_info is None:
        return
    weak_menu, path, populator, idx = slider_next_tick_info
    slider_next_tick_info = None

    if (menu := weak_menu()) is None:
        return
    value = menu.GetVariableNumber(path)

    if not math.isfinite(value):
        # If something's become invalid, we'll have gotten a NaN back. We really don't want to set
        # an option's value to NaN or inf, since it becomes essentially unrecoverable without
        # manually editing settings
        logging.error(f"Got {value} after changing slider!")
    else:
        populator.on_slider_change(menu, idx, value)


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
        else:
            # Sanity check: the selection stack should also be clear now
            nested_selection_stack.clear()

            if (owner := obj.MenuOwner).Class.Name == "WillowGFxMenuFrontend":
                # We had screens, but don't anymore, and came from the frontend menu
                # Re-draw the lobby mods screen so we back out into it
                open_lobby_mods_menu(owner)

    # If we closed the last screen, can remove our hook
    if not populator_stack:
        play_sound.disable()


# When you back out of a nested menu, we need to wait a few ticks before we can set your selection
# back to what it was before
reselect_nested_info: tuple[WeakPointer, str, int, float, float] | None = None


@hook("GearboxFramework.GearboxGFxMovie:OnTick")
def reselect_nested_next_tick(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    global reselect_nested_info
    if reselect_nested_info is None:
        reselect_nested_next_tick.disable()
        return

    weak_menu, list_name, idx, y, original_tick_rate = reselect_nested_info
    if (menu := weak_menu()) is None:
        reselect_nested_next_tick.disable()
        return

    # Ignore ticks from other movies, and wait for this menu to start up enough to focus something
    if obj != menu or not find_focused_item(menu):
        return

    reselect_nested_next_tick.disable()
    reselect_nested_info = None

    menu.SetVariableNumber(list_name + "._y", y)

    invoke = menu.Invoke
    invoke_args = WrappedStruct(invoke.func)
    invoke_args.Method = list_name + ".setSelectedItem"
    invoke_args.args.emplace_struct(Type=ASType.AS_Number, N=idx)
    invoke(invoke_args)

    menu.TickRateSeconds = original_tick_rate


@hook("WillowGame.WillowGFxMenu:ActivateTopPage", hook_type=Type.POST)
def reactivate_upper_screen(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    reactivate_upper_screen.disable()
    draw_custom_menu(obj)

    if nested_selection_stack:
        item, y = nested_selection_stack.pop()
        if not item:
            # May happen if getting focus failed
            return

        match = RE_SELECTED_IDX.match(item)
        if match is None:
            return
        try:
            idx = int(match.group("idx"))
        except ValueError:
            return

        global reselect_nested_info
        reselect_nested_info = (
            WeakPointer(obj),
            match.group("list"),
            idx,
            y,
            obj.TickRateSeconds,
        )

        # Default tickrate is very slow
        obj.TickRateSeconds = 1 / 60

        reselect_nested_next_tick.enable()


# ==================================================================================================


def create_keybinds_menu_impl(obj: WillowGFxMenu) -> None:
    keybinds_frame = unrealsdk.construct_object("WillowGFxMenuScreenFrameKeyBinds", outer=obj)
    keybinds_frame.MenuTag = CUSTOM_KEYBINDS_MENU_TAG
    keybinds_frame.FrameTag = "PCBindings"
    keybinds_frame.CaptionMarkup = "Keybinds"
    keybinds_frame.Tip = "<Strings:WillowMenu.TitleMenu.SelBackBar>"

    init_keybinds_frame.enable()
    init_bind_list.enable()
    bind_keybind_start.enable()
    bind_keybind_finish.enable()
    reset_keybinds.enable()
    localize_key_name.enable()

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
    init_keybinds_frame.disable()

    super_class = obj.Class.SuperField
    assert super_class is not None
    super_func = super_class._find(func.func.Name)
    assert isinstance(super_func, UFunction)
    BoundFunction(super_func, obj)(args.Frame)

    active_items = obj.ActiveItems
    keybinds = obj.Keybinds

    active_items.clear()
    keybinds.clear()

    populator_stack[-1].populate_keybinds(obj)

    return Block


# This function deletes the existing keys from the list, so we just block it to keep them
@hook("WillowGame.WillowGFxMenuScreenFrameKeyBinds:InitBind")
def init_bind_list(*_: Any) -> type[Block]:
    return Block


@hook("WillowGame.WillowGFxMenuScreenFrameKeyBinds:DoBind")
def bind_keybind_start(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> type[Block] | None:
    if (idx := obj.Selection.Current) == 0:
        # Reset keybinds, always allowed, continue
        return None

    if populator_stack[-1].may_bind_key(idx):
        # Allowed to bind, continue
        return None

    # Not allowed, block it
    return Block


@hook("WillowGame.WillowGFxMenuScreenFrameKeyBinds:Bind")
def bind_keybind_finish(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> type[Block]:
    populator_stack[-1].on_bind_key(obj, obj.Selection.Current, args.Key)
    return Block


@hook("WillowGame.WillowGFxMenuScreenFrameKeyBinds:ResetBindings_Clicked")
def reset_keybinds(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> type[Block]:
    if args.Dlg.DialogResult != "Yes":
        return Block

    populator_stack[-1].on_reset_keybinds(obj)
    return Block


@hook("WillowGame.WillowGFxMenuScreenFrameKeyBinds:LocalizeKeyName")
def localize_key_name(
    _obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    func: BoundFunction,
) -> tuple[type[Block], str] | None:
    key: str = args.Key

    if not key.startswith(LOCKED_KEY_PREFIX):
        # Normal, non locked key, use the standard function
        return None

    without_prefix = key.removeprefix(LOCKED_KEY_PREFIX)
    if not without_prefix:
        # Locked key bound to nothing
        return Block, "[ -- ]"

    # Locked key bound to something
    with unrealsdk.hooks.prevent_hooking_direct_calls():
        localized = func(without_prefix)
    return Block, f"[ {localized} ]"


@hook("WillowGame.WillowGFxMenuScreenFrameKeyBinds:Screen_Deactivate", immediately_enable=True)
def keybind_screen_deactivate(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    if obj.MenuTag == CUSTOM_KEYBINDS_MENU_TAG and populator_stack:
        init_bind_list.disable()
        bind_keybind_start.disable()
        bind_keybind_finish.disable()
        reset_keybinds.disable()
        localize_key_name.disable()

        reactivate_upper_screen.enable()
