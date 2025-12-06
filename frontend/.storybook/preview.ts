import type { Preview } from '@storybook/vue3-vite'
import { setup } from '@storybook/vue3-vite'
import { createPinia } from 'pinia'

// Import global styles
import '../src/style.css'

// Setup Pinia for stories that need state management
setup((app) => {
  const pinia = createPinia()
  app.use(pinia)
})

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    backgrounds: {
      default: 'light',
      values: [
        { name: 'light', value: '#f8fafc' },
        { name: 'dark', value: '#0f172a' },
      ],
    },
    a11y: {
      test: 'todo'
    },
    layout: 'centered',
  },
  globalTypes: {
    theme: {
      description: 'Global theme for components',
      defaultValue: 'light',
      toolbar: {
        title: 'Theme',
        icon: 'circlehollow',
        items: ['light', 'dark'],
        dynamicTitle: true,
      },
    },
  },
  decorators: [
    (story, context) => {
      const theme = context.globals.theme || 'light'
      // Apply dark class to root for Tailwind dark mode
      if (theme === 'dark') {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
      
      return {
        components: { story },
        template: `
          <div class="min-h-[200px] p-4 ${theme === 'dark' ? 'bg-slate-900' : 'bg-slate-50'}">
            <story />
          </div>
        `,
      }
    },
  ],
}

export default preview
