"""Dispo 05 research inventory. Existence, current assignment and staffing differ.

Operator pages take precedence over historical community inventories. The user's
confirmed 77 fleet is maintained in fleet.py and is never overwritten here.
"""
from fleet import defaults

RK = 'https://www.roteskreuz.at/niederoesterreich/'
KOTTING = RK + 'kottingbrunn/wer-wir-sind/unsere-bezirksstelle/fuhrpark'
TRAISKIRCHEN = 'https://www.asbtrk.at/fuhrpark'
GAADEN = 'https://www.samariterbund.net/gruppen/samariterbund-gaaden-wienerwald/ueber-uns/dienststelle-gaaden/'
STEINFELDEN = 'https://www.samariterbund.net/gruppen/gruppe-steinfelden-schoenau-leobersdorf/dienststelle/fuhrpark/'
COMMUNITY = 'https://forum.lstsim.de/thread/8013-rlst-144-nn%C3%B6-standort-m%C3%B6dling/'
PHOTO = 'LstSim-Bestandsfoto des Nutzers vom 11.10.2026 (historische Daten, ausdrücklich ungeprüft)'

# Coordinates are town-level simulation points, not verified garage entrances.
STATIONS = [
 ('baden','RK Baden','Baden',48.00147,16.25389,'Rotes Kreuz-Gasse 6, 2500 Baden'),
 ('kottingbrunn','RK Kottingbrunn','Baden',47.951,16.228,'Dammgasse 1, 2542 Kottingbrunn'),
 ('alland','RK Alland','Baden',48.058,16.079,None),
 ('oberwaltersdorf','RK Oberwaltersdorf','Baden',47.977,16.324,None),
 ('leobersdorf','RK Leobersdorf','Baden',47.929,16.214,None),
 ('berndorf','RK Triestingtal · Berndorf','Baden',47.945,16.103,None),
 ('weissenbach','RK Weißenbach/Triesting','Baden',47.983,16.039,None),
 ('landegg','RK Landegg','Baden',47.910,16.414,None),
 ('ebenfurth','RK Ebenfurth','Baden',47.880,16.421,None),
 ('deutsch-brodersdorf','RK Deutsch-Brodersdorf','Baden',47.922,16.484,None),
 ('asb-traiskirchen','ASB Traiskirchen–Trumau','Baden',48.014,16.292,'Karl-Adlitzer-Straße 4, 2514 Traiskirchen'),
 ('asb-steinfelden','ASB Steinfelden–Schönau–Leobersdorf','Baden',47.943,16.260,None),
 ('asb-ebreichsdorf','ASB Ebreichsdorf','Baden',47.962,16.404,None),
 ('moedling','RK Mödling','Mödling',48.08133,16.28427,'Neusiedler Straße 20, 2340 Mödling'),
 ('wiener-neudorf','RK Wiener Neudorf','Mödling',48.083,16.321,None),
 ('guntramsdorf','RK Guntramsdorf','Mödling',48.049,16.309,None),
 ('biedermannsdorf','RK Biedermannsdorf','Mödling',48.082,16.345,None),
 ('perchtoldsdorf','RK Perchtoldsdorf','Mödling',48.120,16.266,None),
 ('brunn','RK Brunn am Gebirge','Mödling',48.109,16.284,None),
 ('voesendorf','RK Vösendorf','Mödling',48.121,16.342,None),
 ('breitenfurt','RK Breitenfurt','Mödling',48.140,16.197,None),
 ('asb-gaaden','ASB Gaaden–Wienerwald','Mödling',48.055,16.201,'Hauptstraße 29, 2531 Gaaden'),
]

# (station, type, local numbers, source, verification). No legacy RTW-N type.
GROUPS = [
 ('kottingbrunn','RTW',[601,602,611,612,613,614,615,616,617],KOTTING,'Betreiberkennung; aktueller RTW-/KTW-/RTW-C-Dienst und NFS-Besetzung prüfen'),
 ('kottingbrunn','KTW',[618],KOTTING,'Betreiberkennung; Typzuordnung noch prüfen'),
 ('kottingbrunn','BKTW',[621,622],KOTTING,'Betreiberquelle; Dienstzeiten sind Übungsannahmen'),
 ('asb-traiskirchen','RTW',[351,352,353],TRAISKIRCHEN,'Betreiber nennt Kennung und Typ; Dienstzeiten sind Übungsannahmen'),
 ('asb-traiskirchen','KTW',[354,356],TRAISKIRCHEN,'Betreiber nennt Kennung und Typ; Dienstzeiten sind Übungsannahmen'),
 ('asb-traiskirchen','BKTW',[355],TRAISKIRCHEN,'Betreiber nennt Kennung und Typ; Dienstzeiten sind Übungsannahmen'),
 ('asb-steinfelden','RTW',[334],STEINFELDEN,'Betreiberquelle; aktuelle Besetzung noch prüfen'),
 ('asb-steinfelden','KTW',[331],STEINFELDEN,'Betreiberquelle; aktuelle Besetzung noch prüfen'),
 ('asb-steinfelden','RTW',[332],PHOTO,'Historische Kennung / aktuelle Dienststelle und Typ prüfen'),
 ('asb-steinfelden','BKTW',[335],PHOTO,'Historische Kennung / aktuelle Dienststelle und Typ prüfen'),
 ('asb-gaaden','RTW',[332,333],GAADEN,'Betreiberquelle; aktuelle Besetzung noch prüfen'),
 ('asb-gaaden','KTW',[331],GAADEN,'Betreiberquelle; aktuelle Besetzung noch prüfen'),
 ('baden','RTW',[2,19],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('baden','KTW',[4,11,15,16,17],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('alland','RTW',[31],PHOTO,'Historische Kennung / aktuellen Bestand und RTW-C-Besetzung prüfen'),
 ('oberwaltersdorf','RTW',[41],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('leobersdorf','RTW',[202],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('leobersdorf','KTW',[201],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('berndorf','RTW',[401,418,419],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('berndorf','KTW',[411,412,414],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('weissenbach','RTW',[441],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('landegg','RTW',[801,802],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('landegg','KTW',[803],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('ebenfurth','RTW',[806],COMMUNITY,'Historischer Communitybestand; aktuelle Kennung und Typ prüfen'),
 ('ebenfurth','KTW',[844],COMMUNITY,'Widersprüchlicher Altbestand; Wiederaufnahme und Typ prüfen'),
 ('deutsch-brodersdorf','KTW',[805,808],PHOTO,'Historische Kennungen; aktuellen Bestand und Typ prüfen'),
 ('asb-ebreichsdorf','RTW',[384],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('asb-ebreichsdorf','KTW',[383,385],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('asb-ebreichsdorf','BKTW',[386],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('bruck','RTW',[4],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('bruck','KTW',[1,6,12],PHOTO,'Historische Kennungen; aktuellen Bestand und Typ prüfen'),
 ('bruck','BKTW',[7],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('hainburg','RTW',[603],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('hainburg','KTW',[608,611],PHOTO,'Historische Kennungen; aktuellen Bestand und Typ prüfen'),
 ('moedling','RTW',[3,7,9],COMMUNITY,'Communitybestand 2021; Typ und ehemalige RTW-N-/heutige RTW-C-Besetzung prüfen'),
 ('moedling','KTW',[20,21,22,23,24],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('moedling','BKTW',[102],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('wiener-neudorf','RTW',[4],COMMUNITY,'Communitybestand 2021; aktuellen Bestand und Typ prüfen'),
 ('wiener-neudorf','KTW',[10],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('guntramsdorf','RTW',[1,6],COMMUNITY,'Communitybestand / Altkennungen; aktuellen Bestand und Typ prüfen'),
 ('guntramsdorf','KTW',[26],PHOTO,'Historische Kennung / aktuellen Bestand und Typ prüfen'),
 ('biedermannsdorf','RTW',[5,8],COMMUNITY,'Communitybestand / Altkennungen; aktuellen Bestand und Typ prüfen'),
 ('perchtoldsdorf','RTW',[2],COMMUNITY,'Communitybestand 2021; aktuellen Bestand und Typ prüfen'),
 ('brunn','RTW',[401,405,410,414],COMMUNITY,'Communitybestand 2021; Typ und ehemalige RTW-N-/heutige RTW-C-Besetzung prüfen'),
 ('brunn','KTW',[407,408,411,412,413],COMMUNITY,'Communitybestand / Altkennungen; aktuellen Bestand und Typ prüfen'),
 ('brunn','BKTW',[480],COMMUNITY,'Communitybestand 2021; aktuellen Bestand und Typ prüfen'),
 ('voesendorf','RTW',[402],COMMUNITY,'Communitybestand 2021; aktuellen Bestand und Typ prüfen'),
 ('breitenfurt','RTW',[404],COMMUNITY,'Communitybestand 2021; aktuellen Bestand und Typ prüfen'),
]


def inventory():
    for station,typ,numbers,source,verification in GROUPS:
        prefix='64' if station in {s[0] for s in STATIONS if s[2]=='Mödling'} else '53' if station in ('bruck','hainburg') else '52'
        for number in numbers:
            yield f'{prefix}/{number:03}',typ,station,source,verification


def upgrade(engine):
    """One-time additive migration for saved singleplayer and multiplayer rooms.

    Manual edits, confirmed 77 vehicles and active missions are never replaced.
    A user can delete an imported candidate permanently after this migration.
    """
    state=engine.state
    if state.get('zone5_fleet_version',0)>=1:return
    from engine import uid
    for id,name,zone,lat,lon,address in STATIONS:
        if any(s['id']==id for s in state['stations']):continue
        state['stations'].append(dict(id=id,name=name,zone=zone,dispo='05',region='Niederösterreich',lat=lat,lon=lon,address=address or name+' · Dienststellenadresse noch prüfen',source='Dispo-05-Recherche 13.10.2026; Standortzuordnung noch prüfen',coordinate_accuracy='Ortsnaher Übungspunkt; nicht gebäudegenau verifiziert',external=False,night_minimum=3))
    calls={v['callsign'] for v in state['vehicles']}
    for call,typ,station,source,verification in inventory():
        if call in calls:continue
        home=engine.station(station)
        data=defaults(call,typ,station)
        data.update(id=uid(),lat=home['lat'],lon=home['lon'],job=None,reservation=None,phase_due=None,alarm_from='ready',ack_deadline=None,manual_out=False,leg=None,duty_managed=True,organization='ASB' if station.startswith('asb-') else 'RK',source=verification+' · '+source,verification=verification,inventory_source=source,inventory_checked='2026-10-13')
        data['status']=engine.idle_status(data)
        state['vehicles'].append(data);calls.add(call)
    state['night_rosters']={}
    state['zone5_fleet_version']=1
