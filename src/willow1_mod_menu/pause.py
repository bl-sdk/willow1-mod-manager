# ruff: noqa: D103
from typing import Any

from unrealsdk.hooks import Type
from unrealsdk.unreal import BoundFunction, UObject, WeakPointer, WrappedStruct

from mods_base import hook

from .options import create_mod_list_options_menu
from .util import find_focused_item

current_menu = WeakPointer()


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

    func(0, "Mods")


@hook("WillowGame.WillowGFxMenuPause:extInitMain", immediately_enable=True)
def open_pause_pre(obj: UObject, _args: WrappedStruct, _ret: Any, _func: BoundFunction) -> None:
    global current_menu
    current_menu = WeakPointer(obj)

    inject_mods_into_pause_screen.enable()
    pause_play_sound.enable()
    reenable_pause_after_nested.enable()
    reenable_pause_after_achievements.enable()


@hook(
    "WillowGame.WillowGFxMenuPause:extInitMain",
    hook_type=Type.POST_UNCONDITIONAL,
    immediately_enable=True,
)
def open_pause_post(*_: Any) -> None:
    inject_mods_into_pause_screen.disable()


# Since we can't safely pass callback names into ActionScript, have to detect when you click mods by
# the menu sound. This has quite some complications trying not to trigger while in other menus...
@hook("GearboxFramework.GearboxGFxMovie:PlaySpecialUISound")
def pause_play_sound(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    if args.SoundString != "Confirm":
        return

    # Disable this hook now, regardless of what screen we actually went into, to try avoid firing
    # spuriously. If we back out of the next screen, another hook should re-enable us.
    pause_play_sound.disable()

    if (menu := current_menu()) is None:
        return

    if len(menu.ScreenStack) > 1:
        # Sanity check, should only be able to fire on the top screen
        return

    if menu.GetVariableString(find_focused_item(obj) + ".mLabel.text") != "Mods":
        return

    # We don't seem to be able to open the multiplayer lobby menu from in game - even if we force
    # load it's definition - so instead just open a standard options list showing each mod
    create_mod_list_options_menu(obj)


# If we open a nested movie (e.g. lobby, quit), we won't re-init the pause menu when we leave it
# This hook will detect when we return to the pause movie, so we can re-enable the sound hook
@hook("WillowGame.WillowGFxUIManager:UpdateFocus", hook_type=Type.POST)
def reenable_pause_after_nested(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    if (menu := current_menu()) is None:
        return

    # If we've re-enabled the current pause movie
    if menu == obj.GetPlayingMovie():
        # Re-enable the sound hook
        pause_play_sound.enable()


@hook("WillowGame.WillowGFxMenuPause:extViewAchievements")
def reenable_pause_after_achievements(*_: Any) -> None:
    # Since the achievements menu just opens the steam overlay, with no in game menus, immediately
    # re-enable the sound hook
    pause_play_sound.enable()


@hook("WillowGame.WillowGFxMenuPause:OnClose", immediately_enable=True)
def pause_close(*_: Any) -> None:
    global current_menu
    current_menu = WeakPointer()

    pause_play_sound.disable()
    reenable_pause_after_nested.disable()
    reenable_pause_after_achievements.disable()
