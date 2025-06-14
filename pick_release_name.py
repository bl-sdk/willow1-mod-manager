#!/usr/bin/env python3
# ruff: noqa: S311

import subprocess
from functools import cache
from pathlib import Path
from random import Random

UNIQUE_ITEM_NAMES = [
    "Ajax Ogre",
    "Ajax's Spear",
    "Anaconda",
    "Aries",
    "Assassin",
    "Athena's Wisdom",
    "Avenger",
    "Bad Ass",
    # Leaving enhanced guns out until we get a build supporting it
    # "Baha's Bigger Blaster",
    "Bastard",
    "Berserker",
    "Bessie",
    "Bitch",
    "Blast Master",
    "Blaster",
    "Bombardier",
    "Bone Shredder Savior",
    "Bone Shredder",
    "Boom Stick",
    "Bulldog",
    "Butcher",
    "Cannon",
    "Catalyst",
    "Centurion",
    "Champion",
    "Chimera",
    "Chiquito Amigo Protector",
    "Chiquito Amigo",
    "Cobra",
    "Commando",
    "Common Man",
    "Cracked Sash",
    "Crux",
    "Cyclops",
    "Defender",
    "Defiler",
    "Destroyer",
    "Dove Hornet",
    "Draco",
    "Equalizer",
    "Eridian Warrior",
    "Fireball",
    "Firebomb",
    "Firefly",
    "Firehawk",
    "Flaregun",
    "Friendly Fire Boom Stick",
    "Friendly Fire",
    "Gasher",
    "Gemini",
    "Glob Gun",
    "Guardian",
    "Gunfighter",
    "Gunman",
    "Gunslinger",
    "Hammer",
    "Heavy Gunner",
    "Hellfire",
    # "Hive Mind",
    "Hornet",
    "Hunter",
    "Hydra",
    "Invader",
    "Ironclad",
    "Jackal",
    "Knoxx's Gold",
    "Krom's Sidearm",
    "Kyros' Power Cyclops",
    "Kyros' Power",
    "Lady Finger",
    "Leader",
    "Leviathan",
    "Lightning",
    "Madjack",
    "Marine",
    "Mega Cannon",
    "Mercenary",
    "Mongol",
    # "Mug Shot",
    "Nailer",
    "Nemesis Invader",
    "Nemesis",
    "Nidhogg",
    "Ogre",
    "Omega",
    "Orion",
    "Patriot",
    "Patton",
    "Peace Keeper",
    "Penetrator",
    "Plaguebearer",
    "Professional",
    "Protector",
    "Ranger",
    "Raven",
    "Reaper",
    "Reaver's Edge Penetrator",
    "Reaver's Edge",
    "Rebel",
    "Redemption",
    "Revolution",
    "Rhino Roaster",
    "Rhino",
    "Rider",
    "Rifle",
    "Rifleman",
    "Rolling Spatter Gun",
    "Rose",
    "Savior",
    "Scavenger",
    "Serpens",
    "Sharpshooter",
    "Shock Trooper",
    # "Silent Night",
    "Skirmisher",
    "Skullmasher",
    "Sledge's Shotgun",
    "Sniper",
    "Specialist",
    "Specter",
    "Splat Gun",
    "Stalker",
    "Stampeding Spatter",
    "Striker",
    # "Sucker Punch",
    "Support Gunner",
    "Surkov",
    "Survivor",
    "T.K's Wave Bulldog",
    "T.K's Wave",
    "Tactician",
    "Tank",
    "Tempest",
    "Thanatos",
    "The Blister",
    "The Chopper",
    "The Clipper",
    "The Dove",
    "The Meat Grinder",
    "The Roaster",
    "The Sentinel",
    "The Spy",
    "Thunder Storm",
    "Titan",
    "Tormentor",
    "Troll",
    "Truxican Wrestler",
    "Tsunami",
    "Typhoon",
    "Undertaker",
    "Unforgiven",
    "Vengeance",
    "Violator",
    # "Violence",
    "Volcano",
    "Warmonger",
    "Wee Wee's Super Booster",
    "Whitting's Elephant Gun",
    "Wildcat",
]

PREVIOUS_RELEASE_NAMES = [
    "Support Gunner",
]


@cache
def get_git_commit_hash(identifier: str | None = None) -> str:
    """
    Gets the full commit hash of the current git repo.

    Args:
        identifier: The identifier of the commit to get, or None to get the latest.
    Returns:
        The commit hash.
    """
    args = ["git", "show", "-s", "--format=%H"]
    if identifier is not None:
        args.append(identifier)

    return subprocess.run(
        args,
        cwd=Path(__file__).parent,
        check=True,
        stdout=subprocess.PIPE,
        encoding="utf8",
    ).stdout.strip()


def pick_release_name(commit_hash: str, excludes: list[str] = PREVIOUS_RELEASE_NAMES) -> str:
    """
    Picks the name to use for a release.

    Args:
        commit_hash: The commit hash to pick the name of.
        excludes: The list of names to exclude.
    Returns:
        The release name.
    """
    # Think it's better to rely on an int than the string's hash method
    rng = Random(int(commit_hash, 16))
    while (name := rng.choice(UNIQUE_ITEM_NAMES)) in excludes:
        pass
    return name


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Picks the friendly name to use for the current release.",
    )
    parser.add_argument(
        "hash",
        nargs="?",
        default=None,
        help="The commit hash to base the name off of. If not given, retrieves from git.",
    )
    parser.add_argument(
        "--exclude",
        metavar="NAME",
        action="append",
        default=[],
        help="Excludes a name as if it were used in a previous release.",
    )
    parser.add_argument(
        "--ignore-previous-releases",
        action="store_true",
        help="Ignores all names which have been used in previous releases.",
    )
    args = parser.parse_args()

    commit_hash = get_git_commit_hash(args.hash)

    excludes = [] if args.ignore_previous_releases else PREVIOUS_RELEASE_NAMES
    excludes += args.exclude

    print(pick_release_name(commit_hash, excludes))  # noqa: T201
