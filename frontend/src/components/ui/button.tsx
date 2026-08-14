import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/*
  Two things were wrong with the stock variants.

  The first was `hover:bg-primary/80`. Fading a button toward the page on hover
  is backwards: the control should feel like it is coming to meet the cursor,
  not dissolving under it. Every variant now moves *away* from the background
  on hover — the filled one darkens, the quiet ones gain a ground — and the
  mixes are done in OKLCH so a 6% step is the same perceived step on the violet
  fill as on the neutral one.

  The second was that a button had no physical behaviour at all. A real control
  has a lit top edge, sits slightly off the page, and travels when pressed.
  That is three lines of CSS and it is most of the difference between an
  interface that feels made and one that feels emitted.
*/
const buttonVariants = cva(
  [
    "group/button inline-flex shrink-0 items-center justify-center rounded-lg border border-transparent bg-clip-padding",
    "text-sm font-medium whitespace-nowrap outline-none select-none",
    // Named properties rather than `transition-all`, which animates layout and
    // is the reason hover felt slightly gummy on the heavier pages.
    "transition-[background-color,border-color,color,box-shadow,translate] duration-150 ease-[cubic-bezier(0.2,0,0,1)]",
    "focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
    // The press. `translate-y-px` alone reads as a glitch; paired with the
    // shadow collapsing on the filled variants it reads as the button being
    // pushed into the page.
    "active:not-aria-[haspopup]:translate-y-px",
    "disabled:pointer-events-none disabled:opacity-50",
    "aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40",
    "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  ].join(" "),
  {
    variants: {
      variant: {
        default: [
          "bg-primary text-primary-foreground",
          // A hairline of light along the top edge, as if the page were lit
          // from above. It is what separates a filled button from a rectangle
          // of colour, and at 18% nobody consciously sees it.
          "shadow-[inset_0_1px_0_0_oklch(1_0_0/0.18),var(--shadow-raised)]",
          "hover:bg-[color-mix(in_oklch,var(--primary),black_9%)] hover:shadow-[inset_0_1px_0_0_oklch(1_0_0/0.18),var(--shadow-float)]",
          // Dark mode inverts the mix: --primary is already lightened there, so
          // mixing in black would push it back toward the page.
          "dark:hover:bg-[color-mix(in_oklch,var(--primary),white_10%)]",
          "active:shadow-[inset_0_1px_2px_0_oklch(0_0_0/0.12)]",
        ].join(" "),
        outline: [
          // Border, no shadow. The filled variant takes the opposite deal — a
          // shadow and a transparent border. Giving one element both is how
          // you end up with two mechanisms saying the same thing.
          "border-border-strong bg-surface-raised text-foreground",
          "hover:border-primary/35 hover:bg-accent/50 hover:text-accent-foreground",
          "aria-expanded:border-primary/35 aria-expanded:bg-accent/50 aria-expanded:text-accent-foreground",
          "active:shadow-none",
          "dark:bg-surface-raised dark:hover:bg-accent/40",
        ].join(" "),
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-[color-mix(in_oklch,var(--secondary),var(--foreground)_7%)] aria-expanded:bg-secondary aria-expanded:text-secondary-foreground",
        ghost:
          "text-muted-foreground hover:bg-accent/60 hover:text-accent-foreground aria-expanded:bg-accent/60 aria-expanded:text-accent-foreground dark:hover:bg-accent/40",
        destructive:
          // The label uses the ink variant: the fill is a 10% wash of the same
          // colour, and text-destructive on top of it reads 3.95:1.
          "bg-destructive/10 text-destructive-ink hover:bg-destructive/18 focus-visible:border-destructive/40 focus-visible:ring-destructive/20 dark:bg-destructive/20 dark:hover:bg-destructive/30 dark:focus-visible:ring-destructive/40",
        // Underline on rest, thickened on hover — a link that only reveals it
        // on hover is invisible to anyone scanning for what is clickable.
        link: "text-primary underline decoration-primary/35 underline-offset-4 hover:decoration-primary",
      },
      size: {
        default:
          "h-8 gap-1.5 px-2.5 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
        xs: "h-6 gap-1 rounded-[min(var(--radius-md),10px)] px-2 text-xs in-data-[slot=button-group]:rounded-lg has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-7 gap-1 rounded-[min(var(--radius-md),12px)] px-2.5 text-[0.8rem] in-data-[slot=button-group]:rounded-lg has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-9 gap-1.5 px-2.5 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
        icon: "size-8",
        "icon-xs":
          "size-6 rounded-[min(var(--radius-md),10px)] in-data-[slot=button-group]:rounded-lg [&_svg:not([class*='size-'])]:size-3",
        "icon-sm":
          "size-7 rounded-[min(var(--radius-md),12px)] in-data-[slot=button-group]:rounded-lg",
        "icon-lg": "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
