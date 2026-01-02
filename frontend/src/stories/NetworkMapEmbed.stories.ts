import type { Meta, StoryObj } from '@storybook/vue3-vite';
import NetworkMapEmbed from '../components/NetworkMapEmbed.vue';
import type { TreeNode, DeviceMetrics } from '../types/network';

// Sample network data
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
  ],
});

// Health metrics
const healthyMetrics: Record<string, DeviceMetrics> = {
  '192.168.1.1': { status: 'healthy', latency: 1, packet_loss: 0 },
  '192.168.1.2': { status: 'healthy', latency: 2, packet_loss: 0 },
  '192.168.1.10': { status: 'healthy', latency: 5, packet_loss: 0 },
  '192.168.1.20': { status: 'healthy', latency: 3, packet_loss: 0 },
  '192.168.1.100': { status: 'healthy', latency: 8, packet_loss: 0 },
  '192.168.1.101': { status: 'healthy', latency: 12, packet_loss: 0 },
};

const mixedMetrics: Record<string, DeviceMetrics> = {
  '192.168.1.1': { status: 'healthy', latency: 1, packet_loss: 0 },
  '192.168.1.2': { status: 'degraded', latency: 50, packet_loss: 5 },
  '192.168.1.10': { status: 'unhealthy', latency: 500, packet_loss: 25 },
  '192.168.1.20': { status: 'healthy', latency: 3, packet_loss: 0 },
  '192.168.1.100': { status: 'healthy', latency: 8, packet_loss: 0 },
  '192.168.1.101': { status: 'degraded', latency: 100, packet_loss: 2 },
};

const meta = {
  title: 'Visualizations/NetworkMapEmbed',
  component: NetworkMapEmbed,
  tags: ['autodocs'],
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component:
          'Embeddable read-only network map for sharing. Supports sensitive mode which hides IP addresses and sanitizes device names. Used for public/iframe embeds.',
      },
    },
  },
  argTypes: {
    data: {
      description: 'The network tree structure to display',
    },
    sensitiveMode: {
      control: 'boolean',
      description: 'When true, hides IP addresses and sanitizes device names',
    },
    isDark: {
      control: 'boolean',
      description: 'Dark mode theme',
    },
    healthMetrics: {
      description: 'Health metrics for each device by IP address',
    },
  },
  decorators: [
    () => ({
      template:
        '<div style="height: 500px; width: 100%; border-radius: 8px; overflow: hidden;"><story /></div>',
    }),
  ],
} satisfies Meta<typeof NetworkMapEmbed>;

export default meta;
type Story = StoryObj<typeof meta>;

// Default light mode view
export const Default: Story = {
  args: {
    data: createSampleNetwork(),
    sensitiveMode: false,
    isDark: false,
  },
};

// Dark mode
export const DarkMode: Story = {
  args: {
    data: createSampleNetwork(),
    sensitiveMode: false,
    isDark: true,
  },
};

// Sensitive mode (IPs hidden)
export const SensitiveMode: Story = {
  args: {
    data: createSampleNetwork(),
    sensitiveMode: true,
    isDark: false,
  },
  parameters: {
    docs: {
      description: {
        story:
          'In sensitive mode, IP addresses are masked and device names are sanitized to protect privacy when sharing publicly.',
      },
    },
  },
};

// Sensitive mode in dark theme
export const SensitiveModeDark: Story = {
  args: {
    data: createSampleNetwork(),
    sensitiveMode: true,
    isDark: true,
  },
};

// With health metrics - all healthy
export const WithHealthMetrics: Story = {
  args: {
    data: createSampleNetwork(),
    sensitiveMode: false,
    isDark: true,
    healthMetrics: healthyMetrics,
  },
  parameters: {
    docs: {
      description: {
        story: 'Embedded map showing health status halos around nodes.',
      },
    },
  },
};

// With mixed health status
export const MixedHealthStatus: Story = {
  args: {
    data: createSampleNetwork(),
    sensitiveMode: false,
    isDark: true,
    healthMetrics: mixedMetrics,
  },
  parameters: {
    docs: {
      description: {
        story: 'Network showing mixed health states visible even in embed mode.',
      },
    },
  },
};

// Iframe embed preview
export const IframePreview: Story = {
  args: {
    data: createSampleNetwork(),
    sensitiveMode: true,
    isDark: true,
    healthMetrics: healthyMetrics,
  },
  decorators: [
    () => ({
      template: `
        <div style="padding: 20px; background: #f1f5f9;">
          <p style="margin-bottom: 10px; font-size: 14px; color: #64748b;">Preview of how the embed appears in an iframe:</p>
          <div style="height: 400px; width: 100%; border: 2px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);">
            <story />
          </div>
        </div>
      `,
    }),
  ],
};

// Minimal network
export const MinimalNetwork: Story = {
  args: {
    data: {
      id: 'router',
      name: 'Home Router',
      role: 'gateway/router',
      ip: '192.168.1.1',
      children: [
        {
          id: 'group-devices',
          name: 'Devices',
          role: 'group',
          children: [
            {
              id: 'pc',
              name: 'Desktop',
              role: 'client',
              ip: '192.168.1.10',
              parentId: 'router',
              children: [],
            },
          ],
        },
      ],
    },
    sensitiveMode: false,
    isDark: true,
  },
};
