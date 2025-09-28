import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { PaperResponse } from "@/types/api"
import { Calendar, Users, Eye, Download, Edit, Trash2 } from "lucide-react"

interface PaperCardProps {
  paper: PaperResponse
  onEdit?: (paper: PaperResponse) => void
  onDelete?: (paper: PaperResponse) => void
  onView?: (paper: PaperResponse) => void
}

export function PaperCard({ paper, onEdit, onDelete, onView }: PaperCardProps) {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  const truncateText = (text: string, maxLength: number) => {
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
  }

  return (
    <Card className="h-full hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base leading-tight line-clamp-2">
            {paper.title}
          </CardTitle>
          <div className="flex gap-1 shrink-0">
            {onEdit && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onEdit(paper)}
                className="h-8 w-8 p-0"
              >
                <Edit className="h-4 w-4" />
              </Button>
            )}
            {onDelete && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDelete(paper)}
                className="h-8 w-8 p-0 text-destructive hover:text-destructive"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Users className="h-4 w-4" />
          <span className="truncate">
            {paper.authors.slice(0, 2).join(', ')}
            {paper.authors.length > 2 && ` +${paper.authors.length - 2} more`}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground line-clamp-3">
          {truncateText(paper.abstract, 200)}
        </p>

        <div className="flex flex-wrap gap-1">
          {paper.categories.slice(0, 3).map((category) => (
            <Badge key={category} variant="secondary" className="text-xs">
              {category}
            </Badge>
          ))}
          {paper.categories.length > 3 && (
            <Badge variant="secondary" className="text-xs">
              +{paper.categories.length - 3}
            </Badge>
          )}
        </div>

        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            <span>{formatDate(paper.published_date)}</span>
          </div>
          <div className="flex items-center gap-3">
            {paper.view_count !== undefined && (
              <div className="flex items-center gap-1">
                <Eye className="h-3 w-3" />
                <span>{paper.view_count}</span>
              </div>
            )}
            {paper.download_count !== undefined && (
              <div className="flex items-center gap-1">
                <Download className="h-3 w-3" />
                <span>{paper.download_count}</span>
              </div>
            )}
          </div>
        </div>

        {onView && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => onView(paper)}
            className="w-full"
          >
            View Paper
          </Button>
        )}
      </CardContent>
    </Card>
  )
}