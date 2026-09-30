import { useState } from 'react';
import { useCoreData } from '../services/coreService.js';
import { Card } from '../components/ui/Card.jsx';
import Button from '../components/ui/Button.jsx';
import WeeklySentimentBars from '../components/charts/WeeklySentimentBars.jsx';

const sentiments = ['positive','neutral','negative'];
export default function StaffAnalytics({ periodId }) {
  const [filters,setFilters]=useState({theme:'',sentiment:'',teaching_week:''});
  const query=new URLSearchParams(Object.entries(filters).filter(([,v])=>v)).toString();
  const {data,error,refresh}=useCoreData(`/api/staff/periods/${encodeURIComponent(periodId)}/analytics?${query}`);
  const a=data?.analytics;
  function filter(key,value) { setFilters(old=>({...old,[key]:value})); }
  return <div className="space-y-6">
    <Card className="p-6"><div className="mi-card-top"><h2 className="text-xl font-semibold">Module analytics</h2><Button variant="secondary" onClick={refresh}>Refresh analytics</Button></div>
      <p className="mi-muted mt-3">Pre-populated sample analysis · no machine learning. New or edited feedback remains unanalysed until labels are supplied.</p>
      <div className="mi-analytics-filters">
        <label>Theme<select value={filters.theme} onChange={e=>filter('theme',e.target.value)}><option value="">All themes</option>{['Workload','Lecturer Attitude','Lesson Duration','Teaching Quality','Class Timing','Lab Instructions','Assessment','Learning Materials','Technical Issues','Others'].map(t=><option key={t}>{t}</option>)}</select></label>
        <label>Sentiment<select value={filters.sentiment} onChange={e=>filter('sentiment',e.target.value)}><option value="">All sentiments</option>{sentiments.map(s=><option key={s} value={s}>{s[0].toUpperCase()+s.slice(1)}</option>)}</select></label>
        <label>Teaching week<select value={filters.teaching_week} onChange={e=>filter('teaching_week',e.target.value)}><option value="">All weeks</option>{Array.from({length:14},(_,i)=>i+1).map(w=><option key={w} value={w}>Week {w}</option>)}</select></label>
      </div><Button variant="subtle" onClick={()=>setFilters({theme:'',sentiment:'',teaching_week:''})}>Clear filters</Button>
    </Card>
    {error && <p role="alert" className="mi-error">{error}</p>}
    {!data && !error && <p role="status">Loading analytics…</p>}
    {a && <>
      <Card className="p-6"><h3 className="mi-muted">Total submitted responses · module</h3><p className="text-3xl font-semibold mt-2">{a.total_responses ?? 'Hidden'}</p></Card>
      {a.suppressed ? <Card className="p-6"><p role="status">{a.message}</p><p className="mi-muted mt-2">Analysis also requires at least five labelled responses. Try clearing filters. No detailed counts, charts or comments are returned for a hidden group.</p></Card> : <>
        <p className="mi-muted">{a.selected_responses} submitted responses match these filters; {a.analysed_responses} have analysis and {a.unanalysed_responses} are unanalysed. Sentiment percentages use labelled matching responses only. Percentages are rounded.</p>
        <div className="mi-module-grid">{sentiments.map(s=><Card className="p-6" key={s}><h3 className="capitalize">{s}</h3><p className="text-3xl font-semibold mt-2">{a.sentiment_percentages[s]}%</p><p className="mi-muted">of analysed matching responses</p></Card>)}</div>
        <Card className="p-6"><h2 className="text-xl font-semibold">Top 5 most discussed themes</h2><p className="mi-muted mt-2">{a.theme_note} One pre-populated theme per response. Mention percentages use all submitted responses matching the current filters.</p>
          <div className="overflow-x-auto"><table className="mi-analytics-table"><caption className="sr-only">Theme mentions and sentiment percentages within each theme</caption><thead><tr><th>Theme</th><th>Mentions</th><th>Responses mentioning theme</th><th>Positive</th><th>Neutral</th><th>Negative</th></tr></thead><tbody>{a.themes.map(t=><tr key={t.theme}><th scope="row">{t.theme}</th><td>{t.mentions}</td><td>{t.response_percentage}%</td>{sentiments.map(s=><td key={s}>{t.sentiment_percentages[s]}%</td>)}</tr>)}</tbody></table></div>
          {!a.themes.length && <p className="mi-muted mt-4">Theme details are hidden to protect anonymity.</p>}
          {a.themes.map(t=><p className="mi-muted mt-2" key={t.theme}>{t.response_percentage}% of submitted responses{query ? ' matching these filters' : ''} mentioned {t.theme.toLowerCase()}.</p>)}
        </Card>
        <Card className="p-6"><h2 className="text-xl font-semibold">Weekly sentiment trend</h2><p className="mi-muted mt-2 mb-4">Counts of analysed matching responses by teaching week. Weeks with fewer than five responses are hidden, not zero.</p>
          {a.weeks.some(w=>!w.suppressed) ? <WeeklySentimentBars data={a.weeks} /> : <p>Weekly details are hidden to protect anonymity.</p>}
          <details className="mt-4"><summary>Accessible weekly data</summary><div className="overflow-x-auto"><table className="mi-analytics-table"><thead><tr><th>Week</th><th>Total</th><th>Positive</th><th>Neutral</th><th>Negative</th></tr></thead><tbody>{a.weeks.map(w=><tr key={w.week}><th>{w.week}</th>{w.suppressed ? <td colSpan={4}>Hidden to protect anonymity</td> : <><td>{w.total}</td>{sentiments.map(s=><td key={s}>{w[s]}</td>)}</>}</tr>)}</tbody></table></div></details>
        </Card>
        <Card className="p-6"><h2 className="text-xl font-semibold">Representative anonymous comments</h2><p className="mi-muted mt-2">Illustrative excerpts selected deterministically from eligible groups, not AI summaries. Each displayed theme/sentiment/week group has at least five responses. Up to six excerpts are shown; selection is not a statistical sample.</p>
          {!a.comments.length && <p className="mt-4">Comments are hidden to protect anonymity in detailed groups.</p>}
          {a.comments.map((c,i)=><article key={i} className="mi-staff-feedback"><p className="mi-muted mb-2">{c.theme} · {c.sentiment} · Week {c.teaching_week}</p><blockquote className="mi-feedback-text">{c.comment}</blockquote></article>)}
        </Card>
      </>}
    </>}
  </div>;
}
