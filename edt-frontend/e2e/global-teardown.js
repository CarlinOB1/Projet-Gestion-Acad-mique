// Efface les comptes et données de test, le fichier d'état (mots de passe et
// sessions) et le dossier temporaire des fichiers déposés.
import { execFileSync } from 'node:child_process';
import { rmSync } from 'node:fs';
import path from 'node:path';
import { ENV_DJANGO } from '../playwright.config.js';

const RACINE = path.resolve(import.meta.dirname, '..', '..');

export default function globalTeardown() {
  try {
    execFileSync(
      path.join(RACINE, '.venv', 'Scripts', 'python.exe'),
      [path.join('edt-frontend', 'e2e', 'preparer_base.py'), 'nettoyer', process.env.E2E_ETAT],
      { cwd: RACINE, env: { ...process.env, ...ENV_DJANGO }, stdio: 'inherit' },
    );
  } finally {
    rmSync(process.env.E2E_DOSSIER, { recursive: true, force: true });
  }
}
