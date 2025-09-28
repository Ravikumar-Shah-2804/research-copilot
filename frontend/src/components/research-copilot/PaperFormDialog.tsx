import { useState, useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { PaperCreate, PaperUpdate, PaperResponse } from "@/types/api"
import { papersAPI } from "@/lib/api/papers"
import { toast } from "sonner"
import { X, Plus } from "lucide-react"

const paperSchema = z.object({
  arxiv_id: z.string().min(1, "ArXiv ID is required"),
  title: z.string().min(1, "Title is required"),
  authors: z.array(z.string()).min(1, "At least one author is required"),
  abstract: z.string().min(1, "Abstract is required"),
  categories: z.array(z.string()).min(1, "At least one category is required"),
  published_date: z.string().min(1, "Published date is required"),
  pdf_url: z.string().url("Valid PDF URL is required"),
  doi: z.string().optional(),
  journal_ref: z.string().optional(),
  comments: z.string().optional(),
  tags: z.array(z.string()).optional(),
  keywords: z.array(z.string()).optional(),
})

type PaperFormData = z.infer<typeof paperSchema>

interface PaperFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  paper?: PaperResponse | null
  onSuccess?: () => void
}

export function PaperFormDialog({ open, onOpenChange, paper, onSuccess }: PaperFormDialogProps) {
  const [loading, setLoading] = useState(false)
  const [authorInput, setAuthorInput] = useState("")
  const [categoryInput, setCategoryInput] = useState("")
  const [tagInput, setTagInput] = useState("")
  const [keywordInput, setKeywordInput] = useState("")

  const isEditing = !!paper

  const form = useForm<PaperFormData>({
    resolver: zodResolver(paperSchema),
    defaultValues: {
      arxiv_id: "",
      title: "",
      authors: [],
      abstract: "",
      categories: [],
      published_date: "",
      pdf_url: "",
      doi: "",
      journal_ref: "",
      comments: "",
      tags: [],
      keywords: [],
    },
  })

  useEffect(() => {
    if (paper) {
      form.reset({
        arxiv_id: paper.arxiv_id,
        title: paper.title,
        authors: paper.authors,
        abstract: paper.abstract,
        categories: paper.categories,
        published_date: paper.published_date.split('T')[0], // Convert to date input format
        pdf_url: paper.pdf_url,
        doi: paper.doi || "",
        journal_ref: paper.journal_ref || "",
        comments: paper.comments || "",
        tags: paper.tags || [],
        keywords: paper.keywords || [],
      })
    } else {
      form.reset({
        arxiv_id: "",
        title: "",
        authors: [],
        abstract: "",
        categories: [],
        published_date: "",
        pdf_url: "",
        doi: "",
        journal_ref: "",
        comments: "",
        tags: [],
        keywords: [],
      })
    }
  }, [paper, form])

  const onSubmit = async (data: PaperFormData) => {
    try {
      setLoading(true)

      if (isEditing && paper) {
        await papersAPI.updatePaper(paper.id, data as PaperUpdate)
        toast.success("Paper updated successfully")
      } else {
        await papersAPI.createPaper(data as PaperCreate)
        toast.success("Paper created successfully")
      }

      onOpenChange(false)
      onSuccess?.()
    } catch (error) {
      console.error("Error saving paper:", error)
      toast.error(isEditing ? "Failed to update paper" : "Failed to create paper")
    } finally {
      setLoading(false)
    }
  }

  const addItem = (field: keyof PaperFormData, input: string, setInput: (value: string) => void) => {
    if (!input.trim()) return

    const currentValues = form.getValues(field) as string[]
    if (!currentValues.includes(input.trim())) {
      form.setValue(field, [...currentValues, input.trim()])
    }
    setInput("")
  }

  const removeItem = (field: keyof PaperFormData, item: string) => {
    const currentValues = form.getValues(field) as string[]
    form.setValue(field, currentValues.filter(v => v !== item))
  }

  const renderArrayField = (
    field: keyof PaperFormData,
    label: string,
    input: string,
    setInput: (value: string) => void,
    placeholder: string
  ) => {
    const values = form.watch(field) as string[]

    return (
      <FormField
        control={form.control}
        name={field}
        render={() => (
          <FormItem>
            <FormLabel>{label}</FormLabel>
            <div className="flex gap-2">
              <Input
                placeholder={placeholder}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault()
                    addItem(field, input, setInput)
                  }
                }}
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => addItem(field, input, setInput)}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex flex-wrap gap-2 mt-2">
              {values.map((item) => (
                <Badge key={item} variant="secondary" className="flex items-center gap-1">
                  {item}
                  <button
                    type="button"
                    onClick={() => removeItem(field, item)}
                    className="ml-1 hover:bg-destructive hover:text-destructive-foreground rounded-full p-0.5"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
            <FormMessage />
          </FormItem>
        )}
      />
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit Paper" : "Add New Paper"}</DialogTitle>
          <DialogDescription>
            {isEditing
              ? "Update the paper information below."
              : "Fill in the details to add a new paper to your library."
            }
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="arxiv_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>ArXiv ID *</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g., 2301.12345" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="published_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Published Date *</FormLabel>
                    <FormControl>
                      <Input type="date" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Title *</FormLabel>
                  <FormControl>
                    <Input placeholder="Paper title" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {renderArrayField("authors", "Authors *", authorInput, setAuthorInput, "Add author")}

            <FormField
              control={form.control}
              name="abstract"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Abstract *</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Paper abstract"
                      className="min-h-24"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {renderArrayField("categories", "Categories *", categoryInput, setCategoryInput, "Add category")}

            <FormField
              control={form.control}
              name="pdf_url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>PDF URL *</FormLabel>
                  <FormControl>
                    <Input placeholder="https://arxiv.org/pdf/..." {...field} />
                  </FormControl>
                  <FormDescription>
                    URL to the PDF file
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="doi"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>DOI</FormLabel>
                    <FormControl>
                      <Input placeholder="10.xxxx/xxxxx" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="journal_ref"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Journal Reference</FormLabel>
                    <FormControl>
                      <Input placeholder="Journal name, volume, pages" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="comments"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Comments</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Additional comments or notes"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {renderArrayField("tags", "Tags", tagInput, setTagInput, "Add tag")}

            {renderArrayField("keywords", "Keywords", keywordInput, setKeywordInput, "Add keyword")}

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={loading}>
                {loading ? "Saving..." : isEditing ? "Update Paper" : "Create Paper"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}