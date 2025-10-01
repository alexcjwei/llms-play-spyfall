import React from 'react';

interface StatusBadgeProps {
  children: React.ReactNode;
  variant?: 'green' | 'red' | 'blue' | 'yellow' | 'purple' | 'gray' | 'orange';
  size?: 'xs' | 'sm' | 'md';
  className?: string;
}

const variantClasses = {
  green: 'bg-green-100 text-green-800',
  red: 'bg-red-100 text-red-800',
  blue: 'bg-blue-100 text-blue-800',
  yellow: 'bg-yellow-100 text-yellow-800',
  purple: 'bg-purple-100 text-purple-800',
  gray: 'bg-gray-100 text-gray-800',
  orange: 'bg-orange-100 text-orange-800',
};

const sizeClasses = {
  xs: 'px-1 py-0.5 text-xs',
  sm: 'px-2 py-1 text-xs',
  md: 'px-3 py-1 text-sm',
};

export function StatusBadge({
  children,
  variant = 'gray',
  size = 'sm',
  className = ''
}: StatusBadgeProps) {
  const classes = [
    'inline-flex items-center font-medium rounded',
    variantClasses[variant],
    sizeClasses[size],
    className
  ].filter(Boolean).join(' ');

  return (
    <span className={classes}>
      {children}
    </span>
  );
}