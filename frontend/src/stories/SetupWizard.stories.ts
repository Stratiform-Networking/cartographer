import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { within, userEvent, expect, fn } from 'storybook/test'
import SetupWizard from '../components/SetupWizard.vue'

const meta = {
  title: 'Pages/SetupWizard',
  component: SetupWizard,
  tags: ['autodocs'],
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component: 'Initial setup wizard for creating the administrator account. Shown on first run when no users exist.',
      },
    },
  },
  decorators: [
    () => ({
      template: '<div style="min-height: 100vh;"><story /></div>',
    }),
  ],
} satisfies Meta<typeof SetupWizard>

export default meta
type Story = StoryObj<typeof meta>

// Default empty state
export const Default: Story = {
  args: {
    onComplete: fn(),
  },
}

// Filled form with valid data
export const FilledForm: Story = {
  args: {
    onComplete: fn(),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement)
    
    // Fill in all fields
    await userEvent.type(canvas.getByPlaceholderText('admin'), 'administrator')
    await userEvent.type(canvas.getByPlaceholderText('John'), 'Jane')
    await userEvent.type(canvas.getByPlaceholderText('Doe'), 'Smith')
    await userEvent.type(canvas.getByPlaceholderText('admin@example.com'), 'jane.smith@company.com')
    
    // Find password inputs
    const passwordInputs = canvasElement.querySelectorAll('input[type="password"]')
    await userEvent.type(passwordInputs[0], 'securepassword123')
    await userEvent.type(passwordInputs[1], 'securepassword123')
    
    // Verify button is enabled
    const submitButton = canvas.getByRole('button', { name: /create administrator account/i })
    await expect(submitButton).not.toBeDisabled()
  },
}

// Password mismatch validation
export const PasswordMismatch: Story = {
  args: {
    onComplete: fn(),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement)
    
    // Fill in basic fields
    await userEvent.type(canvas.getByPlaceholderText('admin'), 'admin')
    await userEvent.type(canvas.getByPlaceholderText('John'), 'John')
    await userEvent.type(canvas.getByPlaceholderText('Doe'), 'Doe')
    await userEvent.type(canvas.getByPlaceholderText('admin@example.com'), 'test@test.com')
    
    // Enter mismatched passwords
    const passwordInputs = canvasElement.querySelectorAll('input[type="password"]')
    await userEvent.type(passwordInputs[0], 'password123')
    await userEvent.type(passwordInputs[1], 'differentpassword')
    
    // Button should remain disabled due to password mismatch
    const submitButton = canvas.getByRole('button', { name: /create administrator account/i })
    await expect(submitButton).toBeDisabled()
  },
}

// Password visibility toggle
export const PasswordToggle: Story = {
  args: {
    onComplete: fn(),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement)
    
    // Find password input and type
    const passwordInput = canvasElement.querySelector('input[id="password"]') as HTMLInputElement
    await userEvent.type(passwordInput, 'mypassword')
    
    // Initially hidden
    await expect(passwordInput).toHaveAttribute('type', 'password')
    
    // Find and click the visibility toggle (first button in the password field area)
    const toggleButtons = canvasElement.querySelectorAll('button[type="button"]')
    await userEvent.click(toggleButtons[0])
    
    // Now should be visible
    await expect(passwordInput).toHaveAttribute('type', 'text')
  },
}

// Short password validation
export const ShortPassword: Story = {
  args: {
    onComplete: fn(),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement)
    
    // Fill in basic fields
    await userEvent.type(canvas.getByPlaceholderText('admin'), 'admin')
    await userEvent.type(canvas.getByPlaceholderText('John'), 'John')
    await userEvent.type(canvas.getByPlaceholderText('Doe'), 'Doe')
    await userEvent.type(canvas.getByPlaceholderText('admin@example.com'), 'test@test.com')
    
    // Enter short passwords (less than 8 chars)
    const passwordInputs = canvasElement.querySelectorAll('input[type="password"]')
    await userEvent.type(passwordInputs[0], 'short')
    await userEvent.type(passwordInputs[1], 'short')
    
    // Button should be disabled
    const submitButton = canvas.getByRole('button', { name: /create administrator account/i })
    await expect(submitButton).toBeDisabled()
  },
}

