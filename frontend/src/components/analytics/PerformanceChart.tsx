"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { BarChart, Bar, XAxis, YAxis } from "recharts"
import { PerformanceMetrics } from "@/types/api"

interface PerformanceChartProps {
  data: PerformanceMetrics
}

const chartConfig = {
  requests: {
    label: "Requests",
    color: "hsl(var(--chart-1))",
  },
  errors: {
    label: "Errors",
    color: "hsl(var(--chart-2))",
  },
}

export function PerformanceChart({ data }: PerformanceChartProps) {
  // Transform operations data for chart
  const chartData = Object.entries(data.operations || {}).map(([operation, metrics]: [string, any]) => ({
    operation: operation.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
    requests: metrics.requests || 0,
    errors: metrics.errors || 0,
    avgResponseTime: metrics.avg_response_time || 0,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>Performance by Operation</CardTitle>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig}>
          <BarChart data={chartData}>
            <XAxis dataKey="operation" />
            <YAxis />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Bar dataKey="requests" fill="var(--color-requests)" />
            <Bar dataKey="errors" fill="var(--color-errors)" />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}