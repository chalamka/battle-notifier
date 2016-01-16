import logging
import json
import sys
import datetime as dt
import os
import time
import slack_webhooks as slack
import worldoftanks_requests as wot

log = logging.getLogger(__name__)
config = {}


def configure_logging(level):
    os.chdir(os.path.dirname(sys.argv[0]))
    if not os.path.exists("logs/"):
        os.mkdir("logs/")

    l = logging.getLogger(__name__)
    logger_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler("logs/" + dt.date.today().strftime("%m-%d-%Y.log"))

    l.setLevel(level)
    file_handler.setFormatter(logger_format)
    l.addHandler(file_handler)


def load_config(filename):
    try:
        with open(filename) as fp:
            return json.load(fp)
    except IOError:
        log.critical("Failed to load configuration file: {}".format(filename))
        log.critical("Exiting script (cannot load config)")
        sys.exit(1)


def battle_notification():
    sh_attachment = []
    cw_attachment = []

    sh_api_response = wot.get_sh_battles(config['application_id'], config['clan_id'])
    sh_battles = process_sh_battles(sh_api_response)

    cw_api_response = wot.get_cw_battles(config['application_id'], config['clan_id'])
    cw_battles = process_cw_battles(cw_api_response)

    if cw_battles:
        cw_messages = create_cw_battle_message(cw_battles)
        cw_fields = [slack.build_slack_field(b['title'], b['message']) for b in cw_messages]
        cw_attachment = [slack.build_slack_attachment("Upcoming clanwars battle",
                                                      "List of upcoming Clan Wars battles", "", "#D00000", cw_fields)]

    if sh_battles:
        sh_messages = create_sh_battle_message(sh_battles)
        sh_fields = [slack.build_slack_field(b['title'], b['message']) for b in sh_messages]
        sh_attachment = [slack.build_slack_attachment("Upcoming stronghold battle",
                                                      "List of upcoming Stronghold battles:", "", "#D00000", sh_fields)]

    if sh_attachment or cw_attachment:
        attachment = cw_attachment + sh_attachment
        sh_payload = slack.build_slack_payload(attachment, "<!channel> Upcoming battles", config['bot_name'],
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

    cw_fields = []

    if cw_battles:
        for battle in cw_battles:
            cw_fields.append(format_cw_battle(battle))

    return cw_fields


def create_sh_battle_message(sh_battles):
    sh_battles_list = sh_battles
    sh_fields = []

    if sh_battles_list:
        for battle in sh_battles_list:
            sh_fields.append(format_sh_battle(battle))

    return sh_fields


def process_clan_info(clan_info, clan_id):
    if clan_info['status'] != 'ok':
        log.critical("wargaming clan api returned error status: {}".format(clan_info['status']))
        sys.exit(1)
    else:
        clan_info = clan_info['data']
        log.info("processing clan information for clan_id: {}".format(clan_id))
        return clan_info


def process_province_info(province_info):
    if province_info['status'] != 'ok':
        log.critical("wargaming province api returned error status: {}".format(province_info['status']))
        sys.exit(1)
    else:
        province_info = province_info['data']
        log.info("processing province information for: {}".format(province_info[0]['province_name']))
        return province_info


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
    # set logging levels to program defaults
    configure_logging(logging.DEBUG)
    log.info("Logging configured")

    # get config file from system arguments
    config_file = "".join(args)
    log.info("Loading config file: {}".format(config_file))

    # load configuration details from config file and set globally
    global config
    config = load_config(config_file)
    log.info("Successfully loaded config file: {}".format(config_file))

    battle_notification()


if __name__ == "__main__":
    main(sys.argv[1:])