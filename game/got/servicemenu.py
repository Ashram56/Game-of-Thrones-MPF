"""Service menu in the ROM's style on the DMD (replaces MPF's built-in service mode, which GMC has no screens for).
Select/Back/+/- are the four D-switches. Levels: top (AUDITS, ADJUSTMENTS, SWITCH TEST, COIL TEST) -> list -> edit.
Audits show the ROM's 207 counters (config/rom/audit_labels.json from data/audits_meaning.csv); adjustments are MPF settings
(data/adjustments.csv) saved on Select. Departure: the ROM's own screen layouts and its coin/utility pages are not rebuilt."""
import json
import os

from mpf.core.mode import Mode

TOP = ("AUDITS", "ADJUSTMENTS", "SWITCH TEST", "COIL TEST")


class ServiceMenu(Mode):
    def mode_start(self, **kwargs):
        self._level = None
        self._i = 0
        self._flip = False
        path = os.path.join(self.machine.machine_path, "config", "rom", "audit_labels.json")
        with open(path, encoding="utf-8") as f:
            self._audit_labels = json.load(f)
        menu = os.path.join(self.machine.machine_path, "config", "rom", "audit_menu.json")
        self._audit_menu = []
        if os.path.exists(menu):
            with open(menu, encoding="utf-8") as f:
                self._audit_menu = json.load(f)       # ROM order and labels (docs/19)
        for sw, fn in (("s_service_select_active", self._select), ("s_service_back_active", self._back),
                       ("s_service_plus_active", self._step), ("s_service_minus_active", self._step)):
            self.add_mode_event_handler(sw, fn, which=sw)

    # --- state -----------------------------------------------------------------------------------
    def _entries(self):
        if self._level == "top":
            return list(TOP)
        if self._level == "audits":
            return [m["name"] for m in self._audit_menu] or sorted(self._audit_labels)
        if self._level in ("adj", "edit"):
            return sorted((s.name for s in self.machine.settings.get_settings()), key=lambda n: self.machine.settings._settings[n].sort)
        if self._level == "coil":
            return sorted(self.machine.coils.keys())
        return []

    def _select(self, **kwargs):
        if self._level is None:
            if self.machine.game:                       # the menu only opens between games
                return
            self._level, self._i = "top", 0
            self.machine.events.post("got_service_open")
        elif self._level == "top":
            self._level = {"AUDITS": "audits", "ADJUSTMENTS": "adj", "SWITCH TEST": "switch", "COIL TEST": "coil"}[TOP[self._i]]
            self._top_i, self._i = self._i, 0
            if self._level == "switch":
                self._last = "PRESS A SWITCH"
                self.machine.switch_controller.add_monitor(self._monitor)
        elif self._level == "adj":
            self._level = "edit"
            self._edit = self._current_value()
        elif self._level == "edit":
            self.machine.settings.set_setting_value(self._entries()[self._i], self._edit)
            self._level = "adj"
        elif self._level == "coil":
            self.machine.coils[self._entries()[self._i]].pulse()
        self._show()

    def _back(self, **kwargs):
        if self._level is None:
            return
        if self._level == "top":
            self._level = None
            self.machine.events.post("got_screen_clear")
            self.machine.events.post("got_service_close")
            return
        if self._level == "edit":
            self._level = "adj"
        else:
            if self._level == "switch":
                self.machine.switch_controller.remove_monitor(self._monitor)
            self._level, self._i = "top", getattr(self, "_top_i", 0)
        self._show()

    def _step(self, which, **kwargs):
        if self._level is None or self._level == "switch":
            return
        d = 1 if which == "s_service_plus_active" else -1
        if self._level == "edit":
            vals = sorted(self.machine.settings._settings[self._entries()[self._i]].values)
            k = vals.index(self._edit) if self._edit in vals else 0
            self._edit = vals[(k + d) % len(vals)]
        else:
            self._i = (self._i + d) % len(self._entries())
        self._show()

    def _monitor(self, change):
        if self._level == "switch" and change.name.startswith("s_"):
            self._last = "%s %s" % (change.name[2:].upper().replace("_", " "), "CLOSED" if change.state else "OPEN")
            self._show()

    def _current_value(self):
        return self.machine.settings.get_setting_value(self._entries()[self._i])

    # --- display -----------------------------------------------------------------------------------
    def lines(self):
        lv = self._level
        e = self._entries()
        if lv == "top":
            return "SERVICE MENU", TOP[self._i], "+/- SELECT  BACK EXIT"
        if lv == "audits":
            name = e[self._i]
            au = self.machine.auditor.current_audits if getattr(self.machine, "auditor", None) else {}
            val = (au.get("events") or {}).get(name, 0)
            info = next((m for m in self._audit_menu if m["name"] == name), None)
            label = info["label"] if info else self._audit_labels[name]
            text = "{:,}".format(int(val))
            if info and info["pct"]:
                plays = int((au.get("events") or {}).get("au_total_plays_ended", 0))
                text += "  %d%%" % (100 * int(val) // plays if plays else 0)
            return "AUDITS %d/%d" % (self._i + 1, len(e)), label[:28].upper(), text
        if lv in ("adj", "edit"):
            s = self.machine.settings._settings[e[self._i]]
            if lv == "adj":
                return "ADJUSTMENT %d/%d" % (self._i + 1, len(e)), str(s.label)[:28].upper(), str(self.machine.settings.get_setting_value_label(s.name)).upper()
            return "EDIT " + str(s.label)[:24].upper(), str(s.values.get(self._edit, self._edit)).upper(), "SELECT SAVES  BACK CANCELS"
        if lv == "switch":
            return "SWITCH TEST", self._last, "BACK EXITS"
        if lv == "coil":
            return "COIL TEST", e[self._i][2:].upper().replace("_", " "), "SELECT PULSES"
        return "", "", ""

    def _show(self):
        self._flip = not self._flip
        l1, l2, l3 = self.lines()
        self.machine.events.post("got_screen_" + ("a" if self._flip else "b"), line1=l1, line2=l2, line3=l3)
