import json

import requests

host = "https://www.icemaroc.com/api/search.php"


def get_company(ice=None):
    if not ice : return {}
    
    url = f"{ host }?query={ ice }"
    try:
        response = requests.get(url)
        response.raise_for_status()

        data_list = response.json()

        if data_list:
            entry = data_list[0]
            data = {
                'status': entry.get('statut'),
                'name': entry.get('raison_sociale'),
                'ice': entry.get('ice'),
                'capital': entry.get('capital'),
                'rc': str(entry.get('num_rc')),
                'city': entry.get('ville_rc'),
                'type': entry.get('forme'),
                'established': entry.get('dateCreation'),
                'activity': entry.get('activite'),
            }
            return data
    except: pass
    return {}


def get_concurrent(rs=None):
    if not rs : return {}
    
    url = f"{ host }?query={ rs }"
    try:
        response = requests.get(url)
        response.raise_for_status()

        data_list = response.json()

        if data_list:
            entry = data_list[0]
            name = entry.get('raison_sociale')
            if lower(name.strip()) == lower(rs.strip()):
                data = {
                    'status': entry.get('statut'), 
                    'name': entry.get('raison_sociale'), 
                    'ice': entry.get('ice'), 
                    'capital': entry.get('capital'), 
                    'rc': str(entry.get('num_rc')), 
                    'city': entry.get('ville_rc'), 
                    'type': entry.get('forme'), 
                    'established': entry.get('dateCreation'), 
                    'activity': entry.get('activite'), 
                }
                return data
    except: pass
    return None


def get_ice_checkup(ice):
    sj = None
    if not ice: return sj
    if len(ice) != 15: return sj
    p1, p2 = ice[:13], ice[13:]
    try:
        n1, n2 = int(p1), int(p2)
        cs = 97 - ((n1 * 100) % 97)
        return {'n1': n1, 'n2': n2, 'cs': cs}
    except:
        return sj