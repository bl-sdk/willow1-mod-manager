# ruff: noqa: D103
from typing import Any

from unrealsdk.hooks import Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

from mods_base import hook

from .lobby import open_lobby_mods_menu

MODS_MENU_TAG = "willow1-mod-menu:mods-frontend"


@hook("WillowGame.WillowGFxMenuScreenDynamicText:Init")
def inject_mods_into_frontend_screen(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    if obj.MenuTag != "Main":
        return

    # The main menu only supports 7 items, so we need to remove the DLC entry to make space for mods

    # However, it seems if we remove any entry from the array, it causes strings to start corrupting
    # across the unrealscript/ActionScript boundary - the Python side sets everything correctly
    # So instead, we do this awkward slice assign to copy all entries down without deleting anything
    dlc_item_idx = next(idx for idx, item in enumerate(obj.Items) if item.Tag == "DLC")
    obj.Items[dlc_item_idx:-1] = obj.Items[dlc_item_idx + 1 :]

    # The last two entries are now identical quit entries - turn the second last into our mods entry
    mod_item = obj.Items[-2]
    mod_item.Tag = MODS_MENU_TAG
    mod_item.CaptionMarkup = "Mods"
    mod_item.bSuppressPC = False
    mod_item.bSuppress360 = False
    mod_item.bSuppressPS3 = False
    mod_item.PageTarget = "None"
    mod_item.Caption = ""


@hook("WillowGame.WillowGFxMenuFrontend:extOpenInitialScreen", immediately_enable=True)
def open_frontend_pre(*_: Any) -> None:
    inject_mods_into_frontend_screen.enable()


@hook(
    "WillowGame.WillowGFxMenuFrontend:extOpenInitialScreen",
    hook_type=Type.POST_UNCONDITIONAL,
    immediately_enable=True,
)
def open_frontend_post(*_: Any) -> None:
    inject_mods_into_frontend_screen.disable()


# This hooks runs on selecting any entry in the main menu
@hook("WillowGame.WillowGFxMenuFrontend:HandleMainMenu", immediately_enable=True)
def frontend_activate(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    if args.ItemTag != MODS_MENU_TAG:
        return
    open_lobby_mods_menu(obj)
