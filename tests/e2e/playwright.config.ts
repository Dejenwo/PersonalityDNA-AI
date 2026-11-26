import { defineConfig, devices } from "@playwright/test";

/**
 * Full-stack end-to-end tests. By default this starts the backend (SQLite, fresh file) and a
 * production build of the web app. Set E2E_EXTERNAL=1 to test servers you started yourself.
 * Requires: Python env with backend deps, and `pnpm --filter @pdna/web build` done first.
 */
const API = "http://127.0.0.1:8000";
const WEB = "http://127.0.0.1:3000";
const external = process.env.E2E_EXTERNAL === "1";
const dbFile = `${process.env.E2E_TMP ?? "/tmp"}/pdna-e2e-${Date.now()}.db`;

export default defineConfig({
  testDir: "./specs",
  timeout: 60_000,
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: { baseURL: WEB, trace: "off" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: external
    ? undefined
    : [
        {
          command: `cd ../../services/backend && PDNA_DATABASE_URL=sqlite:///${dbFile} PDNA_CORS_ORIGINS='["${WEB}"]' PDNA_SESSION_CREATE_RATE_LIMIT=1000 PDNA_AUTH_RATE_LIMIT=1000 PDNA_DEV_OUTBOX_ENDPOINT=true PDNA_WEB_BASE_URL=${WEB} python -c "import uvicorn; from app.main import create_app; uvicorn.run(create_app(create_schema=True), host='127.0.0.1', port=8000)"`,
          url: `${API}/health`,
          reuseExistingServer: false,
          timeout: 60_000,
        },
        {
          command: `cd ../../apps/web && NEXT_PUBLIC_API_URL=${API} npx next start --hostname 127.0.0.1 --port 3000`,
          url: WEB,
          reuseExistingServer: false,
          timeout: 60_000,
        },
      ],
});
