"""Pure aggregation and privacy policy, independent of UI and future ML providers."""
from collections import Counter
from contextlib import closing
import re
from urllib.parse import urlsplit, parse_qs
from auth import AuthError
from database import connect
from core import period_for

THRESHOLD = 5
THEMES = ['Workload','Lecturer Attitude','Lesson Duration','Teaching Quality','Class Timing','Lab Instructions','Assessment','Learning Materials','Technical Issues','Others']
SENTIMENTS = ['positive','neutral','negative']
PRIVACY_MESSAGE = 'Results are hidden to protect anonymity. At least 5 responses are required for this module or detailed group.'

def mix(rows):
    counts=Counter(r['sentiment'] for r in rows)
    return {key:round(100*counts[key]/len(rows),1) for key in SENTIMENTS}

def aggregate(rows, filters=None):
    filters=filters or {}
    chosen=[r for r in rows if all(str(r.get(key))==str(value) for key,value in filters.items() if value)]
    analysed=[r for r in chosen if r.get('sentiment') in SENTIMENTS and r.get('theme') in THEMES and r.get('teaching_week') in range(1,15)]
    result={'suppressed':len(rows)<THRESHOLD or len(chosen)<THRESHOLD or len(analysed)<THRESHOLD,
            'threshold':THRESHOLD,'filters':filters,'options':{'themes':THEMES,'sentiments':SENTIMENTS,'weeks':list(range(1,15))},
            'total_responses':len(rows) if len(rows)>=THRESHOLD else None,
            'message':PRIVACY_MESSAGE,'source':'Pre-populated sample analysis; no ML is running.'}
    if result['suppressed']:
        return result
    result.update(selected_responses=len(chosen),analysed_responses=len(analysed),unanalysed_responses=len(chosen)-len(analysed),
                  sentiment_percentages=mix(analysed),themes=[],weeks=[],comments=[])
    groups={theme:[r for r in analysed if r['theme']==theme] for theme in THEMES}
    # Do not rank or publish counts for themes below threshold.
    eligible=sorted(((theme,group) for theme,group in groups.items() if len(group)>=THRESHOLD),key=lambda item:(-len(item[1]),item[0]))
    for theme,group in eligible[:5]:
        result['themes'].append({'theme':theme,'mentions':len(group),'response_percentage':round(100*len(group)/len(chosen),1),'sentiment_percentages':mix(group)})
    result['theme_note']='Only themes with at least 5 matching responses are eligible for the top five.'
    for week in range(1,15):
        group=[r for r in analysed if r['teaching_week']==week]
        if len(group)<THRESHOLD:
            result['weeks'].append({'week':week,'label':f'W{week}','suppressed':True,'total':None})
        else:
            counts=Counter(r['sentiment'] for r in group)
            result['weeks'].append({'week':week,'label':f'W{week}','suppressed':False,'total':len(group),**{s:counts[s] for s in SENTIMENTS}})
    # Comments additionally need a safe joint theme/sentiment/week cohort.
    cohorts={}
    for r in analysed:
        key=(r['theme'],r['sentiment'],r['teaching_week'])
        cohorts.setdefault(key,[]).append(r)
    for key,group in sorted(cohorts.items()):
        if len(group)>=THRESHOLD:
            # Deterministic illustrative selection, not an AI summary or statistical sample.
            text=sorted({r['comment'] for r in group})[0]
            result['comments'].append({'comment':text,'theme':key[0],'sentiment':key[1],'teaching_week':key[2]})
    result['comments']=result['comments'][:6]
    return result

def analytics_request(path,user,method,url):
    parsed=urlsplit(url)
    match=re.fullmatch(r'/api/staff/periods/([^/]+)/analytics',parsed.path)
    if not match: return None
    if user['role']!='staff': raise AuthError(403,'Staff access is required.')
    if method!='GET': raise AuthError(405,'Method not allowed.')
    query=parse_qs(parsed.query,keep_blank_values=True)
    if any(key not in ('theme','sentiment','teaching_week') or len(value)!=1 for key,value in query.items()):
        raise AuthError(400,'Invalid analytics filters.')
    filters={key:values[0] for key,values in query.items() if values[0]}
    if filters.get('theme') and filters['theme'] not in THEMES: raise AuthError(400,'Unknown theme filter.')
    if filters.get('sentiment') and filters['sentiment'] not in SENTIMENTS: raise AuthError(400,'Unknown sentiment filter.')
    if filters.get('teaching_week') and filters['teaching_week'] not in [str(n) for n in range(1,15)]: raise AuthError(400,'Teaching week must be 1 to 14.')
    with closing(connect(path)) as db:
        period=period_for(db,user,match[1])
        rows=[dict(r) for r in db.execute('''SELECT f.comment,a.sentiment,a.theme,a.teaching_week
            FROM feedback f LEFT JOIN feedback_analysis a ON a.feedback_id=f.id WHERE f.period_id=?''',(match[1],))]
        return 200, {'module':{'code':period['code'],'name':period['name'],'trimester':period['trimester']},'analytics':aggregate(rows,filters)}
