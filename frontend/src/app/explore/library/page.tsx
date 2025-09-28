"use client"

import { useState, useEffect } from "react"
import { SidebarNav } from "@/components/research-copilot/SidebarNav"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Pagination, PaginationContent, PaginationEllipsis, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from "@/components/ui/pagination"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { PaperCard } from "@/components/research-copilot/PaperCard"
import { PaperFormDialog } from "@/components/research-copilot/PaperFormDialog"
import { DeletePaperDialog } from "@/components/research-copilot/DeletePaperDialog"
import { PaperResponse } from "@/types/api"
import { papersAPI } from "@/lib/api/papers"
import { Search, Plus, AlertCircle } from "lucide-react"
import { toast } from "sonner"

export default function LibraryPage() {
  const [papers, setPapers] = useState<PaperResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedCategory, setSelectedCategory] = useState<string>("all")
  const [selectedAuthor, setSelectedAuthor] = useState<string>("all")
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalPapers, setTotalPapers] = useState(0)
  const [categories, setCategories] = useState<string[]>([])
  const [authors, setAuthors] = useState<string[]>([])
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [selectedPaper, setSelectedPaper] = useState<PaperResponse | null>(null)

  const pageSize = 12

  const fetchPapers = async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = {
        search: searchQuery || undefined,
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
        _t: Date.now(), // Cache buster
      }

      // Add filters
      if (selectedCategory && selectedCategory !== 'all') {
        params.categories = selectedCategory
      }
      if (selectedAuthor && selectedAuthor !== 'all') {
        params.authors = selectedAuthor
      }

      const response = await papersAPI.listPapers(params)
      setPapers(response)
      setTotalPapers(response.length) // Note: API should return total count
      setTotalPages(Math.ceil(response.length / pageSize)) // This should come from API

      // Extract unique categories and authors for filters
      const allCategories = new Set<string>()
      const allAuthors = new Set<string>()
      response.forEach(paper => {
        paper.categories.forEach(cat => allCategories.add(cat))
        paper.authors.forEach(author => allAuthors.add(author))
      })
      setCategories(Array.from(allCategories).sort())
      setAuthors(Array.from(allAuthors).sort())

    } catch (err) {
      setError("Failed to load papers. Please try again.")
      console.error("Error fetching papers:", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPapers()
  }, [currentPage, searchQuery, selectedCategory, selectedAuthor])

  const handleSearch = (query: string) => {
    setSearchQuery(query)
    setCurrentPage(1)
  }

  const handleCategoryFilter = (category: string) => {
    setSelectedCategory(category)
    setCurrentPage(1)
  }

  const handleAuthorFilter = (author: string) => {
    setSelectedAuthor(author)
    setCurrentPage(1)
  }

  const handleCreatePaper = () => {
    setSelectedPaper(null)
    setCreateDialogOpen(true)
  }

  const handleEditPaper = (paper: PaperResponse) => {
    setSelectedPaper(paper)
    setEditDialogOpen(true)
  }

  const handleDeletePaper = (paper: PaperResponse) => {
    setSelectedPaper(paper)
    setDeleteDialogOpen(true)
  }

  const handleDialogSuccess = () => {
    // Optimistically remove the paper from the list
    if (selectedPaper) {
      setPapers(prevPapers => prevPapers.filter(p => p.id !== selectedPaper.id))
    }
    fetchPapers() // Refresh the list to ensure consistency
  }

  const handleViewPaper = (paper: PaperResponse) => {
    // TODO: Navigate to paper detail view or open PDF
    window.open(paper.pdf_url, '_blank')
  }

  return (
    <SidebarNav>
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">Library</h1>
          <Button onClick={handleCreatePaper}>
            <Plus className="h-4 w-4 mr-2" />
            Add Paper
          </Button>
        </div>

        {/* Search and Filters */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search papers..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select value={selectedCategory} onValueChange={handleCategoryFilter}>
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue placeholder="All Categories" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {categories.map(category => (
                <SelectItem key={category} value={category}>
                  {category}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={selectedAuthor} onValueChange={handleAuthorFilter}>
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue placeholder="All Authors" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Authors</SelectItem>
              {authors.map(author => (
                <SelectItem key={author} value={author}>
                  {author}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Results count */}
        {!loading && !error && (
          <div className="text-sm text-muted-foreground">
            {totalPapers} paper{totalPapers !== 1 ? 's' : ''} found
          </div>
        )}

        {/* Error state */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Papers grid */}
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="space-y-3">
                <Skeleton className="h-48 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            ))}
          </div>
        ) : papers.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {papers.map((paper) => (
              <PaperCard
                key={paper.id}
                paper={paper}
                onEdit={handleEditPaper}
                onDelete={handleDeletePaper}
                onView={handleViewPaper}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No papers found.</p>
            <Button variant="outline" className="mt-4" onClick={handleCreatePaper}>
              <Plus className="h-4 w-4 mr-2" />
              Add Your First Paper
            </Button>
          </div>
        )}

        {/* Pagination */}
        {!loading && papers.length > 0 && totalPages > 1 && (
          <Pagination>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  className={currentPage === 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                />
              </PaginationItem>

              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const page = i + 1
                return (
                  <PaginationItem key={page}>
                    <PaginationLink
                      onClick={() => setCurrentPage(page)}
                      isActive={currentPage === page}
                      className="cursor-pointer"
                    >
                      {page}
                    </PaginationLink>
                  </PaginationItem>
                )
              })}

              {totalPages > 5 && (
                <PaginationItem>
                  <PaginationEllipsis />
                </PaginationItem>
              )}

              <PaginationItem>
                <PaginationNext
                  onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                  className={currentPage === totalPages ? "pointer-events-none opacity-50" : "cursor-pointer"}
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        )}

        {/* Dialogs */}
        <PaperFormDialog
          open={createDialogOpen}
          onOpenChange={setCreateDialogOpen}
          onSuccess={handleDialogSuccess}
        />

        <PaperFormDialog
          open={editDialogOpen}
          onOpenChange={setEditDialogOpen}
          paper={selectedPaper}
          onSuccess={handleDialogSuccess}
        />

        <DeletePaperDialog
          open={deleteDialogOpen}
          onOpenChange={setDeleteDialogOpen}
          paper={selectedPaper}
          onSuccess={handleDialogSuccess}
        />
      </div>
    </SidebarNav>
  )
}