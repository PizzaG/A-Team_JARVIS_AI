# backtalk: talk to your Claude Code agent out loud.
# Copyright (C) 2026 Jared Rhodenizer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hold-to-talk — a global key listener.

HOLD the key -> mic opens. RELEASE -> mic closes and the utterance is
processed. The button IS the voice-activity detector, which is why this
mode is speaker-safe with no headphones: the mic simply isn't open while
the assistant talks, unless you press the key — and pressing while it
talks interrupts it.

THE KEY-REPEAT TRAP (the bug that kills every naive build): the OS fires
on_press events CONTINUOUSLY while a key is held. Without the held-state
filter below, every repeat reads as a fresh press and keeps cancelling
the reply before it can speak.

macOS needs Input Monitoring permission for the hosting terminal
(System Settings -> Privacy & Security -> Input Monitoring). Windows
works out of the box; some Linux desktops need the user in the `input`
group or an X11 session.
"""
import threading

from pynput import keyboard


def get_key_set(name: str) -> set:
    """Resolve human key name to a set of matching pynput Key / KeyCode objects."""
    name = (name or "home").strip().lower()
    if len(name) == 1:
        return {keyboard.KeyCode.from_char(name)}
    
    aliases = {
        "right_alt": {keyboard.Key.alt_r, keyboard.Key.alt_gr, getattr(keyboard.Key, "alt", None)},
        "alt_r": {keyboard.Key.alt_r, keyboard.Key.alt_gr, getattr(keyboard.Key, "alt", None)},
        "left_alt": {keyboard.Key.alt_l, getattr(keyboard.Key, "alt", None)},
        "alt": {keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr, getattr(keyboard.Key, "alt", None)},
        "right_ctrl": {keyboard.Key.ctrl_r, getattr(keyboard.Key, "ctrl", None)},
        "ctrl_r": {keyboard.Key.ctrl_r, getattr(keyboard.Key, "ctrl", None)},
        "left_ctrl": {keyboard.Key.ctrl_l, getattr(keyboard.Key, "ctrl", None)},
        "ctrl": {keyboard.Key.ctrl_l, keyboard.Key.ctrl_r, getattr(keyboard.Key, "ctrl", None)},
        "right_shift": {keyboard.Key.shift_r, getattr(keyboard.Key, "shift", None)},
        "shift_r": {keyboard.Key.shift_r, getattr(keyboard.Key, "shift", None)},
        "left_shift": {keyboard.Key.shift_l, getattr(keyboard.Key, "shift", None)},
        "shift": {keyboard.Key.shift_l, keyboard.Key.shift_r, getattr(keyboard.Key, "shift", None)},
        "space": {keyboard.Key.space},
        "spacebar": {keyboard.Key.space},
        "home": {keyboard.Key.home},
        "end": {keyboard.Key.end},
    }
    if name in aliases:
        return {k for k in aliases[name] if k is not None}
    
    try:
        return {getattr(keyboard.Key, name)}
    except AttributeError:
        print(f"[ptt] unknown key {name!r} — falling back to 'home'", flush=True)
        return {keyboard.Key.home}


def resolve_key(name: str):
    """Backwards-compatible single-key resolver."""
    keys = get_key_set(name)
    return next(iter(keys))


class PTTListener:
    def __init__(self, key="home"):
        self._key_name = key if isinstance(key, str) else "home"
        self._keys = get_key_set(self._key_name)
        self._held = False
        self._press_evt = threading.Event()
        self._listener = keyboard.Listener(on_press=self._on_press,
                                           on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()

    def _matches(self, k) -> bool:
        if k in self._keys:
            return True
        if hasattr(k, "char") and k.char and any(hasattr(t, "char") and t.char == k.char for t in self._keys):
            return True
        if hasattr(k, "vk") and k.vk and any(hasattr(t, "vk") and t.vk == k.vk for t in self._keys):
            return True
        return False

    def _on_press(self, k):
        if self._matches(k) and not self._held:   # filter key-repeat
            self._held = True
            self._press_evt.set()

    def _on_release(self, k):
        if self._matches(k):
            self._held = False

    def wait_press(self):
        """Block until the key goes DOWN (one event per physical press)."""
        self._press_evt.wait()
        self._press_evt.clear()

    def set_key(self, key):
        """Update the monitored key dynamically."""
        self._key_name = key if isinstance(key, str) else "home"
        self._keys = get_key_set(self._key_name)
        self._held = False

    def is_held(self) -> bool:
        return self._held
