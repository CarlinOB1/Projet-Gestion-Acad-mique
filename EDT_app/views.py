# views.py
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
    Matiere, Module, Seance,
)
from EDT_app.serializers import (
    FaculteSerializer, DepartementSerializer, FiliereSerializer,
    ParcoursSerializer, AnneeAcademiqueSerializer, SemestreSerializer,
    ClasseSerializer, ProfilSerializer, EnseignantSerializer,
    EtudiantSerializer, MatiereSerializer, ModuleSerializer,
    SeanceSerializer, SeanceReportSerializer, ProfilSuspensionSerializer,
)
from .permissions import (
    ProfilActifPermission,
    IsResponsable,
    IsResponsableOrReadOnly,
    IsEnseignant,
    IsEtudiant,
    IsOwnerOrResponsable,
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
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsResponsableOrReadOnly]


class DepartementViewSet(BaseViewSet):
    queryset           = Departement.objects.select_related('faculte').all()
    serializer_class   = DepartementSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsResponsableOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        faculte_id = self.request.query_params.get('faculte_id')
        if faculte_id:
            qs = qs.filter(faculte_id=faculte_id)
        return qs


class FiliereViewSet(BaseViewSet):
    queryset           = Filiere.objects.select_related('departement__faculte').all()
    serializer_class   = FiliereSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsResponsableOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        dept_id = self.request.query_params.get('departement_id')
        if dept_id:
            qs = qs.filter(departement_id=dept_id)
        return qs


class ParcoursViewSet(BaseViewSet):
    queryset           = Parcours.objects.all()
    serializer_class   = ParcoursSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsResponsableOrReadOnly]


class AnneeAcademiqueViewSet(BaseViewSet):
    """
    Action supplémentaire : POST /api/annees/{id}/archiver/
    Tente d'archiver l'année — bloqué si séances confirmées dans le futur.
    """
    queryset           = AnneeAcademique.objects.all()
    serializer_class   = AnneeAcademiqueSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsResponsableOrReadOnly]

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsResponsable])
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
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsResponsableOrReadOnly]

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
    ).all()
    serializer_class   = ClasseSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsResponsableOrReadOnly]

    def get_queryset(self):
        qs          = super().get_queryset()
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

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsResponsable])
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
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsOwnerOrResponsable]

    def get_permissions(self):
        """
        - list et create : responsable uniquement
        - retrieve       : propriétaire ou responsable
        - update/destroy : responsable uniquement
        """
        if self.action in ('list', 'create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), ProfilActifPermission(), IsResponsable()]
        return [IsAuthenticated(), ProfilActifPermission(), IsOwnerOrResponsable()]

    @action(
        detail=True,
        methods=['patch'],
        permission_classes=[IsAuthenticated, IsResponsable],
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
            ProfilSerializer(profil_maj).data,
            status=status.HTTP_200_OK,
        )


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
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsResponsableOrReadOnly]

    def get_queryset(self):
        qs      = super().get_queryset()
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
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsResponsableOrReadOnly]

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), ProfilActifPermission(), IsResponsable()]
        return [IsAuthenticated(), ProfilActifPermission(), IsResponsableOrReadOnly()]

    def get_queryset(self):
        qs          = super().get_queryset()
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
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsResponsableOrReadOnly]

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
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsResponsableOrReadOnly]

    def get_queryset(self):
        qs          = super().get_queryset()
        semestre_id = self.request.query_params.get('semestre_id')
        matiere_id  = self.request.query_params.get('matiere_id')
        if semestre_id:
            qs = qs.filter(semestre_id=semestre_id)
        if matiere_id:
            qs = qs.filter(matiere_id=matiere_id)
        return qs


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
    """
    queryset = Seance.objects.select_related(
        'module__matiere__departement',
        'enseignant__profil__user',
        'enseignant__departement',
        'classe__semestre__annee',
        'classe__filiere',
        'classe__parcours',
        'annee',
    ).all()
    serializer_class   = SeanceSerializer
    permission_classes = [IsAuthenticated, ProfilActifPermission, IsResponsableOrReadOnly]

    def get_queryset(self):
        qs            = super().get_queryset()
        classe_id     = self.request.query_params.get('classe_id')
        enseignant_id = self.request.query_params.get('enseignant_id')
        semestre_id   = self.request.query_params.get('semestre_id')
        statut        = self.request.query_params.get('statut')
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
        if date_debut:
            qs = qs.filter(date_seance__gte=date_debut)
        if date_fin:
            qs = qs.filter(date_seance__lte=date_fin)
        if annee_id:
            qs = qs.filter(annee_id=annee_id)

        return qs.order_by('date_seance', 'heure_debut')

    # ── Action : reporter ────────────────────────────────────────────────────

    @action(
        detail=True,
        methods=['patch'],
        permission_classes=[IsAuthenticated, IsResponsable],
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
        permission_classes=[IsAuthenticated, IsResponsable],
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


# ──────────────────────────────────────────────────────────────────────────────
# VUE HTML D'ACCUEIL (optionnelle)
# ──────────────────────────────────────────────────────────────────────────────

def home_view(request):
    return render(request, 'index.html')