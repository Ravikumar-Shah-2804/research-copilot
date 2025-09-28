"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer } from "recharts"
import { UsageTrends } from "@/types/api"

interface UsageChartProps {
  data: UsageTrends
}

const chartConfig = {
  daily: {
    label: "Daily Usage",
    color: "hsl(var(--chart-1))",
  },
  weekly: {
    label: "Weekly Usage",
    color: "hsl(var(--chart-2))",
  },
  monthly: {
    label: "Monthly Usage",
    color: "hsl(var(--chart-3))",
  },
}

export function UsageChart({ data }: UsageChartProps) {
  // Transform data for chart
  const chartData = data.daily_usage.map((daily, index) => ({
    day: `Day ${index + 1}`,
    daily: daily,
    weekly: data.weekly_usage[Math.floor(index / 7)] || 0,
    monthly: data.monthly_usage[Math.floor(index / 30)] || 0,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>Usage Trends</CardTitle>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig}>
          <LineChart data={chartData}>
            <XAxis dataKey="day" />
            <YAxis />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Line
              type="monotone"
              dataKey="daily"
              stroke="var(--color-daily)"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="weekly"
              stroke="var(--color-weekly)"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="monthly"
              stroke="var(--color-monthly)"
              strokeWidth={2}
              strokeDasharray="10 5"
              dot={false}
            />
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}