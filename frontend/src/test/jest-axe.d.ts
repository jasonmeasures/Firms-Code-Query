import type { AxeResults } from 'jest-axe';

declare module 'vitest' {
  interface Assertion {
    toHaveNoViolations(): { pass: boolean; message(): string };
  }
}

declare module 'jest-axe' {
  export function axe(container: Element): Promise<AxeResults>;
}
