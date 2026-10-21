import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "dist-e2e", "node_modules", "src/api/schema.d.ts"] },
  ...tseslint.configs.recommended,
  {
    rules: {
      // Components are small and commented for a reader new to React; keep the code plain.
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/consistent-type-imports": "error",
    },
  },
);
