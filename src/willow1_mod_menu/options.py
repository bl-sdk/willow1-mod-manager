# ruff: noqa: D103, TD002, TD003, FIX002
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import unrealsdk
from unrealsdk.hooks import Block
from unrealsdk.unreal import BoundFunction, UFunction, UObject, WrappedStruct

from mods_base import Mod, NestedOption, hook, html_to_plain_text

if TYPE_CHECKING:
    from .populators import Populator, WillowGFxMenu

CUSTOM_OPTIONS_MENU_TAG = "willow1-mod-menu:custom-option"

populator_stack: list[Populator] = []


def create_mod_options_menu(menu: WillowGFxMenu, mod: Mod) -> None:
    populator_stack.append(OptionPopulator(mod.name, mod.options))
    open_new_generic_menu(menu)


def create_nested_options_menu(menu: WillowGFxMenu, option: NestedOption) -> None:
    populator_stack.append(OptionPopulator(option.display_name, option.children))
    open_new_generic_menu(menu)


# Avoid circular imports
from .populators.options import OptionPopulator  # noqa: E402

# ==================================================================================================


def open_new_generic_menu(menu: WillowGFxMenu) -> None:
    if len(populator_stack) == 1:
        custom_menu_activate.enable()
        custom_menu_slider_change.enable()
        custom_menu_spinner_change.enable()

    text = unrealsdk.construct_object("WillowGFxMenuScreenGeneric", outer=menu)
    text.MenuTag = CUSTOM_OPTIONS_MENU_TAG
    text.Init(menu, 0)

    menu.ScreenStack.append(text)
    menu.ActivateTopPage(0)
    menu.PlayUISound("Confirm")

    tools = menu.GetLobbyTools()
    tools.menuStart(0, CUSTOM_OPTIONS_MENU_TAG)

    populator = populator_stack[-1]
    populator.populate(tools)

    tools.menuEnd()

    menu.SetVariableString("menu.selections.title.text", html_to_plain_text(populator.title))
    menu.SetVariableString(
        "menu.tooltips.htmlText",
        menu.ResolveDataStoreMarkup("<Strings:WillowMenu.TitleMenu.SelBackBar>"),
    )


@hook("WillowGame.WillowGFxMenu:extKeybinds")
def custom_menu_activate(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> type[Block]:
    try:
        populator = populator_stack[-1]
    except IndexError:
        return Block
    populator.on_activate(obj, args.MenuTag)
    return Block


@hook("WillowGame.WillowGFxMenu:extSpinnerChanged")
def custom_menu_spinner_change(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> type[Block]:
    try:
        populator = populator_stack[-1]
    except IndexError:
        return Block
    populator.on_spinner_change(obj, args.MenuTag, args.IValue)
    return Block


@hook("WillowGame.WillowGFxMenu:extSliderChanged")
def custom_menu_slider_change(
    obj: UObject,
    args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> type[Block]:
    try:
        populator = populator_stack[-1]
    except IndexError:
        return Block
    populator.on_slider_change(obj, args.MenuTag, args.Value)
    return Block


@hook("WillowGame.WillowGFxMenuScreenGeneric:Screen_Deactivate", immediately_enable=True)
def generic_screen_deactivate(
    obj: UObject,
    _args: WrappedStruct,
    _ret: Any,
    _func: BoundFunction,
) -> None:
    if obj.MenuTag == CUSTOM_OPTIONS_MENU_TAG:
        populator_stack.pop()
        # TODO: save mod settings

    if not populator_stack:
        custom_menu_activate.disable()
        custom_menu_spinner_change.disable()
        custom_menu_slider_change.disable()


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
