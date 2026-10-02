import React, { useMemo, useState, useRef } from 'react';
import { cn } from '@/lib/utils';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FileText, Plus, Download, Trash2, FileIcon, FileBarChart, FileSpreadsheet, Upload } from '@/components/ui/icons';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, SelectGroup, SelectLabel } from '@/components/ui/select';
import FormModal from '@/components/shared/FormModal';
import { confirmer } from '@/lib/confirmer';
import { toast } from '@/hooks/use-toast';
import PageHeader from '@/components/shared/PageHeader';
import { getDocuments, createDocument, deleteDocument, downloadDocument } from '@/api/documents';
import apiClient from '@/api/client';
import { trouverSemestreEnCours } from '@/lib/semestres';

const getFileIcon = (filename) => {
  if (!filename) return <FileText className="h-5 w-5" />;
  const ext = filename.split('.').pop().toLowerCase();
  if (['pdf'].includes(ext)) return <FileText className="h-5 w-5 text-red-500" />;
  if (['doc', 'docx'].includes(ext)) return <FileText className="h-5 w-5 text-blue-500" />;
  if (['xls', 'xlsx'].includes(ext)) return <FileSpreadsheet className="h-5 w-5 text-green-500" />;
  if (['ppt', 'pptx'].includes(ext)) return <FileBarChart className="h-5 w-5 text-orange-500" />;
  if (['txt'].includes(ext)) return <FileText className="h-5 w-5 text-gray-500" />;
  return <FileIcon className="h-5 w-5 text-muted-foreground" />;
};

const TYPE_COLORS = {
  cours: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  td: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  tp: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  autre: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
};

const TYPE_LABELS = {
  cours: 'Cours',
  td: 'TD',
  tp: 'TP',
  autre: 'Autre',
};

const TYPES_DOC = [
  { valeur: 'cours', libelle: 'Cours' },
  { valeur: 'td', libelle: 'TD' },
  { valeur: 'tp', libelle: 'TP' },
  { valeur: 'autre', libelle: 'Autre' },
];

const EXTENSIONS_ACCEPTEES = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'];
// Doit rester aligné sur DOCUMENT_MAX_UPLOAD_BYTES (Gestion_edt/settings.py) :
// ici c'est un confort (refus immédiat), le serveur reste seul juge.
const TAILLE_MAX_MO = 20;
const TAILLE_MAX = TAILLE_MAX_MO * 1024 * 1024;

const formatTaille = (octets) =>
  `${new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 }).format(octets / 1024 / 1024)} Mo`;

/** « Chapitre 1 - Introduction.pdf » → « Chapitre 1 - Introduction » */
const titreDepuisNomFichier = (nom) => nom.replace(/\.[^.]+$/, '').replace(/_+/g, ' ').trim();

/** Modules que l'enseignant dispense (les mêmes que « Mes modules »). */
const getMesModules = async () => {
  const response = await apiClient.get('/modules/mes_modules/');
  return response.data?.results ?? response.data;
};

/** Semestre en cours d'abord, puis par classe et par nom. */
function trierModules(modules) {
  const semestres = [...new Map(modules.filter((m) => m.semestre).map((m) => [m.semestre.id, m.semestre])).values()];
  const enCoursId = trouverSemestreEnCours(semestres)?.id;
  const rang = (m) => (m.semestre?.id === enCoursId ? 0 : 1);
  return [...modules].sort(
    (a, b) =>
      rang(a) - rang(b) ||
      (a.classe?.libelle ?? '').localeCompare(b.classe?.libelle ?? '') ||
      (a.libelle ?? '').localeCompare(b.libelle ?? ''),
  );
}

/** Modules regroupés par classe, pour les listes déroulantes. */
function OptionsModules({ modules }) {
  const parClasse = modules.reduce((acc, mod) => {
    const classLabel = mod.classe?.libelle || 'Modules transverses / Sans classe';
    if (!acc[classLabel]) acc[classLabel] = [];
    acc[classLabel].push(mod);
    return acc;
  }, {});
  return Object.entries(parClasse).map(([classLabel, classModules]) => (
    <SelectGroup key={classLabel}>
      <SelectLabel className="bg-muted/50 text-muted-foreground font-semibold py-1">{classLabel}</SelectLabel>
      {classModules.map((mod) => (
        <SelectItem key={mod.id} value={mod.id.toString()} className="pl-6">
          {mod.libelle}
        </SelectItem>
      ))}
    </SelectGroup>
  ));
}

function MessageChamp({ id, children }) {
  if (!children) return null;
  return (
    <p id={id} role="alert" className="text-xs font-medium text-destructive">
      {children}
    </p>
  );
}

export default function DocumentsPage({ readOnly = false }) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [serverError, setServerError] = useState(null);

  // Form state
  const [titre, setTitre] = useState('');
  const [titreModifie, setTitreModifie] = useState(false);
  const [typeDoc, setTypeDoc] = useState('cours');
  const [moduleId, setModuleId] = useState('');
  const [file, setFile] = useState(null);
  const [erreurFichier, setErreurFichier] = useState(null);
  const [survol, setSurvol] = useState(false);
  const [tentative, setTentative] = useState(false);

  // Seulement les modules de l'enseignant : la liste complète du périmètre
  // (29 modules, autres départements compris) rendait le choix pénible.
  // Les étudiants ne déposent rien, ils n'en ont pas besoin.
  const { data: mesModules = [] } = useQuery({
    queryKey: ['mes-modules', 'documents'],
    queryFn: getMesModules,
    enabled: !readOnly,
  });
  const modules = useMemo(() => trierModules(mesModules), [mesModules]);
  const idsMesModules = useMemo(() => new Set(modules.map((m) => m.id)), [modules]);

  const { data: documents = [], isLoading, isError } = useQuery({
    queryKey: ['documents'],
    queryFn: () => getDocuments(),
  });

  // Un bloc par module : semestre en cours d'abord, puis par classe et par nom.
  const groupes = useMemo(() => {
    const parModule = new Map();
    documents.forEach((doc) => {
      const cle = doc.module?.id ?? 'sans-module';
      if (!parModule.has(cle)) parModule.set(cle, { cle, module: doc.module, documents: [] });
      parModule.get(cle).documents.push(doc);
    });
    const ordre = new Map(trierModules([...parModule.values()].map((g) => g.module).filter(Boolean)).map((m, i) => [m.id, i]));
    return [...parModule.values()].sort((a, b) => (ordre.get(a.module?.id) ?? 999) - (ordre.get(b.module?.id) ?? 999));
  }, [documents]);

  const createMutation = useMutation({
    mutationFn: createDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast({
        title: 'Document déposé',
        description: [titre.trim(), moduleChoisi?.libelle].filter(Boolean).join(' · '),
      });
      handleCloseModal();
    },
    onError: (err) => {
      const errorMsg = err.response?.data?.fichier?.[0] || err.message || "Erreur lors de l'upload du document";
      setServerError(errorMsg);
    }
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast({ title: 'Document supprimé' });
    },
    onError: () =>
      toast({
        variant: 'destructive',
        title: "Le document n'a pas pu être supprimé",
        description: 'Réessayez ; si le problème persiste, rechargez la page.',
      }),
  });

  // Le fichier n'a plus d'adresse publique : un simple lien ne peut pas
  // envoyer le jeton de connexion, on passe donc par l'API (downloadDocument).
  const downloadMutation = useMutation({
    mutationFn: downloadDocument,
    onError: () =>
      toast({
        variant: 'destructive',
        title: 'Le téléchargement a échoué',
        description: "Réessayez ; si le problème persiste, contactez l'administrateur.",
      }),
  });

  const moduleChoisi = modules.find((m) => m.id.toString() === moduleId);
  const nbEtudiants = moduleChoisi?.classe?.nombre_etudiants;

  // Depuis le bloc d'un module, on le propose d'office.
  const handleOpenModal = (idModule) => {
    if (idModule) setModuleId(String(idModule));
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setTitre('');
    setTitreModifie(false);
    setTypeDoc('cours');
    setModuleId('');
    setFile(null);
    setErreurFichier(null);
    setSurvol(false);
    setTentative(false);
    setServerError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const choisirFichier = (nouveau) => {
    if (!nouveau) return;
    const ext = nouveau.name.split('.').pop().toLowerCase();
    if (!EXTENSIONS_ACCEPTEES.includes(ext)) {
      setErreurFichier('Ce format n’est pas accepté. Choisissez un PDF, un document Word, Excel, PowerPoint ou un fichier texte.');
      return;
    }
    if (nouveau.size > TAILLE_MAX) {
      setErreurFichier(`Ce fichier fait ${formatTaille(nouveau.size)} : la limite est de ${TAILLE_MAX_MO} Mo.`);
      return;
    }
    setErreurFichier(null);
    setServerError(null);
    setFile(nouveau);
    // Le titre suit le nom du fichier tant que l'utilisateur ne l'a pas retouché.
    if (!titreModifie) setTitre(titreDepuisNomFichier(nouveau.name));
  };

  const retirerFichier = () => {
    setFile(null);
    setErreurFichier(null);
    if (!titreModifie) setTitre('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleFormSubmit = () => {
    setTentative(true);
    if (!titre.trim() || !moduleId || !file) return;

    const formData = new FormData();
    formData.append('titre', titre.trim());
    formData.append('type_doc', typeDoc);
    formData.append('module_id', moduleId);
    formData.append('fichier', file);

    createMutation.mutate(formData);
  };

  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto">
      <PageHeader
        titre={readOnly ? 'Documents' : 'Mes documents'}
        description={readOnly
          ? 'Les supports de cours, TD et TP déposés par vos enseignants.'
          : 'Les supports de cours, TD et TP que vous mettez à disposition de vos étudiants.'}
      >
        {/* Quand la page est vide, l'unique bouton est celui de l'état vide. */}
        {!readOnly && documents.length > 0 && (
          <Button onClick={() => handleOpenModal()} className="gap-2">
            <Plus className="size-4" />
            Ajouter un document
          </Button>
        )}
      </PageHeader>

      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 rounded-xl bg-muted/40 animate-pulse border border-border" />
          ))}
        </div>
      )}

      {isError && (
        <p role="alert" className="py-10 text-center text-sm text-destructive">
          Les documents n’ont pas pu être chargés. Rechargez la page pour réessayer.
        </p>
      )}

      {!isLoading && !isError && documents.length === 0 && (
        <div className="py-16 flex flex-col items-center gap-3 text-muted-foreground text-center">
          <FileText className="size-10 opacity-30" aria-hidden />
          <p className="text-sm text-pretty">
            {readOnly
              ? 'Vos enseignants n’ont encore déposé aucun document.'
              : 'Vous n’avez encore déposé aucun document.'}
          </p>
          {!readOnly && (
            <Button size="sm" className="gap-2" onClick={() => handleOpenModal()}>
              <Plus className="size-4" />
              Ajouter un document
            </Button>
          )}
        </div>
      )}

      {/* Un bloc par module : le nom complet et la classe y figurent une seule fois. */}
      {!isLoading && !isError && groupes.map(({ cle, module: mod, documents: docs }) => (
        <section key={cle} aria-labelledby={`module-${cle}`} className="space-y-3">
          <div className="flex items-center justify-between gap-3 border-b border-border pb-2">
            <div className="min-w-0">
              <h2 id={`module-${cle}`} className="text-base font-semibold leading-snug text-balance">
                {mod?.libelle ?? 'Sans module'}
              </h2>
              <p className="text-xs text-muted-foreground tabular-nums">
                {[mod?.classe?.libelle, `${docs.length} document${docs.length > 1 ? 's' : ''}`].filter(Boolean).join(' · ')}
              </p>
            </div>
            {!readOnly && mod && idsMesModules.has(mod.id) && (
              <Button
                variant="outline"
                size="sm"
                className="shrink-0 gap-1.5 rounded-md"
                onClick={() => handleOpenModal(mod.id)}
                aria-label={`Déposer un document pour ${mod.libelle}`}
              >
                <Plus className="size-3.5" />
                Déposer
              </Button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {docs.map((doc) => (
              <div key={doc.id} className="group border border-border rounded-xl p-4 bg-card shadow-sm hover:shadow-md transition-all flex flex-col justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="mt-1 shrink-0">
                    {getFileIcon(doc.nom_fichier)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-foreground truncate" title={doc.titre}>
                      {doc.titre}
                    </h3>
                    <div className="mt-1.5">
                      <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${TYPE_COLORS[doc.type_doc]}`}>
                        {TYPE_LABELS[doc.type_doc]}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between mt-auto pt-4 border-t border-border/40">
                  <div className="text-[11px] text-muted-foreground tabular-nums">
                    {new Date(doc.created_at).toLocaleDateString('fr-FR')}
                    {doc.taille && ` · ${formatTaille(doc.taille)}`}
                  </div>
                  {/* Toujours visibles : cachés jusqu'au survol, ces boutons
                      n'apparaissaient jamais sur téléphone. */}
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-foreground"
                      aria-label={`Télécharger ${doc.titre ?? 'le document'}`}
                      disabled={downloadMutation.isPending}
                      onClick={() => downloadMutation.mutate(doc)}
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                    {!readOnly && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-destructive hover:bg-destructive/10"
                        aria-label={`Supprimer le document ${doc.titre ?? ''}`.trim()}
                        onClick={async () => {
                          const ok = await confirmer({
                            titre: 'Supprimer ce document ?',
                            description: 'Les étudiants ne pourront plus le consulter ni le télécharger.',
                            libelleConfirmer: 'Supprimer',
                            destructif: true,
                          });
                          if (ok) deleteMutation.mutate(doc.id);
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      ))}

      {/* Modal Upload : on part du fichier, le reste se remplit presque tout seul. */}
      <FormModal
        open={isModalOpen}
        onClose={handleCloseModal}
        onConfirm={handleFormSubmit}
        title="Ajouter un document"
        description="Déposez un support de cours, TD ou TP pour vos étudiants."
        confirmLabel="Déposer"
        isPending={createMutation.isPending}
      >
        <div className="space-y-5 py-1">
          {serverError && (
            <div role="alert" className="p-3 bg-destructive/10 text-destructive text-sm font-medium rounded-md border border-destructive/20">
              {serverError}
            </div>
          )}

          {/* 1. Fichier */}
          <div className="space-y-2">
            <span className="text-sm font-medium leading-none">Fichier *</span>
            <label
              htmlFor="doc-fichier"
              onDragOver={(e) => { e.preventDefault(); setSurvol(true); }}
              onDragLeave={() => setSurvol(false)}
              onDrop={(e) => {
                e.preventDefault();
                setSurvol(false);
                choisirFichier(e.dataTransfer.files?.[0]);
              }}
              className={cn(
                'flex cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed p-5 text-center transition-colors',
                'focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2',
                survol ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/30',
                tentative && !file && 'border-destructive/60',
              )}
            >
              <input
                id="doc-fichier"
                type="file"
                className="sr-only"
                ref={fileInputRef}
                accept={EXTENSIONS_ACCEPTEES.map((e) => `.${e}`).join(',')}
                aria-describedby="doc-fichier-aide"
                onChange={(e) => choisirFichier(e.target.files?.[0])}
              />
              {!file ? (
                <>
                  <span className="mb-1 flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <Upload className="size-5" aria-hidden />
                  </span>
                  <span className="text-sm font-medium">Cliquez ou glissez un fichier ici</span>
                  <span id="doc-fichier-aide" className="text-xs text-muted-foreground text-pretty">
                    PDF, Word, Excel, PowerPoint ou texte · {TAILLE_MAX_MO} Mo maximum
                  </span>
                </>
              ) : (
                <>
                  <span className="mb-1 flex size-10 items-center justify-center rounded-full bg-primary/10">
                    {getFileIcon(file.name)}
                  </span>
                  <span id="doc-fichier-aide" className="max-w-full truncate px-4 text-sm font-medium">{file.name}</span>
                  <span className="text-xs text-muted-foreground tabular-nums">{formatTaille(file.size)}</span>
                  <span className="mt-1 text-xs font-medium text-primary">Cliquez pour changer de fichier</span>
                </>
              )}
            </label>
            {file && (
              <Button type="button" variant="ghost" size="sm" className="h-7 rounded-md px-2 text-muted-foreground hover:text-destructive" onClick={retirerFichier}>
                Retirer le fichier
              </Button>
            )}
            <MessageChamp>{erreurFichier ?? (tentative && !file ? 'Choisissez le fichier à déposer.' : null)}</MessageChamp>
          </div>

          {/* 2. Titre (pré-rempli avec le nom du fichier) */}
          <div className="space-y-2">
            <label htmlFor="doc-titre" className="text-sm font-medium leading-none">Titre du document *</label>
            <input
              id="doc-titre"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              placeholder="Ex : Chapitre 1 - Introduction"
              value={titre}
              aria-invalid={tentative && !titre.trim()}
              aria-describedby="doc-titre-erreur"
              onChange={(e) => { setTitre(e.target.value); setTitreModifie(true); }}
            />
            <MessageChamp id="doc-titre-erreur">{tentative && !titre.trim() ? 'Donnez un titre au document.' : null}</MessageChamp>
          </div>

          {/* 3. Module */}
          <div className="space-y-2">
            <label htmlFor="doc-module" className="text-sm font-medium leading-none">Module concerné *</label>
            <Select value={moduleId} onValueChange={setModuleId}>
              <SelectTrigger id="doc-module" className="w-full" aria-invalid={tentative && !moduleId} aria-describedby="doc-module-aide">
                <SelectValue placeholder="Sélectionner un module" />
              </SelectTrigger>
              <SelectContent>
                {modules.length === 0 && (
                  <div className="px-3 py-2 text-xs text-muted-foreground">
                    Aucun module ne vous est actuellement affecté.
                  </div>
                )}
                <OptionsModules modules={modules} />
              </SelectContent>
            </Select>
            <div id="doc-module-aide">
              {tentative && !moduleId ? (
                <MessageChamp>Choisissez le module concerné.</MessageChamp>
              ) : moduleChoisi?.classe && nbEtudiants != null ? (
                <p className="text-xs text-muted-foreground text-pretty">
                  Visible par {nbEtudiants === 0 ? 'les étudiants' : nbEtudiants === 1 ? 'l’étudiant' : `les ${nbEtudiants} étudiants`} de {moduleChoisi.classe.libelle}.
                </p>
              ) : null}
            </div>
          </div>

          {/* 4. Type : un clic au lieu d'une liste */}
          <fieldset className="space-y-2">
            <legend className="mb-2 text-sm font-medium leading-none">Type de document</legend>
            <div className="grid grid-cols-4 gap-2">
              {TYPES_DOC.map(({ valeur, libelle }) => (
                <label
                  key={valeur}
                  className={cn(
                    'flex h-10 cursor-pointer items-center justify-center rounded-md border text-sm font-medium transition-colors',
                    'has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring has-[:focus-visible]:ring-offset-2',
                    typeDoc === valeur
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-input bg-background text-muted-foreground hover:bg-muted/50',
                  )}
                >
                  <input
                    type="radio"
                    name="doc-type"
                    value={valeur}
                    checked={typeDoc === valeur}
                    onChange={() => setTypeDoc(valeur)}
                    className="sr-only"
                  />
                  {libelle}
                </label>
              ))}
            </div>
          </fieldset>
        </div>
      </FormModal>
    </div>
  );
}
