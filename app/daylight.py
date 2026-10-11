"""Approximate sunrise/sunset from NOAA fractional-year equations, Europe/Vienna.
Source: https://gml.noaa.gov/grad/solcalc/solareqns.PDF
No weather, terrain or real helicopter availability is inferred.
"""
import datetime as dt
import math
import calendar
from functools import lru_cache
from zoneinfo import ZoneInfo

@lru_cache(maxsize=256)
def window(date,lat,lon):
    day=dt.date.fromisoformat(date)
    gamma=2*math.pi/(366 if calendar.isleap(day.year) else 365)*(day.timetuple().tm_yday-1)
    eq=229.18*(.000075+.001868*math.cos(gamma)-.032077*math.sin(gamma)-.014615*math.cos(2*gamma)-.040849*math.sin(2*gamma))
    dec=.006918-.399912*math.cos(gamma)+.070257*math.sin(gamma)-.006758*math.cos(2*gamma)+.000907*math.sin(2*gamma)-.002697*math.cos(3*gamma)+.00148*math.sin(3*gamma)
    latitude=math.radians(lat)
    cos_hour=(math.cos(math.radians(90.833))/math.cos(latitude)/math.cos(dec)-math.tan(latitude)*math.tan(dec))
    if not -1<cos_hour<1:return (0,1440) if cos_hour<=-1 else (0,0)
    angle=math.degrees(math.acos(cos_hour))
    offset=dt.datetime.combine(day,dt.time(12),ZoneInfo('Europe/Vienna')).utcoffset().total_seconds()/60
    noon=720-4*lon-eq+offset
    # C3/C9 do not start before 06:00 in early summer.
    return max(360,round(noon-4*angle)),round(noon+4*angle)
