import { useEffect, useId, useRef } from 'react';
import { X } from 'lucide-react';

// Built on the native <dialog> so focus trapping, Escape and inert background
// content come from the browser rather than hand-rolled key handling.
export default function Modal({ open, onClose, title, description, children, footer }) {
  const ref = useRef(null);
  const titleId = useId();

  useEffect(() => {
    if (!open) return undefined;
    const dialog = ref.current;
    if (dialog && !dialog.open) dialog.showModal();
    // showModal makes the page inert but does not stop it scrolling behind.
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = previous; };
  }, [open]);

  if (!open) return null;

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onClose={onClose}
      onClick={event => { if (event.target === ref.current) onClose(); }}
      className="m-auto w-[min(92vw,720px)] max-h-[85vh] overflow-hidden rounded-xl bg-white p-0 text-slate-800 shadow-xl ring-1 ring-slate-200 backdrop:bg-navy-950/50"
    >
      {/* Column layout keeps the header and footer fixed while the body scrolls. */}
      <div className="flex max-h-[85vh] flex-col">
        <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <div className="min-w-0">
            <h2 id={titleId} className="text-base font-semibold text-slate-900">{title}</h2>
            {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
          >
            <X className="size-5" aria-hidden />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="border-t border-slate-100 px-5 py-3">{footer}</div>}
      </div>
    </dialog>
  );
}
