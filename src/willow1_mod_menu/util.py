from typing import TYPE_CHECKING

from unrealsdk.unreal import UObject, WrappedStruct

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

type WillowGFxMenu = UObject


def find_focused_item(menu: WillowGFxMenu) -> str:
    """
    Runs the 'findFocusedItem' ActionScript function on the given menu.

    Args:
        menu: The menu to invoke the function under
    """
    # Being a little awkward so we can use .emplace_struct
    # This pattern isn't that important for single arg functions, but for longer ones it adds up
    invoke = menu.Invoke
    invoke_args = WrappedStruct(invoke.func)
    invoke_args.Method = "findFocusedItem"
    invoke_args.args.emplace_struct(Type=ASType.AS_Number, N=0)
    return invoke(invoke_args).S
