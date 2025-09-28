"use client"

import * as React from "react"
import { Bot, Send, FileText, BookOpenText, Upload, X } from "lucide-react"
import { SidebarNav } from "@/components/research-copilot/SidebarNav"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Progress } from "@/components/ui/progress"
import AcademicSearchDialog from "@/components/research-copilot/AcademicSearchDialog"
import { papersAPI } from "@/lib/api/papers"
import { ragAPI } from "@/lib/api/rag"
import { analyticsAPI } from "@/lib/api/analytics"
import { toast } from "sonner"
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Array<{ id: string; title: string; authors?: string[]; score: number; url?: string }>;
  tokens_used?: number;
  confidence?: number;
  isStreaming?: boolean;
}

export default function ChatPage() {
  const [messages, setMessages] = React.useState<Message[]>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('chat-messages')
      return saved ? JSON.parse(saved) : [
        { id: "m1", role: "assistant", content: "Hi! I’m your Research Copilot. Ask about papers, topics, or summarize PDFs." },
      ]
    }
    return [
      { id: "m1", role: "assistant", content: "Hi! I’m your Research Copilot. Ask about papers, topics, or summarize PDFs." },
    ]
  })
  const [input, setInput] = React.useState("")
  const [mode, setMode] = React.useState<"search"|"chat"|"summarize">("chat")
  const [model, setModel] = React.useState("gpt-4o-mini")
  const [publisher, setPublisher] = React.useState("arxiv")
  const [uploadDialogOpen, setUploadDialogOpen] = React.useState(false)
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null)
  const [uploadProgress, setUploadProgress] = React.useState(0)
  const [uploading, setUploading] = React.useState(false)
  const [isLoading, setIsLoading] = React.useState(false)
  const [streamingMessageId, setStreamingMessageId] = React.useState<string | null>(null)
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  // Save messages to localStorage whenever they change
  React.useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('chat-messages', JSON.stringify(messages))
    }
  }, [messages])

  async function send() {
    const text = input.trim()
    if (!text || isLoading) return

    const newMsg: Message = { id: crypto.randomUUID(), role: "user", content: text }
    setMessages((prev) => [...prev, newMsg])
    setInput("")
    setIsLoading(true)

    const assistantMsgId = crypto.randomUUID()
    const streamingMsg: Message = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      isStreaming: true,
    }
    setMessages((prev) => [...prev, streamingMsg])
    setStreamingMessageId(assistantMsgId)

    try {
      console.log('[DEBUG] Calling askQuestionStream with text:', text)
      const streamIterable = ragAPI.askQuestionStream(text, {
        search_mode: mode === "search" ? "hybrid" : undefined,
        max_tokens: 1000,
        temperature: 0.7,
      })
      console.log('[DEBUG] Stream iterable type:', typeof streamIterable)

      let accumulatedContent = ""
      let finalSources: any[] = []
      let finalTokens: number | undefined
      let finalConfidence: number | undefined
      let updateCount = 0

      for await (const response of streamIterable) {
        console.log('[DEBUG] Received streaming response:', response)
        if (response.type === 'content' && response.content) {
          accumulatedContent += response.content
          updateCount++
          console.log('[DEBUG] Update count:', updateCount, 'Accumulated content length:', accumulatedContent.length)
          setMessages((prev) =>
            prev.map(msg =>
              msg.id === assistantMsgId
                ? { ...msg, content: accumulatedContent }
                : msg
            )
          )
        } else if (response.type === 'sources' && response.sources) {
          finalSources = response.sources
          console.log('[DEBUG] Received sources:', finalSources.length, 'sources:', finalSources)
        } else if (response.done) {
          finalTokens = response.tokens_used
          finalConfidence = response.confidence
          console.log('[DEBUG] Stream done, total updates:', updateCount, 'tokens:', finalTokens, 'confidence:', finalConfidence)
          break
        }
      }

      // Update the final message with complete data
      console.log('[DEBUG] Final update: content length:', accumulatedContent.length, 'sources count:', finalSources.length, 'tokens:', finalTokens, 'confidence:', finalConfidence)
      setMessages((prev) =>
        prev.map(msg =>
          msg.id === assistantMsgId
            ? {
                ...msg,
                content: accumulatedContent,
                sources: finalSources,
                tokens_used: finalTokens,
                confidence: finalConfidence,
                isStreaming: false,
              }
            : msg
        )
      )

      // Log usage to analytics
      if (finalTokens && finalConfidence !== undefined) {
        try {
          await analyticsAPI.logRagUsage({
            tokens_used: finalTokens,
            confidence: finalConfidence,
            sources_count: finalSources.length,
            response_length: accumulatedContent.length
          })
          console.log('[DEBUG] Usage logged to analytics')
        } catch (error) {
          console.error('[DEBUG] Failed to log usage:', error)
        }
      }

      // Log usage for analytics and billing
      if (finalTokens && finalConfidence !== undefined) {
        console.log('[DEBUG] Attempting to log RAG usage:', {
          tokens_used: finalTokens,
          confidence: finalConfidence,
          sources_count: finalSources.length,
          response_length: accumulatedContent.length
        })
        try {
          const result = await analyticsAPI.logRagUsage({
            tokens_used: finalTokens,
            confidence: finalConfidence,
            sources_count: finalSources.length,
            response_length: accumulatedContent.length
          })
          console.log('[DEBUG] RAG usage logged successfully:', result)
        } catch (error) {
          console.error('[DEBUG] Failed to log RAG usage:', error)
        }
      } else {
        console.log('[DEBUG] Skipping RAG usage log - missing data:', {
          finalTokens,
          finalConfidence,
          finalSources: finalSources?.length
        })
      }
    } catch (error) {
      console.error("Error getting RAG response:", error)
      console.log('[DEBUG] Error occurred, resetting streaming state for message:', assistantMsgId)
      setMessages((prev) =>
        prev.map(msg =>
          msg.id === assistantMsgId
            ? {
                ...msg,
                content: "Sorry, I encountered an error while processing your request. Please try again.",
                isStreaming: false,
              }
            : msg
        )
      )
      toast.error("Failed to get response from RAG system")
    } finally {
      setIsLoading(false)
      setStreamingMessageId(null)
    }
  }

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file)
      setUploadDialogOpen(true)
    } else if (file) {
      toast.error("Please select a PDF file")
    }
  }

  const handleFileUpload = async () => {
    if (!selectedFile) return

    try {
      setUploading(true)
      setUploadProgress(0)

      // First create a paper with basic info
      const paperData = {
        arxiv_id: `upload_${Date.now()}`,
        title: selectedFile.name.replace('.pdf', ''),
        authors: ['Unknown'],
        abstract: 'PDF uploaded for processing',
        categories: ['uploaded'],
        published_date: new Date().toISOString().split('T')[0],
        pdf_url: '#', // Will be updated after upload
      }

      const createdPaper = await papersAPI.createPaper(paperData)

      // Then upload the PDF
      await papersAPI.uploadPaperPDF(createdPaper.id, selectedFile)

      setUploadProgress(100)
      toast.success("PDF uploaded successfully! The paper will be processed shortly.")
      setUploadDialogOpen(false)
      setSelectedFile(null)

    } catch (error) {
      console.error("Error uploading PDF:", error)
      toast.error("Failed to upload PDF")
    } finally {
      setUploading(false)
      setUploadProgress(0)
    }
  }

  const clearFile = () => {
    setSelectedFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <SidebarNav>
      <div className="flex flex-col h-[calc(100svh-0px)]">
        <header className="border-b bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/70">
          <div className="mx-auto max-w-5xl px-4 py-3 flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <Badge variant={mode === "chat" ? "default" : "secondary"} className="cursor-pointer" onClick={()=>setMode("chat")}>Chat</Badge>
              <Badge variant={mode === "search" ? "default" : "secondary"} className="cursor-pointer" onClick={()=>setMode("search")}>Search</Badge>
              <Badge variant={mode === "summarize" ? "default" : "secondary"} className="cursor-pointer" onClick={()=>setMode("summarize")}>Summarize</Badge>
            </div>
            <div className="flex items-center gap-2 ml-auto">
              <Select value={model} onValueChange={setModel}>
                <SelectTrigger size="sm"><SelectValue placeholder="Model" /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectLabel>Models</SelectLabel>
                    <SelectItem value="gpt-4o-mini">GPT-4o-mini</SelectItem>
                    <SelectItem value="llama-3-70b">LLaMA 3 70B</SelectItem>
                    <SelectItem value="mistral-nemo">Mistral Nemo</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
              <Select value={publisher} onValueChange={setPublisher}>
                <SelectTrigger size="sm"><SelectValue placeholder="Publisher" /></SelectTrigger>
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
              <AcademicSearchDialog />
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl px-4 py-6 space-y-4">
            {messages.map((m) => (
              <div key={m.id} className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
                {m.role === "assistant" && (
                  <div className="mt-1 text-primary">
                    <Bot className="size-5"/>
                  </div>
                )}
                <div className={`rounded-lg border p-3 text-sm max-w-[min(100%,65ch)] space-y-3 ${m.role === "user" ? "bg-primary text-primary-foreground" : "bg-card"}`}>
                  <div className="relative">
                    <div className="prose prose-sm max-w-none dark:prose-invert">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                    </div>
                    {m.isStreaming && (
                      <span className="inline-block w-2 h-4 bg-primary ml-1 animate-pulse"></span>
                    )}
                  </div>
                  {m.role === "assistant" && !m.isStreaming && (m.sources || m.tokens_used || m.confidence) && (
                    <div className="border-t pt-2 space-y-2">
                      {m.sources && m.sources.length > 0 && (
                        <div>
                          <div className="text-xs font-medium text-muted-foreground mb-1">Sources:</div>
                          <div className="space-y-1">
                            {m.sources.map((source, idx) => (
                              <div key={idx} className="text-xs bg-muted/50 rounded px-2 py-1">
                                <div className="font-medium truncate">{source.title}</div>
                                {source.authors && source.authors.length > 0 && (
                                  <div className="text-muted-foreground truncate">
                                    {source.authors.join(", ")}
                                  </div>
                                )}
                                <div className="text-muted-foreground">
                                  Score: {(source.score * 100).toFixed(1)}%
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {(m.tokens_used || m.confidence) && (
                        <div className="flex gap-4 text-xs text-muted-foreground">
                          {m.tokens_used && <span>Tokens: {m.tokens_used}</span>}
                          {m.confidence && <span>Confidence: {(m.confidence * 100).toFixed(1)}%</span>}
                        </div>
                      )}
                    </div>
                  )}
                </div>
                {m.role === "user" && (
                  <div className="mt-1 text-primary">
                    <span className="inline-flex size-5 items-center justify-center rounded bg-primary text-primary-foreground text-[10px]">You</span>
                  </div>
                )}
              </div>
            ))}
            {messages.length === 0 && (
              <div className="text-sm text-muted-foreground">No messages yet.</div>
            )}
          </div>
        </main>

        <footer className="border-t">
          <div className="mx-auto max-w-3xl px-4 py-3">
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                className="shrink-0"
                aria-label="Attach file"
                onClick={() => fileInputRef.current?.click()}
              >
                <FileText className="size-4" />
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileSelect}
                className="hidden"
              />
              <Input
                placeholder={mode === "search" ? "Search scholarly sources…" : mode === "summarize" ? "Paste text or link to summarize…" : "Ask a research question…"}
                value={input}
                onChange={(e)=>setInput(e.target.value)}
                onKeyDown={(e)=>{ if(e.key === "Enter" && !e.shiftKey){ e.preventDefault(); send(); } }}
                disabled={isLoading}
              />
              <Button type="button" onClick={send} aria-label="Send" disabled={isLoading || !input.trim()}>
                <Send className="size-4" />
              </Button>
            </div>
            <div className="mt-2 text-[11px] text-muted-foreground flex items-center gap-2">
              <BookOpenText className="size-3.5" /> Results from {publisher}; model {model}
            </div>
          </div>
        </footer>
      </div>

      {/* PDF Upload Dialog */}
      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload PDF</DialogTitle>
            <DialogDescription>
              Upload a PDF file to add it to your research library. The file will be processed and made available for chat and search.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {selectedFile ? (
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  <span className="text-sm font-medium">{selectedFile.name}</span>
                  <span className="text-xs text-muted-foreground">
                    ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearFile}
                  disabled={uploading}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <div className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-6 text-center">
                <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  Click the attach button to select a PDF file
                </p>
              </div>
            )}

            {uploading && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Uploading...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <Progress value={uploadProgress} />
              </div>
            )}
          </div>

          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setUploadDialogOpen(false)
                clearFile()
              }}
              disabled={uploading}
            >
              Cancel
            </Button>
            <Button
              onClick={handleFileUpload}
              disabled={!selectedFile || uploading}
            >
              {uploading ? "Uploading..." : "Upload PDF"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </SidebarNav>
  )
}