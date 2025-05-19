cmake_minimum_required(VERSION 3.24)

project(willow1_mod_manager)

set(UNREALSDK_FLAVOUR WILLOW)
set(EXPLICIT_PYTHON_ARCH win32)
set(EXPLICIT_PYTHON_VERSION 3.13.1)

add_subdirectory(libs/pyunrealsdk)

add_subdirectory(libs/pluginloader EXCLUDE_FROM_ALL)
set_target_properties(pluginloader_dsound PROPERTIES
    EXCLUDE_FROM_ALL false
)

install(
    TARGETS
        pluginloader_dsound
    RUNTIME DESTINATION
        .exe_folder
)
