# ruff: noqa: D103
from typing import Any

from unrealsdk.hooks import Block, Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

from mods_base import hook

MODS_MENU_TAG = "willow1-mod-menu:mods-pause"


# In contrast to the frontend menu, the pause menu uses a generic menu screen, so the best place to
# hook to inject our own seems to be as we're adding the exit option
@hook("WillowGame.WillowGFxLobbyTools:menuAddItem")
def inject_mods_into_pause_screen(
    _obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    func: BoundFunction,
) -> None:
    if args.menuCaption != "$WillowMenu.Pause.Exit":
        return

    # We also don't seem to have a great way of detecting generic item activate events, so instead
    # we hook this to an unused debug function
    func(0, "Mods", MODS_MENU_TAG, "extMainDebug")


@hook("WillowGame.WillowGFxMenuPause:extInitMain", immediately_enable=True)
def open_pause_pre(*_: Any) -> None:
    inject_mods_into_pause_screen.enable()


@hook(
    "WillowGame.WillowGFxMenuPause:extInitMain",
    hook_type=Type.POST_UNCONDITIONAL,
    immediately_enable=True,
)
def open_pause_post(*_: Any) -> None:
    inject_mods_into_pause_screen.disable()


@hook("WillowGame.WillowGFxMenuPause:extMainDebug", immediately_enable=True)
def pause_activate(*_: Any) -> type[Block]:
    # We don't seem to be able to open the multiplayer lobby menu from in game - even if we force
    # load it's definition - so instead just open a standard options list showing each mod
    print("OPEN SIMPLE MODS MENU")  # TODO

    return Block
