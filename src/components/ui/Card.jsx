import InfoTooltip from './InfoTooltip.jsx';

export function Card({ className = '', children, ...props }) {
  return (
    <section className={`rounded-xl bg-white ring-1 ring-slate-200 shadow-sm ${className}`} {...props}>
      {children}
    </section>
  );
}

export function CardHeader({ title, description, tooltip, actions }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
      <div className="min-w-0">
        <h2 className="flex items-center gap-1.5 text-base font-semibold text-slate-900">
          {title}
          {tooltip && <InfoTooltip text={tooltip} />}
        </h2>
        {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
