import type { Meta, StoryObj } from '@storybook/vue3-vite';
import { ref, h, defineComponent, computed } from 'vue';

// Create mocked UserManagement for different states
const createMockedUserManagement = (config: {
  isLoading?: boolean;
  users?: Array<{
    id: string;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
    role: 'owner' | 'readwrite' | 'readonly';
    last_login?: string;
  }>;
  invites?: Array<{
    id: string;
    email: string;
    role: 'readwrite' | 'readonly';
    status: 'pending' | 'accepted' | 'expired' | 'revoked';
    created_at: string;
    expires_at: string;
  }>;
  activeTab?: 'users' | 'invites';
}) => {
  return defineComponent({
    name: 'MockedUserManagement',
    emits: ['close'],
    setup(_, { emit }) {
      const isLoading = ref(config.isLoading ?? false);
      const activeTab = ref(config.activeTab ?? 'users');
      const showAddUser = ref(false);

      const users = ref(
        config.users ?? [
          {
            id: '1',
            username: 'admin',
            email: 'admin@example.com',
            first_name: 'Admin',
            last_name: 'User',
            role: 'owner' as const,
            last_login: new Date().toISOString(),
          },
          {
            id: '2',
            username: 'jsmith',
            email: 'john.smith@example.com',
            first_name: 'John',
            last_name: 'Smith',
            role: 'readwrite' as const,
            last_login: new Date(Date.now() - 86400000).toISOString(),
          },
          {
            id: '3',
            username: 'jdoe',
            email: 'jane.doe@example.com',
            first_name: 'Jane',
            last_name: 'Doe',
            role: 'readonly' as const,
            last_login: new Date(Date.now() - 172800000).toISOString(),
          },
        ]
      );

      const invites = ref(
        config.invites ?? [
          {
            id: '1',
            email: 'newuser@example.com',
            role: 'readwrite' as const,
            status: 'pending' as const,
            created_at: new Date(Date.now() - 3600000).toISOString(),
            expires_at: new Date(Date.now() + 259200000).toISOString(),
          },
          {
            id: '2',
            email: 'viewer@company.com',
            role: 'readonly' as const,
            status: 'accepted' as const,
            created_at: new Date(Date.now() - 86400000).toISOString(),
            expires_at: new Date(Date.now() + 172800000).toISOString(),
          },
        ]
      );

      const pendingInvites = computed(() => invites.value.filter((i) => i.status === 'pending'));
      const pastInvites = computed(() => invites.value.filter((i) => i.status !== 'pending'));

      const getFullName = (user: (typeof users.value)[0]) => `${user.first_name} ${user.last_name}`;

      const getRoleLabel = (role: string) => {
        switch (role) {
          case 'owner':
            return 'Owner';
          case 'readwrite':
            return 'Admin';
          case 'readonly':
            return 'Member';
          default:
            return 'Member';
        }
      };

      const getRoleBadgeClass = (role: string) => {
        switch (role) {
          case 'owner':
            return 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400';
          case 'readwrite':
            return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400';
          case 'readonly':
            return 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400';
          default:
            return 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400';
        }
      };

      const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString(undefined, {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        });
      };

      const formatRelativeDate = (dateStr: string) => {
        const diffMs = Date.now() - new Date(dateStr).getTime();
        const diffHours = Math.floor(diffMs / 3600000);
        if (diffHours < 1) return 'just now';
        if (diffHours < 24) return `${diffHours}h ago`;
        return `${Math.floor(diffHours / 24)}d ago`;
      };

      return () =>
        h(
          'div',
          {
            class:
              'fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm',
          },
          [
            h(
              'div',
              {
                class:
                  'bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col',
              },
              [
                // Header
                h(
                  'div',
                  {
                    class:
                      'flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50',
                  },
                  [
                    h('div', { class: 'flex items-center gap-3' }, [
                      h(
                        'div',
                        {
                          class:
                            'w-9 h-9 rounded-lg bg-cyan-100 dark:bg-cyan-900/30 flex items-center justify-center',
                        },
                        [
                          h(
                            'svg',
                            {
                              xmlns: 'http://www.w3.org/2000/svg',
                              class: 'h-5 w-5 text-cyan-600 dark:text-cyan-400',
                              fill: 'none',
                              viewBox: '0 0 24 24',
                              stroke: 'currentColor',
                              'stroke-width': '2',
                            },
                            [
                              h('path', {
                                'stroke-linecap': 'round',
                                'stroke-linejoin': 'round',
                                d: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
                              }),
                            ]
                          ),
                        ]
                      ),
                      h('div', [
                        h(
                          'h2',
                          { class: 'text-lg font-semibold text-slate-900 dark:text-white' },
                          'User Management'
                        ),
                        h(
                          'p',
                          { class: 'text-xs text-slate-500 dark:text-slate-400' },
                          'Manage users and invitations'
                        ),
                      ]),
                    ]),
                    h(
                      'button',
                      {
                        onClick: () => emit('close'),
                        class:
                          'p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500',
                      },
                      [
                        h(
                          'svg',
                          {
                            xmlns: 'http://www.w3.org/2000/svg',
                            class: 'h-5 w-5',
                            fill: 'none',
                            viewBox: '0 0 24 24',
                            stroke: 'currentColor',
                            'stroke-width': '2',
                          },
                          [
                            h('path', {
                              'stroke-linecap': 'round',
                              'stroke-linejoin': 'round',
                              d: 'M6 18L18 6M6 6l12 12',
                            }),
                          ]
                        ),
                      ]
                    ),
                  ]
                ),

                // Tabs
                h(
                  'div',
                  {
                    class:
                      'flex border-b border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/30',
                  },
                  [
                    h(
                      'button',
                      {
                        onClick: () => (activeTab.value = 'users'),
                        class: [
                          'px-6 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
                          activeTab.value === 'users'
                            ? 'border-cyan-500 text-cyan-600 dark:text-cyan-400 bg-white dark:bg-slate-800'
                            : 'border-transparent text-slate-500 hover:text-slate-700',
                        ],
                      },
                      'Users'
                    ),
                    h(
                      'button',
                      {
                        onClick: () => (activeTab.value = 'invites'),
                        class: [
                          'px-6 py-3 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-2',
                          activeTab.value === 'invites'
                            ? 'border-cyan-500 text-cyan-600 dark:text-cyan-400 bg-white dark:bg-slate-800'
                            : 'border-transparent text-slate-500 hover:text-slate-700',
                        ],
                      },
                      [
                        'Invitations',
                        pendingInvites.value.length > 0 &&
                          h(
                            'span',
                            {
                              class:
                                'px-1.5 py-0.5 text-xs bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded-full tabular-nums',
                            },
                            String(pendingInvites.value.length)
                          ),
                      ]
                    ),
                  ]
                ),

                // Content
                h('div', { class: 'flex-1 overflow-auto p-6' }, [
                  // Users Tab
                  activeTab.value === 'users' && [
                    // Add User Button
                    h('div', { class: 'mb-6' }, [
                      h(
                        'button',
                        {
                          class:
                            'inline-flex items-center gap-2 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors',
                        },
                        [
                          h(
                            'svg',
                            {
                              xmlns: 'http://www.w3.org/2000/svg',
                              class: 'h-5 w-5',
                              fill: 'none',
                              viewBox: '0 0 24 24',
                              stroke: 'currentColor',
                            },
                            [
                              h('path', {
                                'stroke-linecap': 'round',
                                'stroke-linejoin': 'round',
                                'stroke-width': '2',
                                d: 'M12 6v6m0 0v6m0-6h6m-6 0H6',
                              }),
                            ]
                          ),
                          'Add User',
                        ]
                      ),
                    ]),

                    // Loading State
                    isLoading.value &&
                      h('div', { class: 'flex items-center justify-center py-12' }, [
                        h(
                          'svg',
                          {
                            class: 'animate-spin h-8 w-8 text-cyan-500',
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
                      ]),

                    // Users List
                    !isLoading.value &&
                      h(
                        'div',
                        { class: 'space-y-3' },
                        users.value.map((user) =>
                          h(
                            'div',
                            {
                              key: user.id,
                              class:
                                'flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-slate-200 dark:border-slate-700',
                            },
                            [
                              h('div', { class: 'flex items-center gap-4' }, [
                                h(
                                  'div',
                                  {
                                    class: [
                                      'w-10 h-10 rounded-full flex items-center justify-center text-white font-medium',
                                      user.role === 'owner'
                                        ? 'bg-gradient-to-br from-amber-500 to-orange-600'
                                        : 'bg-gradient-to-br from-cyan-500 to-blue-600',
                                    ],
                                  },
                                  user.first_name.charAt(0).toUpperCase()
                                ),
                                h('div', [
                                  h('div', { class: 'flex items-center gap-2' }, [
                                    h(
                                      'span',
                                      { class: 'font-medium text-slate-900 dark:text-white' },
                                      getFullName(user)
                                    ),
                                    h(
                                      'span',
                                      {
                                        class: [
                                          'text-xs px-2 py-0.5 rounded-full',
                                          getRoleBadgeClass(user.role),
                                        ],
                                      },
                                      getRoleLabel(user.role)
                                    ),
                                  ]),
                                  h(
                                    'div',
                                    { class: 'text-sm text-slate-500 dark:text-slate-400' },
                                    [
                                      user.email,
                                      user.last_login &&
                                        h(
                                          'span',
                                          { class: 'ml-2' },
                                          `• Last login: ${formatDate(user.last_login)}`
                                        ),
                                    ]
                                  ),
                                ]),
                              ]),
                              user.role !== 'owner'
                                ? h('div', { class: 'flex items-center gap-2' }, [
                                    h(
                                      'button',
                                      {
                                        class:
                                          'p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700',
                                        title: 'Edit user',
                                      },
                                      [
                                        h(
                                          'svg',
                                          {
                                            xmlns: 'http://www.w3.org/2000/svg',
                                            class: 'h-4 w-4',
                                            fill: 'none',
                                            viewBox: '0 0 24 24',
                                            stroke: 'currentColor',
                                          },
                                          [
                                            h('path', {
                                              'stroke-linecap': 'round',
                                              'stroke-linejoin': 'round',
                                              'stroke-width': '2',
                                              d: 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z',
                                            }),
                                          ]
                                        ),
                                      ]
                                    ),
                                    h(
                                      'button',
                                      {
                                        class:
                                          'p-2 text-red-400 hover:text-red-600 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30',
                                        title: 'Delete user',
                                      },
                                      [
                                        h(
                                          'svg',
                                          {
                                            xmlns: 'http://www.w3.org/2000/svg',
                                            class: 'h-4 w-4',
                                            fill: 'none',
                                            viewBox: '0 0 24 24',
                                            stroke: 'currentColor',
                                          },
                                          [
                                            h('path', {
                                              'stroke-linecap': 'round',
                                              'stroke-linejoin': 'round',
                                              'stroke-width': '2',
                                              d: 'M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16',
                                            }),
                                          ]
                                        ),
                                      ]
                                    ),
                                  ])
                                : h(
                                    'div',
                                    { class: 'text-xs text-slate-400 italic' },
                                    'Cannot modify owner'
                                  ),
                            ]
                          )
                        )
                      ),
                  ],

                  // Invitations Tab
                  activeTab.value === 'invites' && [
                    // Invite Button
                    h('div', { class: 'mb-6' }, [
                      h(
                        'button',
                        {
                          class:
                            'inline-flex items-center gap-2 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors',
                        },
                        [
                          h(
                            'svg',
                            {
                              xmlns: 'http://www.w3.org/2000/svg',
                              class: 'h-5 w-5',
                              fill: 'none',
                              viewBox: '0 0 24 24',
                              stroke: 'currentColor',
                            },
                            [
                              h('path', {
                                'stroke-linecap': 'round',
                                'stroke-linejoin': 'round',
                                'stroke-width': '2',
                                d: 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
                              }),
                            ]
                          ),
                          'Send Invitation',
                        ]
                      ),
                    ]),

                    // Pending Invitations
                    pendingInvites.value.length > 0 &&
                      h('div', { class: 'mb-6' }, [
                        h(
                          'h3',
                          { class: 'text-sm font-medium text-slate-600 dark:text-slate-400 mb-3' },
                          'Pending Invitations'
                        ),
                        h(
                          'div',
                          { class: 'space-y-2' },
                          pendingInvites.value.map((invite) =>
                            h(
                              'div',
                              {
                                key: invite.id,
                                class:
                                  'flex items-center justify-between p-4 bg-amber-50 dark:bg-amber-900/10 rounded-lg border border-amber-200 dark:border-amber-800/30',
                              },
                              [
                                h('div', { class: 'flex items-center gap-3' }, [
                                  h(
                                    'div',
                                    {
                                      class:
                                        'w-10 h-10 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white',
                                    },
                                    [
                                      h(
                                        'svg',
                                        {
                                          xmlns: 'http://www.w3.org/2000/svg',
                                          class: 'h-5 w-5',
                                          fill: 'none',
                                          viewBox: '0 0 24 24',
                                          stroke: 'currentColor',
                                        },
                                        [
                                          h('path', {
                                            'stroke-linecap': 'round',
                                            'stroke-linejoin': 'round',
                                            'stroke-width': '2',
                                            d: 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
                                          }),
                                        ]
                                      ),
                                    ]
                                  ),
                                  h('div', [
                                    h('div', { class: 'flex items-center gap-2' }, [
                                      h(
                                        'span',
                                        { class: 'font-medium text-slate-900 dark:text-white' },
                                        invite.email
                                      ),
                                      h(
                                        'span',
                                        {
                                          class: [
                                            'text-xs px-2 py-0.5 rounded-full',
                                            getRoleBadgeClass(invite.role),
                                          ],
                                        },
                                        getRoleLabel(invite.role)
                                      ),
                                    ]),
                                    h(
                                      'div',
                                      {
                                        class: 'text-xs text-slate-500 dark:text-slate-400 mt-0.5',
                                      },
                                      `Sent ${formatRelativeDate(invite.created_at)} • Expires in 3d`
                                    ),
                                  ]),
                                ]),
                                h('div', { class: 'flex items-center gap-2' }, [
                                  h(
                                    'button',
                                    {
                                      class:
                                        'p-2 text-slate-400 hover:text-cyan-600 dark:hover:text-cyan-400 rounded-lg hover:bg-white dark:hover:bg-slate-800',
                                      title: 'Resend invitation',
                                    },
                                    [
                                      h(
                                        'svg',
                                        {
                                          xmlns: 'http://www.w3.org/2000/svg',
                                          class: 'h-4 w-4',
                                          fill: 'none',
                                          viewBox: '0 0 24 24',
                                          stroke: 'currentColor',
                                        },
                                        [
                                          h('path', {
                                            'stroke-linecap': 'round',
                                            'stroke-linejoin': 'round',
                                            'stroke-width': '2',
                                            d: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
                                          }),
                                        ]
                                      ),
                                    ]
                                  ),
                                  h(
                                    'button',
                                    {
                                      class:
                                        'p-2 text-red-400 hover:text-red-600 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20',
                                      title: 'Revoke invitation',
                                    },
                                    [
                                      h(
                                        'svg',
                                        {
                                          xmlns: 'http://www.w3.org/2000/svg',
                                          class: 'h-4 w-4',
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
                                ]),
                              ]
                            )
                          )
                        ),
                      ]),

                    // Past Invitations
                    pastInvites.value.length > 0 &&
                      h('div', [
                        h(
                          'h3',
                          { class: 'text-sm font-medium text-slate-600 dark:text-slate-400 mb-3' },
                          'History'
                        ),
                        h(
                          'div',
                          { class: 'space-y-2' },
                          pastInvites.value.map((invite) =>
                            h(
                              'div',
                              {
                                key: invite.id,
                                class:
                                  'flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-900/30 rounded-lg border border-slate-200 dark:border-slate-700 opacity-60',
                              },
                              [
                                h('div', { class: 'flex items-center gap-3' }, [
                                  h(
                                    'div',
                                    { class: 'text-sm text-slate-600 dark:text-slate-400' },
                                    invite.email
                                  ),
                                  h(
                                    'span',
                                    {
                                      class: [
                                        'text-xs px-2 py-0.5 rounded-full',
                                        invite.status === 'accepted'
                                          ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                                          : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400',
                                      ],
                                    },
                                    invite.status === 'accepted' ? 'Accepted' : 'Expired'
                                  ),
                                ]),
                                h(
                                  'div',
                                  { class: 'text-xs text-slate-400' },
                                  formatRelativeDate(invite.created_at)
                                ),
                              ]
                            )
                          )
                        ),
                      ]),
                  ],
                ]),
              ]
            ),
          ]
        );
    },
  });
};

const meta = {
  title: 'Modals/UserManagement',
  tags: ['autodocs'],
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component:
          'User management modal for owners to manage users and invitations. Includes tabs for viewing/editing users and managing pending invitations.',
      },
    },
  },
  decorators: [
    () => ({
      template: '<div style="min-height: 100vh; background: #1e293b;"><story /></div>',
    }),
  ],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

// Default users tab view
export const UsersTab: Story = {
  render: () => ({
    components: { UserManagement: createMockedUserManagement({ activeTab: 'users' }) },
    template: '<UserManagement @close="() => {}" />',
  }),
};

// Loading state
export const Loading: Story = {
  render: () => ({
    components: { UserManagement: createMockedUserManagement({ isLoading: true }) },
    template: '<UserManagement @close="() => {}" />',
  }),
};

// Invitations tab
export const InvitationsTab: Story = {
  render: () => ({
    components: { UserManagement: createMockedUserManagement({ activeTab: 'invites' }) },
    template: '<UserManagement @close="() => {}" />',
  }),
};

// No pending invitations
export const NoPendingInvites: Story = {
  render: () => ({
    components: {
      UserManagement: createMockedUserManagement({
        activeTab: 'invites',
        invites: [
          {
            id: '1',
            email: 'old@example.com',
            role: 'readonly',
            status: 'accepted',
            created_at: new Date(Date.now() - 604800000).toISOString(),
            expires_at: new Date().toISOString(),
          },
        ],
      }),
    },
    template: '<UserManagement @close="() => {}" />',
  }),
};

// Empty state
export const EmptyState: Story = {
  render: () => ({
    components: {
      UserManagement: createMockedUserManagement({
        users: [
          {
            id: '1',
            username: 'admin',
            email: 'admin@example.com',
            first_name: 'Admin',
            last_name: 'User',
            role: 'owner',
            last_login: new Date().toISOString(),
          },
        ],
        invites: [],
      }),
    },
    template: '<UserManagement @close="() => {}" />',
  }),
  parameters: {
    docs: {
      description: {
        story: 'Minimal state with only the owner user and no invitations.',
      },
    },
  },
};

// Many users
export const ManyUsers: Story = {
  render: () => ({
    components: {
      UserManagement: createMockedUserManagement({
        users: [
          {
            id: '1',
            username: 'admin',
            email: 'admin@example.com',
            first_name: 'Admin',
            last_name: 'User',
            role: 'owner',
            last_login: new Date().toISOString(),
          },
          {
            id: '2',
            username: 'jsmith',
            email: 'john.smith@example.com',
            first_name: 'John',
            last_name: 'Smith',
            role: 'readwrite',
            last_login: new Date(Date.now() - 3600000).toISOString(),
          },
          {
            id: '3',
            username: 'jdoe',
            email: 'jane.doe@example.com',
            first_name: 'Jane',
            last_name: 'Doe',
            role: 'readwrite',
            last_login: new Date(Date.now() - 7200000).toISOString(),
          },
          {
            id: '4',
            username: 'bob',
            email: 'bob@example.com',
            first_name: 'Bob',
            last_name: 'Wilson',
            role: 'readonly',
            last_login: new Date(Date.now() - 86400000).toISOString(),
          },
          {
            id: '5',
            username: 'alice',
            email: 'alice@example.com',
            first_name: 'Alice',
            last_name: 'Johnson',
            role: 'readonly',
            last_login: new Date(Date.now() - 172800000).toISOString(),
          },
          {
            id: '6',
            username: 'charlie',
            email: 'charlie@example.com',
            first_name: 'Charlie',
            last_name: 'Brown',
            role: 'readonly',
          },
        ],
      }),
    },
    template: '<UserManagement @close="() => {}" />',
  }),
};
