// Adapted from shadcn/ui Sheet (MIT), backed by Radix Dialog focus management.
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ComponentProps } from "react";
import { cn } from "../lib/utils";

export function Sheet(props: ComponentProps<typeof Dialog.Root>) {
  return <Dialog.Root {...props} />;
}
export function SheetTrigger(props: ComponentProps<typeof Dialog.Trigger>) {
  return <Dialog.Trigger {...props} />;
}
export function SheetTitle(props: ComponentProps<typeof Dialog.Title>) {
  return <Dialog.Title className="sr-only" {...props} />;
}
export function SheetDescription(
  props: ComponentProps<typeof Dialog.Description>,
) {
  return <Dialog.Description className="sr-only" {...props} />;
}
export function SheetContent({
  children,
  className,
  ...props
}: ComponentProps<typeof Dialog.Content>) {
  return (
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 z-40 bg-slate-950/50" />
      <Dialog.Content
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-[min(20rem,90vw)] flex-col overflow-y-auto bg-sidebar text-white shadow-xl",
          className,
        )}
        {...props}
      >
        {children}
        <Dialog.Close
          className="absolute right-3 top-5 flex size-11 items-center justify-center rounded-lg text-white hover:bg-white/10"
          aria-label="Zamknij nawigację"
        >
          <X aria-hidden="true" size={20} />
        </Dialog.Close>
      </Dialog.Content>
    </Dialog.Portal>
  );
}
