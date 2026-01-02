import type { Meta, StoryObj } from '@storybook/vue3-vite';
import { fn } from 'storybook/test';
import AssistantChat from '../components/AssistantChat.vue';

const meta = {
  title: 'Components/AssistantChat',
  component: AssistantChat,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
    docs: {
      description: {
        component:
          'AI-powered network assistant chat interface. Supports multiple LLM providers (OpenAI, Anthropic, Gemini, Ollama) with streaming responses.',
      },
    },
  },
  argTypes: {
    onClose: { action: 'close' },
  },
  decorators: [
    () => ({
      template: `
        <div class="w-[400px] h-[600px] border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
          <story />
        </div>
      `,
    }),
  ],
} satisfies Meta<typeof AssistantChat>;

export default meta;
type Story = StoryObj<typeof meta>;

// Default state
export const Default: Story = {
  args: {
    onClose: fn(),
  },
};

// Note: The AssistantChat component fetches available providers on mount
// In a real implementation, you might want to mock the API calls
// For now, we demonstrate the component in its default state
