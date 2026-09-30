import * as React from "react"

/**
 * Button — componente básico do template (shadcn-style, sem dependências externas).
 * Aceita className para sobrescrita via Tailwind.
 */
export function Button({
  type = "button",
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type={type}
      className={`inline-flex h-10 items-center justify-center rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 disabled:pointer-events-none disabled:opacity-50 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-200 ${
        className ?? ""
      }`}
      {...props}
    />
  )
}
