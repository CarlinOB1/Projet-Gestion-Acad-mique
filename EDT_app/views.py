from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    Faculte, Departement, Filiere, Parcours,
    AnneeAcademique, Semestre, Classe,
    Profil, Enseignant, Etudiant,
    Matiere, Module, Seance, ReferentClasse,
    DocumentPedagogique,
)
from EDT_app.serializers import (
    FaculteSerializer, DepartementSerializer, FiliereSerializer,
    ParcoursSerializer, AnneeAcademiqueSerializer, SemestreSerializer,
    ClasseSerializer, ProfilSerializer, EnseignantSerializer,
    EtudiantSerializer, MatiereSerializer, ModuleSerializer,
    SeanceSerializer, SeanceReportSerializer, ProfilSuspensionSerializer,
    DocumentPedagogiqueSerializer,
)
from .permissions import (
    ProfilActifPermission,
    IsChefDepartement,
    IsChefDepartementOrReadOnly,
    IsEnseignant,
    IsEtudiant,
    IsOwnerOrChefDepartement,
    IsReferentClasse,
    IsChefOrReferentOrReadOnly,
    IsDocumentOwnerOrReadOnly,
)


# ──────────────────────────────────────────────────────────────────────────────
# MIXIN COMMUN
# ──────────────────────────────────────────────────────────────────────────────

class BaseViewSet(viewsets.ModelViewSet):
    """
    Mixin appliqué à tous les ViewSets :
    - IsAuthenticated  : toute requête doit être authentifiée
    - ProfilActifPermission : bloque les profils suspendus
    """
    permission_classes = [IsAuthenticated, ProfilActifPermission]


# ──────────────────────────────────────────────────────────────────────────────
# 1. ORGANISATION ACADÉMIQUE
# ──────────────────────────────────────────────────────────────────────────────

class FaculteViewSet(BaseViewSet):
    """
    list   GET  /api/facultes/
    create POST /api/facultes/
    retrieve/update/delete sur /api/facultes/{id}/
    Écriture réservée au responsable.
    """
    queryset           = Faculte.objects.all()
    serializer_class   = FaculteSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsChefDepartementOrReadOnly]


class DepartementViewSet(BaseViewSet):
    queryset           = Departement.objects.select_related('faculte').all()
    serializer_class   = DepartementSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsChefDepartementOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        faculte_id = self.request.query_params.get('faculte_id')
        if faculte_id:
            qs = qs.filter(faculte_id=faculte_id)
        return qs


class FiliereViewSet(BaseViewSet):
    queryset           = Filiere.objects.select_related('departement__faculte').all()
    serializer_class   = FiliereSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsChefDepartementOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        dept_id = self.request.query_params.get('departement_id')
        if dept_id:
            qs = qs.filter(departement_id=dept_id)
        return qs


class ParcoursViewSet(BaseViewSet):
    queryset           = Parcours.objects.all()
    serializer_class   = ParcoursSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsChefDepartementOrReadOnly]


class AnneeAcademiqueViewSet(BaseViewSet):
    """
    Action supplémentaire : POST /api/annees/{id}/archiver/
    Tente d'archiver l'année — bloqué si séances confirmées dans le futur.
    """
    queryset           = AnneeAcademique.objects.all()
    serializer_class   = AnneeAcademiqueSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsChefDepartementOrReadOnly]

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsChefDepartement])
    def archiver(self, request, pk=None):
        annee = self.get_object()

        if annee.statut == 'archivée':
            return Response(
                {'detail': "Cette année est déjà archivée."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today         = timezone.now().date()
        seances_futur = Seance.objects.filter(
            annee=annee,
            statut='Confirmée',
            date_seance__gt=today,
        )
        if seances_futur.exists():
            return Response(
                {
                    'detail': (
                        f"Impossible d'archiver : {seances_futur.count()} "
                        f"séance(s) confirmée(s) dans le futur."
                    ),
                    'seances_bloquantes': seances_futur.count(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        annee.statut = 'archivée'
        annee.save()
        return Response(
            AnneeAcademiqueSerializer(annee).data,
            status=status.HTTP_200_OK,
        )


class SemestreViewSet(BaseViewSet):
    queryset           = Semestre.objects.select_related('annee').all()
    serializer_class   = SemestreSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsChefDepartementOrReadOnly]

    def get_queryset(self):
        qs       = super().get_queryset()
        annee_id = self.request.query_params.get('annee_id')
        if annee_id:
            qs = qs.filter(annee_id=annee_id)
        return qs


class ClasseViewSet(BaseViewSet):
    """
    Action supplémentaire : POST /api/classes/{id}/passer_semestre/
    Fait avancer les étudiants éligibles vers la classe du semestre cible.
    Paramètre attendu : { "semestre_cible_id": <int> }
    """
    queryset = Classe.objects.select_related(
        'parcours', 'filiere', 'semestre__annee', 'annee'
    ).prefetch_related('etudiant_set').all()
    serializer_class   = ClasseSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsChefDepartementOrReadOnly]

    def get_queryset(self):
        qs          = super().get_queryset()
        user        = self.request.user

        if hasattr(user, 'profil') and hasattr(user.profil, 'enseignant') and \
                not (user.is_superuser or user.groups.filter(name='responsable').exists()):
            enseignant = user.profil.enseignant
            departements_diriges = enseignant.departements_diriges.all()
            if departements_diriges.exists():
                # Chef de département : classes de ses départements gérés
                qs = qs.filter(filiere__departement__in=departements_diriges)
            else:
                # Enseignant simple : classes de son propre département uniquement
                qs = qs.filter(filiere__departement=enseignant.departement)

        annee_id    = self.request.query_params.get('annee_id')
        semestre_id = self.request.query_params.get('semestre_id')
        filiere_id  = self.request.query_params.get('filiere_id')
        if annee_id:
            qs = qs.filter(annee_id=annee_id)
        if semestre_id:
            qs = qs.filter(semestre_id=semestre_id)
        if filiere_id:
            qs = qs.filter(filiere_id=filiere_id)
        return qs

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsChefDepartement])
    def passer_semestre(self, request, pk=None):
        """
        Transfère les étudiants éligibles de cette classe vers une classe cible.

        Corps attendu :
          { "semestre_cible_id": <int> }

        Logique :
          1. Vérifie que le semestre cible existe et appartient à la même année.
          2. Trouve ou crée la classe cible (même parcours + filière, semestre cible).
          3. Pour chaque étudiant non suspendu → met à jour sa classe.
          4. Retourne un résumé.
        """
        classe_source = self.get_object()
        semestre_cible_id = request.data.get('semestre_cible_id')

        if not semestre_cible_id:
            return Response(
                {'detail': "Le champ 'semestre_cible_id' est obligatoire."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            semestre_cible = Semestre.objects.get(pk=semestre_cible_id)
        except Semestre.DoesNotExist:
            return Response(
                {'detail': "Semestre cible introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Trouve ou crée la classe cible
        classe_cible, created = Classe.objects.get_or_create(
            parcours=classe_source.parcours,
            filiere=classe_source.filiere,
            semestre=semestre_cible,
            annee=semestre_cible.annee,
        )

        etudiants     = Etudiant.objects.filter(classe=classe_source).select_related('profil')
        passes        = []
        bloques       = []

        for etudiant in etudiants:
            if etudiant.profil.statut == 'suspendu':
                bloques.append({
                    'matricule': etudiant.matricule,
                    'motif': 'Profil suspendu',
                })
                continue

            etudiant.classe = classe_cible
            etudiant.save()
            passes.append(etudiant.matricule)

        return Response(
            {
                'classe_source': ClasseSerializer(classe_source).data,
                'classe_cible':  ClasseSerializer(classe_cible).data,
                'classe_cible_creee': created,
                'passes':  passes,
                'bloques': bloques,
                'total_passes':  len(passes),
                'total_bloques': len(bloques),
            },
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# 2. LES ACTEURS
# ──────────────────────────────────────────────────────────────────────────────

class ProfilViewSet(BaseViewSet):
    """
    Actions supplémentaires :
      PATCH /api/profils/{id}/changer_statut/
      Corps : { "statut": "suspendu"|"actif", "motif_suspension": "..." }
    """
    queryset           = Profil.objects.select_related('user').all()
    serializer_class   = ProfilSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsOwnerOrChefDepartement]

    def get_permissions(self):
        """
        - list et create : responsable uniquement
        - retrieve       : propriétaire ou responsable
        - update/destroy : responsable uniquement
        """
        if self.action in ('list', 'create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), ProfilActifPermission(), IsChefDepartement()]
        return [IsAuthenticated(), ProfilActifPermission(), IsOwnerOrChefDepartement()]

    @action(
        detail=True,
        methods=['patch'],
        permission_classes=[IsAuthenticated, IsChefDepartement],
        url_path='changer_statut',
    )
    def changer_statut(self, request, pk=None):
        """
        Suspend ou réactive un profil.
        Utilise ProfilSuspensionSerializer pour forcer le motif si suspendu.
        """
        profil     = self.get_object()
        serializer = ProfilSuspensionSerializer(
            data=request.data,
            context={'profil': profil},
        )
        serializer.is_valid(raise_exception=True)
        profil_maj = serializer.save()
        return Response(
            ProfilSerializer(profil_maj, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated, ProfilActifPermission],
        url_path='me',
    )
    def me(self, request):
        """Retourne le profil complet de l'utilisateur connecté."""
        profil = request.user.profil
        data = ProfilSerializer(profil, context={'request': request}).data
        
        # Enrichissement avec les données spécifiques au rôle
        if hasattr(profil, 'enseignant'):
            data['enseignant'] = EnseignantSerializer(profil.enseignant, context={'request': request}).data
        elif hasattr(profil, 'etudiant'):
            data['etudiant'] = EtudiantSerializer(profil.etudiant, context={'request': request}).data
            
        return Response(data, status=status.HTTP_200_OK)


class EnseignantViewSet(BaseViewSet):
    """
    Action supplémentaire :
      GET /api/enseignants/mon_planning/
      Retourne les séances de la semaine en cours pour l'enseignant connecté.
    """
    queryset = Enseignant.objects.select_related(
        'profil__user', 'departement__faculte'
    ).all()
    serializer_class   = EnseignantSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsChefDepartementOrReadOnly]

    def get_queryset(self):
        qs      = super().get_queryset()
        user    = self.request.user

        # Filtre pour Chef de Département
        if hasattr(user, 'profil') and hasattr(user.profil, 'enseignant'):
            enseignant = user.profil.enseignant
            departements_diriges = enseignant.departements_diriges.all()
            if departements_diriges.exists() and not (user.is_superuser or user.groups.filter(name='responsable').exists()):
                qs = qs.filter(departement__in=departements_diriges)

        dept_id = self.request.query_params.get('departement_id')
        if dept_id:
            qs = qs.filter(departement_id=dept_id)
        return qs

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated, ProfilActifPermission, IsEnseignant],
        url_path='mon_planning',
    )
    def mon_planning(self, request):
        """
        Retourne les séances de l'enseignant connecté.
        Paramètres optionnels : ?semaine=YYYY-MM-DD (lundi de la semaine)
                                ?semestre_id=<int>
        """
        enseignant = request.user.profil.enseignant
        seances    = Seance.objects.filter(
            enseignant=enseignant
        ).select_related(
            'module__matiere', 'classe__semestre', 'annee'
        ).order_by('date_seance', 'heure_debut')

        semestre_id = request.query_params.get('semestre_id')
        if semestre_id:
            seances = seances.filter(classe__semestre_id=semestre_id)

        # Filtre optionnel par semaine (lundi de la semaine au format YYYY-MM-DD)
        semaine = request.query_params.get('semaine')
        if semaine:
            try:
                from datetime import date, timedelta
                lundi = date.fromisoformat(semaine)
                # Recale sur le lundi au cas où la date donnée n'en est pas un
                lundi = lundi - timedelta(days=lundi.weekday())
                dimanche = lundi + timedelta(days=6)
                seances = seances.filter(date_seance__range=(lundi, dimanche))
            except ValueError:
                return Response(
                    {'detail': "Format de date invalide. Utilisez YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = SeanceSerializer(seances, many=True)
        return Response(serializer.data)


class EtudiantViewSet(BaseViewSet):
    """
    Action supplémentaire :
      GET /api/etudiants/mon_planning/
      Retourne les séances de la classe de l'étudiant connecté.
    """
    queryset = Etudiant.objects.select_related(
        'profil__user', 'parcours', 'filiere',
        'classe__semestre__annee',
    ).all()
    serializer_class   = EtudiantSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsChefDepartementOrReadOnly]

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), ProfilActifPermission(), IsChefDepartement()]
        return [IsAuthenticated(), ProfilActifPermission(), IsChefDepartementOrReadOnly()]

    def get_queryset(self):
        qs          = super().get_queryset()
        user        = self.request.user

        # Filtre pour Chef de Département
        if hasattr(user, 'profil') and hasattr(user.profil, 'enseignant'):
            enseignant = user.profil.enseignant
            departements_diriges = enseignant.departements_diriges.all()
            if departements_diriges.exists() and not (user.is_superuser or user.groups.filter(name='responsable').exists()):
                qs = qs.filter(classe__filiere__departement__in=departements_diriges)

        classe_id   = self.request.query_params.get('classe_id')
        filiere_id  = self.request.query_params.get('filiere_id')
        parcours_id = self.request.query_params.get('parcours_id')
        if classe_id:
            qs = qs.filter(classe_id=classe_id)
        if filiere_id:
            qs = qs.filter(filiere_id=filiere_id)
        if parcours_id:
            qs = qs.filter(parcours_id=parcours_id)
        return qs

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated, ProfilActifPermission, IsEtudiant],
        url_path='mon_planning',
    )
    def mon_planning(self, request):
        """
        Retourne les séances de la classe de l'étudiant connecté.
        Paramètres optionnels : ?semaine=YYYY-MM-DD
                                ?statut=Confirmée|Annulée|Reportée
        """
        from django.core.exceptions import ObjectDoesNotExist
        from rest_framework.exceptions import PermissionDenied

        try:
            etudiant = request.user.profil.etudiant
        except ObjectDoesNotExist:
            raise PermissionDenied("Cette ressource est réservée aux étudiants.")

        seances  = Seance.objects.filter(
            classe=etudiant.classe
        ).select_related(
            'module__matiere', 'enseignant__profil__user', 'annee'
        ).order_by('date_seance', 'heure_debut')

        statut = request.query_params.get('statut')
        if statut:
            seances = seances.filter(statut=statut)

        semaine = request.query_params.get('semaine')
        if semaine:
            try:
                from datetime import date, timedelta
                lundi    = date.fromisoformat(semaine)
                lundi    = lundi - timedelta(days=lundi.weekday())
                dimanche = lundi + timedelta(days=6)
                seances  = seances.filter(date_seance__range=(lundi, dimanche))
            except ValueError:
                return Response(
                    {'detail': "Format de date invalide. Utilisez YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = SeanceSerializer(seances, many=True)
        return Response(serializer.data)


# ──────────────────────────────────────────────────────────────────────────────
# 3. CONTENU PÉDAGOGIQUE
# ──────────────────────────────────────────────────────────────────────────────

class MatiereViewSet(BaseViewSet):
    queryset = Matiere.objects.select_related('departement__faculte').all()
    serializer_class   = MatiereSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsChefDepartementOrReadOnly]

    def get_queryset(self):
        qs      = super().get_queryset()
        dept_id = self.request.query_params.get('departement_id')
        if dept_id:
            qs = qs.filter(departement_id=dept_id)
        return qs


class ModuleViewSet(BaseViewSet):
    queryset = Module.objects.select_related(
        'matiere__departement', 'semestre__annee'
    ).all()
    serializer_class   = ModuleSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsChefDepartementOrReadOnly]

    def get_queryset(self):
        qs          = super().get_queryset()
        semestre_id = self.request.query_params.get('semestre_id')
        matiere_id  = self.request.query_params.get('matiere_id')
        if semestre_id:
            qs = qs.filter(semestre_id=semestre_id)
        if matiere_id:
            qs = qs.filter(matiere_id=matiere_id)
        return qs

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated, ProfilActifPermission, IsEnseignant],
        url_path='mes_modules',
    )
    def mes_modules(self, request):
        """
        Retourne les modules que l'enseignant connecté dispense (basé sur ses séances).
        """
        from rest_framework.exceptions import PermissionDenied
        if not hasattr(request.user.profil, 'enseignant'):
            raise PermissionDenied("Seuls les enseignants peuvent voir leurs modules.")
            
        enseignant = request.user.profil.enseignant
        modules = Module.objects.filter(seance__enseignant=enseignant).distinct()
        
        # On utilise le serializer de module
        serializer = self.get_serializer(modules, many=True)
        return Response(serializer.data)


# ──────────────────────────────────────────────────────────────────────────────
# 4. PLANIFICATION
# ──────────────────────────────────────────────────────────────────────────────

class SeanceViewSet(BaseViewSet):
    """
    Actions supplémentaires :
      PATCH /api/seances/{id}/reporter/
        Corps : { "date_report", "heure_debut_report", "heure_fin_report" }

      GET /api/seances/conflits/
        Liste toutes les séances en conflit (enseignant ou classe)
        pour le semestre actif.

      GET /api/seances/{id}/seances_liees/
        Retourne la séance jumelle (cours mutualisé) si elle existe.
    """
    queryset = Seance.objects.select_related(
        'module__matiere__departement',
        'enseignant__profil__user',
        'enseignant__departement',
        'classe__semestre__annee',
        'classe__filiere',
        'classe__parcours',
        'annee',
        'seance_liee',
    ).all()
    serializer_class   = SeanceSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsChefOrReferentOrReadOnly]

    def get_permissions(self):
        """
        Permissions d'écriture selon le rôle :
          - superuser / responsable : accès total
          - chef de département    : accès aux séances des filières de son dépt
          - référent de classe      : accès aux séances de ses classes assignées
        Les lectures (GET) restent libères pour tout utilisateur actif.
        """
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [IsAuthenticated(), ProfilActifPermission()]
        return [IsAuthenticated(), ProfilActifPermission(), IsChefOrReferentOrReadOnly()]

    def _get_classes_autorisees(self):
        """
        Retourne les IDs de classes sur lesquelles l'utilisateur a droit d'écriture.
        - responsable / superuser : toutes les classes
        - chef de département : classes dont la filière appartient à son département
        - référent de classe : ses classes assignées
        """
        user = self.request.user
        if user.is_superuser or user.groups.filter(name='responsable').exists():
            return None  # None = pas de filtre, accès total
        if not hasattr(user, 'profil') or not hasattr(user.profil, 'enseignant'):
            return []  # Aucun accès en écriture
        enseignant = user.profil.enseignant
        classes_ids = set()
        # Chef de département
        for dept in enseignant.departements_diriges.prefetch_related('filieres__classe_set'):
            for filiere in dept.filieres.all():
                classes_ids.update(filiere.classe_set.values_list('id', flat=True))
        # Référent de classe
        if hasattr(enseignant, 'referent_classes'):
            classes_ids.update(
                enseignant.referent_classes.classes.values_list('id', flat=True)
            )
        return classes_ids

    def perform_create(self, serializer):
        """Vérifie que la classe cible est dans le périmètre autorisé."""
        classes_autorisees = self._get_classes_autorisees()
        if classes_autorisees is not None:  # None = accès total
            classe = serializer.validated_data.get('classe')
            if classe and classe.id not in classes_autorisees:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(
                    "Vous n'avez pas les droits pour planifier des séances dans cette classe."
                )
        serializer.save()

    def perform_update(self, serializer):
        """Même vérification à la mise à jour."""
        classes_autorisees = self._get_classes_autorisees()
        if classes_autorisees is not None:
            classe = serializer.validated_data.get('classe', self.get_object().classe)
            if classe and classe.id not in classes_autorisees:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(
                    "Vous n'avez pas les droits pour modifier des séances dans cette classe."
                )
        serializer.save()

    def get_queryset(self):
        qs            = super().get_queryset()
        user          = self.request.user

        # Filtre pour Chef de Département
        if hasattr(user, 'profil') and hasattr(user.profil, 'enseignant'):
            enseignant = user.profil.enseignant
            departements_diriges = enseignant.departements_diriges.all()
            if departements_diriges.exists() and not (user.is_superuser or user.groups.filter(name='responsable').exists()):
                qs = qs.filter(classe__filiere__departement__in=departements_diriges)

        classe_id     = self.request.query_params.get('classe_id')
        enseignant_id = self.request.query_params.get('enseignant_id')
        semestre_id   = self.request.query_params.get('semestre_id')
        statut        = self.request.query_params.get('statut')
        type_seance   = self.request.query_params.get('type_seance')
        date_debut    = self.request.query_params.get('date_debut')
        date_fin      = self.request.query_params.get('date_fin')
        annee_id      = self.request.query_params.get('annee_id')

        if classe_id:
            qs = qs.filter(classe_id=classe_id)
        if enseignant_id:
            qs = qs.filter(enseignant_id=enseignant_id)
        if semestre_id:
            qs = qs.filter(classe__semestre_id=semestre_id)
        if statut:
            qs = qs.filter(statut=statut)
        if type_seance:
            qs = qs.filter(type_seance=type_seance)
        if date_debut:
            qs = qs.filter(date_seance__gte=date_debut)
        if date_fin:
            qs = qs.filter(date_seance__lte=date_fin)
        if annee_id:
            qs = qs.filter(annee_id=annee_id)

        return qs.order_by('date_seance', 'heure_debut')

    # ── Action : seances_liees ────────────────────────────────────────────

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[IsAuthenticated, ProfilActifPermission],
        url_path='seances_liees',
    )
    def seances_liees(self, request, pk=None):
        """
        Retourne la (ou les) séance(s) jumelle(s) d'un cours mutualisé.
        Si la séance n'est pas mutualisée, retourne une liste vide.
        """
        seance = self.get_object()
        liees  = []
        if seance.seance_liee:
            liees.append(seance.seance_liee)
        liees.extend(seance.seances_associees.all())
        serializer = SeanceSerializer(liees, many=True)
        return Response({'count': len(liees), 'results': serializer.data})

    # ── Action : reporter ────────────────────────────────────────────────────

    @action(
        detail=True,
        methods=['patch'],
        permission_classes=[IsAuthenticated, IsChefDepartement],
        url_path='reporter',
    )
    def reporter(self, request, pk=None):
        """
        Reporte une séance vers un nouveau créneau.
        Le statut passe automatiquement à 'Reportée'.
        Toutes les validations du modèle sont réappliquées sur le nouveau créneau.
        """
        seance     = self.get_object()
        serializer = SeanceReportSerializer(
            data=request.data,
            context={'seance': seance},
        )
        serializer.is_valid(raise_exception=True)
        seance_maj = serializer.save()
        return Response(
            SeanceSerializer(seance_maj).data,
            status=status.HTTP_200_OK,
        )

    # ── Action : conflits ────────────────────────────────────────────────────

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated, IsChefDepartement],
        url_path='conflits',
    )
    def conflits(self, request):
        """
        Détecte toutes les séances en conflit pour un semestre donné.
        Paramètre obligatoire : ?semestre_id=<int>

        Un conflit est détecté quand deux séances confirmées partagent
        le même créneau et le même enseignant OU la même classe.
        """
        semestre_id = request.query_params.get('semestre_id')
        if not semestre_id:
            return Response(
                {'detail': "Le paramètre 'semestre_id' est obligatoire."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        seances = Seance.objects.filter(
            classe__semestre_id=semestre_id,
            statut='Confirmée',
        ).select_related(
            'enseignant__profil__user',
            'classe__filiere',
            'module__matiere',
        ).order_by('date_seance', 'heure_debut')

        conflits_ids = set()

        for seance in seances:
            # Conflit enseignant
            conflit_ens = seances.filter(
                enseignant=seance.enseignant,
                date_seance=seance.date_seance,
                heure_debut__lt=seance.heure_fin,
                heure_fin__gt=seance.heure_debut,
            ).exclude(pk=seance.pk)

            # Conflit classe
            conflit_cls = seances.filter(
                classe=seance.classe,
                date_seance=seance.date_seance,
                heure_debut__lt=seance.heure_fin,
                heure_fin__gt=seance.heure_debut,
            ).exclude(pk=seance.pk)

            if conflit_ens.exists() or conflit_cls.exists():
                conflits_ids.add(seance.pk)

        seances_en_conflit = seances.filter(pk__in=conflits_ids)
        serializer = SeanceSerializer(seances_en_conflit, many=True)
        return Response(
            {
                'count':   len(conflits_ids),
                'results': serializer.data,
            }
        )


# ==========================================
# 6. DOCUMENTS PÉDAGOGIQUES
# ==========================================

class DocumentViewSet(BaseViewSet):
    """
    Gestion des documents pédagogiques.
    """
    queryset = DocumentPedagogique.objects.select_related('module', 'enseignant').all()
    serializer_class = DocumentPedagogiqueSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsDocumentOwnerOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        module_id = self.request.query_params.get('module_id')
        if module_id:
            qs = qs.filter(module_id=module_id)

        if user.is_superuser:
            return qs

        if not hasattr(user, 'profil'):
            return qs.none()

        # Filtrage selon le rôle
        if hasattr(user.profil, 'etudiant'):
            # L'étudiant voit les documents des modules liés à ses séances confirmées (ou juste les modules de son semestre/classe)
            # Simplification : modules des séances planifiées pour sa classe
            modules_ids = Seance.objects.filter(
                classe=user.profil.etudiant.classe,
                statut='confirmee'
            ).values_list('module_id', flat=True).distinct()
            qs = qs.filter(module_id__in=modules_ids)
            
        elif hasattr(user.profil, 'enseignant'):
            enseignant = user.profil.enseignant
            if not enseignant.departements_diriges.exists() and not (user.is_superuser or user.groups.filter(name='responsable').exists()):
                # Enseignant simple : on filtre pour ne lui montrer que ses propres documents (ou ceux de ses modules)
                # Mais il est souvent plus simple qu'il voit ses propres documents
                qs = qs.filter(enseignant=enseignant)

        return qs

    def perform_create(self, serializer):
        enseignant = self.request.user.profil.enseignant
        serializer.save(enseignant=enseignant)


# ──────────────────────────────────────────────────────────────────────────────
# VUE HTML D'ACCUEIL (optionnelle)
# ──────────────────────────────────────────────────────────────────────────────

def home_view(request):
    return render(request, 'index.html')