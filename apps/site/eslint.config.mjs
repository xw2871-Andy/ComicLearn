import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

const eslintConfig = [
  ...nextCoreWebVitals,
  ...nextTypescript,
  {
    rules: {
      "@next/next/no-page-custom-font": "off",
      "react/no-unescaped-entities": "off"
    }
  },
  {
    ignores: [".next/**", "node_modules/**"]
  }
];

export default eslintConfig;
