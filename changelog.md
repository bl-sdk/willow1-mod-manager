# Changelog

## v2.3: Firehawk
- Fixed that the release zip for classic put the pluginloader in the wrong location, meaning fresh
  installs would not load. Upgraded installs still worked, no functional changes.

## v2.2: Warmonger
- Added support for BL1E, big thanks to Ry.
- Fixed the race condition which would sometimes cause the SDK to fail to initialize with a "no
  module named keybinds" error.
- Upgraded to Python 3.14.
- Added the `mod_manager.extra_sys_path` config option.
- Added support for launching launching an IPython kernel inside the SDK, which lets you interact
  with the SDK from Jupyter.

### [Keybinds v1.2](https://github.com/bl-sdk/willow_keybinds/blob/master/Readme.md#v12)
> No functional changes. Updated linting and CI logic.

### [Mods Base v1.12](https://github.com/bl-sdk/mods_base/blob/master/Readme.md#v19)
> - Added extra typing overloads to the `keybind` factory, to allow cases such as
>   `keybind("name", callback=func)`
>
> - Added support for BL4 and BL1E.
>
> - Deprecated `ValueOption.on_change`, as well as setting it via `__call__`, in favour of separate,
>   more explicit, `on_change_anytime` and `on_change_while_enabled` callbacks.
>
> - Added a `HookType.pause()` context manager. This may sometimes be preferable over the
>   `unrealsdk.hooks.prevent_hooking_direct_calls()` context manager.

### [pyunrealsdk v1.10.0](https://github.com/bl-sdk/pyunrealsdk/blob/master/changelog.md#v180)
> - The `pyunrealsdk.init_script` and `pyunrealsdk.pyexec_root` config options are now relative to the
>   folder containing the `pyunrealsdk.dll`. Previously, they were relative to the cwd, which could
>   cause issues if it changed.
>
> - Type stubs are now automatically generated based off of the source code, rather than being kept in
>   sync by hand. This caught several places they weren't fully accurate.
>
> - The `unrealsdk.hooks.Type` and `unrealsdk.logging.Level` enums should now use native Python enums,
>   rather than pybind's older version. These should be fully backwards compatible.
>
> - `UProperty`, and all it's subclasses, have been renamed to `ZProperty`, like they were in
>   unrealsdk. The existing names are all still available as deprecated aliases.
>
> - Upgraded to Pybind 3.0, which may matter for native modules.
>
> - Assigning one wrapped array to another with a compatible, but different, property, will now
>   automatically do the "convert to list" workaround for you.

### UI Utils v1.3
- Linting fixes

### [unrealsdk v3.2.0](https://github.com/bl-sdk/unrealsdk/blob/master/changelog.md#v320)
> - Now supports Borderlands 1 Enhanced and Borderlands 4, including several new types.
>
> - Renamed all `UProperty` types to `ZProperty`, and moved their headers from
>   `unrealsdk/unreal/classes/properties` to `unrealsdk/unreal/properties`.
>
> - Introduced `unrealsdk/flavour.h`, which splits flavour defines down into more specific feature
>   flags. Using these may be more appropriate in places.
>
> - The log file now includes thread id, and added highlighting to the external console logs.

### Willow1 Mod Menu v1.2
- Now properly keeps track of what item you selected when opening a nested menu, and returns to that
  item when you close it.
- Tried to improve how fraction slider option values are displayed.
- Tweaks to support BL1 Enhanced.

## v2.1: Orion
### Willow1 Mod Menu v1.1
- Fixed that Boolean and Slider options didn't properly detect changes.

## v2.0: Support Gunner
- Initial Release

## Older
A few v1.x versions were released as ad hoc prereleases, while BL1 support was being properly merged
into unrealsdk.
