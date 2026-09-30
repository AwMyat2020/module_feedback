import { useId } from 'react';
import { Info } from 'lucide-react';

// Hover or keyboard-focus to reveal. `align` keeps it on-screen near edges.
export default function InfoTooltip({ text, align = 'center' }) {
  const id = useId();
  const position = {
    center: 'left-1/2 -translate-x-1/2',
    left: 'left-0',
    right: 'right-0',
  }[align];

  return (
    <span className="group relative inline-flex">
      <button
        type="button"
        aria-describedby={id}
        aria-label="More information"
        className="rounded-full text-slate-400 hover:text-slate-600 focus-visible:text-slate-600"
      >
        <Info className="size-4" aria-hidden />
      </button>
      <span
        id={id}
        role="tooltip"
        className={`pointer-events-none invisible absolute bottom-full z-30 mb-2 w-60 rounded-lg bg-navy-950 px-3 py-2 text-xs font-normal leading-relaxed text-white opacity-0 shadow-lg transition-opacity group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100 ${position}`}
      >
        {text}
      </span>
    </span>
  );
}
