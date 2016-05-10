import logging
import json
import sys
import datetime as dt
import os
import time
from urllib.error import HTTPError
import slack_webhooks as slack
import worldoftanks_requests as wot
import argparse
from itertools import dropwhile
from math import log2, ceil


class BattleNotifier:
    def __init__(self, config_path='config.json', log_level=logging.CRITICAL):
        self.battles = []
        self.logger = None
        self._configure_logging(log_level)

        config = self._load_config(config_path)
        self.application_id = config['application_id']
        self.clan_id = config['clan_id']
        self.bot_name = config['bot_name']
        self.icon_emoji = config['icon_emoji']
        self.channel_name = config['channel_name']
        self.slack_url = config['slack_url']

    def run(self):
        while True:
            try:
                if self._update_battles():
                    self._slack_notification()
                time.sleep(30)
            except KeyboardInterrupt:
                self.logger.log("Interrupted, shutting down")
                sys.exit(1)

    def _update_battles(self):
        new_battles = self._get_new_battles()
        if not new_battles:
            return False
        else:
            self.battles += new_battles
            self.battles.sort(key=lambda x: x[0].time)
            self.battles = list(dropwhile(lambda x: x[0].time < dt.datetime.now(), self.battles))
            return True

    def _get_new_battles(self):
        try:
            new_battles = wot.get_cw_battles(self.application_id, self.clan_id)
            battles_info = [(battle,
                             wot.get_province_info(self.application_id, battle.front_id, battle.province_id),
                             wot.get_clan_info(self.application_id, battle.competitor_id)
                             for battle in new_battles if battle.battle_id not in self.battles)]
            return battles_info
        except HTTPError:
            self.logger.error("HTTP Error when getting battles")
            return []

    def _simul_check(self, battle):
        pass

    def _slack_notification(self):
        attachments = []
        payload = None
        thumb_url = "http://na.wargaming.net/clans/media/clans/emblems/cl_{}/{}/emblem_64x64.png"
        current_time = dt.datetime.now()

        for battle, province, clan in self.battles:
            if not battle.notified:
                province_text = "Province: {} Map: {}".format(province.province_name, province.arena_name)

                battle_start_time = dt.datetime.fromtimestamp(int(battle.time))
                time_until_battle = current_time - battle_start_time
                minutes_until_battle = time_until_battle.total_seconds() / 60

                if battle.type == 'attack' and battle.attack_type == 'tournament':
                    time_text = "Tournament Round {} of {} begins at {} CST popping in {} minutes".format(
                        province.round_number,
                        ceil(log2(len(province.attackers))),
                        battle_start_time.strftime("%H:%M"),
                        minutes_until_battle)
                else:
                    time_text = "{} begins at {} CST popping in {} minutes".format(
                        battle.type.title(),
                        battle_start_time.strftime("%H:%M"),
                        minutes_until_battle)

                if self._simul_check(battle):
                    simul_text = ""

                battle_attachment = slack.build_slack_attachment(pretext="Upcoming CW battle vs. {}".format(clan.tag),
                                                                 fields=[],
                                                                 title=":rddt: RDDT vs. {} :fire:".format(clan.tag),
                                                                 level="good" if battle.type == 'defence' else "danger",
                                                                 thumb_url=thumb_url.format(clan.clan_id[-3:], clan.clan_id),
                                                                 text="{}\n{}\n{}".format(province_text, time_text, simul_text))
                attachments.append()

    def _configure_logging(self, level):
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

        self.logger = l

    def _load_config(self, filename):
        try:
            with open(filename) as fp:
                return json.load(fp)
        except IOError:
            self.logger.critical("Failed to load configuration file: {}".format(filename))
            self.logger.critical("Exiting script (cannot load config)")
            sys.exit(1)


def write_json(filename, to_write):
    with open(filename, 'w') as fp:
        return json.dump(to_write, fp)


def configure_parser():
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers()

    cw_parser = subparser.add_parser('cw_notification')
    cw_parser.set_defaults(func=cw_notification)

    sh_parser = subparser.add_parser('sh_notification')
    sh_parser.set_defaults(func=sh_notification)

    daemon = subparser.add_parser('daemon')
    daemon.set_defaults(func=notify_loop)

    return parser


def cw_notification(args):
    cw_attachment = []
    cw_messages = None

    cw_api_response = wot.get_cw_battles(config['application_id'], config['clan_id'])
    cw_battles = process_cw_battles(cw_api_response)

    if cw_battles:
        cw_messages = create_cw_battle_message(cw_battles)
        cw_fields = [slack.build_slack_field(b['title'], b['message']) for b in cw_messages]
        message_color = "danger" if cw_battles[0]['type'] == 'attack' else 'good'
        cw_attachment = [slack.build_slack_attachment("Upcoming clanwars battle",
                                                      "List of upcoming Clan Wars battles", "", message_color, cw_fields)]

    if cw_messages:
        cw_payload = slack.build_slack_payload(cw_attachment, "<!channel> Upcoming battles", config['bot_name'],
                                               config['icon_emoji'], config['channel_name'])
        slack.send_slack_webhook(config['slack_url'], cw_payload)


def sh_notification(args):
    sh_attachment = []

    sh_api_response = wot.get_sh_battles(config['application_id'], config['clan_id'])
    sh_battles = process_sh_battles(sh_api_response)

    if sh_battles:
        sh_messages = create_sh_battle_message(sh_battles)
        sh_fields = [slack.build_slack_field(b['title'], b['message']) for b in sh_messages]
        sh_attachment = [slack.build_slack_attachment("Upcoming stronghold battle",
                                                      "List of upcoming Stronghold battles:", "", "#D00000", sh_fields)]

    if sh_attachment:
        sh_payload = slack.build_slack_payload(sh_attachment, "<!channel> Upcoming battles", config['bot_name'],
                                               config['icon_emoji'], config['channel_name'])
        slack.send_slack_webhook(config['slack_url'], sh_payload)


def process_cw_battles(cw_battles):
    if cw_battles['status'] != 'ok':
        log.critical("wargaming globalmap/clanbattles API returned error status: {}".format(cw_battles['status']))
        sys.exit(1)
    else:
        if cw_battles['meta']['count'] != 0:
            log.info("Found {} cw battles to process".format(cw_battles['meta']['count']))
            cw_battles = cw_battles['data']
        else:
            log.info("No cw battles to process")
            cw_battles = []

    return cw_battles


def process_sh_battles(sh_battles):
    if sh_battles['status'] != 'ok':
        log.critical("wargaming stronghold/plannedbattles API returned error status: {}".format(sh_battles['status']))
        sys.exit(1)
    else:
        if sh_battles['meta']['count'] != 0:
            log.info("Found {} cw battles to process".format(sh_battles['meta']['count']))
            sh_battles = sh_battles['data'][config['clan_id']]
        else:
            log.info("No sh battles to process")
            sh_battles = []

    return sh_battles


def create_cw_battle_message(cw_battles):
    cw_battles = [c for c in cw_battles]
    cw_battles.sort(key=lambda x: x['time'])

    current_time = dt.datetime.now()

    cw_fields = []
    processed = list(load_config('processed.json'))

    if cw_battles:
        for battle in cw_battles:
            battle_time = dt.datetime.fromtimestamp(int(battle['time']))
            battle_id = str(battle['time']) + battle['province_name']

            if battle_time > current_time and battle_id not in processed:
                cw_fields.append(format_cw_battle(battle))
                processed.append(battle_id)

    write_json('processed.json', processed)

    return cw_fields


def create_sh_battle_message(sh_battles):
    sh_battles_list = sh_battles
    sh_fields = []

    if sh_battles_list:
        for battle in sh_battles_list:
            sh_fields.append(format_sh_battle(battle))

    return sh_fields


def format_cw_battle(battle):
    battle_time = dt.datetime.fromtimestamp(int(battle['time']))
    current_time = dt.datetime.now()
    time_delta = battle_time - current_time
    hours_to_battle = int((time_delta.seconds / 60) / 60)
    minutes_to_battle = int((time_delta.seconds / 60) % 60)

    competitor_clan_info = process_clan_info(wot.get_clan_info(config['application_id'], battle['competitor_id']),
                                             battle['competitor_id'])

    province_info = process_province_info(wot.get_province_info(config['application_id'],
                                                                battle['front_id'],
                                                                battle['province_id']))

    text = ":rddt: RDDT vs {} :fire:\n" \
           "Province: {} - Map: {}\n" \
           "Battle starts in {} hour(s) and {} minute(s) [{} at {} CST]"\
        .format(competitor_clan_info[str(battle['competitor_id'])]['tag'],
                province_info[0]['province_name'],
                province_info[0]['arena_name'],
                hours_to_battle,
                minutes_to_battle,
                battle_time.strftime("%m/%d/%Y"),
                battle_time.strftime("%H:%M"))

    # wait 1 second between calls in order to stay below API restriction
    time.sleep(1)
    return {'title': ":siren: Clan Wars {} :siren:".format(battle['type']), 'message': text}


def format_sh_battle(battle):
    battle_time = dt.datetime.fromtimestamp(int(battle['battle_planned_date']))
    current_time = dt.datetime.now()
    time_delta = battle_time - current_time
    hours_to_battle = int((time_delta.seconds / 60) / 60)
    minutes_to_battle = int((time_delta.seconds / 60) % 60)
    message = ":rddt: {} vs. {} :fire:\nSpecial pops in {} hour(s) and {} minute(s) [{} at {} CST]" \
        .format(battle['attacker_clan_tag'],
                battle['defender_clan_tag'],
                hours_to_battle,
                minutes_to_battle,
                battle_time.strftime("%m/%d/%Y"),
                battle_time.strftime("%H:%M"))
    return {'title': ":siren: Stronghold {} :siren:".format(battle['battle_type']), 'message': message}


def main(args):
    # parse arguments from command line and call the desired function / script
    parser = configure_parser()
    parsed_args = parser.parse_args()
    
    parsed_args.func(parsed_args)

if __name__ == "__main__":
    main(sys.argv)
