import {
  Bar, BarChart, CartesianGrid, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { SENTIMENTS, SENTIMENT_META } from '../../utils/constants.js';
import ChartTooltip from './ChartTooltip.jsx';

// Stacked weekly bars: how the positive/neutral/negative mix of a theme evolves.
export default function WeeklySentimentBars({ data, markWeek }) {
  const upToNow = data.filter((d) => d.total !== null);
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={upToNow} margin={{ top: 16, right: 16, bottom: 0, left: -16 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 12, fill: '#64748b' }} tickLine={false} axisLine={{ stroke: '#cbd5e1' }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#64748b' }} tickLine={false} axisLine={false} />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: '#f1f5f9' }} />
          <Legend itemSorter={null} formatter={(key) => SENTIMENT_META[key]?.label ?? key} wrapperStyle={{ fontSize: 12 }} />
          {markWeek && (
            <ReferenceLine x={`W${markWeek}`} stroke="#a42a2a" strokeDasharray="4 4"
              label={{ value: 'Change detected', position: 'top', fontSize: 11, fill: '#a42a2a' }} />
          )}
          {SENTIMENTS.map((s, i) => (
            <Bar key={s} dataKey={s} stackId="sentiment" fill={SENTIMENT_META[s].color} maxBarSize={48}
              radius={i === SENTIMENTS.length - 1 ? [4, 4, 0, 0] : 0} isAnimationActive={false} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
