import React, { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FileText, Plus, Download, Trash2, FileIcon, FileBarChart, FileSpreadsheet } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, SelectGroup, SelectLabel } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import FormModal from '@/components/shared/FormModal';
import { confirmer } from '@/lib/confirmer';
import { toast } from '@/hooks/use-toast';
import PageHeader from '@/components/shared/PageHeader';
import { getDocuments, createDocument, deleteDocument } from '@/api/documents';
import { getModules } from '@/api/academique';

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

export default function DocumentsPage({ readOnly = false }) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef(null);

  const [selectedModuleId, setSelectedModuleId] = useState('all');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [serverError, setServerError] = useState(null);

  // Form state
  const [titre, setTitre] = useState('');
  const [typeDoc, setTypeDoc] = useState('cours');
  const [moduleId, setModuleId] = useState('');
  const [file, setFile] = useState(null);

  // Clé distincte de ['mes-modules'] (page « Mes modules », autre requête) :
  // partager la clé faisait afficher à une page la liste chargée par l'autre.
  const { data: modules = [] } = useQuery({
    queryKey: ['modules', 'documents'],
    queryFn: () => getModules(),
  });

  const { data: documents = [], isLoading, isError } = useQuery({
    queryKey: ['documents', selectedModuleId],
    queryFn: () => {
      const params = selectedModuleId !== 'all' ? { module_id: selectedModuleId } : {};
      return getDocuments(params);
    },
  });

  const createMutation = useMutation({
    mutationFn: createDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
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

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setTitre('');
    setTypeDoc('cours');
    setModuleId('');
    setFile(null);
    setServerError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleFormSubmit = () => {
    if (!titre || !moduleId || !file) {
      setServerError('Veuillez remplir tous les champs obligatoires.');
      return;
    }

    const formData = new FormData();
    formData.append('titre', titre);
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
          <div className="w-[200px]">
            <Select value={selectedModuleId} onValueChange={setSelectedModuleId}>
              <SelectTrigger className="bg-background" aria-label="Filtrer par module">
                <SelectValue placeholder="Filtrer par module" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous les modules</SelectItem>
                {Object.entries(
                  modules.reduce((acc, mod) => {
                    const classLabel = mod.classe?.libelle || 'Modules transverses / Sans classe';
                    if (!acc[classLabel]) acc[classLabel] = [];
                    acc[classLabel].push(mod);
                    return acc;
                  }, {})
                ).map(([classLabel, classModules]) => (
                  <SelectGroup key={classLabel}>
                    <SelectLabel className="bg-muted/50 text-muted-foreground font-semibold py-1">{classLabel}</SelectLabel>
                    {classModules.map((mod) => (
                      <SelectItem key={mod.id} value={mod.id.toString()} className="pl-6">
                        {mod.libelle}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                ))}
              </SelectContent>
            </Select>
          </div>

          {!readOnly && (
            <Button onClick={() => setIsModalOpen(true)} className="gap-2">
              <Plus className="size-4" />
              Ajouter un document
            </Button>
          )}
      </PageHeader>

      {/* Liste des documents */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 rounded-xl bg-muted/40 animate-pulse border border-border" />
          ))}
        </div>
      )}
      
      {!isLoading && !isError && documents.length === 0 && (
        <div className="py-16 flex flex-col items-center gap-3 text-muted-foreground text-center">
          <FileText className="size-10 opacity-30" aria-hidden />
          <p className="text-sm text-pretty">
            {selectedModuleId !== 'all'
              ? 'Aucun document pour ce module.'
              : readOnly
                ? 'Vos enseignants n’ont encore déposé aucun document.'
                : 'Vous n’avez encore déposé aucun document.'}
          </p>
          {/* Une action claire depuis l'état vide, plutôt qu'un simple constat. */}
          {selectedModuleId !== 'all' ? (
            <Button variant="outline" size="sm" onClick={() => setSelectedModuleId('all')}>
              Voir tous les modules
            </Button>
          ) : !readOnly && (
            <Button size="sm" className="gap-2" onClick={() => setIsModalOpen(true)}>
              <Plus className="size-4" />
              Ajouter un document
            </Button>
          )}
        </div>
      )}

      {!isLoading && !isError && documents.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {documents.map((doc) => (
            <div key={doc.id} className="group border border-border rounded-xl p-4 bg-card shadow-sm hover:shadow-md transition-all flex flex-col justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="mt-1 shrink-0">
                  {getFileIcon(doc.nom_fichier)}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-foreground truncate" title={doc.titre}>
                    {doc.titre}
                  </h3>
                  <div className="flex flex-wrap items-center gap-2 mt-1.5">
                    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${TYPE_COLORS[doc.type_doc]}`}>
                      {TYPE_LABELS[doc.type_doc]}
                    </span>
                    <span className="text-xs text-muted-foreground truncate max-w-[150px]">
                      {doc.module?.libelle}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between mt-auto pt-4 border-t border-border/40">
                <div className="text-[11px] text-muted-foreground tabular-nums">
                  {new Date(doc.created_at).toLocaleDateString('fr-FR')}
                  {doc.taille && ` · ${new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 }).format(doc.taille / 1024 / 1024)} Mo`}
                </div>
                {/* Toujours visibles : cachés jusqu'au survol, ces boutons
                    n'apparaissaient jamais sur téléphone. */}
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground" asChild aria-label={`Télécharger ${doc.titre ?? 'le document'}`}>
                    <a href={doc.fichier_url} target="_blank" rel="noopener noreferrer" download>
                      <Download className="h-4 w-4" />
                    </a>
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
      )}

      {/* Modal Upload */}
      <FormModal
        open={isModalOpen}
        onClose={handleCloseModal}
        onConfirm={handleFormSubmit}
        title="Ajouter un document"
        description="Ajoutez un support de cours, TD, TP ou examen pour vos étudiants."
        isPending={createMutation.isPending}
      >
        <div className="space-y-4 py-1">
          {serverError && (
            <div className="p-3 bg-destructive/10 text-destructive text-sm font-medium rounded-md border border-destructive/20 animate-shake">
              {serverError}
            </div>
          )}

          <div className="space-y-2">
            <label className="text-sm font-medium leading-none">Titre du document *</label>
            <input
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              placeholder="Ex: Chapitre 1 - Introduction"
              value={titre}
              onChange={(e) => setTitre(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium leading-none">Module concerné *</label>
            <Select value={moduleId} onValueChange={setModuleId}>
              <SelectTrigger>
                <SelectValue placeholder="Sélectionner un module" />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(
                  modules.reduce((acc, mod) => {
                    const classLabel = mod.classe?.libelle || 'Modules transverses / Sans classe';
                    if (!acc[classLabel]) acc[classLabel] = [];
                    acc[classLabel].push(mod);
                    return acc;
                  }, {})
                ).map(([classLabel, classModules]) => (
                  <SelectGroup key={classLabel}>
                    <SelectLabel className="bg-muted/50 text-muted-foreground font-semibold py-1">{classLabel}</SelectLabel>
                    {classModules.map((mod) => (
                      <SelectItem key={mod.id} value={mod.id.toString()} className="pl-6">
                        {mod.libelle}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium leading-none">Type de document</label>
            <Select value={typeDoc} onValueChange={setTypeDoc}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="cours">Support de Cours</SelectItem>
                <SelectItem value="td">Travaux Dirigés (TD)</SelectItem>
                <SelectItem value="tp">Travaux Pratiques (TP)</SelectItem>
                <SelectItem value="autre">Autre</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium leading-none">Fichier *</label>
            <div className="border-2 border-dashed border-border rounded-lg p-6 flex flex-col items-center justify-center text-center hover:bg-muted/30 transition-colors">
              <input 
                type="file" 
                className="hidden" 
                ref={fileInputRef}
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    setFile(e.target.files[0]);
                  }
                }}
              />
              {!file ? (
                <>
                  <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center mb-3 text-primary">
                    <FileText className="h-5 w-5" />
                  </div>
                  <p className="text-sm font-medium mb-1">Cliquez pour sélectionner un fichier</p>
                  <p className="text-xs text-muted-foreground">PDF, Word, Excel, PowerPoint, TXT (Max 50MB)</p>
                  <Button variant="outline" size="sm" className="mt-4" onClick={() => fileInputRef.current?.click()}>
                    Parcourir les fichiers
                  </Button>
                </>
              ) : (
                <>
                  <div className="h-10 w-10 rounded-full bg-green-500/10 flex items-center justify-center mb-3 text-green-600">
                    {getFileIcon(file.name)}
                  </div>
                  <p className="text-sm font-medium mb-1 truncate max-w-full px-4">{file.name}</p>
                  <p className="text-xs text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  <Button variant="ghost" size="sm" className="mt-3 text-destructive hover:text-destructive" onClick={() => { setFile(null); fileInputRef.current.value = ''; }}>
                    Retirer le fichier
                  </Button>
                </>
              )}
            </div>
            <p className="text-[10px] text-muted-foreground mt-1">Note: Seuls les fichiers PDF, Word, Excel, PowerPoint et Text (.txt) sont autorisés.</p>
          </div>
        </div>
      </FormModal>
    </div>
  );
}
