// Tests dans le navigateur (CORRECTIONS / plan de tests, étape C3).
//
// Lancement, depuis edt-frontend :
//   npx playwright test
//
// Prérequis : la base jetable `edt_charge` existe et a été remplie par
// seed.py (voir charge/locustfile.py). Jamais la base de travail : le
// script de préparation refuse toute autre base.
//
// La configuration démarre ses propres serveurs, sur des ports à part
// (Django 8011, Vite 3011), sans toucher à ceux du travail quotidien
// (8000, 3000). Chaque lancement tire au hasard une clé secrète Django et
// range les fichiers déposés dans un dossier temporaire : les sessions de
// test ne valent rien ailleurs, et media/ reste propre.
import { defineConfig, devices } from '@playwright/test';
import { randomBytes } from 'node:crypto';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';

// Calculés une fois par lancement : les processus de test héritent de ces
// variables au lieu d'en tirer de nouvelles.
process.env.E2E_SECRET ??= randomBytes(32).toString('hex');
process.env.E2E_DOSSIER ??= mkdtempSync(path.join(tmpdir(), 'edt-e2e-'));

const RACINE = path.resolve(import.meta.dirname, '..');
const PYTHON = path.join(RACINE, '.venv', 'Scripts', 'python.exe');

export const ENV_DJANGO = {
  DB_NAME: 'edt_charge',
  DJANGO_SECRET_KEY: process.env.E2E_SECRET,
  DJANGO_MEDIA_ROOT: path.join(process.env.E2E_DOSSIER, 'media'),
  PYTHONIOENCODING: 'utf-8',
};

export default defineConfig({
  testDir: './e2e',
  // Les scénarios partagent les mêmes comptes : un seul à la fois.
  workers: 1,
  fullyParallel: false,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [['list']],
  globalSetup: './e2e/global-setup.js',
  globalTeardown: './e2e/global-teardown.js',
  use: {
    baseURL: 'http://localhost:3011',
    trace: 'retain-on-failure',
    ...devices['Desktop Chrome'],
  },
  webServer: [
    {
      command: `"${PYTHON}" manage.py runserver 8011 --noreload`,
      cwd: RACINE,
      env: ENV_DJANGO,
      url: 'http://127.0.0.1:8011/admin/login/',
      reuseExistingServer: false,
      timeout: 120_000,
      // Journaux des serveurs masqués ; 'pipe' pour les voir.
      stdout: 'ignore',
      stderr: 'ignore',
    },
    {
      command: 'npx vite --port 3011 --strictPort',
      env: { EDT_API_URL: 'http://localhost:8011' },
      url: 'http://localhost:3011',
      reuseExistingServer: false,
      timeout: 120_000,
      // Journaux des serveurs masqués ; 'pipe' pour les voir.
      stdout: 'ignore',
      stderr: 'ignore',
    },
  ],
});
