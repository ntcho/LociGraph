import { cva, type VariantProps } from "class-variance-authority"
import * as React from "react"

import { cn } from "~lib/utils"

const alertVariants = cva(
  "relative w-full rounded-lg border border-stone-200 p-4 [&>svg~*]:pl-7 [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-stone-950 dark:border-stone-800 dark:[&>svg]:text-stone-50",
  {
    variants: {
      variant: {
        default: "bg-white text-stone-950 dark:bg-stone-950 dark:text-stone-50",
        destructive:
          "border-red-500/50 text-red-500 [&>svg]:text-red-500 dark:border-red-500/50 dark:text-red-600 dark:dark:border-red-600 dark:[&>svg]:text-red-600",
        warning:
          "border-orange-500/50 text-orange-500 [&>svg]:text-orange-500 dark:border-orange-500/50 dark:text-orange-600 dark:dark:border-orange-600 dark:[&>svg]:text-orange-600"
      }
    },
    defaultVariants: {
      variant: "default"
    }
  }
)

const Alert = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof alertVariants>
>(({ className, variant, ...props }, ref) => (
  <div
    ref={ref}
    role="alert"
    className={cn(alertVariants({ variant }), className)}
    {...props}
  />
))
Alert.displayName = "Alert"

const AlertTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h5
    ref={ref}
    className={cn("text-base mb-1.5 font-medium leading-none", className)}
    {...props}
  />
))
AlertTitle.displayName = "AlertTitle"

const AlertDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-sm [&_p]:leading-relaxed", className)}
    {...props}
  />
))
AlertDescription.displayName = "AlertDescription"

export { Alert, AlertTitle, AlertDescription }
