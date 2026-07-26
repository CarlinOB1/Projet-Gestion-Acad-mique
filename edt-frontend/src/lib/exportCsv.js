/**
 * @file exportCsv.js
 * @description Utilitaire générique d'export de données tabulaires en fichier CSV,
 * déclenchant un téléchargement côté navigateur.
 */

/**
 * Échappe une valeur pour l'insertion sécurisée dans une cellule CSV.
 * @param {*} value
 * @returns {string}
 */
const escapeCsvValue = (value) => {
    if (value === null || value === undefined) return '';
    const stringValue = String(value);
    if (/[",\n;]/.test(stringValue)) {
        return `"${stringValue.replace(/"/g, '""')}"`;
    }
    return stringValue;
};

/**
 * Génère et télécharge un fichier CSV à partir de lignes de données brutes.
 *
 * @param {string} filename - Nom du fichier (sans extension, ajoutée automatiquement).
 * @param {Array<Object>} rows - Lignes de données brutes (objets).
 * @param {Array<{ key: string, label: string, accessor?: (row: Object) => string }>} columns
 *   - key : clé de secours si accessor absent
 *   - label : en-tête de colonne affiché
 *   - accessor : fonction optionnelle pour extraire/formater la valeur depuis la ligne
 */
export const exportToCsv = (filename, rows, columns) => {
    if (!rows || rows.length === 0) return;

    const header = columns.map((col) => escapeCsvValue(col.label)).join(';');

    const lines = rows.map((row) =>
        columns
            .map((col) => {
                const value = col.accessor ? col.accessor(row) : row[col.key];
                return escapeCsvValue(value);
            })
            .join(';')
    );

    const csvContent = [header, ...lines].join('\n');
    // BOM UTF-8 pour un affichage correct des accents dans Excel
    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });

    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${filename}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
};