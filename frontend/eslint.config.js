// Lint rules, including the architecture: which folder may import which.
//
// Everything lives under src/app (src/ keeps only main.tsx and styles/).
// Dependency direction (one way only):
//   app/shared  <-  app/core  <-  app/features  <-  app shell (App, pages, layout, hooks, providers)
// shared/   stateless building blocks: models (types) and lib (pure logic)
// core/     app-wide singletons: config, http + interceptors, auth, api, realtime, store
// features/ UI slices; they never import each other and are composed in the app shell
// pages/    one folder per page; a page composes features and never imports another page
import { readdirSync } from 'node:fs';
import js from '@eslint/js';
import { createTypeScriptImportResolver } from 'eslint-import-resolver-typescript';
import importX from 'eslint-plugin-import-x';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';
import tseslint from 'typescript-eslint';

// Read from disk so a new feature or page is covered without editing this file.
const subfolders = (dir) => {
  try {
    return readdirSync(dir, { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => d.name);
  } catch {
    return [];
  }
};
const FEATURES = subfolders('./src/app/features');
const PAGES = subfolders('./src/app/pages');
// The app shell is every file in src/app outside these three folders.
const shell = { from: './src/app', except: ['./core', './shared', './features'] };

const zones = [
  // Features are isolated from each other.
  ...FEATURES.map((f) => ({
    target: `./src/app/features/${f}`,
    from: './src/app/features',
    except: [`./${f}`],
    message: 'Features must not import other features. Compose them in the app shell.',
  })),
  { target: './src/app/features', ...shell, message: 'Features must not depend on the app shell.' },
  // Pages are isolated from each other; shared page chrome lives in layout/.
  ...PAGES.map((pg) => ({
    target: `./src/app/pages/${pg}`,
    from: './src/app/pages',
    except: [`./${pg}`],
    message: 'Pages must not import other pages. Move shared parts to layout/ or a feature.',
  })),
  { target: './src/app/layout', from: './src/app/pages', message: 'layout/ wraps pages; it must not import them.' },
  {
    target: './src/app/core',
    from: './src/app/features',
    message: 'core/ must not depend on features.',
  },
  {
    target: './src/app/shared',
    from: ['./src/app/core', './src/app/features'],
    message: 'shared/ is stateless building blocks: it depends on nothing outside shared/.',
  },
  { target: './src/app/core', ...shell, message: 'core/ must not depend on the app shell.' },
  { target: './src/app/shared', ...shell, message: 'shared/ must not depend on the app shell.' },
  { target: './src/app/shared/models', from: './src/app/shared/lib', message: 'models/ holds types only.' },
];

// Direction inside core/: config <- auth <- http <- api; realtime and store sit beside api.
// Not applied to tests, which may wire real collaborators together.
const coreZones = [
  {
    target: './src/app/core/config',
    from: ['./src/app/core/api', './src/app/core/auth', './src/app/core/http', './src/app/core/realtime', './src/app/core/store'],
    message: 'core/config holds constants only: it depends on shared/ alone.',
  },
  {
    target: './src/app/core/auth',
    from: ['./src/app/core/api', './src/app/core/http', './src/app/core/realtime', './src/app/core/store'],
    message: 'core/auth depends on config only.',
  },
  {
    target: './src/app/core/http',
    from: ['./src/app/core/api', './src/app/core/realtime', './src/app/core/store'],
    message: 'core/http is transport only: it must not know endpoints, realtime or the store.',
  },
  {
    target: './src/app/core/api',
    from: ['./src/app/core/realtime', './src/app/core/store'],
    message: 'core/api calls endpoints through core/http; it must not reach into realtime or the store.',
  },
  {
    target: './src/app/core/realtime',
    from: ['./src/app/core/api', './src/app/core/http', './src/app/core/store'],
    message: 'core/realtime talks to its LiveSink interface, not to the store or HTTP.',
  },
  {
    target: './src/app/core/store',
    from: ['./src/app/core/api', './src/app/core/http', './src/app/core/realtime'],
    message: 'core/store holds state only: no I/O.',
  },
];

export default tseslint.config(
  { ignores: ['dist', 'node_modules'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  reactHooks.configs.flat.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: { globals: globals.browser },
    plugins: { 'import-x': importX },
    settings: {
      'import-x/resolver-next': [createTypeScriptImportResolver({ project: './tsconfig.json' })],
    },
    rules: {
      'import-x/no-restricted-paths': ['error', { zones: [...zones, ...coreZones] }],
      'import-x/no-cycle': 'error',
      'import-x/no-duplicates': 'error',
      'import-x/no-self-import': 'error',
      'import-x/no-useless-path-segments': 'error',
      '@typescript-eslint/consistent-type-imports': 'error',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      'no-restricted-syntax': [
        'error',
        { selector: 'ExportAllDeclaration', message: 'No barrel files: import from the defining module.' },
      ],
    },
  },
  {
    files: ['**/*.test.{ts,tsx}'],
    rules: { 'import-x/no-restricted-paths': ['error', { zones }] },
  },
);
