import { Link } from 'react-router';
import { LoaderCircle } from 'lucide-react';

const VARIANTS = {
  primary: 'bg-brand-700 text-white hover:bg-brand-600 disabled:bg-slate-400',
  secondary: 'bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50 disabled:text-slate-400',
  ghost: 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
  subtle: 'bg-brand-50 text-brand-700 hover:bg-brand-100',
};

const SIZES = {
  sm: 'h-8 px-3 text-sm gap-1.5',
  md: 'h-10 px-4 text-sm gap-2',
  lg: 'h-11 px-5 text-base gap-2',
};

export default function Button({
  variant = 'primary', size = 'md', to, loading = false, icon: Icon, className = '', children, disabled, ...props
}) {
  const classes = `inline-flex items-center justify-center rounded-lg font-medium transition-colors disabled:cursor-not-allowed ${VARIANTS[variant]} ${SIZES[size]} ${className}`;
  const content = (
    <>
      {loading ? <LoaderCircle className="size-4 animate-spin" aria-hidden /> : Icon && <Icon className="size-4" aria-hidden />}
      {children}
    </>
  );
  if (to) {
    return <Link to={to} className={classes} {...props}>{content}</Link>;
  }
  return (
    <button type="button" className={classes} disabled={disabled || loading} {...props}>
      {content}
    </button>
  );
}
