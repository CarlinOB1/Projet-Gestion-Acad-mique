# forms.py
from django import forms
from django.forms import DateInput
from .models import Semestre, AnneeAcademique, Seance


class DatePickerInput(DateInput):
    """Widget calendrier natif HTML5."""
    input_type = 'date'


class AnneeAcademiqueAdminForm(forms.ModelForm):
    """Formulaire avec widget calendrier pour AnneeAcademique."""
    class Meta:
        model = AnneeAcademique
        fields = '__all__'
        widgets = {
            'date_debut': DatePickerInput(),
            'date_fin': DatePickerInput(),
        }


class SemestreAdminForm(forms.ModelForm):
    """
    Formulaire avec widget calendrier et avertissement
    non bloquant sur la durée du semestre.
    """
    confirmer_duree = forms.BooleanField(
        required=False,
        label="Je confirme que la durée du semestre est correcte",
        initial=False,
    )

    class Meta:
        model = Semestre
        fields = '__all__'
        widgets = {
            'date_debut': DatePickerInput(),
            'date_fin': DatePickerInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        confirmer_duree = cleaned_data.get('confirmer_duree')

        if date_debut and date_fin:
            mois_difference = (date_fin.year - date_debut.year) * 12 + \
                              (date_fin.month - date_debut.month)

            if mois_difference < 4 and not confirmer_duree:
                self.add_error(
                    'confirmer_duree',
                    forms.ValidationError(
                        f"⚠️ Attention : ce semestre dure seulement "
                        f"{mois_difference} mois. "
                        f"La durée recommandée est d'au moins 4 mois. "
                        f"Cochez la case ci-dessous pour confirmer."
                    )
                )
        return cleaned_data


class SeanceAdminForm(forms.ModelForm):
    """
    Formulaire avec avertissement non bloquant pour les séances
    planifiées un samedi.
    """
    confirmer_samedi = forms.BooleanField(
        required=False,
        label="Je confirme que cette séance est bien planifiée un samedi",
        initial=False,
    )

    class Meta:
        model = Seance
        fields = '__all__'
        widgets = {
            'date_seance': DatePickerInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        date_seance = cleaned_data.get('date_seance')
        confirmer_samedi = cleaned_data.get('confirmer_samedi')

        if date_seance:
            # Samedi = weekday() == 5
            if date_seance.weekday() == 5 and not confirmer_samedi:
                self.add_error(
                    'confirmer_samedi',
                    forms.ValidationError(
                        "⚠️ Attention : cette séance est planifiée un samedi. "
                        "Cochez la case ci-dessous pour confirmer."
                    )
                )
        return cleaned_data