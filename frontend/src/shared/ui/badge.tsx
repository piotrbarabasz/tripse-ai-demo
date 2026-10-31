// Adapted from shadcn/ui Badge (MIT).
import type { ComponentProps } from "react";
import { cn } from "../lib/utils";

export function Badge({ className, ...props }: ComponentProps<"span">) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border border-border bg-muted px-2 py-1 text-xs font-medium text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}
