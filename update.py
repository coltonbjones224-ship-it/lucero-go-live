import json, random, hashlib
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
ROOT=Path(__file__).parent
ROUTES=[('Red','Metro',440,3250,'#e53935'),('Green','Metro',390,2780,'#22c55e'),('Orange','Metro',325,2290,'#f28c28'),('Yellow','Metro',280,1950,'#eab308'),('Purple','Metro',245,1760,'#9333ea'),('Pink','Metro',200,1340,'#ec77c4'),('D4','Bus',160,940,'#64748b'),('D6','Bus',145,850,'#64748b'),('S34','Bus',125,730,'#64748b'),('A','Light rail',110,650,'#06b6d4'),('S','Light rail',95,580,'#06b6d4'),('C','Light rail',90,530,'#06b6d4'),('2','Metro',85,510,'#475569'),('P','Light rail',80,490,'#06b6d4'),('Southside Shuttle','Metro',76,410,'#475569')]
START=date(2026,10,14)
TZ=ZoneInfo('America/New_York')
def factor(hour):
    return (0.03 if hour<5 else 0.25 if hour<7 else 1.55 if hour<10 else 0.85 if hour<16 else 1.7 if hour<19 else 0.75 if hour<22 else 0.3)
def run(now=None):
    now=now or datetime.now(TZ)
    today=now.date(); elapsed=max(0,(today-START).days)
    result=[]
    for name,mode,base_trips,base_views,color in ROUTES:
        views=trips=minutes=0
        # Opening day baseline and deterministic hourly increments thereafter.
        for day in range(elapsed+1):
            d=START+timedelta(days=day)
            max_hour=now.hour if day==elapsed else 23
            for h in range(max_hour+1):
                seed=int.from_bytes(hashlib.sha256(f'{d}:{name}:{h}'.encode()).digest()[:8],'big')
                rng=random.Random(seed)
                mult=factor(h) * (0.78 if d.weekday()>=5 else 1)
                day_mod=0.85+rng.random()*0.3
                hour_frac=(now.minute+1)/60 if day==elapsed and h==max_hour else 1
                # Approximate first-day full totals using base values as scale.
                normalization=sum(factor(x) for x in range(24))
                t=round(base_trips*mult*day_mod*hour_frac/normalization)
                v=round(base_views*mult*day_mod*hour_frac/normalization)
                dur={'Metro':28,'Bus':19,'Light rail':22}[mode]
                trips+=t; views+=v; minutes+=round(t*dur*(0.85+rng.random()*0.3))
        # Daily values calculated separately from cumulative by using previous day's endpoint
        result.append(dict(id=name,mode=mode,color=color,trips=trips,views=views,go_minutes=minutes,points=minutes*10+views))
    previous=None
    if elapsed>0:
        previous=run(datetime.combine(today-timedelta(days=1),datetime.max.time(),tzinfo=TZ))['lines']
    for r in result:
        old=next((x for x in previous if x['id']==r['id']),None) if previous else None
        r['today_views']=r['views']-(old['views'] if old else 0)
        r['today_points']=r['points']-(old['points'] if old else 0)
        r['today_trips']=r['trips']-(old['trips'] if old else 0)
    result.sort(key=lambda x:x['views'],reverse=True)
    return {'generated_at':now.isoformat(timespec='minutes'),'simulation_date':str(today),'day_number':elapsed+1,'note':'Fictional deterministic hourly simulation. GO points = 10 per GO minute + 1 per view.','lines':result}
if __name__=='__main__':
    (ROOT/'data.json').write_text(json.dumps(run(),indent=2)+'\n')
    print('Updated data.json')
