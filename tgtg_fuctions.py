from tgtg import TgtgClient

import datetime as dt
from datetime import datetime
import pytz

# Constants
PING_ERROR      = -1
PING_NOTHING    = 0
PING_PRERELEASE = 1
PING_AVAILABLE  = 2

UNKNOWN_MINS = 1000000

EST = pytz.timezone('US/Eastern')
UTC_FMT = "%Y-%m-%dT%H:%M:%SZ"
EST_FMT = '%H:%M:%S %Y-%m-%d %Z'
AM = "AM"
PM = "PM"

DAYS_OF_WEEK = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}

# Pulls all bags that are favorited on the account being worked on
def get_all_favorite_ids(client: TgtgClient) -> list:
    items = client.get_items()
    item_ids = []

    for individual in items:
        item_ids.append(individual["item"]["item_id"])

    return item_ids

def get_specific_item(client: TgtgClient, item_id: str) -> str:
    return client.get_item(item_id)

def is_top_of_min() -> bool:
    u_now_sec: int = datetime.now(pytz.utc).second
    return u_now_sec == 0

# UTC times are already formatted in TGTG. Get the current time in EST, convert it to UTC for TGTG comparison  
async def time_now_utc() -> str:
    u: datetime = datetime.now(pytz.utc)
    return f"{u.year}-{u.month:02}-{u.day:02}T{u.hour:02}:{u.minute:02}:{u.second:02}Z"

# Get the exact time in UTC, one day in advance (some bags are automatically)
async def tgtg_one_day_ahead(utc_time: str) -> str:
    current_utc: datetime = datetime.strptime(utc_time, UTC_FMT)
    next_utc: datetime = current_utc + dt.timedelta(days=1)
    return next_utc.strftime(UTC_FMT)

# Purpose: How much more time in minutes until time_to_check? Compare with current time.
# Input: time_to_check TGTG UTC
async def time_diff_mins(time_to_check: str) -> int:
    if time_to_check is None:
        return UNKNOWN_MINS # max minute notif - could be higher

    dt_check = datetime.strptime(time_to_check, UTC_FMT)
    delta = dt_check - datetime.utcnow()
    return delta.seconds // 60  # Since deltatime can only give it in seconds, get how many more minutes

# From TGTG's UTC format to EST format - simple
async def utc_to_est(utc_time: str) -> str:
    if utc_time is None:
        return "None"

    dt_utc: datetime = datetime.strptime(utc_time, UTC_FMT)
    return dt_utc.astimezone(EST).strftime(EST_FMT) 

# Very messy. Helper function for now.. can be cleaned later
# From TGTG UTC format to EST format - verbose and readable to humans
async def easy_est(utc_time: str, short=False) -> str:
    if utc_time is None:
        return "None"

    utc_aware = pytz.utc.localize(datetime.strptime(utc_time, UTC_FMT))
    e: datetime = utc_aware.astimezone(EST)
    if short:
        e_now: datetime = datetime.now(pytz.utc).astimezone(EST)
        if e_now.day == e.day:
            short_day = "Today"
        elif e_now.day + 1 == e.day:
            short_day = "Tomorrow"
        else:
            # Format: TUES OCT 3
            short_day = f"{DAYS_OF_WEEK[utc_aware.weekday()]}. {utc_aware.strftime('%b')}. {e.day:02}"
        
        return f"{(e.hour % (12 if e.hour != 12 else 24))}:{e.minute:02} {PM if e.hour > 12 else AM} - {short_day}"
    else:
        return f"{(e.hour % (12 if e.hour != 12 else 24)):02}:{e.minute:02}:{e.second:02} {PM if e.hour > 12 else AM}, {e.day:02}-{e.month:02}-{e.year:02}"
