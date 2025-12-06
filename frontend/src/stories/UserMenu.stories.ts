import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { within, userEvent, expect, fn } from 'storybook/test'
import { ref, h, defineComponent } from 'vue'

// Create a mocked UserMenu component that doesn't depend on useAuth
const createMockedUserMenu = (config: {
  user: { username: string; email: string; first_name: string; last_name: string; role: 'owner' | 'readwrite' | 'readonly' };
  isOpen?: boolean;
}) => {
  return defineComponent({
    name: 'MockedUserMenu',
    emits: ['logout', 'manageUsers', 'notifications', 'updates'],
    setup(props, { emit }) {
      const isOpen = ref(config.isOpen ?? false)
      const showPasswordModal = ref(false)

      const user = config.user
      const isOwner = user.role === 'owner'
      
      const displayName = `${user.first_name} ${user.last_name}`.trim() || user.username
      const userInitial = user.first_name?.charAt(0).toUpperCase() || 'U'
      
      const roleLabel = {
        owner: 'Owner',
        readwrite: 'Read/Write',
        readonly: 'Read Only',
      }[user.role]
      
      const roleBadgeClass = {
        owner: 'text-amber-600 dark:text-amber-400',
        readwrite: 'text-emerald-600 dark:text-emerald-400',
        readonly: 'text-slate-500 dark:text-slate-400',
      }[user.role]

      return () => h('div', { class: 'relative' }, [
        // User Button
        h('button', {
          onClick: () => { isOpen.value = !isOpen.value },
          class: 'flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors'
        }, [
          // Avatar
          h('div', { 
            class: 'w-7 h-7 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white text-xs font-semibold shadow-sm' 
          }, userInitial),
          h('div', { class: 'flex flex-col items-start' }, [
            h('span', { class: 'text-sm font-medium text-slate-700 dark:text-slate-200 max-w-24 truncate leading-tight' }, displayName),
            h('span', { class: `text-[10px] leading-tight font-medium ${roleBadgeClass}` }, roleLabel)
          ]),
          // Dropdown Arrow
          h('svg', { 
            xmlns: 'http://www.w3.org/2000/svg',
            class: `h-4 w-4 text-slate-400 transition-transform ml-0.5 ${isOpen.value ? 'rotate-180' : ''}`,
            fill: 'none',
            viewBox: '0 0 24 24',
            stroke: 'currentColor'
          }, [
            h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M19 9l-7 7-7-7' })
          ])
        ]),
        
        // Dropdown Menu
        isOpen.value && h('div', { 
          class: 'absolute right-0 mt-2 w-56 rounded-xl shadow-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 overflow-hidden z-50'
        }, [
          // User Info Header
          h('div', { class: 'px-4 py-3 bg-slate-50 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-700' }, [
            h('div', { class: 'flex items-center gap-3' }, [
              h('div', { 
                class: 'w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white text-base font-semibold shadow-sm' 
              }, userInitial),
              h('div', { class: 'flex-1 min-w-0' }, [
                h('p', { class: 'text-sm font-semibold text-slate-900 dark:text-white truncate' }, displayName),
                h('p', { class: 'text-xs text-slate-500 dark:text-slate-400 truncate' }, user.email)
              ])
            ])
          ]),
          
          // Menu Items
          h('div', { class: 'py-1' }, [
            // Manage Users (Owner only)
            isOwner && h('button', {
              onClick: () => { isOpen.value = false; emit('manageUsers') },
              class: 'w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors'
            }, [
              h('div', { class: 'w-8 h-8 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center' }, [
                h('svg', { xmlns: 'http://www.w3.org/2000/svg', class: 'h-4 w-4 text-amber-600 dark:text-amber-400', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
                  h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z' })
                ])
              ]),
              h('div', { class: 'flex flex-col items-start' }, [
                h('span', { class: 'font-medium' }, 'Manage Users'),
                h('span', { class: 'text-xs text-slate-500 dark:text-slate-400' }, 'Add, edit, remove users')
              ])
            ]),
            
            // Notifications
            h('button', {
              onClick: () => { isOpen.value = false; emit('notifications') },
              class: 'w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors'
            }, [
              h('div', { class: 'w-8 h-8 rounded-lg bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center' }, [
                h('svg', { xmlns: 'http://www.w3.org/2000/svg', class: 'h-4 w-4 text-violet-600 dark:text-violet-400', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
                  h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9' })
                ])
              ]),
              h('div', { class: 'flex flex-col items-start' }, [
                h('span', { class: 'font-medium' }, 'Notifications'),
                h('span', { class: 'text-xs text-slate-500 dark:text-slate-400' }, 'Email & Discord alerts')
              ])
            ]),
            
            // Updates
            h('button', {
              onClick: () => { isOpen.value = false; emit('updates') },
              class: 'w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors'
            }, [
              h('div', { class: 'w-8 h-8 rounded-lg bg-cyan-100 dark:bg-cyan-900/30 flex items-center justify-center' }, [
                h('svg', { xmlns: 'http://www.w3.org/2000/svg', class: 'h-4 w-4 text-cyan-600 dark:text-cyan-400', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
                  h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15' })
                ])
              ]),
              h('div', { class: 'flex flex-col items-start' }, [
                h('span', { class: 'font-medium' }, 'Updates'),
                h('span', { class: 'text-xs text-slate-500 dark:text-slate-400' }, 'Check for new versions')
              ])
            ]),
            
            // Change Password
            h('button', {
              onClick: () => { isOpen.value = false; showPasswordModal.value = true },
              class: 'w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors'
            }, [
              h('div', { class: 'w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-700 flex items-center justify-center' }, [
                h('svg', { xmlns: 'http://www.w3.org/2000/svg', class: 'h-4 w-4 text-slate-600 dark:text-slate-400', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
                  h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z' })
                ])
              ]),
              h('div', { class: 'flex flex-col items-start' }, [
                h('span', { class: 'font-medium' }, 'Change Password'),
                h('span', { class: 'text-xs text-slate-500 dark:text-slate-400' }, 'Update your password')
              ])
            ])
          ]),
          
          // Logout
          h('div', { class: 'border-t border-slate-200 dark:border-slate-700 p-2' }, [
            h('button', {
              onClick: () => { isOpen.value = false; emit('logout') },
              class: 'w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors'
            }, [
              h('svg', { xmlns: 'http://www.w3.org/2000/svg', class: 'h-4 w-4', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
                h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1' })
              ]),
              'Sign Out'
            ])
          ])
        ])
      ])
    }
  })
}

const meta = {
  title: 'Components/UserMenu',
  component: createMockedUserMenu({
    user: { username: 'johndoe', email: 'john@example.com', first_name: 'John', last_name: 'Doe', role: 'owner' }
  }),
  tags: ['autodocs'],
  parameters: {
    docs: {
      description: {
        component: 'User menu dropdown with profile info, settings access, and logout functionality. Shows different options based on user role.',
      },
    },
  },
  argTypes: {
    onLogout: { action: 'logout' },
    onManageUsers: { action: 'manageUsers' },
    onNotifications: { action: 'notifications' },
    onUpdates: { action: 'updates' },
  },
  decorators: [
    () => ({
      template: `
        <div class="flex justify-end w-96 min-h-[400px] p-4">
          <story />
        </div>
      `,
    }),
  ],
} satisfies Meta<any>

export default meta
type Story = StoryObj<typeof meta>

// Owner user (closed)
export const OwnerClosed: Story = {
  render: (args) => ({
    components: { 
      MockedUserMenu: createMockedUserMenu({
        user: { username: 'admin', email: 'admin@company.com', first_name: 'John', last_name: 'Admin', role: 'owner' },
        isOpen: false
      })
    },
    setup() {
      return { args }
    },
    template: '<MockedUserMenu @logout="args.onLogout" @manage-users="args.onManageUsers" @notifications="args.onNotifications" @updates="args.onUpdates" />',
  }),
  args: {
    onLogout: fn(),
    onManageUsers: fn(),
    onNotifications: fn(),
    onUpdates: fn(),
  },
  parameters: {
    docs: {
      description: {
        story: 'Owner user menu in closed state. Click to open the dropdown.',
      },
    },
  },
}

// Owner user (open)
export const OwnerOpen: Story = {
  render: (args) => ({
    components: { 
      MockedUserMenu: createMockedUserMenu({
        user: { username: 'admin', email: 'admin@company.com', first_name: 'John', last_name: 'Admin', role: 'owner' },
        isOpen: true
      })
    },
    setup() {
      return { args }
    },
    template: '<MockedUserMenu @logout="args.onLogout" @manage-users="args.onManageUsers" @notifications="args.onNotifications" @updates="args.onUpdates" />',
  }),
  args: {
    onLogout: fn(),
    onManageUsers: fn(),
    onNotifications: fn(),
    onUpdates: fn(),
  },
  parameters: {
    docs: {
      description: {
        story: 'Owner has access to all menu items including "Manage Users".',
      },
    },
  },
}

// Read/Write user (open)
export const ReadWriteOpen: Story = {
  render: (args) => ({
    components: { 
      MockedUserMenu: createMockedUserMenu({
        user: { username: 'jane', email: 'jane@company.com', first_name: 'Jane', last_name: 'Editor', role: 'readwrite' },
        isOpen: true
      })
    },
    setup() {
      return { args }
    },
    template: '<MockedUserMenu @logout="args.onLogout" @manage-users="args.onManageUsers" @notifications="args.onNotifications" @updates="args.onUpdates" />',
  }),
  args: {
    onLogout: fn(),
    onManageUsers: fn(),
    onNotifications: fn(),
    onUpdates: fn(),
  },
  parameters: {
    docs: {
      description: {
        story: 'Read/Write users do NOT see the "Manage Users" option (owner-only feature).',
      },
    },
  },
}

// Read-only user (open)
export const ReadOnlyOpen: Story = {
  render: (args) => ({
    components: { 
      MockedUserMenu: createMockedUserMenu({
        user: { username: 'viewer', email: 'viewer@company.com', first_name: 'View', last_name: 'Only', role: 'readonly' },
        isOpen: true
      })
    },
    setup() {
      return { args }
    },
    template: '<MockedUserMenu @logout="args.onLogout" @manage-users="args.onManageUsers" @notifications="args.onNotifications" @updates="args.onUpdates" />',
  }),
  args: {
    onLogout: fn(),
    onManageUsers: fn(),
    onNotifications: fn(),
    onUpdates: fn(),
  },
  parameters: {
    docs: {
      description: {
        story: 'Read-only users have limited access. "Manage Users" is not visible.',
      },
    },
  },
}

// Interaction test - Open dropdown
export const DropdownInteraction: Story = {
  render: (args) => ({
    components: { 
      MockedUserMenu: createMockedUserMenu({
        user: { username: 'admin', email: 'admin@company.com', first_name: 'John', last_name: 'Admin', role: 'owner' },
        isOpen: false
      })
    },
    setup() {
      return { args }
    },
    template: '<MockedUserMenu @logout="args.onLogout" @manage-users="args.onManageUsers" @notifications="args.onNotifications" @updates="args.onUpdates" />',
  }),
  args: {
    onLogout: fn(),
    onManageUsers: fn(),
    onNotifications: fn(),
    onUpdates: fn(),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement)
    
    // Find and click the user menu button
    const userButton = canvasElement.querySelector('button')
    if (userButton) {
      await userEvent.click(userButton)
      
      // Verify dropdown is now visible
      await expect(canvas.getByText('Notifications')).toBeInTheDocument()
      await expect(canvas.getByText('Sign Out')).toBeInTheDocument()
    }
  },
}

// Interaction test - Click logout
export const LogoutInteraction: Story = {
  render: (args) => ({
    components: { 
      MockedUserMenu: createMockedUserMenu({
        user: { username: 'admin', email: 'admin@company.com', first_name: 'John', last_name: 'Admin', role: 'owner' },
        isOpen: true
      })
    },
    setup() {
      return { args }
    },
    template: '<MockedUserMenu @logout="args.onLogout" @manage-users="args.onManageUsers" @notifications="args.onNotifications" @updates="args.onUpdates" />',
  }),
  args: {
    onLogout: fn(),
    onManageUsers: fn(),
    onNotifications: fn(),
    onUpdates: fn(),
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    
    // Click Sign Out button
    const signOutButton = canvas.getByText('Sign Out')
    await userEvent.click(signOutButton)
    
    // Verify logout was called
    await expect(args.onLogout).toHaveBeenCalled()
  },
}
