from mods_base.mod_list import base_mod

from . import frontend, lobby, options, pause  # noqa: F401  # pyright: ignore[reportUnusedImport]

__all__: list[str] = [
    "__author__",
    "__version__",
    "__version_info__",
]

__version_info__: tuple[int, int] = (1, 1)
__version__: str = f"{__version_info__[0]}.{__version_info__[1]}"
__author__: str = "bl-sdk"

base_mod.components.append(base_mod.ComponentInfo("Willow1 Mod Menu", __version__))
