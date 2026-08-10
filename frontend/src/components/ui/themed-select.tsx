"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export interface SelectOption {
  value: string;
  label: string;
}

// Native <select> option lists are painted by the OS, so in dark mode Chrome
// gives you a white popup our light text vanishes into. This renders the list
// as real elements using the popover tokens.
export function ThemedSelect({
  id,
  value,
  onChange,
  options,
  placeholder = "Select…",
  className,
  "aria-label": ariaLabel,
  "aria-invalid": ariaInvalid,
  "aria-describedby": ariaDescribedBy,
}: {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  className?: string;
  "aria-label"?: string;
  "aria-invalid"?: boolean;
  "aria-describedby"?: string;
}) {
  return (
    <Select
      items={options}
      value={value}
      onValueChange={(next) => onChange((next as string) ?? "")}
    >
      <SelectTrigger
        id={id}
        aria-label={ariaLabel}
        aria-invalid={ariaInvalid}
        aria-describedby={ariaDescribedBy}
        className={cn("h-9 w-full bg-surface-raised px-3", className)}
      >
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>

      <SelectContent className="max-h-72">
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
