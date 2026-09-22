# EDT_app/fichiers.py
#
# Règles communes aux fichiers téléversés (documents pédagogiques, photos) :
#   - valider_fichier_televerse : extension autorisée, taille maximale, et
#     signature réelle du contenu (pas seulement le nom que le client déclare) ;
#   - chemin_televerse : range chaque fichier sous un dossier au nom aléatoire,
#     pour que l'adresse d'un fichier ne puisse pas être devinée.
#
# Utilisé à la fois par le validateur du modèle (models.validate_extension_fichier)
# et par le serializer : une seule règle, jamais deux copies qui divergent.
import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone
from django.utils.text import get_valid_filename

TAILLE_MAX_PAR_DEFAUT = 20 * 1024 * 1024  # 20 Mo

_ZIP = (b'PK\x03\x04',)                           # docx, xlsx, pptx
_OLE = (b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',)     # doc, xls, ppt (anciens formats)

# Extension -> débuts de fichier acceptés. None = fichier texte (voir plus bas).
SIGNATURES = {
    '.pdf':  (b'%PDF-',),
    '.docx': _ZIP, '.xlsx': _ZIP, '.pptx': _ZIP,
    '.doc':  _OLE, '.xls':  _OLE, '.ppt':  _OLE,
    '.txt':  None,
}
EXTENSIONS_AUTORISEES = frozenset(SIGNATURES)

_TAILLE_ENTETE = 8192


def taille_maximale():
    return getattr(settings, 'DOCUMENT_MAX_UPLOAD_BYTES', TAILLE_MAX_PAR_DEFAUT)


def valider_fichier_televerse(fichier):
    ext = os.path.splitext(fichier.name)[1].lower()
    if ext not in EXTENSIONS_AUTORISEES:
        raise ValidationError(
            f"Les fichiers de type '{ext}' ne sont pas autorisés. "
            "Formats acceptés : PDF, DOC, XLS, PPT, TXT."
        )

    # Un fichier déjà enregistré (revalidation d'une ligne existante) n'est plus
    # relu : seul un envoi en cours porte un contenu à contrôler.
    if not isinstance(fichier, UploadedFile):
        return

    maximum = taille_maximale()
    if fichier.size > maximum:
        raise ValidationError(
            f"Le fichier dépasse la taille maximale autorisée ({maximum // (1024 * 1024)} Mo)."
        )

    fichier.seek(0)
    debut = fichier.read(_TAILLE_ENTETE)
    fichier.seek(0)

    signatures = SIGNATURES[ext]
    if signatures is None:
        # Texte : un octet nul ne se trouve jamais dans un texte normal, mais
        # toujours dans un exécutable ou un binaire déguisé.
        conforme = b'\x00' not in debut
    else:
        conforme = debut.startswith(signatures)
    if not conforme:
        raise ValidationError(
            f"Le contenu du fichier ne correspond pas à son extension '{ext}'."
        )


def chemin_televerse(dossier, nom_fichier):
    """
    `dossier` peut contenir des marques strftime (ex. 'documents/%Y/%m').
    Résultat : <dossier>/<32 caractères aléatoires>/<nom d'origine assaini>.
    Le nom d'origine est conservé pour l'affichage et le téléchargement.
    """
    dossier = timezone.now().strftime(dossier)
    nom = get_valid_filename(os.path.basename(nom_fichier))
    return f'{dossier}/{uuid.uuid4().hex}/{nom}'
