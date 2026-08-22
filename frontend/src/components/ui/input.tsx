import * as React from "react"
import { Input as InputPrimitive } from "@base-ui/react/input"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      className={cn(
        // Buttons are raised, fields are recessed. The 1px inset shadow is the
        // whole trick: it makes an input read as a slot cut into the page
        // rather than another rectangle sitting on it, which is what tells you
        // at a glance which things you type into and which you press.
        "h-8 w-full min-w-0 rounded-lg border border-input bg-surface-raised px-2.5 py-1 text-base outline-none",
        "shadow-[inset_0_1px_2px_0_oklch(0.28_0.032_265/0.06)] dark:shadow-[inset_0_1px_2px_0_oklch(0_0_0/0.25)]",
        "transition-[border-color,box-shadow] duration-150 ease-[cubic-bezier(0.2,0,0,1)]",
        "file:inline-flex file:h-6 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground",
        "placeholder:text-muted-foreground",
        "hover:border-border-strong",
        "focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
        "disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-60 disabled:shadow-none",
        "aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40",
        "md:text-sm dark:bg-input/25",
        className
      )}
      {...props}
    />
  )
}

export { Input }
