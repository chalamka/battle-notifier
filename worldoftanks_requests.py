import requests
from urllib.error import HTTPError
import datetime as dt


class CWBattle:
    def __init__(self, response):
        self.attack_type = response['data']['attack_type']
        self.front_id = response['data']['front_id']
        self.front_name = response['data']['front_name']
        self.competitor_id = response['data']['competitor_id']
        self.time = response['data']['time']
        self.vehicle_level = response['data']['vehicle_level']
        self.province_id = response['data']['province_id']
        self.type = response['data']['type']
        self.province_name = response['data']['province_name']

    def convert_time(self):
        return dt.datetime.fromtimestamp(int(self.time))


def get_cw_battles(application_id, clan_id):
    """
    Get cw battle information for a clan from worldoftanks API
    :return:  list of Battle objects
    """
    payload = {'application_id': application_id, 'clan_id': clan_id}

    cw_url = 'https://api.worldoftanks.com/wot/globalmap/clanbattles/'

    r = requests.get(cw_url, params=payload)
    cw_battles = r.json()

    if cw_battles['status'] != 'ok':
        raise HTTPError(r.url, cw_battles['status'])
    else:
        return [CWBattle(battle) for battle in cw_battles['data']]


def get_sh_battles(application_id, clan_id):
    """
    Get sh battle information for a clan from worldoftanks API
    :return:
    """
    payload = {'application_id': application_id, 'clan_id': clan_id}

    sh_url = 'https://api.worldoftanks.com/wot/stronghold/plannedbattles/'

    sh_battles = requests.get(sh_url, params=payload)

    return sh_battles.json()


def get_clan_info(application_id, clan_id):
    payload = {'application_id': application_id, 'clan_id': clan_id}

    clan_url = 'https://api.worldoftanks.com/wot/globalmap/claninfo/'

    clan_info = requests.get(clan_url, params=payload)

    return clan_info.json()


def get_province_info(application_id, front_id, province_id):
    payload = {'application_id': application_id, 'front_id': front_id, 'province_id': province_id}

    province_url = 'https://api.worldoftanks.com/wot/globalmap/provinces/'

    province_info = requests.get(province_url, params=payload)

    return province_info.json()
