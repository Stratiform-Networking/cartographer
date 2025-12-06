import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { fn } from 'storybook/test'
import NetworkMap from '../components/NetworkMap.vue'
import type { TreeNode, DeviceMetrics } from '../types/network'

// Sample network data for stories
const createSampleNetwork = (): TreeNode => ({
  id: 'router-main',
  name: 'Main Gateway',
  role: 'gateway/router',
  ip: '192.168.1.1',
  hostname: 'gateway.local',
  children: [
    {
      id: 'group-infrastructure',
      name: 'Infrastructure',
      role: 'group',
      children: [
        {
          id: 'switch-1',
          name: 'Core Switch',
          role: 'switch/ap',
          ip: '192.168.1.2',
          hostname: 'switch.local',
          parentId: 'router-main',
          connectionSpeed: '10 Gbps',
          children: [],
        },
        {
          id: 'firewall-1',
          name: 'pfSense Firewall',
          role: 'firewall',
          ip: '192.168.1.3',
          hostname: 'pfsense.local',
          parentId: 'router-main',
          children: [],
        },
      ],
    },
    {
      id: 'group-servers',
      name: 'Servers',
      role: 'group',
      children: [
        {
          id: 'server-web',
          name: 'Web Server',
          role: 'server',
          ip: '192.168.1.10',
          hostname: 'web.local',
          parentId: 'switch-1',
          connectionSpeed: '1 Gbps',
          children: [],
        },
        {
          id: 'server-db',
          name: 'Database Server',
          role: 'server',
          ip: '192.168.1.11',
          hostname: 'db.local',
          parentId: 'switch-1',
          connectionSpeed: '1 Gbps',
          children: [],
        },
        {
          id: 'nas-1',
          name: 'Synology NAS',
          role: 'nas',
          ip: '192.168.1.20',
          hostname: 'nas.local',
          parentId: 'switch-1',
          connectionSpeed: '2.5 Gbps',
          children: [],
        },
      ],
    },
    {
      id: 'group-clients',
      name: 'Clients',
      role: 'group',
      children: [
        {
          id: 'client-1',
          name: 'Workstation',
          role: 'client',
          ip: '192.168.1.100',
          hostname: 'desktop.local',
          parentId: 'switch-1',
          children: [],
        },
        {
          id: 'client-2',
          name: 'Laptop',
          role: 'client',
          ip: '192.168.1.101',
          hostname: 'laptop.local',
          parentId: 'switch-1',
          children: [],
        },
      ],
    },
    {
      id: 'group-services',
      name: 'Services',
      role: 'group',
      children: [
        {
          id: 'service-docker',
          name: 'Docker Host',
          role: 'service',
          ip: '192.168.1.50',
          hostname: 'docker.local',
          parentId: 'server-web',
          children: [],
        },
      ],
    },
  ],
})

// Simple network with just a few nodes
const createSimpleNetwork = (): TreeNode => ({
  id: 'router',
  name: 'Router',
  role: 'gateway/router',
  ip: '192.168.1.1',
  children: [
    {
      id: 'group-devices',
      name: 'Devices',
      role: 'group',
      children: [
        {
          id: 'pc-1',
          name: 'Desktop PC',
          role: 'client',
          ip: '192.168.1.10',
          parentId: 'router',
          children: [],
        },
        {
          id: 'laptop-1',
          name: 'Laptop',
          role: 'client',
          ip: '192.168.1.11',
          parentId: 'router',
          children: [],
        },
      ],
    },
  ],
})

// Sample health metrics
const healthyMetrics: Record<string, DeviceMetrics> = {
  '192.168.1.1': { status: 'healthy', latency: 1, packet_loss: 0 },
  '192.168.1.2': { status: 'healthy', latency: 2, packet_loss: 0 },
  '192.168.1.3': { status: 'healthy', latency: 3, packet_loss: 0 },
  '192.168.1.10': { status: 'healthy', latency: 5, packet_loss: 0 },
  '192.168.1.11': { status: 'healthy', latency: 4, packet_loss: 0 },
  '192.168.1.20': { status: 'healthy', latency: 3, packet_loss: 0 },
  '192.168.1.100': { status: 'healthy', latency: 8, packet_loss: 0 },
  '192.168.1.101': { status: 'healthy', latency: 12, packet_loss: 0 },
  '192.168.1.50': { status: 'healthy', latency: 6, packet_loss: 0 },
}

const mixedMetrics: Record<string, DeviceMetrics> = {
  '192.168.1.1': { status: 'healthy', latency: 1, packet_loss: 0 },
  '192.168.1.2': { status: 'degraded', latency: 50, packet_loss: 5 },
  '192.168.1.3': { status: 'healthy', latency: 3, packet_loss: 0 },
  '192.168.1.10': { status: 'unhealthy', latency: 500, packet_loss: 25 },
  '192.168.1.11': { status: 'healthy', latency: 4, packet_loss: 0 },
  '192.168.1.20': { status: 'degraded', latency: 100, packet_loss: 2 },
  '192.168.1.100': { status: 'healthy', latency: 8, packet_loss: 0 },
  '192.168.1.101': { status: 'unhealthy', latency: 1000, packet_loss: 50 },
  '192.168.1.50': { status: 'healthy', latency: 6, packet_loss: 0 },
}

const meta = {
  title: 'Visualizations/NetworkMap',
  component: NetworkMap,
  tags: ['autodocs'],
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component: 'Interactive D3-based network topology visualization. Supports pan/zoom, node selection, and drag-to-reposition in edit mode. Shows health status with colored halos around nodes.',
      },
    },
  },
  argTypes: {
    data: {
      description: 'The network tree structure to display',
    },
    selectedId: {
      control: 'text',
      description: 'ID of the currently selected node',
    },
    mode: {
      control: 'select',
      options: ['pan', 'edit'],
      description: 'Interaction mode - pan only or edit (allows node dragging)',
    },
    healthMetrics: {
      description: 'Health metrics for each device by IP address',
    },
  },
  decorators: [
    () => ({
      template: '<div style="height: 600px; width: 100%;"><story /></div>',
    }),
  ],
} satisfies Meta<typeof NetworkMap>

export default meta
type Story = StoryObj<typeof meta>

// Default network map view
export const Default: Story = {
  args: {
    data: createSampleNetwork(),
    mode: 'pan',
    onNodeSelected: fn(),
    onNodePositionChanged: fn(),
  },
}

// Simple network with fewer nodes
export const SimpleNetwork: Story = {
  args: {
    data: createSimpleNetwork(),
    mode: 'pan',
    onNodeSelected: fn(),
    onNodePositionChanged: fn(),
  },
}

// Network with a selected node
export const WithSelectedNode: Story = {
  args: {
    data: createSampleNetwork(),
    selectedId: 'server-web',
    mode: 'pan',
    onNodeSelected: fn(),
    onNodePositionChanged: fn(),
  },
}

// Edit mode (allows dragging nodes)
export const EditMode: Story = {
  args: {
    data: createSampleNetwork(),
    mode: 'edit',
    onNodeSelected: fn(),
    onNodePositionChanged: fn(),
  },
  parameters: {
    docs: {
      description: {
        story: 'In edit mode, nodes can be dragged to reposition them. The new position is persisted.',
      },
    },
  },
}

// Network with all healthy devices
export const AllHealthy: Story = {
  args: {
    data: createSampleNetwork(),
    healthMetrics: healthyMetrics,
    mode: 'pan',
    onNodeSelected: fn(),
    onNodePositionChanged: fn(),
  },
  parameters: {
    docs: {
      description: {
        story: 'All devices showing healthy status with green glow halos.',
      },
    },
  },
}

// Network with mixed health status
export const MixedHealth: Story = {
  args: {
    data: createSampleNetwork(),
    healthMetrics: mixedMetrics,
    mode: 'pan',
    onNodeSelected: fn(),
    onNodePositionChanged: fn(),
  },
  parameters: {
    docs: {
      description: {
        story: 'Network showing mixed health states - healthy (green), degraded (amber), and unhealthy (red) nodes.',
      },
    },
  },
}

// Empty network (just the root)
export const EmptyNetwork: Story = {
  args: {
    data: {
      id: 'router',
      name: 'Gateway',
      role: 'gateway/router',
      ip: '192.168.1.1',
      children: [],
    },
    mode: 'pan',
    onNodeSelected: fn(),
    onNodePositionChanged: fn(),
  },
  parameters: {
    docs: {
      description: {
        story: 'Network with only the root gateway node - starting point for a new network.',
      },
    },
  },
}

// Large network with many devices
const createLargeNetwork = (): TreeNode => {
  const network = createSampleNetwork()
  // Add more clients
  const clientGroup = network.children?.find(g => g.id === 'group-clients')
  if (clientGroup) {
    for (let i = 3; i <= 10; i++) {
      clientGroup.children?.push({
        id: `client-${i}`,
        name: `Client Device ${i}`,
        role: 'client',
        ip: `192.168.1.${99 + i}`,
        parentId: 'switch-1',
        children: [],
      })
    }
  }
  return network
}

export const LargeNetwork: Story = {
  args: {
    data: createLargeNetwork(),
    mode: 'pan',
    onNodeSelected: fn(),
    onNodePositionChanged: fn(),
  },
  parameters: {
    docs: {
      description: {
        story: 'A larger network demonstrating the layout with many client devices.',
      },
    },
  },
}

