import type { Meta, StoryObj } from '@storybook/vue3-vite';
import { fn } from 'storybook/test';
import NodeInfoPanel from '../components/NodeInfoPanel.vue';
import type { TreeNode, DeviceMetrics } from '../types/network';

// Sample node data
const createMockNode = (overrides: Partial<TreeNode> = {}): TreeNode => ({
  id: '192.168.1.10',
  name: 'Web Server',
  hostname: 'webserver.local',
  ip: '192.168.1.10',
  role: 'server',
  monitoringEnabled: true,
  notes: 'Production web server running nginx',
  parentId: '192.168.1.1',
  connectionSpeed: '1GbE',
  createdAt: '2024-01-15T10:00:00Z',
  updatedAt: '2024-06-15T12:00:00Z',
  version: 3,
  ...overrides,
});

const createMockDevices = (): TreeNode[] => [
  { id: '192.168.1.1', name: 'Gateway', ip: '192.168.1.1', role: 'gateway/router' },
  { id: '192.168.1.2', name: 'Core Switch', ip: '192.168.1.2', role: 'switch/ap' },
  { id: '192.168.1.10', name: 'Web Server', ip: '192.168.1.10', role: 'server' },
  { id: '192.168.1.20', name: 'NAS', ip: '192.168.1.20', role: 'nas' },
];

const meta = {
  title: 'Components/NodeInfoPanel',
  component: NodeInfoPanel,
  tags: ['autodocs'],
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component:
          'Panel showing detailed information about a selected network node including health metrics, connection info, notes, and LAN port configuration.',
      },
    },
  },
  argTypes: {
    node: {
      control: 'object',
      description: 'The selected network node',
    },
    canEdit: {
      control: 'boolean',
      description: 'Whether the user can edit node details',
    },
    allDevices: {
      control: 'object',
      description: 'All devices in the network for connection selection',
    },
  },
  decorators: [
    () => ({
      template: `
        <div class="h-screen flex justify-end bg-slate-100 dark:bg-slate-900">
          <story />
        </div>
      `,
    }),
  ],
} satisfies Meta<typeof NodeInfoPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

// Default server node
export const Default: Story = {
  args: {
    node: createMockNode(),
    canEdit: true,
    allDevices: createMockDevices(),
    onClose: fn(),
    onToggleMonitoring: fn(),
    onUpdateNotes: fn(),
    onUpdateLanPorts: fn(),
  },
};

// Gateway node
export const GatewayNode: Story = {
  args: {
    node: createMockNode({
      id: '192.168.1.1',
      name: 'Main Gateway',
      hostname: 'router.local',
      ip: '192.168.1.1',
      role: 'gateway/router',
      notes: 'Primary internet gateway',
    }),
    canEdit: true,
    allDevices: createMockDevices(),
    onClose: fn(),
  },
};

// Switch/AP node with LAN ports
export const SwitchWithPorts: Story = {
  args: {
    node: createMockNode({
      id: '192.168.1.2',
      name: 'Core Switch',
      hostname: 'switch.local',
      ip: '192.168.1.2',
      role: 'switch/ap',
      lanPorts: {
        rows: 1,
        cols: 8,
        ports: [
          { row: 1, col: 1, type: 'rj45', status: 'active', speed: '1G' },
          { row: 1, col: 2, type: 'rj45', status: 'active', speed: '1G' },
          { row: 1, col: 3, type: 'rj45', status: 'unused', speed: 'auto' },
          { row: 1, col: 4, type: 'rj45', status: 'unused', speed: 'auto' },
          { row: 1, col: 5, type: 'rj45', status: 'unused', speed: 'auto' },
          { row: 1, col: 6, type: 'rj45', status: 'unused', speed: 'auto' },
          { row: 1, col: 7, type: 'sfp', status: 'active', speed: '10G' },
          { row: 1, col: 8, type: 'sfp', status: 'blocked', speed: '10G' },
        ],
      },
    }),
    canEdit: true,
    allDevices: createMockDevices(),
    onClose: fn(),
  },
};

// Client device
export const ClientDevice: Story = {
  args: {
    node: createMockNode({
      id: '192.168.1.100',
      name: 'MacBook Pro',
      hostname: 'macbook.local',
      ip: '192.168.1.100',
      role: 'client',
      notes: '',
    }),
    canEdit: true,
    allDevices: createMockDevices(),
    onClose: fn(),
  },
};

// Read-only mode
export const ReadOnly: Story = {
  args: {
    node: createMockNode(),
    canEdit: false,
    allDevices: createMockDevices(),
    onClose: fn(),
  },
};

// Monitoring disabled
export const MonitoringDisabled: Story = {
  args: {
    node: createMockNode({
      monitoringEnabled: false,
    }),
    canEdit: true,
    allDevices: createMockDevices(),
    onClose: fn(),
  },
};

// Unknown device type
export const UnknownDevice: Story = {
  args: {
    node: createMockNode({
      id: '192.168.1.200',
      name: 'Unknown Device',
      ip: '192.168.1.200',
      role: 'unknown',
      hostname: undefined,
    }),
    canEdit: true,
    allDevices: createMockDevices(),
    onClose: fn(),
  },
};
