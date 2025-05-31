# ruff: noqa: D103, ERA001, ARG001, T201
from typing import TYPE_CHECKING, Any

import unrealsdk
from unrealsdk.hooks import Block
from unrealsdk.unreal import BoundFunction, UObject, WeakPointer, WrappedStruct

from mods_base import CoopSupport, Game, Mod, get_ordered_mod_list, hook, html_to_plain_text
from mods_base.mod_list import base_mod

# from .options import create_mod_options_menu

type WillowGFxLobbyMultiplayer = UObject
type WillowGFxMenuFrontend = UObject

if TYPE_CHECKING:
    from enum import auto

    from unrealsdk.unreal._uenum import UnrealEnum  # pyright: ignore[reportMissingModuleSource]

    class ASType(UnrealEnum):
        AS_Undefined = auto()
        AS_Null = auto()
        AS_Number = auto()
        AS_String = auto()
        AS_Boolean = auto()
        AS_MAX = auto()

else:
    from unrealsdk import find_enum

    ASType = find_enum("ASType")

FRIENDLY_DISPLAY_VERSION = unrealsdk.config.get("willow1_mod_menu", {}).get(
    "display_version",
    base_mod.version,
)
CUSTOM_LOBBY_MENU_TAG = "willow1-mod-menu:lobby"


current_menu = WeakPointer()
drawn_mods: list[Mod] = []


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

    obj.menuStart(0, CUSTOM_LOBBY_MENU_TAG)

    drawn_mods.clear()
    for idx, mod in enumerate(get_ordered_mod_list()):
        # Filter out the standard enabled statuses, for more variation in the list - it's harder
        # to tell what's enabled or not when every single entry has a suffix
        # If there's a custom status, we'll still show that
        status = html_to_plain_text(mod.get_status()).strip()
        suffix = "" if mod.is_enabled and status in ("Enabled", "Loaded") else f" ({status})"

        obj.menuAddItem(
            0,
            html_to_plain_text(mod.name) + suffix,
            str(idx),
            "extHostP",  # The callback run on selecting an entry
            "Focus:extMenuFocus",  # The callback run on changing focus
        )
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


@hook("WillowGame.WillowGFxLobbyMultiplayer:extMenuFocus")
def menu_focus(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> type[Block]:
    try:
        selected_mod = drawn_mods[int(args.MenuTag)]
    except (ValueError, IndexError):
        return Block

    update_menu_for_mod(obj, selected_mod)
    return Block


@hook("WillowGame.WillowGFxLobbyMultiplayer:extHostP")
def menu_select(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> type[Block]:
    try:
        selected_mod = drawn_mods[int(args.MenuTag)]
    except (ValueError, IndexError):
        return Block

    print("selected mod", selected_mod.name)

    # obj.Close()
    # frontend = obj.PlayerOwner.GFxUIManager.GetPlayingMovie()
    # create_mod_options_menu(frontend, selected_mod)

    return Block


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
    menu_focus.disable()
    menu_select.disable()
    menu_close.disable()

    global current_menu
    current_menu = WeakPointer()
    drawn_mods.clear()


def open_lobby_mods_menu(frontend: WillowGFxMenuFrontend) -> None:
    """
    Opens the multiplayer lobby-based mods menu.

    Args:
        frontend: The frontend movie to open under.
    """
    block_search_delegate.enable()
    init_content.enable()
    menu_focus.enable()
    menu_select.enable()
    menu_close.enable()

    frontend.OpenMP()
