// Prépare les comptes et les données de test sur la base jetable.
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { ENV_DJANGO } from '../playwright.config.js';

const RACINE = path.resolve(import.meta.dirname, '..', '..');

export default function globalSetup() {
  process.env.E2E_ETAT = path.join(process.env.E2E_DOSSIER, 'etat.json');
  execFileSync(
    path.join(RACINE, '.venv', 'Scripts', 'python.exe'),
    [path.join('edt-frontend', 'e2e', 'preparer_base.py'), 'preparer', process.env.E2E_ETAT],
    { cwd: RACINE, env: { ...process.env, ...ENV_DJANGO }, stdio: 'inherit' },
  );
}
