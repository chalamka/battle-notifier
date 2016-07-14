import logging
import json
import sys
import datetime as dt
import os
import time
from urllib.error import HTTPError
import slack_webhooks as slack
import worldoftanks_requests as wot
from itertools import dropwhile
from math import log2, ceil


class BattleNotifier:
    def __init__(self, config_path='config.json', log_level=logging.CRITICAL):
        self.battles = []
        self.logger = configure_logging(log_level)

        config = self._load_config(config_path)
        self.application_id = config['application_id']
        self.clan_id = config['clan_id']
        self.bot_name = config['bot_name']
        self.icon_emoji = config['icon_emoji']
        self.channel_name = config['channel_name']
        self.slack_url = config['slack_url']
        self.update_interval = config['update_interval']
        self.clan_tag = config['clan_tag']

    def run(self):
        while True:
            try:
                if self._update_battles():
                    self.logger.info("Found battle") 
                    self._slack_notification()
                time.sleep(self.update_interval)
                self.logger.info("Sleep cycle completed")
            except KeyboardInterrupt:
                self.logger.critical("Interrupted, shutting down")
                sys.exit(1)

    def _update_battles(self):
        new_battles = self._get_new_battles()
        if not new_battles:
            return False
        else:
            self.battles += new_battles
            self.battles.sort(key=lambda x: x[0].time)
            self.battles = list(dropwhile(lambda x: dt.datetime.fromtimestamp(x[0].time) < dt.datetime.now(), self.battles))
            if self.battles:
                return True
            else:
                return False

    def _get_new_battles(self):
        try:
            new_battles = wot.get_cw_battles(self.application_id, self.clan_id)
            battles_info = [(battle,
                             wot.get_province_info(self.application_id, battle.front_id, battle.province_id),
                             wot.get_clan_info(self.application_id, battle.competitor_id))
                            for battle in new_battles if battle.battle_id not in [b.battle_id for b, _, __ in self.battles]]
            return battles_info
        except HTTPError:
            self.logger.error("HTTP Error when getting battles")
            return []

    def _simul_check(self, battle):
        simuls = []

        for b, _, __ in self.battles:
            if abs((b.convert_time() - battle.convert_time()).total_seconds() / 60) < 5 and battle.battle_id != b.battle_id:
                simuls.append(b)

        return simuls

    def _slack_notification(self):
        attachments = []
        thumb_url = "http://na.wargaming.net/clans/media/clans/emblems/cl_{}/{}/emblem_64x64.png"
        current_time = dt.datetime.now()

        for battle, province, clan in self.battles:
            if not battle.notified:
                battle.notified = True
                province_text = "*Province:* {} *Map:* {} *Server:*  {}".format(province.province_name,
                                                                                province.arena_name,
                                                                                province.server)

                battle_start_time = dt.datetime.fromtimestamp(int(battle.time))
                time_until_battle = battle_start_time - current_time
                minutes_until_battle = time_until_battle.total_seconds() / 60

                if battle.type == 'attack' and battle.attack_type == 'tournament':
                    time_text = "Tournament Round {} begins at {} CST popping in {} minutes".format(
                        province.round_number,
                        # this doesn't work right now 
                        # ceil(log2(len(province.attackers))),
                        battle_start_time.strftime("%H:%M"),
                        int(minutes_until_battle - 14))
                else:
                    time_text = "*{}* begins at {} CST popping in {} minutes".format(
                        battle.type.title(),
                        battle_start_time.strftime("%H:%M"),
                        int(minutes_until_battle - 14))

                simul_text = ""
                simuls = self._simul_check(battle)
                if simuls:
                    simul_text = "There are {} battles occurring at this time: {}, {}.".format(
                            len(simuls) + 1,
                            province.province_name,
                            ", ".join([b.province_name for b in simuls]))

                battle_attachment = slack.build_slack_attachment(fallback="Upcoming CW battle vs. {}".format(clan.tag),
                                                                 pretext="",
                                                                 fields=[],
                                                                 title=":{0}: {0} vs. {1} :fire:".format(self.clan_tag, clan.tag),
                                                                 level="good" if battle.type == 'defence' else "danger",
                                                                 thumb_url=thumb_url.format(str(clan.clan_id)[-3:], clan.clan_id),
                                                                 text="{}\n{}\n{}".format(province_text, time_text, simul_text),
                                                                 markdown_in=['text'])
                attachments.append(battle_attachment)

        payload = slack.build_slack_payload(attachments, "<!channel>", self.bot_name, self.icon_emoji, self.channel_name)
        slack.send_slack_webhook(self.slack_url, payload)
        self.logger.info("Slack webhook notification sent")

    def _load_config(self, filename):
        try:
            with open(filename) as fp:
                return json.load(fp)
        except IOError:
            self.logger.critical("Failed to load configuration file: {}".format(filename))
            self.logger.critical("Exiting (cannot load config)")
            sys.exit(1)


def write_json(filename, to_write):
    with open(filename, 'w') as fp:
        return json.dump(to_write, fp)


def configure_logging(level):
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    if not os.path.exists("logs/"):
        os.mkdir("logs/")

    l = logging.getLogger(__name__)
    logger_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler("logs/" + dt.date.today().strftime("%m-%d-%Y.log"))

    l.setLevel(level)
    file_handler.setFormatter(logger_format)
    l.addHandler(file_handler)

    return l


def main(args):
    bn = BattleNotifier()
    bn.run()

if __name__ == "__main__":
    main(sys.argv)
