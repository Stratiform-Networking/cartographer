import type { Meta, StoryObj } from '@storybook/vue3-vite';
import { within, userEvent, expect } from 'storybook/test';
import { ref, h, defineComponent } from 'vue';

// Create mock AcceptInvite components for different states
const createMockedAcceptInvite = (config: {
  state: 'loading' | 'error' | 'success' | 'form';
  error?: string;
  inviteInfo?: {
    email: string;
    role: 'readonly' | 'readwrite';
    invited_by_name: string;
  };
}) => {
  return defineComponent({
    name: 'MockedAcceptInvite',
    setup() {
      const isLoading = ref(config.state === 'loading');
      const error = ref(config.state === 'error' ? config.error || 'Invalid invitation' : null);
      const success = ref(config.state === 'success');
      const inviteInfo = ref(config.state === 'form' ? config.inviteInfo : null);
      const isSubmitting = ref(false);
      const formError = ref<string | null>(null);

      const form = ref({
        username: '',
        firstName: '',
        lastName: '',
        password: '',
        confirmPassword: '',
      });

      const getRoleBadgeClass = (role: string) => {
        switch (role) {
          case 'readwrite':
            return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400';
          case 'readonly':
            return 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400';
          default:
            return 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400';
        }
      };

      const getRoleLabel = (role: string) => {
        switch (role) {
          case 'readwrite':
            return 'Admin';
          case 'readonly':
            return 'Member';
          default:
            return 'Member';
        }
      };

      const onSubmit = () => {
        if (form.value.password !== form.value.confirmPassword) {
          formError.value = 'Passwords do not match';
          return;
        }
        isSubmitting.value = true;
        setTimeout(() => {
          isSubmitting.value = false;
          success.value = true;
        }, 1000);
      };

      return () =>
        h(
          'div',
          {
            class:
              'min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-cyan-900 flex items-center justify-center p-4',
          },
          [
            h('div', { class: 'w-full max-w-md' }, [
              // Loading State
              isLoading.value &&
                h(
                  'div',
                  { class: 'bg-white dark:bg-slate-800 rounded-2xl shadow-2xl p-8 text-center' },
                  [
                    h(
                      'svg',
                      {
                        class: 'animate-spin h-12 w-12 text-cyan-500 mx-auto mb-4',
                        xmlns: 'http://www.w3.org/2000/svg',
                        fill: 'none',
                        viewBox: '0 0 24 24',
                      },
                      [
                        h('circle', {
                          class: 'opacity-25',
                          cx: '12',
                          cy: '12',
                          r: '10',
                          stroke: 'currentColor',
                          'stroke-width': '4',
                        }),
                        h('path', {
                          class: 'opacity-75',
                          fill: 'currentColor',
                          d: 'M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z',
                        }),
                      ]
                    ),
                    h(
                      'p',
                      { class: 'text-slate-600 dark:text-slate-400' },
                      'Verifying invitation...'
                    ),
                  ]
                ),

              // Error State
              error.value &&
                h(
                  'div',
                  { class: 'bg-white dark:bg-slate-800 rounded-2xl shadow-2xl p-8 text-center' },
                  [
                    h(
                      'div',
                      {
                        class:
                          'w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center',
                      },
                      [
                        h(
                          'svg',
                          {
                            xmlns: 'http://www.w3.org/2000/svg',
                            class: 'h-8 w-8 text-red-500',
                            fill: 'none',
                            viewBox: '0 0 24 24',
                            stroke: 'currentColor',
                          },
                          [
                            h('path', {
                              'stroke-linecap': 'round',
                              'stroke-linejoin': 'round',
                              'stroke-width': '2',
                              d: 'M6 18L18 6M6 6l12 12',
                            }),
                          ]
                        ),
                      ]
                    ),
                    h(
                      'h2',
                      { class: 'text-xl font-semibold text-slate-900 dark:text-white mb-2' },
                      'Invalid Invitation'
                    ),
                    h('p', { class: 'text-slate-600 dark:text-slate-400 mb-6' }, error.value),
                    h(
                      'a',
                      {
                        href: '/',
                        class:
                          'inline-flex items-center gap-2 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors',
                      },
                      'Go to Login'
                    ),
                  ]
                ),

              // Success State
              success.value &&
                h(
                  'div',
                  { class: 'bg-white dark:bg-slate-800 rounded-2xl shadow-2xl p-8 text-center' },
                  [
                    h(
                      'div',
                      {
                        class:
                          'w-16 h-16 mx-auto mb-4 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center',
                      },
                      [
                        h(
                          'svg',
                          {
                            xmlns: 'http://www.w3.org/2000/svg',
                            class: 'h-8 w-8 text-green-500',
                            fill: 'none',
                            viewBox: '0 0 24 24',
                            stroke: 'currentColor',
                          },
                          [
                            h('path', {
                              'stroke-linecap': 'round',
                              'stroke-linejoin': 'round',
                              'stroke-width': '2',
                              d: 'M5 13l4 4L19 7',
                            }),
                          ]
                        ),
                      ]
                    ),
                    h(
                      'h2',
                      { class: 'text-xl font-semibold text-slate-900 dark:text-white mb-2' },
                      'Account Created!'
                    ),
                    h(
                      'p',
                      { class: 'text-slate-600 dark:text-slate-400 mb-6' },
                      'Your account has been created successfully. You can now log in with your credentials.'
                    ),
                    h(
                      'a',
                      {
                        href: '/',
                        class:
                          'inline-flex items-center gap-2 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors',
                      },
                      'Go to Login'
                    ),
                  ]
                ),

              // Form State
              inviteInfo.value &&
                !success.value &&
                h(
                  'div',
                  { class: 'bg-white dark:bg-slate-800 rounded-2xl shadow-2xl overflow-hidden' },
                  [
                    // Header
                    h(
                      'div',
                      {
                        class:
                          'px-8 py-6 bg-gradient-to-r from-cyan-600 to-teal-600 text-white text-center',
                      },
                      [
                        h('h1', { class: 'text-2xl font-bold mb-1' }, '🗺️ Cartographer'),
                        h('p', { class: 'text-cyan-100 text-sm' }, 'Network Mapping Tool'),
                      ]
                    ),
                    // Invitation Info
                    h(
                      'div',
                      { class: 'px-8 pt-6 pb-4 border-b border-slate-200 dark:border-slate-700' },
                      [
                        h('p', { class: 'text-slate-600 dark:text-slate-400 text-center' }, [
                          h(
                            'strong',
                            { class: 'text-slate-900 dark:text-white' },
                            inviteInfo.value.invited_by_name
                          ),
                          ' has invited you to join with ',
                          h(
                            'span',
                            {
                              class: [
                                'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                                getRoleBadgeClass(inviteInfo.value.role),
                              ],
                            },
                            getRoleLabel(inviteInfo.value.role)
                          ),
                          ' access.',
                        ]),
                      ]
                    ),
                    // Form
                    h(
                      'form',
                      {
                        onSubmit: (e: Event) => {
                          e.preventDefault();
                          onSubmit();
                        },
                        class: 'p-8 space-y-4',
                      },
                      [
                        // Email (disabled)
                        h('div', [
                          h(
                            'label',
                            {
                              class:
                                'block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1',
                            },
                            'Email'
                          ),
                          h('input', {
                            type: 'email',
                            value: inviteInfo.value.email,
                            disabled: true,
                            class:
                              'w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-slate-100 dark:bg-slate-900 text-slate-500 dark:text-slate-400',
                          }),
                        ]),
                        // Username
                        h('div', [
                          h(
                            'label',
                            {
                              class:
                                'block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1',
                            },
                            'Username'
                          ),
                          h('input', {
                            type: 'text',
                            value: form.value.username,
                            onInput: (e: Event) =>
                              (form.value.username = (e.target as HTMLInputElement).value),
                            required: true,
                            class:
                              'w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                            placeholder: 'Choose a username',
                          }),
                          h(
                            'p',
                            { class: 'text-xs text-slate-500 mt-1' },
                            'Letters, numbers, underscores, and hyphens only'
                          ),
                        ]),
                        // Names
                        h('div', { class: 'grid grid-cols-2 gap-3' }, [
                          h('div', [
                            h(
                              'label',
                              {
                                class:
                                  'block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1',
                              },
                              'First Name'
                            ),
                            h('input', {
                              type: 'text',
                              value: form.value.firstName,
                              onInput: (e: Event) =>
                                (form.value.firstName = (e.target as HTMLInputElement).value),
                              required: true,
                              class:
                                'w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                              placeholder: 'John',
                            }),
                          ]),
                          h('div', [
                            h(
                              'label',
                              {
                                class:
                                  'block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1',
                              },
                              'Last Name'
                            ),
                            h('input', {
                              type: 'text',
                              value: form.value.lastName,
                              onInput: (e: Event) =>
                                (form.value.lastName = (e.target as HTMLInputElement).value),
                              required: true,
                              class:
                                'w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                              placeholder: 'Doe',
                            }),
                          ]),
                        ]),
                        // Password
                        h('div', [
                          h(
                            'label',
                            {
                              class:
                                'block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1',
                            },
                            'Password'
                          ),
                          h('input', {
                            type: 'password',
                            value: form.value.password,
                            onInput: (e: Event) =>
                              (form.value.password = (e.target as HTMLInputElement).value),
                            required: true,
                            minlength: 8,
                            class:
                              'w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                            placeholder: '••••••••',
                          }),
                          h('p', { class: 'text-xs text-slate-500 mt-1' }, 'Minimum 8 characters'),
                        ]),
                        // Confirm Password
                        h('div', [
                          h(
                            'label',
                            {
                              class:
                                'block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1',
                            },
                            'Confirm Password'
                          ),
                          h('input', {
                            type: 'password',
                            value: form.value.confirmPassword,
                            onInput: (e: Event) =>
                              (form.value.confirmPassword = (e.target as HTMLInputElement).value),
                            required: true,
                            minlength: 8,
                            class:
                              'w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                            placeholder: '••••••••',
                          }),
                        ]),
                        // Error
                        formError.value &&
                          h(
                            'div',
                            {
                              class:
                                'p-3 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-500/50 rounded-lg',
                            },
                            [
                              h(
                                'p',
                                { class: 'text-sm text-red-600 dark:text-red-400' },
                                formError.value
                              ),
                            ]
                          ),
                        // Submit
                        h(
                          'button',
                          {
                            type: 'submit',
                            disabled: isSubmitting.value,
                            class:
                              'w-full px-4 py-3 bg-cyan-600 text-white font-medium rounded-lg hover:bg-cyan-700 disabled:opacity-50 transition-colors',
                          },
                          isSubmitting.value ? 'Creating Account...' : 'Create Account'
                        ),
                      ]
                    ),
                  ]
                ),
            ]),
          ]
        );
    },
  });
};

const meta = {
  title: 'Pages/AcceptInvite',
  tags: ['autodocs'],
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component:
          'Invitation acceptance page where invited users create their accounts. Shown when following an invite link.',
      },
    },
  },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

// Loading state
export const Loading: Story = {
  render: () => ({
    components: { AcceptInvite: createMockedAcceptInvite({ state: 'loading' }) },
    template: '<AcceptInvite />',
  }),
};

// Invalid/expired token error
export const InvalidToken: Story = {
  render: () => ({
    components: {
      AcceptInvite: createMockedAcceptInvite({
        state: 'error',
        error: 'This invitation has expired or is no longer valid',
      }),
    },
    template: '<AcceptInvite />',
  }),
};

// Success state after account creation
export const AccountCreated: Story = {
  render: () => ({
    components: { AcceptInvite: createMockedAcceptInvite({ state: 'success' }) },
    template: '<AcceptInvite />',
  }),
};

// Form with Admin (readwrite) role invitation
export const AdminInvite: Story = {
  render: () => ({
    components: {
      AcceptInvite: createMockedAcceptInvite({
        state: 'form',
        inviteInfo: {
          email: 'newuser@example.com',
          role: 'readwrite',
          invited_by_name: 'John Smith',
        },
      }),
    },
    template: '<AcceptInvite />',
  }),
};

// Form with Member (readonly) role invitation
export const MemberInvite: Story = {
  render: () => ({
    components: {
      AcceptInvite: createMockedAcceptInvite({
        state: 'form',
        inviteInfo: {
          email: 'viewer@company.com',
          role: 'readonly',
          invited_by_name: 'Admin User',
        },
      }),
    },
    template: '<AcceptInvite />',
  }),
};

// Form filling interaction test
export const FormInteraction: Story = {
  render: () => ({
    components: {
      AcceptInvite: createMockedAcceptInvite({
        state: 'form',
        inviteInfo: {
          email: 'test@example.com',
          role: 'readwrite',
          invited_by_name: 'Demo User',
        },
      }),
    },
    template: '<AcceptInvite />',
  }),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);

    // Fill out the form
    const usernameInput = canvas.getByPlaceholderText('Choose a username');
    await userEvent.type(usernameInput, 'newuser123');

    const firstNameInput = canvas.getByPlaceholderText('John');
    await userEvent.type(firstNameInput, 'Jane');

    const lastNameInput = canvas.getByPlaceholderText('Doe');
    await userEvent.type(lastNameInput, 'Smith');

    // Verify form values
    await expect(usernameInput).toHaveValue('newuser123');
    await expect(firstNameInput).toHaveValue('Jane');
    await expect(lastNameInput).toHaveValue('Smith');
  },
};
