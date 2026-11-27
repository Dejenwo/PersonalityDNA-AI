import type { Messages } from "./messages/en";
import { en } from "./messages/en";

/**
 * Reviewed catalogues by locale code. Add a language here only after its translation has been reviewed by a
 * native speaker (docs/LOCALIZATION.md); a partial catalogue falls back to English key by key.
 */
export const CATALOGUES: Record<string, Messages> = { en };
