"use client"

import * as React from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Form, FormControl, FormField, FormItem, FormMessage } from "@/components/ui/form"
import { searchAPI } from "@/lib/api/search"
import { toast } from "sonner"
import { Loader2 } from "lucide-react"
import { searchSchema, SearchFormData } from "@/lib/schemas/auth"
import { sanitizeSearchQuery } from "@/lib/utils/sanitization"

export function AcademicSearchDialog({ triggerClassName }: { triggerClassName?: string }) {
  const [open, setOpen] = React.useState(false)
  const [isSearching, setIsSearching] = React.useState(false)

  const form = useForm<SearchFormData>({
    resolver: zodResolver(searchSchema),
    defaultValues: {
      query: "",
      publisher: "arxiv",
      searchMode: "hybrid",
      sortBy: "relevance",
    },
  })

  const onSubmit = async (data: SearchFormData) => {
    setIsSearching(true)
    try {
      // Sanitize query
      const sanitizedQuery = sanitizeSearchQuery(data.query)

      let searchResponse

      if (data.searchMode === "bm25_only") {
        searchResponse = await searchAPI.bm25Search(sanitizedQuery, {
          limit: 10,
          filters: { publisher: data.publisher }
        })
      } else if (data.searchMode === "vector_only") {
        searchResponse = await searchAPI.vectorSearch(sanitizedQuery, {
          limit: 10,
          filters: { publisher: data.publisher }
        })
      } else {
        searchResponse = await searchAPI.search(sanitizedQuery, {
          mode: data.searchMode,
          limit: 10,
          filters: { publisher: data.publisher }
        })
      }

      // For now, just show a success message with result count
      toast.success(`Found ${searchResponse.total} results for "${sanitizedQuery}"`)
      setOpen(false)
      form.reset()

      // TODO: Navigate to search results page or display results
      console.log("Search results:", searchResponse.results)

    } catch (error) {
      console.error("Search error:", error)
      toast.error("Failed to perform search")
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className={triggerClassName}>Academic Search</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Academic Search</DialogTitle>
          <DialogDescription>Search scholarly articles across publishers and repositories.</DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-3">
            <FormField
              control={form.control}
              name="query"
              render={({ field }) => (
                <FormItem>
                  <FormControl>
                    <Input
                      placeholder="Search papers, topics, authors…"
                      disabled={isSearching}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="flex gap-2 flex-wrap items-center">
              <FormField
                control={form.control}
                name="publisher"
                render={({ field }) => (
                  <FormItem>
                    <Select value={field.value} onValueChange={field.onChange} disabled={isSearching}>
                      <SelectTrigger>
                        <SelectValue placeholder="Publisher" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          <SelectLabel>Publisher</SelectLabel>
                          <SelectItem value="arxiv">arXiv</SelectItem>
                          <SelectItem value="semantic-scholar">Semantic Scholar</SelectItem>
                          <SelectItem value="crossref">CrossRef</SelectItem>
                          <SelectItem value="pubmed">PubMed</SelectItem>
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="searchMode"
                render={({ field }) => (
                  <FormItem>
                    <Select value={field.value} onValueChange={field.onChange} disabled={isSearching}>
                      <SelectTrigger>
                        <SelectValue placeholder="Search Mode" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          <SelectLabel>Search Mode</SelectLabel>
                          <SelectItem value="hybrid">Hybrid</SelectItem>
                          <SelectItem value="bm25_only">BM25 Only</SelectItem>
                          <SelectItem value="vector_only">Vector Only</SelectItem>
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="sortBy"
                render={({ field }) => (
                  <FormItem>
                    <Select value={field.value} onValueChange={field.onChange} disabled={isSearching}>
                      <SelectTrigger>
                        <SelectValue placeholder="Sort by" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          <SelectLabel>Sort</SelectLabel>
                          <SelectItem value="relevance">Relevance</SelectItem>
                          <SelectItem value="recent">Most recent</SelectItem>
                          <SelectItem value="citations">Citations</SelectItem>
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </FormItem>
                )}
              />
              <Button type="submit" disabled={isSearching}>
                {isSearching ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Searching...
                  </>
                ) : (
                  "Search"
                )}
              </Button>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

export default AcademicSearchDialog