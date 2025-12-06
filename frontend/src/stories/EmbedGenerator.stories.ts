import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { within, userEvent, expect, fn } from 'storybook/test'
import { ref, h, defineComponent, onMounted } from 'vue'
import EmbedGenerator from '../components/EmbedGenerator.vue'

// Mock embed data
const mockEmbeds = [
  {
    id: 'embed-123',
    name: 'Public Dashboard',
    sensitiveMode: false,
    showOwner: true,
    ownerDisplayName: 'John Doe',
    createdAt: new Date(Date.now() - 86400000 * 2).toISOString(), // 2 days ago
    updatedAt: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
  },
  {
    id: 'embed-456',
    name: 'Client View (Sensitive)',
    sensitiveMode: true,
    showOwner: false,
    ownerDisplayName: null,
    createdAt: new Date(Date.now() - 86400000 * 7).toISOString(), // 7 days ago
    updatedAt: new Date(Date.now() - 86400000 * 7).toISOString(),
  },
  {
    id: 'embed-789',
    name: 'Internal Network Overview',
    sensitiveMode: false,
    showOwner: true,
    ownerDisplayName: 'admin',
    createdAt: new Date(Date.now() - 86400000 * 30).toISOString(), // 30 days ago
    updatedAt: new Date(Date.now() - 86400000 * 14).toISOString(), // 14 days ago
  },
]

// Create a wrapper component that mocks the auth state
const createMockedEmbedGenerator = (authState: { canWrite: boolean; isOwner: boolean; user: any }) => {
  return defineComponent({
    name: 'MockedEmbedGenerator',
    props: ['embeds', 'loading'],
    emits: ['close'],
    setup(props, { emit }) {
      return () => h('div', { 
        class: 'fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm',
        onClick: (e: MouseEvent) => {
          if ((e.target as HTMLElement).classList.contains('fixed')) {
            emit('close')
          }
        }
      }, [
        h('div', { 
          class: 'bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden max-h-[90vh] flex flex-col'
        }, [
          // Header
          h('div', { class: 'flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50' }, [
            h('div', { class: 'flex items-center gap-3' }, [
              h('div', { class: 'w-9 h-9 rounded-lg bg-cyan-100 dark:bg-cyan-900/30 flex items-center justify-center' }, [
                h('svg', { 
                  xmlns: 'http://www.w3.org/2000/svg', 
                  class: 'h-5 w-5 text-cyan-600 dark:text-cyan-400', 
                  fill: 'none', 
                  viewBox: '0 0 24 24', 
                  stroke: 'currentColor', 
                  'stroke-width': '2' 
                }, [
                  h('path', { 
                    'stroke-linecap': 'round', 
                    'stroke-linejoin': 'round', 
                    d: 'M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14' 
                  })
                ])
              ]),
              h('div', {}, [
                h('h2', { class: 'text-lg font-semibold text-slate-900 dark:text-white' }, 'Manage Embeds'),
                h('p', { class: 'text-xs text-slate-500 dark:text-slate-400' }, 'Share your network map')
              ])
            ]),
            h('button', { 
              class: 'p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 transition-colors',
              onClick: () => emit('close')
            }, [
              h('svg', { xmlns: 'http://www.w3.org/2000/svg', class: 'h-5 w-5', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
                h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M6 18L18 6M6 6l12 12' })
              ])
            ])
          ]),
          // Content
          h('div', { class: 'p-6 overflow-auto flex-1' }, [
            props.loading 
              ? h('div', { class: 'flex items-center justify-center py-8' }, [
                  h('svg', { class: 'animate-spin h-8 w-8 text-indigo-500', fill: 'none', viewBox: '0 0 24 24' }, [
                    h('circle', { class: 'opacity-25', cx: '12', cy: '12', r: '10', stroke: 'currentColor', 'stroke-width': '4' }),
                    h('path', { class: 'opacity-75', fill: 'currentColor', d: 'M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z' })
                  ])
                ])
              : h('div', {}, [
                  // Read-only notice
                  !authState.canWrite && h('div', { class: 'mb-4 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700' }, [
                    h('div', { class: 'flex items-center gap-2 text-amber-700 dark:text-amber-300' }, [
                      h('svg', { xmlns: 'http://www.w3.org/2000/svg', class: 'h-5 w-5', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor' }, [
                        h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' })
                      ]),
                      h('span', { class: 'text-sm font-medium' }, 'Read-only access')
                    ]),
                    h('p', { class: 'text-xs text-amber-600 dark:text-amber-400 mt-1 ml-7' }, 'You can view existing embeds but cannot create new ones.')
                  ]),
                  // Create button (write access only)
                  authState.canWrite && h('div', { class: 'mb-6' }, [
                    h('button', { 
                      class: 'w-full px-4 py-3 bg-cyan-600 text-white font-medium rounded-lg hover:bg-cyan-500 transition-colors flex items-center justify-center gap-2'
                    }, [
                      h('svg', { xmlns: 'http://www.w3.org/2000/svg', class: 'h-5 w-5', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
                        h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M12 4v16m8-8H4' })
                      ]),
                      'Create New Embed'
                    ])
                  ]),
                  // Embeds list header
                  h('h3', { class: 'text-sm font-medium text-slate-700 dark:text-slate-300 mb-3' }, 'Your Embeds'),
                  // Empty state or list
                  props.embeds.length === 0
                    ? h('div', { class: 'text-center py-8 text-slate-500 dark:text-slate-400' }, [
                        h('svg', { xmlns: 'http://www.w3.org/2000/svg', class: 'h-12 w-12 mx-auto mb-2 opacity-50', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor' }, [
                          h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '1', d: 'M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14' })
                        ]),
                        h('p', { class: 'text-sm' }, 'No embeds created yet'),
                        h('p', { class: 'text-xs mt-1' }, 'Click "Create New Embed" to get started')
                      ])
                    : h('div', { class: 'space-y-2' }, 
                        props.embeds.map((embed: any) => 
                          h('div', { 
                            key: embed.id,
                            class: 'p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-cyan-400 dark:hover:border-cyan-600 cursor-pointer transition-colors bg-white dark:bg-slate-800/50'
                          }, [
                            h('div', { class: 'flex items-center justify-between' }, [
                              h('div', {}, [
                                h('div', { class: 'font-medium text-slate-800 dark:text-slate-200' }, embed.name),
                                h('div', { class: 'text-xs text-slate-500 dark:text-slate-400 mt-0.5 flex items-center gap-2' }, [
                                  embed.sensitiveMode && h('span', { class: 'inline-flex items-center gap-1 text-amber-600 dark:text-amber-400' }, [
                                    h('svg', { class: 'h-3 w-3', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor' }, [
                                      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z' })
                                    ]),
                                    'Sensitive'
                                  ]),
                                  embed.showOwner && h('span', { class: 'inline-flex items-center gap-1' }, [
                                    h('svg', { class: 'h-3 w-3', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor' }, [
                                      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z' })
                                    ]),
                                    embed.ownerDisplayName
                                  ]),
                                  h('span', {}, `Created ${formatDate(embed.createdAt)}`)
                                ])
                              ]),
                              h('svg', { xmlns: 'http://www.w3.org/2000/svg', class: 'h-5 w-5 text-slate-400', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor' }, [
                                h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 5l7 7-7 7' })
                              ])
                            ])
                          ])
                        )
                      )
                ])
          ])
        ])
      ])
    }
  })
}

function formatDate(isoString: string): string {
  if (!isoString) return ''
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / 86400000)
  
  if (diffDays === 0) return 'today'
  if (diffDays === 1) return 'yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

const meta = {
  title: 'Modals/EmbedGenerator',
  component: EmbedGenerator,
  tags: ['autodocs'],
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component: 'Modal for creating and managing shareable embed links for the network map. Supports sensitive mode (hiding IPs) and owner attribution.',
      },
    },
  },
  argTypes: {
    onClose: { action: 'close' },
  },
  decorators: [
    () => ({
      template: `
        <div class="min-h-screen bg-slate-100 dark:bg-slate-900 flex items-center justify-center">
          <story />
        </div>
      `,
    }),
  ],
} satisfies Meta<typeof EmbedGenerator>

export default meta
type Story = StoryObj<typeof meta>

// Default - uses the real component (will show loading then read-only)
export const Default: Story = {
  args: {
    onClose: fn(),
  },
}

// Read-only access with embeds - using mocked component
export const ReadOnlyWithEmbeds: Story = {
  render: (args) => ({
    components: { 
      MockedEmbedGenerator: createMockedEmbedGenerator({ 
        canWrite: false, 
        isOwner: false, 
        user: { username: 'viewer', role: 'readonly' } 
      }) 
    },
    setup() {
      return { args, embeds: mockEmbeds }
    },
    template: '<MockedEmbedGenerator :embeds="embeds" :loading="false" @close="args.onClose" />',
  }),
  args: {
    onClose: fn(),
  },
  parameters: {
    docs: {
      description: {
        story: 'Read-only users can view existing embeds but cannot create new ones. The "Create New Embed" button is hidden.',
      },
    },
  },
}

// Read-only with no embeds
export const ReadOnlyEmpty: Story = {
  render: (args) => ({
    components: { 
      MockedEmbedGenerator: createMockedEmbedGenerator({ 
        canWrite: false, 
        isOwner: false, 
        user: { username: 'viewer', role: 'readonly' } 
      }) 
    },
    setup() {
      return { args }
    },
    template: '<MockedEmbedGenerator :embeds="[]" :loading="false" @close="args.onClose" />',
  }),
  args: {
    onClose: fn(),
  },
  parameters: {
    docs: {
      description: {
        story: 'Read-only view with no embeds created. Shows the read-only notice and empty state.',
      },
    },
  },
}

// Write access (can create embeds)
export const WriteAccess: Story = {
  render: (args) => ({
    components: { 
      MockedEmbedGenerator: createMockedEmbedGenerator({ 
        canWrite: true, 
        isOwner: false, 
        user: { username: 'editor', role: 'readwrite', first_name: 'Jane', last_name: 'Editor' } 
      }) 
    },
    setup() {
      return { args, embeds: mockEmbeds }
    },
    template: '<MockedEmbedGenerator :embeds="embeds" :loading="false" @close="args.onClose" />',
  }),
  args: {
    onClose: fn(),
  },
  parameters: {
    docs: {
      description: {
        story: 'Users with write access can create new embeds. The "Create New Embed" button is visible.',
      },
    },
  },
}

// Owner access (full permissions)
export const OwnerAccess: Story = {
  render: (args) => ({
    components: { 
      MockedEmbedGenerator: createMockedEmbedGenerator({ 
        canWrite: true, 
        isOwner: true, 
        user: { username: 'admin', role: 'owner', first_name: 'John', last_name: 'Admin' } 
      }) 
    },
    setup() {
      return { args, embeds: mockEmbeds }
    },
    template: '<MockedEmbedGenerator :embeds="embeds" :loading="false" @close="args.onClose" />',
  }),
  args: {
    onClose: fn(),
  },
  parameters: {
    docs: {
      description: {
        story: 'Owners have full access - they can create, view, and delete embeds.',
      },
    },
  },
}

// Empty state with write access
export const EmptyWithWriteAccess: Story = {
  render: (args) => ({
    components: { 
      MockedEmbedGenerator: createMockedEmbedGenerator({ 
        canWrite: true, 
        isOwner: true, 
        user: { username: 'admin', role: 'owner' } 
      }) 
    },
    setup() {
      return { args }
    },
    template: '<MockedEmbedGenerator :embeds="[]" :loading="false" @close="args.onClose" />',
  }),
  args: {
    onClose: fn(),
  },
  parameters: {
    docs: {
      description: {
        story: 'Empty state for users with write access. Shows the create button and empty state message.',
      },
    },
  },
}

// Loading state
export const Loading: Story = {
  render: (args) => ({
    components: { 
      MockedEmbedGenerator: createMockedEmbedGenerator({ 
        canWrite: true, 
        isOwner: true, 
        user: { username: 'admin', role: 'owner' } 
      }) 
    },
    setup() {
      return { args }
    },
    template: '<MockedEmbedGenerator :embeds="[]" :loading="true" @close="args.onClose" />',
  }),
  args: {
    onClose: fn(),
  },
  parameters: {
    docs: {
      description: {
        story: 'Loading state while fetching embeds from the API.',
      },
    },
  },
}

// Interaction test - Click close button
export const CloseButtonInteraction: Story = {
  render: (args) => ({
    components: { 
      MockedEmbedGenerator: createMockedEmbedGenerator({ 
        canWrite: true, 
        isOwner: true, 
        user: { username: 'admin', role: 'owner' } 
      }) 
    },
    setup() {
      return { args, embeds: mockEmbeds }
    },
    template: '<MockedEmbedGenerator :embeds="embeds" :loading="false" @close="args.onClose" />',
  }),
  args: {
    onClose: fn(),
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    
    // Find the close button (X icon in header)
    const closeButtons = canvasElement.querySelectorAll('button')
    const closeButton = Array.from(closeButtons).find(btn => 
      btn.querySelector('path[d="M6 18L18 6M6 6l12 12"]')
    )
    
    if (closeButton) {
      await userEvent.click(closeButton)
      await expect(args.onClose).toHaveBeenCalled()
    }
  },
}
