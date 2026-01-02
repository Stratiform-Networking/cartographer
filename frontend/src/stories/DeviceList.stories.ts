import type { Meta, StoryObj } from '@storybook/vue3-vite';
import { within, userEvent, expect, fn } from 'storybook/test';
import DeviceList from '../components/DeviceList.vue';
import type { TreeNode } from '../types/network';

// Sample device tree data
const createMockDevices = (): TreeNode => ({
  id: 'router-1',
  name: 'Main Gateway',
  role: 'gateway/router',
  ip: '192.168.1.1',
  children: [
    {
      id: 'switch-1',
      name: 'Core Switch',
      role: 'switch/ap',
      ip: '192.168.1.2',
      children: [
        {
          id: 'server-1',
          name: 'Web Server',
          role: 'server',
          ip: '192.168.1.10',
          children: [],
        },
        {
          id: 'nas-1',
          name: 'NAS Storage',
          role: 'nas',
          ip: '192.168.1.20',
          children: [],
        },
      ],
    },
    {
      id: 'firewall-1',
      name: 'Edge Firewall',
      role: 'firewall',
      ip: '192.168.1.3',
      children: [],
    },
    {
      id: 'client-1',
      name: 'Workstation-01',
      role: 'client',
      ip: '192.168.1.100',
      children: [],
    },
    {
      id: 'client-2',
      name: 'MacBook Pro',
      role: 'client',
      ip: '192.168.1.101',
      children: [],
    },
    {
      id: 'service-1',
      name: 'Docker Host',
      role: 'service',
      ip: '192.168.1.50',
      children: [],
    },
  ],
});

const meta = {
  title: 'Components/DeviceList',
  component: DeviceList,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
    docs: {
      description: {
        component:
          'A searchable list of network devices with role-based color coding and health status indicators.',
      },
    },
  },
  argTypes: {
    root: {
      control: 'object',
      description: 'The root tree node containing all devices',
    },
    selectedId: {
      control: 'text',
      description: 'ID of the currently selected device',
    },
    onSelect: { action: 'select' },
  },
  decorators: [
    () => ({
      template: `
        <div class="w-80 h-[500px] border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden bg-white dark:bg-slate-800">
          <story />
        </div>
      `,
    }),
  ],
} satisfies Meta<typeof DeviceList>;

export default meta;
type Story = StoryObj<typeof meta>;

// Default story with sample devices
export const Default: Story = {
  args: {
    root: createMockDevices(),
    onSelect: fn(),
  },
};

// With a selected device
export const WithSelection: Story = {
  args: {
    root: createMockDevices(),
    selectedId: 'server-1',
    onSelect: fn(),
  },
};

// Story testing search functionality
export const SearchFunctionality: Story = {
  args: {
    root: createMockDevices(),
    onSelect: fn(),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);

    // Find and interact with the search input
    const searchInput = canvas.getByPlaceholderText('Search devices...');

    // Type a search query
    await userEvent.type(searchInput, 'server');

    // Verify the search filters the list
    await expect(canvas.getByText('Web Server')).toBeInTheDocument();
  },
};

// Story with search showing no results
export const SearchNoResults: Story = {
  args: {
    root: createMockDevices(),
    onSelect: fn(),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);

    const searchInput = canvas.getByPlaceholderText('Search devices...');
    await userEvent.type(searchInput, 'nonexistent-device');

    // Should show empty state
    await expect(canvas.getByText('No devices found')).toBeInTheDocument();
  },
};

// Empty device list
export const EmptyList: Story = {
  args: {
    root: {
      id: 'root',
      name: 'Network',
      role: 'group',
      children: [],
    } as TreeNode,
    onSelect: fn(),
  },
};

// Large device list for performance testing
export const LargeList: Story = {
  args: {
    root: {
      id: 'router-1',
      name: 'Main Gateway',
      role: 'gateway/router',
      ip: '192.168.1.1',
      children: Array.from({ length: 50 }, (_, i) => ({
        id: `device-${i}`,
        name: `Device ${i + 1}`,
        role: ['client', 'server', 'service', 'nas'][i % 4] as string,
        ip: `192.168.1.${i + 10}`,
        children: [],
      })),
    } as TreeNode,
    onSelect: fn(),
  },
};

// Click interaction test
export const ClickToSelect: Story = {
  args: {
    root: createMockDevices(),
    onSelect: fn(),
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);

    // Click on a device
    const device = canvas.getByText('Web Server');
    await userEvent.click(device);

    // Verify the select handler was called
    await expect(args.onSelect).toHaveBeenCalledWith('server-1');
  },
};
