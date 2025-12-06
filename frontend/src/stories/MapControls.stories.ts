import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { fn } from 'storybook/test'
import MapControls from '../components/MapControls.vue'
import type { TreeNode } from '../types/network'

// Sample root node for the stories
const sampleRoot: TreeNode = {
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
      children: [],
    },
    {
      id: 'server-1',
      name: 'Web Server',
      role: 'server',
      ip: '192.168.1.10',
      children: [],
    },
  ],
}

const emptyRoot: TreeNode = {
  id: 'root',
  name: 'Network',
  role: 'group',
  children: [],
}

const meta = {
  title: 'Components/MapControls',
  component: MapControls,
  tags: ['autodocs'],
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component: 'The main toolbar/header for the network map. Contains scan controls, save/export functionality, and settings.',
      },
    },
  },
  argTypes: {
    root: {
      control: 'object',
      description: 'Root tree node containing network data',
    },
    hasUnsavedChanges: {
      control: 'boolean',
      description: 'Whether there are unsaved layout changes',
    },
    canEdit: {
      control: 'boolean',
      description: 'Whether the user has write permissions',
    },
    onUpdateMap: { action: 'updateMap' },
    onApplyLayout: { action: 'applyLayout' },
    onLog: { action: 'log' },
    onRunning: { action: 'running' },
    onClearLogs: { action: 'clearLogs' },
    onCleanUpLayout: { action: 'cleanUpLayout' },
    onAutoLoadFromServer: { action: 'autoLoadFromServer' },
    onSaved: { action: 'saved' },
  },
  decorators: [
    () => ({
      template: `
        <div class="w-full">
          <story />
        </div>
      `,
    }),
  ],
} satisfies Meta<typeof MapControls>

export default meta
type Story = StoryObj<typeof meta>

// Default state with network data
export const Default: Story = {
  args: {
    root: sampleRoot,
    hasUnsavedChanges: false,
    canEdit: true,
    onUpdateMap: fn(),
    onApplyLayout: fn(),
    onLog: fn(),
    onRunning: fn(),
    onClearLogs: fn(),
    onCleanUpLayout: fn(),
    onAutoLoadFromServer: fn(),
    onSaved: fn(),
  },
}

// With unsaved changes (highlights save button)
export const UnsavedChanges: Story = {
  args: {
    root: sampleRoot,
    hasUnsavedChanges: true,
    canEdit: true,
    onUpdateMap: fn(),
    onApplyLayout: fn(),
    onLog: fn(),
    onRunning: fn(),
    onClearLogs: fn(),
    onCleanUpLayout: fn(),
    onAutoLoadFromServer: fn(),
    onSaved: fn(),
  },
}

// Read-only mode (some buttons disabled)
export const ReadOnlyMode: Story = {
  args: {
    root: sampleRoot,
    hasUnsavedChanges: false,
    canEdit: false,
    onUpdateMap: fn(),
    onApplyLayout: fn(),
    onLog: fn(),
    onRunning: fn(),
    onClearLogs: fn(),
    onCleanUpLayout: fn(),
    onAutoLoadFromServer: fn(),
    onSaved: fn(),
  },
}

// Empty network (no devices scanned yet)
export const EmptyNetwork: Story = {
  args: {
    root: emptyRoot,
    hasUnsavedChanges: false,
    canEdit: true,
    onUpdateMap: fn(),
    onApplyLayout: fn(),
    onLog: fn(),
    onRunning: fn(),
    onClearLogs: fn(),
    onCleanUpLayout: fn(),
    onAutoLoadFromServer: fn(),
    onSaved: fn(),
  },
}

// Read-only with empty network
export const ReadOnlyEmpty: Story = {
  args: {
    root: emptyRoot,
    hasUnsavedChanges: false,
    canEdit: false,
    onUpdateMap: fn(),
    onApplyLayout: fn(),
    onLog: fn(),
    onRunning: fn(),
    onClearLogs: fn(),
    onCleanUpLayout: fn(),
    onAutoLoadFromServer: fn(),
    onSaved: fn(),
  },
}

