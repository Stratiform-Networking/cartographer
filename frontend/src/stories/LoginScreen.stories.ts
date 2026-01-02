import type { Meta, StoryObj } from '@storybook/vue3-vite';
import { within, userEvent, expect, fn } from 'storybook/test';
import LoginScreen from '../components/LoginScreen.vue';

const meta = {
  title: 'Pages/LoginScreen',
  component: LoginScreen,
  tags: ['autodocs'],
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component:
          'The main login page for Cartographer. Features a dark gradient background with a glassmorphic card design.',
      },
    },
  },
  decorators: [
    () => ({
      template: '<div style="min-height: 100vh;"><story /></div>',
    }),
  ],
} satisfies Meta<typeof LoginScreen>;

export default meta;
type Story = StoryObj<typeof meta>;

// Default empty state
export const Default: Story = {
  args: {
    onSuccess: fn(),
  },
};

// Story with interaction test for form validation
export const FilledForm: Story = {
  args: {
    onSuccess: fn(),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);

    // Find and fill the username field
    const usernameInput = canvas.getByPlaceholderText('Enter your username');
    await userEvent.type(usernameInput, 'admin');

    // Find and fill the password field
    const passwordInput = canvas.getByPlaceholderText('••••••••');
    await userEvent.type(passwordInput, 'secretpassword');

    // Verify the inputs have the values
    await expect(usernameInput).toHaveValue('admin');
    await expect(passwordInput).toHaveValue('secretpassword');
  },
};

// Story showing password visibility toggle
export const PasswordToggle: Story = {
  args: {
    onSuccess: fn(),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);

    // Type a password
    const passwordInput = canvas.getByPlaceholderText('••••••••');
    await userEvent.type(passwordInput, 'mypassword123');

    // Initially password should be hidden (type="password")
    await expect(passwordInput).toHaveAttribute('type', 'password');

    // Find and click the visibility toggle button
    const toggleButtons = canvasElement.querySelectorAll('button[type="button"]');
    const toggleButton = toggleButtons[0];
    await userEvent.click(toggleButton);

    // Now password should be visible (type="text")
    await expect(passwordInput).toHaveAttribute('type', 'text');
  },
};

// Story showing disabled button when form is invalid
export const EmptyFormDisabledButton: Story = {
  args: {
    onSuccess: fn(),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);

    // Find the submit button
    const submitButton = canvas.getByRole('button', { name: /sign in/i });

    // Button should be disabled when form is empty
    await expect(submitButton).toBeDisabled();
  },
};
