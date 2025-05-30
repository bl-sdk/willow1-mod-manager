# ruff: noqa: D103
import re
from typing import TYPE_CHECKING, Any

import unrealsdk
from unrealsdk.hooks import Block
from unrealsdk.unreal import BoundFunction, UObject, WeakPointer, WrappedStruct

from mods_base import CoopSupport, Game, Mod, get_ordered_mod_list, hook, html_to_plain_text
from mods_base.mod_list import base_mod

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
RE_SELECTED_IDX = re.compile(r"_level\d+\.mMenu\.mList\.item(\d+)$")

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


# This hook is when the menu is actually initalized - we overwrite it with all our own logic
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

    obj.menuStart(obj.GetLocalPlayerID())

    drawn_mods.clear()
    for mod in get_ordered_mod_list():
        obj.menuAddItem(0, html_to_plain_text(mod.name))
        drawn_mods.append(mod)

    obj.menuEnd()

    obj.SetVariableString("lobby.system.text", FRIENDLY_DISPLAY_VERSION)
    obj.SetVariableBool("lobby.tips._visible", True)
    obj.SetVariableBool("lobby.montage._visible", False)
    obj.SetVariableNumber("lobby.tips._y", obj.GetVariableNumber("lobby.montage._y"))

    next_tick.enable()

    return Block


# There's a handful of things we don't seem to be able to immediately change, update them next tick
@hook("WillowGame.WillowUIInteraction:TickImp")
def next_tick(*_: Any) -> None:
    next_tick.disable()
    if (menu := current_menu()) is None:
        return

    menu.SetVariableString("lobby.tab.text", "SDK Mod Manager")
    menu.SetVariableString("lobby.optionsHeader.text", "Mods")

    # Most of the mod details could be updated in the inital hook, but there's a few parts which
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
        tooltip += "     [Space] " + "DISABLE" if mod.is_enabled else "ENABLE"
    tooltip += "     <Strings:WillowMenu.TitleMenu.BackBar>"

    menu.SetVariableString("lobby.tooltips.text", tooltip)


# Kind of hackily, we detect when you reselect items by looking for the sound it plays. There isn't
# a better hook for this
@hook("GearboxFramework.GearboxGFxMovie:PlaySpecialUISound")
def menu_move(
    _obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    if args.SoundString != "VerticalMovement":
        return

    if (menu := current_menu()) is None:
        return

    # Being a little awkward so we can use .emplace_struct
    # This pattern isn't that important for single arg functions, but for longer ones it adds up
    invoke = menu.Invoke
    invoke_args = WrappedStruct(invoke.func)
    invoke_args.Method = "findFocusedItem"
    invoke_args.args.emplace_struct(Type=ASType.AS_String, S="string")
    selected = invoke(invoke_args).S

    match = RE_SELECTED_IDX.match(selected)
    if match is None:
        return
    selected_idx = int(match.group(1))
    if selected_idx >= len(drawn_mods):
        return

    update_menu_for_mod(menu, drawn_mods[selected_idx])


@hook("WillowGame.WillowGFxLobbyMultiplayer:OnClose")
def menu_close(
    _obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    block_search_delegate.disable()
    init_content.disable()
    next_tick.disable()
    menu_move.disable()
    menu_close.disable()

    global current_menu
    current_menu = WeakPointer()
    drawn_mods.clear()


def open_mods_menu(frontend: WillowGFxMenuFrontend) -> None:
    """
    Opens the mods menu.

    Args:
        frontend: The frontend movie to open under.
    """
    block_search_delegate.enable()
    init_content.enable()
    menu_move.enable()
    menu_close.enable()

    frontend.OpenMP()
