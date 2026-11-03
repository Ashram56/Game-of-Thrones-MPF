"""Counts the ROM's audit counters (got.audit_map) into MPF's auditor ('events' class) so they show in the service menu."""
from mpf.core.mode import Mode

from got import audit_map as am
from got.mystery import load_table


class RomAudits(Mode):
    def mode_start(self, **kwargs):
        self._mystery_audits = {e["name"]: e["audit"] for e in load_table()}
        for au, sw in am.SWITCH_AUDITS.items():
            self.add_mode_event_handler(sw + "_active", self._count, name=au)
        for ev, au in am.EVENT_AUDITS.items():
            self.add_mode_event_handler(ev, self._count, name=au)
        for sw, au in am.COIN_AUDITS.items():
            self.add_mode_event_handler(sw + "_active", self._count, name=au)
        self.add_mode_event_handler("got_pop_award", self._pop)
        self.add_mode_event_handler("got_match", self._match)
        self.add_mode_event_handler("got_video_mode_result", self._video_mode)
        self.add_mode_event_handler("got_special_credit", self._count, name="au_total_specials")
        self.add_mode_event_handler("got_mystery_award", self._mystery)
        self.add_mode_event_handler("got_house_confirmed", self._house_select)
        self.add_mode_event_handler("game_ended", self._players)
        for key in am.BATTLE_START:
            self.add_mode_event_handler("mode_%s_started" % key, self._count, name=am.BATTLE_START[key])
        self.add_mode_event_handler("mode_targaryen_started", self._targaryen_start)
        self.add_mode_event_handler("got_house_complete", self._house_complete)

    def _audit(self, name):
        auditor = getattr(self.machine, "auditor", None)
        if auditor:
            auditor.audit("events", name)

    def _count(self, name, **kwargs):
        self._audit(name)

    def _pop(self, award=None, **kwargs):
        self._audit("au_pops_total_awards")
        if award in am.POP_AUDITS:
            self._audit(am.POP_AUDITS[award])

    def _match(self, won=False, **kwargs):
        if won:
            self._audit("au_total_matches")

    def _video_mode(self, outcome=None, **kwargs):
        if outcome in am.VIDEO_MODE_AUDITS:
            self._audit(am.VIDEO_MODE_AUDITS[outcome])

    def _mystery(self, award=None, **kwargs):
        if award in self._mystery_audits:
            self._audit(self._mystery_audits[award])

    def _house_select(self, house=None, **kwargs):
        if house in am.HOUSE_SELECT:
            self._audit(am.HOUSE_SELECT[house])

    def _players(self, **kwargs):
        game = self.machine.game
        n = len(game.player_list) if game else 0
        if n in am.PLAYER_GAMES:
            self._audit(am.PLAYER_GAMES[n])

    def _targaryen_start(self, **kwargs):
        stage = min(2, int(self._stage_hint()))
        self._audit(am.TARGARYEN_START[stage])

    def _stage_hint(self):
        p = self.machine.game.player if self.machine.game else None
        return (p.got_dragon_stage or 0) if p else 0

    def _house_complete(self, key=None, **kwargs):
        if key in am.BATTLE_COMPLETE:
            self._audit(am.BATTLE_COMPLETE[key])
        elif key == "targaryen":
            self._audit(am.TARGARYEN_COMPLETE[2])
