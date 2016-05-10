import requests
from urllib.error import HTTPError
import datetime as dt
from time import sleep


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
        self.battle_id = str(self.province_id) + str(self.time)
        self.notified = False

    def convert_time(self):
        return dt.datetime.fromtimestamp(int(self.time))


class Clan:
    def __init__(self, response):
        self.clan_id = response['data']['clan_id']
        self.name = response['data']['name']
        self.tag = response['data']['tag']


class Province:
    def __init__(self, response):
        self.arena_id = response['data'][0]['arena_id']
        self.arena_name = response['data'][0]['arena_name']
        self.attackers = response['data'][0]['attackers']
        self.battles_start_at = response['data'][0]['battles_start_at']
        self.competitors = response['data'][0]['competitors']
        self.current_min_bet = response['data'][0]['current_min_bet']
        self.daily_revenue = response['data'][0]['daily_revenue']
        self.front_id = response['data'][0]['front_id']
        self.front_name = response['data'][0]['front_name']
        self.is_borders_disabled = response['data'][0]['is_borders_disabled']
        self.landing_type = response['data'][0]['landing_type']
        self.last_won_bet = response['data'][0]['last_won_bet']
        self.max_bets = response['data'][0]['max_bets']
        self.neighbours = response['data'][0]['neighbours']
        self.owner_clan_id = response['data'][0]['owner_clan_id']
        self.pillage_end_at = response['data'][0]['pillage_end_at']
        self.prime_time = response['data'][0]['prime_time']
        self.province_id = response['data'][0]['province_id']
        self.province_name = response['data'][0]['province_name']
        self.revenue_level = response['data'][0]['revenue_level']
        self.round_number = response['data'][0]['round_number']
        self.server = response['data'][0]['server']
        self.status = response['data'][0]['status']
        self.uri = response['data'][0]['uri']
        self.world_redivision = response['data'][0]['world_redivision']
        self.active_battles = response['data'][0]['active_battles']

def get_cw_battles(application_id, clan_id):
    """
    Get cw battle information for a clan from worldoftanks API
    :return:  list of Battle objects
    """
    payload = {'application_id': application_id, 'clan_id': clan_id}

    cw_url = 'https://api.worldoftanks.com/wot/globalmap/clanbattles/'

    r = requests.get(cw_url, params=payload)
    cw_battles = r.json()
    sleep(.2)

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

    r = requests.get(clan_url, params=payload)
    clan_info = r.json()
    sleep(.2)

    if clan_info['status'] != 'ok':
        raise HTTPError(r.url, clan_info['status'])
    else:
        return Clan(clan_info)


def get_province_info(application_id, front_id, province_id):
    payload = {'application_id': application_id, 'front_id': front_id, 'province_id': province_id}

    province_url = 'https://api.worldoftanks.com/wot/globalmap/provinces/'

    r = requests.get(province_url, params=payload)
    province_info = r.json()
    sleep(.2)

    if province_info['status'] != 'ok':
        raise HTTPError(r.url, province_info['status'])
    else:
        return Province(province_info)
