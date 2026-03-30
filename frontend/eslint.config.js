import pluginVue from "eslint-plugin-vue";

export default [
  ...pluginVue.configs["flat/essential"],
  {
    rules: {
      // Relax rules that conflict with the existing codebase style
      "vue/multi-word-component-names": "off",
      "vue/html-self-closing": "off",
      // Catch real bugs
      "vue/no-unused-vars": "warn",
      "vue/no-mutating-props": "error",
      "vue/require-v-for-key": "error",
      "vue/no-use-v-if-with-v-for": "error",
      "vue/no-v-html": "warn",
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
      "no-undef": "off", // Vue globals handled by compiler
    },
  },
];
