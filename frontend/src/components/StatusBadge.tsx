import React from 'react';
import { CheckCircle2, XCircle, HelpCircle, MinusCircle } from 'lucide-react';
import { StageStatus } from '../types';

interface StatusBadgeProps {
  status: StageStatus | string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md', className = '' }) => {
  const norm = (status || '').toUpperCase();

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-sm px-2.5 py-1 gap-1.5',
    lg: 'text-base px-3 py-1.5 gap-2 font-medium',
  };

  const iconSizes = {
    sm: 13,
    md: 15,
    lg: 18,
  };

  const isPass = norm === 'PASS' || norm === 'VERIFIED';
  const isFail = norm === 'FAIL' || norm === 'UNRESOLVED';
  const isUnknown = norm === 'UNKNOWN' || norm === 'UNDETERMINED';
  const isNotReached = norm === 'NOT REACHED' || norm === 'NOT_REACHED' || norm === 'NOT_EVALUABLE' || norm === 'NOT EVALUABLE';

  let config = {
    color: 'bg-gray-800 text-gray-300 border-gray-700',
    icon: <MinusCircle size={iconSizes[size]} className="shrink-0 text-gray-400" />,
    text: norm || 'UNKNOWN',
    ariaLabel: `Status: ${norm || 'UNKNOWN'}`,
  };

  if (isPass) {
    config = {
      color: 'bg-emerald-950/80 text-emerald-300 border-emerald-700/60',
      icon: <CheckCircle2 size={iconSizes[size]} className="shrink-0 text-emerald-400" />,
      text: norm,
      ariaLabel: `Status: ${norm}`,
    };
  } else if (isFail) {
    config = {
      color: 'bg-red-950/80 text-red-300 border-red-700/60',
      icon: <XCircle size={iconSizes[size]} className="shrink-0 text-red-400" />,
      text: norm,
      ariaLabel: `Status: ${norm}`,
    };
  } else if (isUnknown) {
    config = {
      color: 'bg-amber-950/80 text-amber-300 border-amber-700/60',
      icon: <HelpCircle size={iconSizes[size]} className="shrink-0 text-amber-400" />,
      text: norm,
      ariaLabel: `Status: ${norm}`,
    };
  } else if (isNotReached) {
    config = {
      color: 'bg-slate-800/80 text-slate-400 border-slate-700/60',
      icon: <MinusCircle size={iconSizes[size]} className="shrink-0 text-slate-400" />,
      text: norm.replace('_', ' '),
      ariaLabel: `Status: ${norm.replace('_', ' ')}`,
    };
  }

  return (
    <span
      role="status"
      aria-label={config.ariaLabel}
      className={`inline-flex items-center rounded-md border font-mono tracking-tight font-semibold ${sizeClasses[size]} ${config.color} ${className}`}
    >
      {config.icon}
      <span>{config.text}</span>
    </span>
  );
};
