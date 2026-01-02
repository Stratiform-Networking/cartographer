import type { Meta, StoryObj } from '@storybook/vue3-vite';
import { fn } from 'storybook/test';
import NotificationSettingsGlobal from '../components/NotificationSettingsGlobal.vue';

// Mock preferences
const createMockPreferences = (overrides = {}) => ({
  email_address: 'user@example.com',
  email_enabled: true,
  discord_enabled: false,
  discord_delivery_method: 'channel' as const,
  discord_guild_id: null,
  discord_channel_id: null,
  cartographer_up_enabled: true,
  cartographer_down_enabled: true,
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

const meta = {
  title: 'Components/NotificationSettingsGlobal',
  component: NotificationSettingsGlobal,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
    docs: {
      description: {
        component:
          'Global notification settings panel for configuring email and Discord notifications across all networks.',
      },
    },
  },
  argTypes: {
    preferences: {
      control: 'object',
      description: 'User notification preferences',
    },
    serviceStatus: {
      control: 'object',
      description: 'Status of notification services',
    },
    discordLink: {
      control: 'object',
      description: 'Discord account link status',
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
} satisfies Meta<typeof NotificationSettingsGlobal>;

export default meta;
type Story = StoryObj<typeof meta>;

// Default state with email configured
export const Default: Story = {
  args: {
    preferences: createMockPreferences(),
    serviceStatus: createMockServiceStatus(),
    discordLink: createMockDiscordLink(false),
    onUpdate: fn(),
    'onTest-email': fn(),
    'onTest-discord': fn(),
    'onLink-discord': fn(),
    'onUnlink-discord': fn(),
  },
};

// With Discord linked
export const DiscordLinked: Story = {
  args: {
    preferences: createMockPreferences({
      discord_enabled: true,
      discord_delivery_method: 'dm',
    }),
    serviceStatus: createMockServiceStatus({
      discord: { configured: true, enabled: true },
    }),
    discordLink: createMockDiscordLink(true),
    onUpdate: fn(),
    'onTest-email': fn(),
    'onTest-discord': fn(),
    'onLink-discord': fn(),
    'onUnlink-discord': fn(),
  },
};

// All notifications disabled
export const AllDisabled: Story = {
  args: {
    preferences: createMockPreferences({
      email_enabled: false,
      discord_enabled: false,
      cartographer_up_enabled: false,
      cartographer_down_enabled: false,
    }),
    serviceStatus: createMockServiceStatus(),
    discordLink: createMockDiscordLink(false),
    onUpdate: fn(),
    'onTest-email': fn(),
    'onTest-discord': fn(),
    'onLink-discord': fn(),
    'onUnlink-discord': fn(),
  },
};

// Email not configured (service level)
export const EmailNotConfigured: Story = {
  args: {
    preferences: createMockPreferences({
      email_address: '',
      email_enabled: false,
    }),
    serviceStatus: createMockServiceStatus({
      email: { configured: false, enabled: false },
    }),
    discordLink: createMockDiscordLink(false),
    onUpdate: fn(),
    'onTest-email': fn(),
    'onTest-discord': fn(),
    'onLink-discord': fn(),
    'onUnlink-discord': fn(),
  },
};

// Discord channel delivery
export const DiscordChannelDelivery: Story = {
  args: {
    preferences: createMockPreferences({
      discord_enabled: true,
      discord_delivery_method: 'channel',
      discord_guild_id: '123456789',
      discord_channel_id: '987654321',
    }),
    serviceStatus: createMockServiceStatus({
      discord: { configured: true, enabled: true },
    }),
    discordLink: createMockDiscordLink(true),
    onUpdate: fn(),
    'onTest-email': fn(),
    'onTest-discord': fn(),
    'onLink-discord': fn(),
    'onUnlink-discord': fn(),
  },
};
