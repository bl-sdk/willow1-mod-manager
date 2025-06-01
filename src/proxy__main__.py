# When launching via Steam, the CWD is (sometimes) `<steam>\Borderlands`. When launching via Mod
# Organiser, or by running the exe directly, it's `Borderlands\Binaries`. This means we can't put a
# single location in the `unrealsdk.toml`.
# This file is copied into a few different places by the release script, and attempts to normalize
# the path to the expected location

import importlib.util
import sys
from pathlib import Path

from unrealsdk import logging

binaries_dir = Path(sys.executable).resolve().parent
real_init_script = binaries_dir.parent / "sdk_mods" / "__main__.py"

logging.misc(f"Redirecting init script to: {real_init_script}")

# Use importlib to completely replace ourselves as the root module
spec = importlib.util.spec_from_file_location("__main__", real_init_script)
assert spec is not None and spec.loader is not None

module = importlib.util.module_from_spec(spec)
sys.modules["__main__"] = module
spec.loader.exec_module(module)
