from django import forms
from petitions.models import Petition, Comment, Answer


class PetitionForm(forms.ModelForm):
    class Meta:
        model = Petition
        fields = ['subject', 'content', 'category', 'anonymous']


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['content']
