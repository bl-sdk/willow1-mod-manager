# ruff: noqa: D103
from typing import Any

import unrealsdk
from unrealsdk.hooks import Block
from unrealsdk.unreal import BoundFunction, UFunction, UObject, WrappedStruct

from mods_base import Mod, hook, html_to_plain_text

from .populators.options import OptionPopulator

type WillowGFxMenu = UObject
type WillowGFxLobbyTools = UObject


def create_options_menu(obj: WillowGFxMenu, mod: Mod) -> None:
    text = unrealsdk.construct_object("WillowGFxMenuScreenGeneric", outer=obj)
    text.Init(obj, 0)
    obj.ScreenStack.append(text)
    obj.ActivateTopPage(0)
    obj.PlayUISound("Confirm")

    tools = obj.GetLobbyTools()
    tools.menuStart(0)

    OptionPopulator(mod.options).populate(tools)

    tools.menuEnd()

    obj.SetVariableString("menu.selections.title.text", html_to_plain_text(mod.name))
    obj.SetVariableString(
        "menu.tooltips.htmlText",
        obj.ResolveDataStoreMarkup("<Strings:WillowMenu.TitleMenu.SelBackBar>"),
    )


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
