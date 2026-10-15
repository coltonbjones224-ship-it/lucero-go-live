import json, random, hashlib, math
from datetime import datetime, date, timedelta, time
from zoneinfo import ZoneInfo
from pathlib import Path

ROOT = Path(__file__).parent
TZ = ZoneInfo('America/New_York')
START = date(2026, 10, 14)

# (line, mode, initial GO trips/day, initial views/day, color)
ROUTES = [
    ('Red','Metro',440,3250,'#e53935'),
    ('Green','Metro',390,2780,'#22c55e'),
    ('Orange','Metro',325,2290,'#f28c28'),
    ('Yellow','Metro',280,1950,'#eab308'),
    ('Purple','Metro',245,1760,'#9333ea'),
    ('Pink','Metro',200,1340,'#ec77c4'),
    ('D4','Bus',160,940,'#64748b'),
    ('D6','Bus',145,850,'#64748b'),
    ('S34','Bus',125,730,'#64748b'),
    ('A','Light rail',110,650,'#06b6d4'),
    ('S','Light rail',95,580,'#06b6d4'),
    ('C','Light rail',90,530,'#06b6d4'),
    ('2','Metro',85,510,'#475569'),
    ('P','Light rail',80,490,'#06b6d4'),
    ('Southside Shuttle','Metro',76,410,'#475569'),
]

# Regional context, not 1.5m people riding transit every day.
METRO_POPULATION = 1_500_000
DISTRICT_POPULATIONS = {
    'downtown_core': 300_000,
    'north_shopping_office_zoo': 50_000,
    'west_residential': 30_000,
    'south_mixed_use_arena': 15_000,
    'east_nightlife_office': 10_000,
    'north_manassas_state': 8_000,
    'west_young_university': 7_000,
}
S34_CORRIDOR_POPULATION = 3_000  # Already included in metro population.

# Preliminary demand multipliers. These are estimates, not observed passenger counts.
# Park-and-ride traffic makes Green, Orange, Yellow stronger than local residents alone imply.
DEMAND = {
    'Red': 1.12, 'Green': 1.20, 'Orange': 1.15, 'Yellow': 1.19,
    'Purple': 1.05, 'Pink': 0.96, '2': 0.96,
    'Southside Shuttle': 0.94,
    'D4': 1.10, 'D6': 1.10, 'S34': 0.32,
    'A': 1.02, 'S': 1.04, 'C': 1.05, 'P': 0.99,
}

# Peak windows are assumptions pending exact agency service definitions.
PEAK_WINDOWS = ((7, 10), (16, 19))
ALWAYS_ON = {'Green', 'Yellow', 'Southside Shuttle', 'D6'}

def is_peak(hour):
    return any(a <= hour < b for a, b in PEAK_WINDOWS)

def weekday_factor(hour):
    return (0.03 if hour < 5 else 0.25 if hour < 7 else 1.55 if hour < 10
            else 0.85 if hour < 16 else 1.70 if hour < 19
            else 0.75 if hour < 22 else 0.30)

def between(minute, start, end):
    return start <= minute < end

def service_state(name, dt):
    """Approximate service availability at a local time, allowing end-of-line overruns."""
    h, m = dt.hour, dt.minute
    minute = h * 60 + m
    if name in ALWAYS_ON:
        return 'overnight' if minute < 270 else 'running'
    if name == 'D4':
        # Direction-specific departures are tracked in metadata below.
        return 'running' if between(minute, 370, 1335) else 'closed'
    if name == 'S34':
        return 'running' if between(minute, 350, 1290) else 'closed'
    if name in {'A','S','C','P'}:
        # Friday/Saturday: last departure around midnight; service may finish later.
        end = 1440 if dt.weekday() in (4,5) else 1380
        return 'running' if between(minute, 330, end) else 'closed'
    # Non-24h Metro: 4:30 AM to midnight (approximate last departures).
    return 'running' if minute >= 270 else 'closed'

def frequency(name, dt):
    minute = dt.hour * 60 + dt.minute
    if name == 'D4':
        return 15 if is_peak(dt.hour) else 20
    if name == 'S34':
        return 20 if is_peak(dt.hour) else 30
    if name == 'D6':
        # 10:15 PM to midnight, and 4:30 AM until D4 resumes: 20 minutes.
        # Daytime frequency isn't yet specified; use the D4-like provisional pattern.
        if minute < 270:
            return 25
        if minute < 370 or minute >= 1335:
            return 20
        return 15 if is_peak(dt.hour) else 20
    return None

def hour_activity(name, dt):
    if service_state(name, dt) == 'closed':
        return 0.0
    hour = dt.hour
    f = weekday_factor(hour) * (0.78 if dt.weekday() >= 5 else 1.0)
    # Corridor-specific modifiers. Avoid treating population as boardings.
    if name in {'Green','Orange','Yellow'} and dt.weekday() < 5 and is_peak(hour):
        f *= 1.18  # Manassas State / Gage Gehris park-and-ride
    if name == 'Yellow' and (hour < 5 or hour >= 22):
        f *= 1.50  # Overnight Government Center-Montclair replacement segment
    if name in {'Red','Orange'} and hour >= 22:
        f *= 1.10  # Late arrivals before shutdown
    if name in {'Purple','Red','Orange','Yellow'} and dt.weekday() >= 4 and (hour >= 19 or hour < 3):
        f *= 1.22  # Montclair nightlife / zoo visitors (proxy)
    if name in {'D4','D6'} and (hour < 7 or hour >= 20):
        f *= 1.10  # Hospital shift changes and visitors
    if name == 'S34':
        f *= 0.90  # Low-density corridor
    return f

def route_info(name, now):
    info = {'status': service_state(name, now), 'frequency_minutes': frequency(name, now)}
    if name == 'Yellow':
        overnight = (now.hour * 60 + now.minute) < 270  # Midnight-4:30 AM extension
        info.update(terminus='Montclair' if overnight else 'Government Center',
                    overnight_extension_active=overnight,
                    replaces_overnight=['Red','Orange'])
    if name == 'D6':
        info.update(via=['Government Center'], terminus='Central Hospital',
                    additional_trip_minutes=10, service='24/7')
    if name == 'D4':
        info.update(first_northbound='06:20',last_northbound='21:55',
                    first_southbound='06:10',last_southbound='22:15')
    if name == 'S34':
        info.update(first_northbound='05:50',last_northbound='21:30',
                    first_southbound='06:15',last_southbound='21:05',
                    corridor_population_max=S34_CORRIDOR_POPULATION)
    if name in {'Green','Southside Shuttle'}:
        info['shared_alignment_with'] = 'Southside Shuttle' if name == 'Green' else 'Green'
    return info

def seed_rng(d, name, hour):
    seed = int.from_bytes(hashlib.sha256(f'{d}:{name}:{hour}:v2'.encode()).digest()[:8], 'big')
    return random.Random(seed)

def hour_counts(name, mode, base_trips, base_views, d, hour):
    dt = datetime.combine(d, time(hour,0), tzinfo=TZ)
    weight = hour_activity(name, dt)
    if weight <= 0:
        return (0,0,0)
    rng = seed_rng(d, name, hour)
    # Normalize by route-specific service and day demand; route baselines remain plausible.
    normalizer = sum(hour_activity(name, datetime.combine(d,time(h),tzinfo=TZ)) for h in range(24))
    if not normalizer:
        return (0,0,0)
    scale = DEMAND[name] * (0.78 if d.weekday() >= 5 else 1.0)
    # The normalized hourly weights distribute each line's adjusted daily activity.
    fluctuation = 0.85 + rng.random() * 0.30
    t = round(base_trips * scale * weight / normalizer * fluctuation)
    v = round(base_views * scale * weight / normalizer * fluctuation)
    duration = {'Metro':28, 'Bus':19, 'Light rail':22}[mode]
    if name == 'D6':
        duration += 10
    if name == 'Yellow' and (hour < 5):
        duration += 12  # Provisional extension travel time; confirm later.
    minutes = round(t * duration * (0.85 + rng.random()*0.30))
    return (t,v,minutes)

def run(now=None):
    now = (now or datetime.now(TZ)).astimezone(TZ)
    today = now.date()
    if today < START:
        raise ValueError('Simulation date precedes opening day')
    elapsed = (today - START).days
    lines = []
    for name,mode,base_trips,base_views,color in ROUTES:
        totals = [0,0,0]
        today_counts = [0,0,0]
        last_hour_counts = [0,0,0]
        for day in range(elapsed+1):
            d = START + timedelta(days=day)
            final_hour = now.hour if d == today else 23
            for h in range(final_hour+1):
                c = hour_counts(name,mode,base_trips,base_views,d,h)
                # Partial current hour: same deterministic snapshot grows until full hour.
                fraction = (now.minute+1)/60 if d == today and h == now.hour else 1.0
                c = [round(x*fraction) for x in c]
                for k in range(3):
                    totals[k] += c[k]
                    if d == today:
                        today_counts[k] += c[k]
                if d == today and h == now.hour:
                    last_hour_counts = c
        trips,views,minutes = totals
        day_trips,day_views,day_minutes = today_counts
        status = route_info(name, now)
        lines.append(dict(id=name,mode=mode,color=color,trips=trips,views=views,
                          go_minutes=minutes,points=minutes*10+views,
                          today_trips=day_trips,today_views=day_views,
                          today_go_minutes=day_minutes,today_points=day_minutes*10+day_views,
                          current_hour_trips=last_hour_counts[0],
                          current_hour_views=last_hour_counts[1],
                          current_hour_points=last_hour_counts[2]*10+last_hour_counts[1],
                          **status))
    lines.sort(key=lambda x: x['views'],reverse=True)
    return {'generated_at':now.isoformat(timespec='minutes'),
            'simulation_date':str(today),'day_number':elapsed+1,
            'note':'Fictional deterministic simulation, provisional demand assumptions. GO points = 10 per GO minute + 1 per view.',
            'metro_population':METRO_POPULATION,
            'mapped_district_population':sum(DISTRICT_POPULATIONS.values()),
            'district_populations':DISTRICT_POPULATIONS,
            'lines':lines}

if __name__=='__main__':
    (ROOT/'data.json').write_text(json.dumps(run(),indent=2)+'\n')
    print('Updated data.json')