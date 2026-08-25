import * as React from "react"
import * as DialogPrimitive from "@radix-ui/react-dialog"
import { X } from "lucide-react"

import { cn } from "@/lib/utils"

const Dialog = DialogPrimitive.Root
const DialogTrigger = DialogPrimitive.Trigger
const DialogPortal = DialogPrimitive.Portal
const DialogClose = DialogPrimitive.Close

const DialogOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-50 bg-black/50 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      className
    )}
    {...props}
  />
))
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName

const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>
>(({ className, children, ...props }, ref) => (
  <DialogPortal>
    <DialogOverlay />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        // Bounded by the viewport (dvh, so mobile browser chrome is accounted
        // for) and laid out as a column: content longer than the screen scrolls
        // inside DialogBody instead of growing past the top and bottom edges.
        // The gutter and padding tighten on narrow phones — 2rem of margin plus
        // 3rem of padding left barely 240px of text column on a 320px screen.
        "fixed left-1/2 top-1/2 z-50 flex max-h-[92dvh] w-[calc(100%-1.5rem)] max-w-sm -translate-x-1/2 -translate-y-1/2 flex-col gap-3 overflow-hidden rounded-3xl bg-card p-4 shadow-[var(--shadow-float)] duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 xs:w-[calc(100%-2rem)] xs:gap-4 xs:p-6 sm:max-h-[85dvh]",
        className
      )}
      {...props}
    >
      {children}
      <DialogPrimitive.Close className="absolute end-3 top-3 rounded-full p-1 text-muted-foreground opacity-70 transition-opacity hover:bg-secondary hover:opacity-100 focus:outline-none focus:ring-1 focus:ring-ring xs:end-4 xs:top-4">
        <X className="size-4" />
        <span className="sr-only">Close</span>
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DialogPortal>
))
DialogContent.displayName = DialogPrimitive.Content.displayName

const DialogHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  // `pe-8` keeps the title clear of the absolutely positioned close button
  // instead of running under it once the text wraps on a narrow screen.
  <div className={cn("flex shrink-0 flex-col space-y-1.5 pe-8 text-start", className)} {...props} />
)
DialogHeader.displayName = "DialogHeader"

/**
 * The scrolling middle of a dialog. Put everything variable-length in here so
 * the title and the call to action stay put while the content moves — the
 * negative margins let the scrollbar sit against the dialog edge rather than
 * inside its padding.
 */
const DialogBody = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  // Block flow inside, not a flex column: overflowing content in a flex column
  // gets *shrunk* to fit, which silently collapsed an image strip to a few
  // pixels and let it spill over the footer. Blocks keep their natural height
  // and let the scroll do the work.
  // The negative margin has to track DialogContent's responsive padding, or the
  // scrollbar detaches from the dialog edge on one side of the breakpoint.
  <div
    className={cn(
      "-mx-4 min-h-0 flex-1 space-y-3 overflow-y-auto overscroll-contain px-4 xs:-mx-6 xs:space-y-4 xs:px-6",
      className
    )}
    {...props}
  />
)
DialogBody.displayName = "DialogBody"

/** Pinned below the scroll area — where the primary action belongs. */
const DialogFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex shrink-0 flex-col gap-2", className)} {...props} />
)
DialogFooter.displayName = "DialogFooter"

const DialogTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn("text-base font-bold leading-tight tracking-tight [overflow-wrap:anywhere] xs:text-lg", className)}
    {...props}
  />
))
DialogTitle.displayName = DialogPrimitive.Title.displayName

const DialogDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description ref={ref} className={cn("text-sm text-muted-foreground", className)} {...props} />
))
DialogDescription.displayName = DialogPrimitive.Description.displayName

export {
  Dialog,
  DialogPortal,
  DialogOverlay,
  DialogTrigger,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogBody,
  DialogFooter,
  DialogTitle,
  DialogDescription,
}
