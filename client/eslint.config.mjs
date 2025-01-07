import eslint from '@eslint/js';
import eslintConfigPrettier from 'eslint-config-prettier';
import eslintPluginVue from 'eslint-plugin-vue';
import globals from 'globals';
import typescriptEslint from 'typescript-eslint';

export default typescriptEslint.config(
    { ignores: ['*.d.ts', '**/sdks/**'] },
    {
    extends: [
        eslint.configs.recommended,
      ...typescriptEslint.configs.recommended,
      ...eslintPluginVue.configs['flat/recommended'],
    ],
    files: ['**/*.{ts,vue}'],

    languageOptions: {
        globals: globals.browser,
        ecmaVersion: 'latest',
        sourceType: "module",

        parserOptions: {
            parser: "@typescript-eslint/parser",
        },
    },
},
eslintConfigPrettier
);
