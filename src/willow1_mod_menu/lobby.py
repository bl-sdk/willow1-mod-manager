# ruff: noqa: D103
import math
import re
import traceback
from typing import Any

import unrealsdk
from unrealsdk.hooks import Block, Type
from unrealsdk.unreal import BoundFunction, UObject, WeakPointer, WrappedStruct

from mods_base import (
    CoopSupport,
    EInputEvent,
    Game,
    Mod,
    get_ordered_mod_list,
    hook,
    html_to_plain_text,
)
from mods_base.mod_list import base_mod

from .util import find_focused_item

type WillowGFxLobbyMultiplayer = UObject
type WillowGFxMenuFrontend = UObject


FRIENDLY_DISPLAY_VERSION = unrealsdk.config.get("willow1_mod_menu", {}).get(
    "display_version",
    base_mod.version,
)
RE_SELECTED_IDX = re.compile(r"^_level\d+\.mMenu\.mList\.item(\d+)$")

current_menu = WeakPointer()
drawn_mods: list[Mod] = []


def open_lobby_mods_menu(frontend: WillowGFxMenuFrontend) -> None:
    """
    Opens the multiplayer lobby-based mods menu.

    Args:
        frontend: The frontend movie to open under.
    """
    block_search_delegate.enable()
    init_content.enable()
    play_sound.enable()
    handle_input_key.enable()
    menu_scroll.enable()
    menu_close.enable()

    frontend.OpenMP()


# Avoid circular import
from .options import create_mod_options_menu  # noqa: E402


# This is called when the movie is first started, to start looking for online games. We just want to
# completely block it
@hook("WillowGame.WillowGFxLobbyMultiplayer:UpdateSearchDelegate")
def block_search_delegate(
    _obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> type[Block]:
    return Block


def get_mod_title(mod: Mod) -> str:
    """
    Combines the mod name and status into a single title.

    Args:
        mod: The mod to get the title of.
    Returns:
        The title to use for the mod in this menu.
    """
    # Filter out the standard enabled statuses, for more variation in the list - it's harder
    # to tell what's enabled or not when every single entry has a suffix
    # If there's a custom status, we'll still show that
    status = html_to_plain_text(mod.get_status()).strip()
    suffix = "" if mod.is_enabled and status in ("Enabled", "Loaded") else f" ({status})"
    return html_to_plain_text(mod.name) + suffix


# This hook is when the menu is actually initialized - we overwrite it with all our own logic
@hook("WillowGame.WillowGFxLobbyMultiplayer:extInitContent")
def init_content(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> type[Block]:
    global current_menu
    current_menu = WeakPointer(obj)

    setattr(obj, "__OnInputKey__Delegate", obj.HandleInputKey)

    # Setting a custom tag here seems to subtly corrupt something on the ActionScript end,
    # eventually leading to stack corruption and a crash
    # Luckily, it seems to work fine without
    obj.menuStart(0)

    drawn_mods.clear()
    for mod in get_ordered_mod_list():
        # This function has extra options for other commands, and a lot of base game calls pass
        # something like `menuAddItem(0, "title", "tag", "extHostP", "Focus:extMenuFocus")`
        # Unfortunately for us, it seems passing anything after the title also results in corruption
        # This gives us a rough time later on actually detecting select/focus
        obj.menuAddItem(0, get_mod_title(mod))
        drawn_mods.append(mod)

    obj.menuEnd()

    obj.SetVariableString("lobby.system.text", FRIENDLY_DISPLAY_VERSION)
    obj.SetVariableBool("lobby.tips._visible", True)
    obj.SetVariableBool("lobby.montage._visible", False)
    obj.SetVariableNumber("lobby.tips._y", obj.GetVariableNumber("lobby.montage._y"))

    init_next_tick.enable()

    return Block


# There's a handful of things we don't seem to be able to immediately change, update them next tick
@hook("WillowGame.WillowUIInteraction:TickImp")
def init_next_tick(*_: Any) -> None:
    init_next_tick.disable()
    if (menu := current_menu()) is None:
        return

    menu.SetVariableString("lobby.tab.text", "SDK Mod Manager")
    menu.SetVariableString("lobby.optionsHeader.text", "Mods")
    menu.SetVariableNumber("mMenu.mList._y", 0)

    # Most of the mod details could be updated in the initial hook, but there's a few parts which
    # need to be here
    update_menu_for_mod(menu, drawn_mods[0])


def update_menu_for_mod(menu: WillowGFxLobbyMultiplayer, mod: Mod) -> None:
    """
    Updates the lobby menu with all mod specific details.

    Args:
        menu: The menu to update.
        mod: The mod to get details from.
    """
    menu.SetVariableString("lobby.missionHeader.text", html_to_plain_text(mod.get_status()))
    menu.SetVariableString("lobby.tips.text", html_to_plain_text(mod.description))
    menu.SetVariableString("lobby.levelName.text", f"By {html_to_plain_text(mod.author)}")
    menu.SetVariableString("lobby.className.text", html_to_plain_text(mod.version))
    menu.SetVariableString("lobby.charName.text", html_to_plain_text(mod.name))

    mini_desc: str = ""

    if Game.get_current() not in mod.supported_games:
        supported = [g.name for g in Game if g in mod.supported_games and g.name is not None]
        mini_desc += "This mod supports: " + ", ".join(supported) + "\n"

    match mod.coop_support:
        case CoopSupport.Unknown:
            mini_desc += "Coop Support: Unknown"
        case CoopSupport.Incompatible:
            mini_desc += "Coop Support: Incompatible"
        case CoopSupport.RequiresAllPlayers:
            mini_desc += "Coop Support: Requires All Players"
        case CoopSupport.ClientSide:
            mini_desc += "Coop Support: Client Side"
        case CoopSupport.HostOnly:
            mini_desc += "Coop Support: Host Only"

    menu.SetVariableString("lobby.missionName.text", mini_desc)

    tooltip = "$<StringAliasMap:GFx_Accept> DETAILS"
    if not mod.enabling_locked:
        tooltip += "     [Space] " + ("DISABLE" if mod.is_enabled else "ENABLE")
    tooltip += "     <Strings:WillowMenu.TitleMenu.BackBar>"

    menu.SetVariableString("lobby.tooltips.text", tooltip)


def get_focused_mod(menu: WillowGFxLobbyMultiplayer) -> Mod | None:
    """
    Gets the mod which is currently focused.

    Args:
        menu: The current menu to read the focused mod of.
    Returns:
        The selected mod, or None if unable to find.
    """
    focused = find_focused_item(menu)
    match = RE_SELECTED_IDX.match(focused)
    if match is None:
        return None

    try:
        return drawn_mods[int(match.group(1))]
    except (IndexError, ValueError):
        return None


# Since we can't detect select/menu moves with the dedicated hooks, the hack we do instead is to
# look for the sounds they make
@hook("GearboxFramework.GearboxGFxMovie:PlaySpecialUISound")
def play_sound(
    _obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    match args.SoundString:
        case "VerticalMovement":
            select_next_tick.enable()
        case "Confirm":
            if (menu := current_menu()) is None:
                return
            mod = get_focused_mod(menu)
            if mod is None:
                return

            menu.Close()
            frontend = menu.PlayerOwner.GFxUIManager.GetPlayingMovie()
            create_mod_options_menu(frontend, mod)
        case _:
            return


# For vertical movement, if scrolling using up/down, the sound plays after changing focus, we could
# use the above hook. If using mouse however, it player before, so we need to wait a tick to update.
@hook("WillowGame.WillowUIInteraction:TickImp")
def select_next_tick(*_: Any) -> None:
    select_next_tick.disable()
    if (menu := current_menu()) is None:
        return
    mod = get_focused_mod(menu)
    if mod is not None:
        update_menu_for_mod(menu, mod)


@hook("WillowGame.WillowGFxLobbyMultiplayer:HandleInputKey")
def handle_input_key(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> tuple[type[Block], bool] | None:
    key: str = args.ukey
    event: EInputEvent = args.uevent

    if not (key == "SpaceBar" and event == EInputEvent.IE_Released):
        return None

    mod = get_focused_mod(obj)
    if mod is None or mod.enabling_locked:
        return None

    old_enabled = mod.is_enabled
    try:
        (mod.disable if old_enabled else mod.enable)()
    except Exception:  # noqa: BLE001
        traceback.print_exc()

    # Extra safety layer in case the mod rejected the toggle, no need to update if we haven't
    # changed state
    if old_enabled != mod.is_enabled:
        update_menu_for_mod(obj, mod)

        obj.SetVariableString(find_focused_item(obj) + ".mLabel.text", get_mod_title(mod))

    return Block, True


@hook("WillowGame.WillowGFxLobbyBase:inNext", hook_type=Type.POST)
@hook("WillowGame.WillowGFxLobbyBase:inPrev", hook_type=Type.POST)
def menu_scroll(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    # If we have more than a page of menu items (14), the scrolling slightly breaks, and the top
    # item gets displayed off screen. This is probably a vanilla bug.
    # Note this hook is not suitable for focus change, since it's not triggered on mouse movement.

    if not math.isfinite(list_y := obj.GetVariableNumber("mMenu.mList._y")):
        return
    if list_y >= 0:
        # Already scrolled to the top, no need to do anything
        return

    if get_focused_mod(obj) == drawn_mods[0]:
        # Special case: if we just scrolled to index 0 always scroll back to the top
        obj.SetVariableNumber("mMenu.mList._y", 0)
        return

    # You can still scroll off the top, as long as you're not selecting the very top item.

    # Unfortunately, this seems non-trivial to fix.
    # For one, there isn't really a good way to detect if the focused item is off screen.
    # Then even if we come up with a heuristic, changing Y while not at the top has some weird
    # effects, it'll bring the header back and leave us with some empty menu items.

    # Leaving it for now. You can always just scroll up an extra time.


@hook("WillowGame.WillowGFxLobbyMultiplayer:OnClose")
def menu_close(
    _obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    block_search_delegate.disable()
    init_content.disable()
    init_next_tick.disable()
    play_sound.disable()
    select_next_tick.disable()
    handle_input_key.disable()
    menu_scroll.disable()
    menu_close.disable()

    global current_menu
    current_menu = WeakPointer()
    drawn_mods.clear()
