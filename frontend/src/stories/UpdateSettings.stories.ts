import type { Meta, StoryObj } from '@storybook/vue3-vite';
import { ref, h, defineComponent } from 'vue';

// Create mocked UpdateSettings for different states
const createMockedUpdateSettings = (config: {
  currentVersion: string;
  latestVersion?: string;
  hasUpdate?: boolean;
  updateType?: 'major' | 'minor' | 'patch' | null;
  isChecking?: boolean;
  notifyLevel?: 'major' | 'minor' | 'patch';
}) => {
  return defineComponent({
    name: 'MockedUpdateSettings',
    props: {
      isOpen: { type: Boolean, default: true },
    },
    emits: ['close'],
    setup(props, { emit }) {
      const isCheckingVersion = ref(config.isChecking ?? false);
      const updateNotifyLevel = ref(config.notifyLevel ?? 'minor');

      const updateCheckResult = ref(
        config.hasUpdate !== undefined
          ? {
              success: true,
              current_version: config.currentVersion,
              latest_version: config.latestVersion || config.currentVersion,
              has_update: config.hasUpdate,
              update_type: config.updateType,
            }
          : null
      );

      const updateNotifyOptions = [
        {
          value: 'major' as const,
          label: 'Major updates only',
          badge: 'x.0.0',
          badgeClass: 'bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-400',
          selectedBg: 'bg-rose-50 dark:bg-rose-900/20',
          selectedBorder: 'border-rose-300 dark:border-rose-700',
          description: 'Significant new features, redesigns, or breaking changes',
        },
        {
          value: 'minor' as const,
          label: 'Minor updates and above',
          badge: '0.x.0',
          badgeClass: 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400',
          selectedBg: 'bg-amber-50 dark:bg-amber-900/20',
          selectedBorder: 'border-amber-300 dark:border-amber-700',
          description: 'New features, improvements, and major releases',
        },
        {
          value: 'patch' as const,
          label: 'All updates',
          badge: '0.0.x',
          badgeClass:
            'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400',
          selectedBg: 'bg-emerald-50 dark:bg-emerald-900/20',
          selectedBorder: 'border-emerald-300 dark:border-emerald-700',
          description: 'Every update including bug fixes and patches',
        },
      ];

      const getUpdateTypeLabel = (updateType: string | null) => {
        switch (updateType) {
          case 'major':
            return 'Major Release';
          case 'minor':
            return 'New Features';
          case 'patch':
            return 'Bug Fixes';
          default:
            return 'Update';
        }
      };

      const checkForUpdates = () => {
        isCheckingVersion.value = true;
        setTimeout(() => {
          isCheckingVersion.value = false;
          if (config.hasUpdate) {
            updateCheckResult.value = {
              success: true,
              current_version: config.currentVersion,
              latest_version: config.latestVersion || config.currentVersion,
              has_update: true,
              update_type: config.updateType || 'minor',
            };
          }
        }, 1500);
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
                  'bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-lg overflow-hidden',
              },
              [
                // Header
                h(
                  'div',
                  {
                    class:
                      'flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 rounded-t-xl',
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
                                d: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
                              }),
                            ]
                          ),
                        ]
                      ),
                      h('div', [
                        h(
                          'h2',
                          { class: 'text-lg font-semibold text-slate-900 dark:text-white' },
                          'Application Updates'
                        ),
                        h(
                          'p',
                          { class: 'text-xs text-slate-500 dark:text-slate-400' },
                          'Check for updates and configure notifications'
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

                // Content
                h('div', { class: 'p-6 space-y-6' }, [
                  // Current Version & Check Button
                  h(
                    'div',
                    {
                      class:
                        'flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-slate-200 dark:border-slate-700',
                    },
                    [
                      h('div', [
                        h(
                          'p',
                          { class: 'text-sm text-slate-500 dark:text-slate-400' },
                          'Current Version'
                        ),
                        h(
                          'p',
                          { class: 'text-2xl font-bold text-slate-900 dark:text-white' },
                          `v${config.currentVersion}`
                        ),
                      ]),
                      h(
                        'button',
                        {
                          onClick: checkForUpdates,
                          disabled: isCheckingVersion.value,
                          class:
                            'px-4 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50 flex items-center gap-2',
                        },
                        [
                          h(
                            'svg',
                            {
                              xmlns: 'http://www.w3.org/2000/svg',
                              class: ['h-5 w-5', isCheckingVersion.value ? 'animate-spin' : ''],
                              fill: 'none',
                              viewBox: '0 0 24 24',
                              stroke: 'currentColor',
                              'stroke-width': '2',
                            },
                            [
                              h('path', {
                                'stroke-linecap': 'round',
                                'stroke-linejoin': 'round',
                                d: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
                              }),
                            ]
                          ),
                          isCheckingVersion.value ? 'Checking...' : 'Check for Updates',
                        ]
                      ),
                    ]
                  ),

                  // Update Check Result
                  updateCheckResult.value &&
                    h(
                      'div',
                      {
                        class: [
                          'p-4 rounded-lg',
                          updateCheckResult.value.has_update
                            ? 'bg-gradient-to-r from-cyan-50 to-blue-50 dark:from-cyan-900/20 dark:to-blue-900/20 border border-cyan-200 dark:border-cyan-700/30'
                            : 'bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 border border-emerald-200 dark:border-emerald-700/30',
                        ],
                      },
                      [
                        h('div', { class: 'flex items-start gap-4' }, [
                          h(
                            'div',
                            {
                              class: [
                                'w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0',
                                updateCheckResult.value.has_update
                                  ? 'bg-cyan-100 dark:bg-cyan-900/40'
                                  : 'bg-emerald-100 dark:bg-emerald-900/40',
                              ],
                            },
                            [
                              updateCheckResult.value.has_update
                                ? h(
                                    'svg',
                                    {
                                      xmlns: 'http://www.w3.org/2000/svg',
                                      class: 'h-6 w-6 text-cyan-600 dark:text-cyan-400',
                                      fill: 'none',
                                      viewBox: '0 0 24 24',
                                      stroke: 'currentColor',
                                      'stroke-width': '2',
                                    },
                                    [
                                      h('path', {
                                        'stroke-linecap': 'round',
                                        'stroke-linejoin': 'round',
                                        d: 'M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10',
                                      }),
                                    ]
                                  )
                                : h(
                                    'svg',
                                    {
                                      xmlns: 'http://www.w3.org/2000/svg',
                                      class: 'h-6 w-6 text-emerald-600 dark:text-emerald-400',
                                      fill: 'none',
                                      viewBox: '0 0 24 24',
                                      stroke: 'currentColor',
                                      'stroke-width': '2',
                                    },
                                    [
                                      h('path', {
                                        'stroke-linecap': 'round',
                                        'stroke-linejoin': 'round',
                                        d: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
                                      }),
                                    ]
                                  ),
                            ]
                          ),
                          h('div', { class: 'flex-1 min-w-0' }, [
                            h('div', { class: 'flex items-center gap-3' }, [
                              h(
                                'p',
                                {
                                  class: [
                                    'text-lg font-semibold',
                                    updateCheckResult.value.has_update
                                      ? 'text-cyan-700 dark:text-cyan-400'
                                      : 'text-emerald-700 dark:text-emerald-400',
                                  ],
                                },
                                updateCheckResult.value.has_update
                                  ? 'Update Available!'
                                  : "You're up to date!"
                              ),
                              updateCheckResult.value.has_update &&
                                h(
                                  'a',
                                  {
                                    href: '#',
                                    class:
                                      'inline-flex items-center gap-1 px-2.5 py-1 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium rounded-lg transition-colors',
                                  },
                                  [
                                    h(
                                      'svg',
                                      {
                                        xmlns: 'http://www.w3.org/2000/svg',
                                        class: 'h-3.5 w-3.5',
                                        fill: 'none',
                                        viewBox: '0 0 24 24',
                                        stroke: 'currentColor',
                                        'stroke-width': '2',
                                      },
                                      [
                                        h('path', {
                                          'stroke-linecap': 'round',
                                          'stroke-linejoin': 'round',
                                          d: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
                                        }),
                                      ]
                                    ),
                                    'Changelog',
                                  ]
                                ),
                            ]),
                            h(
                              'p',
                              {
                                class: [
                                  'text-sm mt-1',
                                  updateCheckResult.value.has_update
                                    ? 'text-cyan-600 dark:text-cyan-500'
                                    : 'text-emerald-600 dark:text-emerald-500',
                                ],
                              },
                              updateCheckResult.value.has_update
                                ? `v${updateCheckResult.value.latest_version} is available · ${getUpdateTypeLabel(updateCheckResult.value.update_type)}`
                                : `Running the latest version (v${updateCheckResult.value.current_version})`
                            ),
                          ]),
                        ]),
                      ]
                    ),

                  // Update Notification Preferences
                  h('div', { class: 'space-y-4' }, [
                    h('div', [
                      h(
                        'h3',
                        {
                          class:
                            'text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider flex items-center gap-2',
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
                              'stroke-width': '2',
                            },
                            [
                              h('path', {
                                'stroke-linecap': 'round',
                                'stroke-linejoin': 'round',
                                d: 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9',
                              }),
                            ]
                          ),
                          'Update Notifications',
                        ]
                      ),
                      h(
                        'p',
                        { class: 'text-sm text-slate-500 dark:text-slate-400 mt-1' },
                        'Choose which types of updates show a notification banner'
                      ),
                    ]),
                    h(
                      'div',
                      { class: 'space-y-2' },
                      updateNotifyOptions.map((option) =>
                        h(
                          'label',
                          {
                            class: [
                              'flex items-start gap-3 p-4 rounded-xl cursor-pointer transition-all duration-200',
                              updateNotifyLevel.value === option.value
                                ? `${option.selectedBg} border-2 ${option.selectedBorder} shadow-sm`
                                : 'bg-slate-50 dark:bg-slate-700/50 border-2 border-transparent hover:bg-slate-100 dark:hover:bg-slate-700',
                            ],
                          },
                          [
                            h('input', {
                              type: 'radio',
                              value: option.value,
                              checked: updateNotifyLevel.value === option.value,
                              onChange: () => (updateNotifyLevel.value = option.value),
                              class:
                                'mt-1 h-4 w-4 border-slate-300 dark:border-slate-600 text-cyan-600',
                            }),
                            h('div', { class: 'flex-1 min-w-0' }, [
                              h('div', { class: 'flex items-center gap-2 flex-wrap' }, [
                                h(
                                  'span',
                                  { class: 'font-semibold text-slate-900 dark:text-white' },
                                  option.label
                                ),
                                h(
                                  'span',
                                  {
                                    class: [
                                      'text-xs px-2 py-0.5 rounded-full font-bold',
                                      option.badgeClass,
                                    ],
                                  },
                                  option.badge
                                ),
                              ]),
                              h(
                                'p',
                                { class: 'text-sm text-slate-500 dark:text-slate-400 mt-1' },
                                option.description
                              ),
                            ]),
                          ]
                        )
                      )
                    ),
                  ]),
                ]),

                // Footer
                h(
                  'div',
                  {
                    class:
                      'px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 flex justify-end',
                  },
                  [
                    h(
                      'button',
                      {
                        onClick: () => emit('close'),
                        class:
                          'px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg font-medium hover:bg-slate-300 dark:hover:bg-slate-600 transition-colors',
                      },
                      'Done'
                    ),
                  ]
                ),
              ]
            ),
          ]
        );
    },
  });
};

const meta = {
  title: 'Modals/UpdateSettings',
  tags: ['autodocs'],
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component:
          'Application update settings modal for checking for updates and configuring which types of updates trigger the notification banner.',
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

// Default state - no update check yet
export const Default: Story = {
  render: () => ({
    components: { UpdateSettings: createMockedUpdateSettings({ currentVersion: '1.2.3' }) },
    template: '<UpdateSettings :isOpen="true" @close="() => {}" />',
  }),
};

// Update available - minor
export const MinorUpdateAvailable: Story = {
  render: () => ({
    components: {
      UpdateSettings: createMockedUpdateSettings({
        currentVersion: '1.2.3',
        latestVersion: '1.3.0',
        hasUpdate: true,
        updateType: 'minor',
      }),
    },
    template: '<UpdateSettings :isOpen="true" @close="() => {}" />',
  }),
};

// Update available - major
export const MajorUpdateAvailable: Story = {
  render: () => ({
    components: {
      UpdateSettings: createMockedUpdateSettings({
        currentVersion: '1.2.3',
        latestVersion: '2.0.0',
        hasUpdate: true,
        updateType: 'major',
      }),
    },
    template: '<UpdateSettings :isOpen="true" @close="() => {}" />',
  }),
};

// Update available - patch
export const PatchUpdateAvailable: Story = {
  render: () => ({
    components: {
      UpdateSettings: createMockedUpdateSettings({
        currentVersion: '1.2.3',
        latestVersion: '1.2.4',
        hasUpdate: true,
        updateType: 'patch',
      }),
    },
    template: '<UpdateSettings :isOpen="true" @close="() => {}" />',
  }),
};

// Up to date
export const UpToDate: Story = {
  render: () => ({
    components: {
      UpdateSettings: createMockedUpdateSettings({
        currentVersion: '1.2.3',
        latestVersion: '1.2.3',
        hasUpdate: false,
        updateType: null,
      }),
    },
    template: '<UpdateSettings :isOpen="true" @close="() => {}" />',
  }),
};

// Checking for updates
export const Checking: Story = {
  render: () => ({
    components: {
      UpdateSettings: createMockedUpdateSettings({ currentVersion: '1.2.3', isChecking: true }),
    },
    template: '<UpdateSettings :isOpen="true" @close="() => {}" />',
  }),
};

// Different notification levels
export const NotifyMajorOnly: Story = {
  render: () => ({
    components: {
      UpdateSettings: createMockedUpdateSettings({ currentVersion: '1.2.3', notifyLevel: 'major' }),
    },
    template: '<UpdateSettings :isOpen="true" @close="() => {}" />',
  }),
  parameters: {
    docs: {
      description: {
        story: 'User configured to only be notified of major updates.',
      },
    },
  },
};

export const NotifyAllUpdates: Story = {
  render: () => ({
    components: {
      UpdateSettings: createMockedUpdateSettings({ currentVersion: '1.2.3', notifyLevel: 'patch' }),
    },
    template: '<UpdateSettings :isOpen="true" @close="() => {}" />',
  }),
  parameters: {
    docs: {
      description: {
        story: 'User configured to be notified of all updates including patches.',
      },
    },
  },
};
