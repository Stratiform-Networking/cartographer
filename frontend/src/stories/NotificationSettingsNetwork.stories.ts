import type { Meta, StoryObj } from '@storybook/vue3-vite';
import { fn } from 'storybook/test';
import NotificationSettingsNetwork from '../components/NotificationSettingsNetwork.vue';

// Mock preferences
const createMockPreferences = (overrides = {}) => ({
  email_enabled: true,
  discord_enabled: false,
  device_up_enabled: true,
  device_down_enabled: true,
  anomaly_detection_enabled: true,
  ...overrides,
});

// Mock service status
const createMockServiceStatus = (overrides = {}) => ({
  email: { configured: true, enabled: true },
  discord: { configured: false, enabled: false },
  ...overrides,
});

// Mock discord link
const createMockDiscordLink = (linked = false) =>
  linked
    ? {
        linked: true,
        discord_username: 'User#1234',
        discord_user_id: '123456789',
      }
    : {
        linked: false,
        discord_username: null,
        discord_user_id: null,
      };

// Mock anomaly stats
const createMockAnomalyStats = (hasAnomalies = false) => ({
  total_anomalies_24h: hasAnomalies ? 5 : 0,
  anomalies_by_device: hasAnomalies
    ? {
        '192.168.1.10': 3,
        '192.168.1.20': 2,
      }
    : {},
  last_anomaly: hasAnomalies ? '2024-06-15T10:30:00Z' : null,
});

const meta = {
  title: 'Components/NotificationSettingsNetwork',
  component: NotificationSettingsNetwork,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
    docs: {
      description: {
        component:
          'Network-specific notification settings panel for configuring alerts for a particular network including device status and anomaly detection.',
      },
    },
  },
  argTypes: {
    networkId: {
      control: 'text',
      description: 'UUID of the network',
    },
    preferences: {
      control: 'object',
      description: 'Network notification preferences',
    },
    serviceStatus: {
      control: 'object',
      description: 'Status of notification services',
    },
    discordLink: {
      control: 'object',
      description: 'Discord account link status',
    },
    anomalyStats: {
      control: 'object',
      description: 'Anomaly detection statistics',
    },
  },
  decorators: [
    () => ({
      template: `
        <div class="max-w-2xl mx-auto bg-white dark:bg-slate-900 rounded-lg shadow-lg">
          <story />
        </div>
      `,
    }),
  ],
} satisfies Meta<typeof NotificationSettingsNetwork>;

export default meta;
type Story = StoryObj<typeof meta>;

// Default state
export const Default: Story = {
  args: {
    networkId: '550e8400-e29b-41d4-a716-446655440000',
    preferences: createMockPreferences(),
    serviceStatus: createMockServiceStatus(),
    discordLink: createMockDiscordLink(false),
    anomalyStats: createMockAnomalyStats(false),
    onUpdate: fn(),
    'onTest-email': fn(),
    'onTest-discord': fn(),
  },
};

// With Discord enabled
export const WithDiscord: Story = {
  args: {
    networkId: '550e8400-e29b-41d4-a716-446655440000',
    preferences: createMockPreferences({
      discord_enabled: true,
    }),
    serviceStatus: createMockServiceStatus({
      discord: { configured: true, enabled: true },
    }),
    discordLink: createMockDiscordLink(true),
    anomalyStats: createMockAnomalyStats(false),
    onUpdate: fn(),
    'onTest-email': fn(),
    'onTest-discord': fn(),
  },
};

// With anomalies detected
export const WithAnomalies: Story = {
  args: {
    networkId: '550e8400-e29b-41d4-a716-446655440000',
    preferences: createMockPreferences({
      anomaly_detection_enabled: true,
    }),
    serviceStatus: createMockServiceStatus(),
    discordLink: createMockDiscordLink(false),
    anomalyStats: createMockAnomalyStats(true),
    onUpdate: fn(),
    'onTest-email': fn(),
    'onTest-discord': fn(),
  },
};

// All notifications disabled
export const AllDisabled: Story = {
  args: {
    networkId: '550e8400-e29b-41d4-a716-446655440000',
    preferences: createMockPreferences({
      email_enabled: false,
      discord_enabled: false,
      device_up_enabled: false,
      device_down_enabled: false,
      anomaly_detection_enabled: false,
    }),
    serviceStatus: createMockServiceStatus(),
    discordLink: createMockDiscordLink(false),
    anomalyStats: createMockAnomalyStats(false),
    onUpdate: fn(),
    'onTest-email': fn(),
    'onTest-discord': fn(),
  },
};

// Only device down alerts
export const OnlyDeviceDown: Story = {
  args: {
    networkId: '550e8400-e29b-41d4-a716-446655440000',
    preferences: createMockPreferences({
      device_up_enabled: false,
      device_down_enabled: true,
      anomaly_detection_enabled: false,
    }),
    serviceStatus: createMockServiceStatus(),
    discordLink: createMockDiscordLink(false),
    anomalyStats: createMockAnomalyStats(false),
    onUpdate: fn(),
    'onTest-email': fn(),
    'onTest-discord': fn(),
  },
};
