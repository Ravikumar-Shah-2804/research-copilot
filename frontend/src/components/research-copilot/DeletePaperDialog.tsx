import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { PaperResponse } from "@/types/api"
import { papersAPI } from "@/lib/api/papers"
import { toast } from "sonner"
import { useState } from "react"

interface DeletePaperDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  paper: PaperResponse | null
  onSuccess?: () => void
}

export function DeletePaperDialog({ open, onOpenChange, paper, onSuccess }: DeletePaperDialogProps) {
  const [loading, setLoading] = useState(false)

  const handleDelete = async () => {
    if (!paper) return

    try {
      setLoading(true)
      await papersAPI.deletePaper(paper.id)
      toast.success("Paper deleted successfully")
      onOpenChange(false)
      onSuccess?.()
    } catch (error) {
      console.error("Error deleting paper:", error)
      toast.error("Failed to delete paper")
    } finally {
      setLoading(false)
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete Paper</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to delete "{paper?.title}"? This action cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={loading}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleDelete}
            disabled={loading}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {loading ? "Deleting..." : "Delete"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}