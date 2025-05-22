import unrealsdk

from mods_base import get_pc


def show_chat_message(message: str, user: str | None = None) -> None:
    """
    Prints a message to chat.

    Args:
        message: The message to print.
        user: The user to print the chat message as. If None, defaults to the current user.
    """

    pc = get_pc(possibly_loading=True)
    if pc is None:
        raise RuntimeError(
            "Unable to show chat message since player controller could not be found!",
            message,
        )

    if user is None:
        user = pc.PlayerReplicationInfo.PlayerName

    (hud := pc.myHUD).GetHUDMovie().AddChatText(
        0,
        f"{user}: {message}",
        hud.DefaultMessageDuration,
        unrealsdk.make_struct("Color", R=255, G=255, B=255, A=255),
        pc.PlayerReplicationInfo,
    )
