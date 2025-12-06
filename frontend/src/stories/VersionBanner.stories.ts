import type { Meta, StoryObj } from '@storybook/vue3-vite'
import { ref, h, defineComponent, computed } from 'vue'

// Create mocked VersionBanner for different states
const createMockedVersionBanner = (config: {
  currentVersion: string;
  latestVersion: string;
  updateType: 'major' | 'minor' | 'patch';
  show?: boolean;
}) => {
  return defineComponent({
    name: 'MockedVersionBanner',
    setup() {
      const show = ref(config.show ?? true)
      const showSettings = ref(false)

      const bannerClasses = computed(() => {
        switch (config.updateType) {
          case 'major':
            return 'bg-gradient-to-r from-rose-500 to-pink-500 text-white shadow-lg shadow-rose-500/20'
          case 'minor':
            return 'bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-lg shadow-cyan-500/20'
          case 'patch':
            return 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-lg shadow-emerald-500/20'
          default:
            return 'bg-slate-700 text-white'
        }
      })

      const getUpdateTypeLabel = (type: string) => {
        switch (type) {
          case 'major': return 'Major Update'
          case 'minor': return 'New Features'
          case 'patch': return 'Bug Fixes'
          default: return 'Update'
        }
      }

      const dismiss = () => {
        show.value = false
      }

      return () => show.value ? h('div', { class: ['relative z-50 flex items-center justify-center gap-3 px-4 py-2 text-sm font-medium cursor-pointer transition-colors duration-200', bannerClasses.value] }, [
        // Update icon
        h('div', { class: 'flex-shrink-0' }, [
          config.updateType === 'major' && h('svg', { class: 'w-5 h-5', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
            h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z' }),
          ]),
          config.updateType === 'minor' && h('svg', { class: 'w-5 h-5', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
            h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M13 10V3L4 14h7v7l9-11h-7z' }),
          ]),
          config.updateType === 'patch' && h('svg', { class: 'w-5 h-5', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
            h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15' }),
          ]),
        ]),

        // Message
        h('span', [
          h('strong', getUpdateTypeLabel(config.updateType)),
          ` available — v${config.latestVersion} `,
          h('span', { class: 'hidden sm:inline opacity-75' }, `(you're on v${config.currentVersion})`),
        ]),

        // View changelog hint
        h('span', { class: 'hidden md:inline-flex items-center gap-1 opacity-75 hover:opacity-100 transition-opacity' }, [
          h('span', 'View changelog'),
          h('svg', { class: 'w-4 h-4', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
            h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14' }),
          ]),
        ]),

        // Close button
        h('button', { onClick: (e: Event) => { e.stopPropagation(); dismiss() }, class: 'absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg transition-colors hover:bg-black/10 dark:hover:bg-white/10', title: 'Dismiss this notification' }, [
          h('svg', { class: 'w-4 h-4', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
            h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M6 18L18 6M6 6l12 12' }),
          ]),
        ]),

        // Settings button
        h('button', { onClick: (e: Event) => { e.stopPropagation(); showSettings.value = true }, class: 'absolute right-10 top-1/2 -translate-y-1/2 p-1.5 rounded-lg transition-colors hover:bg-black/10 dark:hover:bg-white/10', title: 'Configure update notifications' }, [
          h('svg', { class: 'w-4 h-4', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
            h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' }),
            h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z' }),
          ]),
        ]),
      ]) : null
    },
  })
}

const meta = {
  title: 'Components/VersionBanner',
  tags: ['autodocs'],
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component: 'Notification banner displayed at the top of the page when a new version is available. Color-coded by update type: rose for major, cyan for minor, emerald for patch.',
      },
    },
  },
  decorators: [
    () => ({
      template: `
        <div style="min-height: 400px; background: #f8fafc;">
          <story />
          <div style="padding: 20px; color: #64748b; text-align: center;">
            Application content would appear here
          </div>
        </div>
      `,
    }),
  ],
} satisfies Meta

export default meta
type Story = StoryObj<typeof meta>

// Major update (rose/pink gradient)
export const MajorUpdate: Story = {
  render: () => ({
    components: { VersionBanner: createMockedVersionBanner({ currentVersion: '1.2.3', latestVersion: '2.0.0', updateType: 'major' }) },
    template: '<VersionBanner />',
  }),
  parameters: {
    docs: {
      description: {
        story: 'Major updates show a rose/pink gradient to draw attention to significant changes.',
      },
    },
  },
}

// Minor update (cyan/blue gradient)
export const MinorUpdate: Story = {
  render: () => ({
    components: { VersionBanner: createMockedVersionBanner({ currentVersion: '1.2.3', latestVersion: '1.3.0', updateType: 'minor' }) },
    template: '<VersionBanner />',
  }),
  parameters: {
    docs: {
      description: {
        story: 'Minor updates (new features) show a cyan/blue gradient.',
      },
    },
  },
}

// Patch update (emerald/teal gradient)
export const PatchUpdate: Story = {
  render: () => ({
    components: { VersionBanner: createMockedVersionBanner({ currentVersion: '1.2.3', latestVersion: '1.2.4', updateType: 'patch' }) },
    template: '<VersionBanner />',
  }),
  parameters: {
    docs: {
      description: {
        story: 'Patch updates (bug fixes) show an emerald/teal gradient.',
      },
    },
  },
}

// Hidden banner
export const Hidden: Story = {
  render: () => ({
    components: { VersionBanner: createMockedVersionBanner({ currentVersion: '1.2.3', latestVersion: '1.3.0', updateType: 'minor', show: false }) },
    template: '<VersionBanner />',
  }),
  parameters: {
    docs: {
      description: {
        story: 'Banner is hidden when there is no update or user has dismissed it.',
      },
    },
  },
}

// In context with dark header
export const WithDarkHeader: Story = {
  render: () => ({
    components: { VersionBanner: createMockedVersionBanner({ currentVersion: '1.2.3', latestVersion: '1.4.0', updateType: 'minor' }) },
    template: '<VersionBanner />',
  }),
  decorators: [
    () => ({
      template: `
        <div style="min-height: 400px;">
          <story />
          <header style="background: #0f172a; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between;">
            <div style="color: white; font-weight: 600; font-size: 18px;">🗺️ Cartographer</div>
            <div style="color: #94a3b8; font-size: 14px;">Network Mapping Tool</div>
          </header>
          <main style="padding: 24px; background: #f1f5f9; min-height: 300px;">
            <div style="background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
              Main content area
            </div>
          </main>
        </div>
      `,
    }),
  ],
  parameters: {
    docs: {
      description: {
        story: 'Banner displayed in context with the application header.',
      },
    },
  },
}

// All three types stacked for comparison
export const AllTypes: Story = {
  render: () => ({
    setup() {
      const MajorBanner = createMockedVersionBanner({ currentVersion: '1.0.0', latestVersion: '2.0.0', updateType: 'major' })
      const MinorBanner = createMockedVersionBanner({ currentVersion: '1.2.0', latestVersion: '1.3.0', updateType: 'minor' })
      const PatchBanner = createMockedVersionBanner({ currentVersion: '1.2.3', latestVersion: '1.2.4', updateType: 'patch' })
      return { MajorBanner, MinorBanner, PatchBanner }
    },
    template: `
      <div style="display: flex; flex-direction: column; gap: 8px; padding: 16px; background: #f8fafc;">
        <p style="color: #64748b; margin-bottom: 8px; font-size: 14px;">Major Update:</p>
        <MajorBanner />
        <p style="color: #64748b; margin-top: 16px; margin-bottom: 8px; font-size: 14px;">Minor Update:</p>
        <MinorBanner />
        <p style="color: #64748b; margin-top: 16px; margin-bottom: 8px; font-size: 14px;">Patch Update:</p>
        <PatchBanner />
      </div>
    `,
  }),
  parameters: {
    docs: {
      description: {
        story: 'Comparison of all three update type banners side by side.',
      },
    },
  },
}

