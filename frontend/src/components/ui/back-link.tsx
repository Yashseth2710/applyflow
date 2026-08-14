import { ArrowLeft } from "lucide-react";

import { Link } from "@/components/ui/link";
import { cn } from "@/lib/utils";

/**
 * The "back to the list" link at the top of every detail page.
 *
 * Four pages each wrote their own, using a literal "←" character. A text arrow
 * inherits the body font's idea of what an arrow looks like — it sits on the
 * baseline instead of optically centred, its weight has nothing to do with the
 * lucide icons beside it, and a screen reader announces it as "leftwards
 * arrow". This is a drawn icon at the same stroke as the rest of the set, and
 * it slides on hover so the direction is felt rather than just seen.
 */
export function BackLink({
  href,
  children,
  className,
}: {
  href: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "group inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground",
        className,
      )}
    >
      <ArrowLeft
        className="size-4 transition-transform duration-150 ease-[cubic-bezier(0.2,0,0,1)] group-hover:-translate-x-0.5"
        aria-hidden
      />
      {children}
    </Link>
  );
}
