"""The original Season 1 episodes the remaster ships for its retro mode (Telltale 2007).

Steam installs them in the language set for the game, but each episode folder holds two complete archives: the English
one and the one in that language, each with its own chores and lip files. The game prefers the English one, so the
dubbed voices play with the English timing and get cut off. Moving the English archive aside makes the game use the
dubbed one, with the chores Telltale timed for it (the fix Telltale's own staff suggested back then). Nothing is
deleted: the archive only gets another name, and taking the fix back renames it again.
"""
import os

HIDDEN = ".DubPolice"


def data_dir(game, e):
    return os.path.join(game, f"ep{e}", "Pack", "data")


def english(game, e):
    return os.path.join(data_dir(game, e), f"SamMax{e}_english.ttarch")


def dubbed(game, e, language):
    return os.path.join(data_dir(game, e), f"SamMax{e}_{language}.ttarch")


def available(game, episodes, language="german"):
    """The episodes that have the dubbed archive next to the English one (or already moved aside)."""
    return [e for e in episodes if os.path.isfile(dubbed(game, e, language))
            and (os.path.isfile(english(game, e)) or os.path.isfile(english(game, e) + HIDDEN))]


def is_dubbed(game, e):
    return os.path.isfile(english(game, e) + HIDDEN)


def dub(game, e, language):
    """Let the episode use its dubbed archive. Returns True if something changed."""
    if not os.path.isfile(dubbed(game, e, language)):
        raise ValueError(f"Episode {e}: kein Archiv in dieser Sprache")
    path = english(game, e)
    if os.path.isfile(path):
        if os.path.isfile(path + HIDDEN):
            os.remove(path + HIDDEN)
        os.replace(path, path + HIDDEN)
        return True
    return False


def restore(game, e):
    """Give the episode its English archive back. Returns True if there was something to undo."""
    path = english(game, e)
    if os.path.isfile(path + HIDDEN):
        if os.path.isfile(path):
            os.remove(path + HIDDEN)
        else:
            os.replace(path + HIDDEN, path)
        return True
    return False
