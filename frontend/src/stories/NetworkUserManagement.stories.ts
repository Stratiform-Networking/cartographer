import type { Meta, StoryObj } from '@storybook/vue3-vite';
import { fn } from 'storybook/test';
import NetworkUserManagement from '../components/NetworkUserManagement.vue';

const meta = {
  title: 'Components/NetworkUserManagement',
  component: NetworkUserManagement,
  tags: ['autodocs'],
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component:
          'Panel for managing user permissions on a specific network. Allows network owners to add/remove users and set their access roles.',
      },
    },
  },
  argTypes: {
    networkId: {
      control: 'text',
      description: 'UUID of the network',
    },
    ownerId: {
      control: 'text',
      description: 'UUID of the network owner',
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
} satisfies Meta<typeof NetworkUserManagement>;

export default meta;
type Story = StoryObj<typeof meta>;

// Default state
export const Default: Story = {
  args: {
    networkId: '550e8400-e29b-41d4-a716-446655440000',
    ownerId: '123e4567-e89b-12d3-a456-426614174000',
    onClose: fn(),
  },
};

// Different network
export const DifferentNetwork: Story = {
  args: {
    networkId: '660e8400-e29b-41d4-a716-446655440001',
    ownerId: '123e4567-e89b-12d3-a456-426614174000',
    onClose: fn(),
  },
};
