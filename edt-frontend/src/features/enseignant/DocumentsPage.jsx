import React, { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FileText, Plus, Download, Trash2, FileIcon, FileBarChart, FileSpreadsheet } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import FormModal from '@/components/shared/FormModal';
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

  const { data: modules = [] } = useQuery({
    queryKey: ['mes-modules'],
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
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents'] }),
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
    <div className="space-y-6 p-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-5">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 text-primary rounded-lg hidden sm:block">
            <FileText className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Documents Pédagogiques</h1>
            <p className="text-muted-foreground text-sm mt-0.5">
              Gérez les supports de cours, TD, TP et examens de vos modules.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="w-[200px]">
            <Select value={selectedModuleId} onValueChange={setSelectedModuleId}>
              <SelectTrigger className="bg-background shadow-sm">
                <SelectValue placeholder="Filtrer par module" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous les modules</SelectItem>
                {modules.map((mod) => (
                  <SelectItem key={mod.id} value={mod.id.toString()}>
                    {mod.libelle}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {!readOnly && (
            <Button onClick={() => setIsModalOpen(true)} className="shadow-sm">
              <Plus className="mr-2 h-4 w-4" />
              Uploader un document
            </Button>
          )}
        </div>
      </div>

      {/* Liste des documents */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 rounded-xl bg-muted/40 animate-pulse border border-border" />
          ))}
        </div>
      )}
      
      {!isLoading && !isError && documents.length === 0 && (
        <div className="py-16 flex flex-col items-center gap-3 text-muted-foreground">
          <FileText className="h-10 w-10 opacity-30" />
          <p className="text-sm">Aucun document pédagogique trouvé.</p>
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
                <div className="text-[11px] text-muted-foreground">
                  {new Date(doc.created_at).toLocaleDateString()}
                  {doc.taille && ` · ${(doc.taille / 1024 / 1024).toFixed(2)} MB`}
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground" asChild>
                    <a href={doc.fichier_url} target="_blank" rel="noopener noreferrer" download>
                      <Download className="h-4 w-4" />
                    </a>
                  </Button>
                  {!readOnly && (
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="h-8 w-8 text-destructive hover:bg-destructive/10"
                      onClick={() => {
                        if (window.confirm("Voulez-vous vraiment supprimer ce document ?")) {
                          deleteMutation.mutate(doc.id);
                        }
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
        title="Uploader un document pédagogique"
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
                {modules.map((mod) => (
                  <SelectItem key={mod.id} value={mod.id.toString()}>
                    {mod.libelle}
                  </SelectItem>
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
