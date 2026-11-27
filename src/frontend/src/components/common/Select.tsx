import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { cn } from '../../utils/cn';
import { Check, ChevronDown } from 'lucide-react';

/**
 * Lightweight Radix/shadcn-style Select.
 *
 * Usage:
 *   <Select value={v} onValueChange={setV}>
 *     <SelectTrigger><SelectValue placeholder="Pick one" /></SelectTrigger>
 *     <SelectContent>
 *       <SelectItem value="a">Option A</SelectItem>
 *     </SelectContent>
 *   </Select>
 */

interface SelectContextType {
  value: string;
  onValueChange: (value: string) => void;
  open: boolean;
  setOpen: (open: boolean) => void;
  labels: Map<string, React.ReactNode>;
}

const SelectContext = createContext<SelectContextType | null>(null);

function useSelectContext(): SelectContextType {
  const ctx = useContext(SelectContext);
  if (!ctx) {
    throw new Error('Select components must be used within <Select>');
  }
  return ctx;
}

// Walk the children tree and collect value -> label for every <SelectItem>,
// so <SelectValue /> can show the selected label even while the list is closed.
function collectLabels(children: React.ReactNode, labels: Map<string, React.ReactNode>) {
  React.Children.forEach(children, (child) => {
    if (!React.isValidElement(child)) return;
    const props = child.props as { value?: unknown; children?: React.ReactNode };
    if (child.type === SelectItem && typeof props.value === 'string') {
      labels.set(props.value, props.children);
    } else if (props.children) {
      collectLabels(props.children, labels);
    }
  });
}

interface SelectProps {
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  className?: string;
  children?: React.ReactNode;
}

function Select({ value, defaultValue = '', onValueChange, className, children }: SelectProps) {
  const [internal, setInternal] = useState(defaultValue);
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const current = value !== undefined ? value : internal;

  const handleChange = (next: string) => {
    if (value === undefined) setInternal(next);
    onValueChange?.(next);
    setOpen(false);
  };

  // Close on outside click or Escape
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const labels = new Map<string, React.ReactNode>();
  collectLabels(children, labels);

  return (
    <SelectContext.Provider value={{ value: current, onValueChange: handleChange, open, setOpen, labels }}>
      <div ref={rootRef} className={cn('relative', className)}>
        {children}
      </div>
    </SelectContext.Provider>
  );
}

const SelectTrigger = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement>>(
  ({ className, children, onClick, ...props }, ref) => {
    const { open, setOpen } = useSelectContext();
    return (
      <button
        ref={ref}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        className={cn(
          'flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
          className
        )}
        onClick={(e) => {
          onClick?.(e);
          setOpen(!open);
        }}
        {...props}
      >
        {children}
        <ChevronDown className="h-4 w-4 opacity-50" />
      </button>
    );
  }
);
SelectTrigger.displayName = 'SelectTrigger';

const SelectValue = React.forwardRef<
  HTMLSpanElement,
  React.HTMLAttributes<HTMLSpanElement> & { placeholder?: string }
>(({ className, placeholder, children, ...props }, ref) => {
  const { value, labels } = useSelectContext();
  const label = labels.has(value) ? labels.get(value) : undefined;
  const hasSelection = label !== undefined && label !== null;
  return (
    <span
      ref={ref}
      className={cn('truncate', !hasSelection && 'text-muted-foreground', className)}
      {...props}
    >
      {children ?? (hasSelection ? label : placeholder)}
    </span>
  );
});
SelectValue.displayName = 'SelectValue';

const SelectContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { position?: 'popper' | 'inline' }
>(({ className, children, position: _position, ...props }, ref) => {
  const { open } = useSelectContext();
  if (!open) return null;
  return (
    <div
      ref={ref}
      role="listbox"
      className={cn(
        'absolute left-0 top-full z-50 mt-1 max-h-72 min-w-full overflow-auto rounded-md border bg-popover text-popover-foreground shadow-md',
        className
      )}
      {...props}
    >
      <div className="p-1">{children}</div>
    </div>
  );
});
SelectContent.displayName = 'SelectContent';

interface SelectItemProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onSelect'> {
  value: string;
  disabled?: boolean;
}

const SelectItem = React.forwardRef<HTMLDivElement, SelectItemProps>(
  ({ className, children, value, disabled, onClick, ...props }, ref) => {
    const { value: selected, onValueChange } = useSelectContext();
    const isSelected = selected === value;
    return (
      <div
        ref={ref}
        role="option"
        aria-selected={isSelected}
        aria-disabled={disabled}
        className={cn(
          'relative flex w-full cursor-pointer select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none hover:bg-accent hover:text-accent-foreground',
          isSelected && 'bg-accent/50',
          disabled && 'pointer-events-none opacity-50',
          className
        )}
        onClick={(e) => {
          onClick?.(e);
          if (!disabled) onValueChange(value);
        }}
        {...props}
      >
        <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
          {isSelected && <Check className="h-4 w-4" />}
        </span>
        {children}
      </div>
    );
  }
);
SelectItem.displayName = 'SelectItem';

export { Select, SelectTrigger, SelectContent, SelectItem, SelectValue };
