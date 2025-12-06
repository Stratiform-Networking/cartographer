import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { within, expect } from 'storybook/test'
import MetricCard from '../components/MetricCard.vue'

const meta = {
  title: 'Components/MetricCard',
  component: MetricCard,
  tags: ['autodocs'],
  parameters: {
    docs: {
      description: {
        component: 'A compact metric display card with optional status indicator. Used for displaying network statistics and health metrics.',
      },
    },
  },
  argTypes: {
    label: {
      control: 'text',
      description: 'The label for the metric',
    },
    value: {
      control: 'text',
      description: 'The value to display',
    },
    sublabel: {
      control: 'text',
      description: 'Optional sublabel below the value',
    },
    status: {
      control: 'select',
      options: [undefined, 'good', 'warning', 'bad'],
      description: 'Status indicator color',
    },
  },
} satisfies Meta<typeof MetricCard>

export default meta
type Story = StoryObj<typeof meta>

// Default story
export const Default: Story = {
  args: {
    label: 'Active Devices',
    value: '42',
  },
}

// Good status
export const GoodStatus: Story = {
  args: {
    label: 'Uptime',
    value: '99.9%',
    sublabel: 'Last 30 days',
    status: 'good',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement)
    
    // Verify the label is displayed
    await expect(canvas.getByText('Uptime')).toBeInTheDocument()
    
    // Verify the value is displayed
    await expect(canvas.getByText('99.9%')).toBeInTheDocument()
    
    // Verify the sublabel is displayed
    await expect(canvas.getByText('Last 30 days')).toBeInTheDocument()
  },
}

// Warning status
export const WarningStatus: Story = {
  args: {
    label: 'CPU Usage',
    value: '78%',
    sublabel: 'Consider optimization',
    status: 'warning',
  },
}

// Bad status
export const BadStatus: Story = {
  args: {
    label: 'Connection',
    value: 'Offline',
    sublabel: 'Since 10 mins ago',
    status: 'bad',
  },
}

// Without status indicator
export const NoStatus: Story = {
  args: {
    label: 'Total Bandwidth',
    value: '1.2 TB',
    sublabel: 'This month',
  },
}

// Network metric examples
export const NetworkDevices: Story = {
  args: {
    label: 'Network Devices',
    value: '156',
    sublabel: '+12 since last scan',
    status: 'good',
  },
}

export const LatencyMetric: Story = {
  args: {
    label: 'Avg Latency',
    value: '12ms',
    sublabel: 'To gateway',
    status: 'good',
  },
}

export const HighLatencyMetric: Story = {
  args: {
    label: 'Avg Latency',
    value: '250ms',
    sublabel: 'Degraded performance',
    status: 'warning',
  },
}

