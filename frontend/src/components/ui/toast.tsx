import * as React from "react"
import { cn } from "@/lib/utils"
import { X } from "lucide-react"

export interface ToastMessage {
  id: string
  title?: string
  description?: string
  variant?: "default" | "destructive" | "success"
}

interface ToastContextType {
  toast: (message: Omit<ToastMessage, "id">) => void
  toasts: ToastMessage[]
  dismiss: (id: string) => void
}

const ToastContext = React.createContext<ToastContextType | undefined>(undefined)

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = React.useState<ToastMessage[]>([])

  const toast = React.useCallback(({ title, description, variant = "default" }: Omit<ToastMessage, "id">) => {
    const id = Math.random().toString(36).substring(2, 9)
    setToasts((prev) => [...prev, { id, title, description, variant }])

    // 4秒後に自動消去
    setTimeout(() => {
      dismiss(id)
    }, 4000)
  }, [])

  const dismiss = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ toast, toasts, dismiss }}>
      {children}
      <Toaster />
    </ToastContext.Provider>
  )
}

export const useToast = () => {
  const context = React.useContext(ToastContext)
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider")
  }
  return {
    toast: context.toast,
    toasts: context.toasts,
    dismiss: context.dismiss,
  }
}

const Toaster: React.FC = () => {
  const { toasts, dismiss } = useToast()

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 w-full max-w-sm pointer-events-none">
      {toasts.map(({ id, title, description, variant }) => (
        <div
          key={id}
          className={cn(
            "pointer-events-auto flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border p-4 pr-8 shadow-lg transition-all duration-300 transform translate-y-0",
            variant === "destructive" && "border-destructive bg-destructive/90 text-destructive-foreground",
            variant === "success" && "border-primary/50 bg-primary/20 backdrop-blur-md text-foreground",
            variant === "default" && "border-white/10 bg-card/85 backdrop-blur-md text-foreground"
          )}
        >
          <div className="grid gap-1">
            {title && <div className="text-sm font-semibold">{title}</div>}
            {description && <div className="text-xs opacity-90">{description}</div>}
          </div>
          <button
            onClick={() => dismiss(id)}
            className="absolute right-2 top-2 rounded-md p-1 text-foreground/50 opacity-0 transition-opacity hover:text-foreground focus:opacity-100 group-hover:opacity-100 focus:outline-none focus:ring-1"
            style={{ opacity: 0.8 }}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  )
}
