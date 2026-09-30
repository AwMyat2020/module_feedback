import { Link } from 'react-router';
import { ChevronRight } from 'lucide-react';

export default function PageHeader({ title, subtitle, breadcrumbs = [], actions, meta }) {
  return (
    <div className="mb-6">
      {breadcrumbs.length > 0 && (
        <nav aria-label="Breadcrumb" className="mb-2">
          <ol className="flex flex-wrap items-center gap-1 text-sm text-slate-500">
            {breadcrumbs.map((crumb, i) => (
              <li key={crumb.label} className="flex items-center gap-1">
                {i > 0 && <ChevronRight className="size-3.5 text-slate-400" aria-hidden />}
                {crumb.to ? <Link to={crumb.to} className="hover:text-slate-800 hover:underline">{crumb.label}</Link> : <span aria-current="page" className="text-slate-700">{crumb.label}</span>}
              </li>
            ))}
          </ol>
        </nav>
      )}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
          {meta && <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-slate-600">{meta}</div>}
        </div>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </div>
    </div>
  );
}
