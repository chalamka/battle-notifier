import requests


def get_cw_battles(application_id, clan_id):
    """
    Get cw battle information for a clan from worldoftanks API
    :return:  dictionary of parsed json data for each battle type
    """
    payload = {'application_id': application_id, 'clan_id': clan_id}

    cw_url = 'https://api.worldoftanks.com/wot/globalmap/clanbattles/'

    cw_battles = requests.get(cw_url, params=payload)

    return cw_battles.json()


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