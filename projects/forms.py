from django import forms
from pytas.http import TASClient
from django.core.urlresolvers import reverse_lazy
from django.utils.functional import lazy
from models import ProjectExtras
import bibtexparser
import logging

logger = logging.getLogger('projects')

RESEARCH = 0
STARTUP = 2
PROJECT_TYPES = (
    ('', 'Choose One'),
    (RESEARCH, 'Research'),
    (STARTUP, 'Startup'),
)


def get_fields_choices():
    choices = (('', 'Choose One'),)
    tas = TASClient()
    fields = tas.fields()
    for f in fields:
        choices = choices + ((f['id'], f['name']),)
        if f['children']:
            for c in f['children']:
                choices = choices + ((c['id'], '--- ' + c['name']),)
                if c['children']:
                    for g in c['children']:
                        choices = choices + ((g['id'], '--- --- ' + g['name']),)
    return choices


def get_accept_project_terms_help_text():
    user_terms_url = reverse_lazy('tc_view_specific_version_page',
                                    args=['user-terms', '1.00'])
    project_terms_url = reverse_lazy('tc_view_specific_version_page',
                                    args=['project-terms', '1.00'])
    text = 'Please review the Chameleon <a href="%s">User Terms of Use</a> and ' \
           '<a href="%s">Project Lead Terms of Use</a>.' % \
           (user_terms_url, project_terms_url)
    return text

get_accept_project_terms_help_text_lazy = lazy(get_accept_project_terms_help_text, str)


class ProjectCreateForm( forms.Form ):
    title = forms.CharField(
        label='Title',
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Research into how...'}),
    )
    nickname = forms.CharField(
        label='Project Nickname',
        max_length='50',
        help_text='Provide a nickname to identify your project across the Chameleon Infrastructure',
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Project Nickname'}),
    )
    description = forms.CharField(
        label='Abstract (~200 words)',
        help_text='An application for a project has to include a description of the '
                  'research or education project to be performed using the testbed and '
                  'the type of resources needed. It should address the following '
                  'questions: What are the research challenges or educational objectives '
                  'of the project? How are they relevant to cloud computing research? '
                  'Why are they important? What types of experiments or educational '
                  'activities will be carried out? Please, make sure that the abstract '
                  'is self-contained; eventually it may be published on the Chameleon '
                  'website.',
        required=True,
        widget=forms.Textarea(attrs={'placeholder': 'We propose to...'}),
    )
    supplemental_details = forms.CharField(
        label='Resource Justification',
        help_text='Provide supplemental detail on how you intend to use Chameleon to '
                  'accomplish your research goals. This text will not be publicly '
                  'viewable and may include details that you do not wish to publish.',
        required=True,
        widget=forms.Textarea(attrs={'placeholder': 'Resource Justification'}),
    )
    funding_source = forms.CharField(
        label='Source(s) of funding',
        help_text='If the proposed research is related to a funded grant or has pending '
                  'support, please include funding agency name(s) and grant name(s).',
        required=False,
        widget=forms.Textarea()
    )
    fieldId = forms.ChoiceField(
        label='Field of Science',
        choices=(),
        initial='3',
        help_text='Please indicate a primary field of science for this research.',
    )
    accept_project_terms = forms.BooleanField(
        label='I agree to abide by Chameleon Acceptable Use Policies.',
        help_text=get_accept_project_terms_help_text_lazy(),
    )

    def __init__(self, *args, **kwargs):
        super(ProjectCreateForm, self).__init__(*args, **kwargs)
        self.fields['fieldId'].choices = get_fields_choices()

class EditNicknameForm(forms.Form):
    nickname = forms.CharField(
        label='',
        max_length='50',
        help_text='',
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Project Nickname'}),
    )

    def is_valid(self):
        valid = super(EditNicknameForm, self).is_valid()
        if not valid:
            return valid
        self.cleaned_data['nickname'] = self.cleaned_data['nickname'].strip()
        if not self.cleaned_data['nickname']:
            return False

        is_duplicate = ProjectExtras.objects.filter(nickname=self.cleaned_data['nickname']).count() > 0
        if is_duplicate:
            return False

        return True

class AllocationCreateForm(forms.Form):
    description = forms.CharField(
        label='Abstract (~200 words)',
        help_text='An application for a project has to include a description of the '
                  'research or education project to be performed using the testbed and '
                  'the type of resources needed. It should address the following '
                  'questions: What are the research challenges or educational objectives '
                  'of the project? How are they relevant to cloud computing research? '
                  'Why are they important? What types of experiments or educational '
                  'activities will be carried out? Please, make sure that the abstract '
                  'is self-contained; eventually it may be published on the Chameleon '
                  'website.',
        required=True,
        widget=forms.Textarea(attrs={'placeholder': 'We propose to...'}),
    )
    supplemental_details = forms.CharField(
        label='Resource Justification',
        help_text='Please provide an update on the use of your current allocation - any '
                  'success stories, publications, presentations, or just a general '
                  'update on the progress of your research on Chameleon. This is helpful '
                  'for us as we communicate with NSF regarding the value Chameleon is '
                  'bringing to the research community.',
        required=True,
        widget=forms.Textarea(),
    )
    funding_source = forms.CharField(
        label='Source(s) of funding',
        help_text='If the proposed research is related to a funded grant or has pending '
                  'support, please include funding agency name(s) and grant name(s).',
        required=False,
        widget=forms.Textarea()
    )
    accept_project_terms = forms.BooleanField(
        label='I agree to abide by Chameleon Acceptable Use Policies',
        help_text=get_accept_project_terms_help_text_lazy(),
    )

class ProjectAddUserForm(forms.Form):
    username = forms.CharField(
        label='Add a User to Project',
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Username of User'}),
    )

class AddBibtexPublicationForm(forms.Form):

    project_id = forms.CharField(widget=forms.HiddenInput())

    bibtex_string = forms.CharField(
        label='Publication(s) in BibTeX format',
        help_text='Please enter journal articles/publication in BibTex Format.',
        required=True,
        widget=forms.Textarea(attrs={'placeholder': '@article{...'}),
    )

    def is_valid(self):
        valid = super(AddBibtexPublicationForm, self).is_valid()
        if not valid:
            return valid
        bib_database = bibtexparser.loads(self.cleaned_data['bibtex_string'])
        logger.info(bib_database.entries)

        for entry in bib_database.entries:
            logger.info('entry valid?' + str((('journal' in entry or 'publisher' in entry or 'booktitle' in entry))))
            if not ('journal' in entry or 'publisher' in entry or 'booktitle' in entry) \
                or not 'title' in entry or not 'year' in entry or not 'author' in entry:
                self.add_error('bibtex_string', 'Missing one of required fields ' \
                    + '"publication/journal/booktitle, title, year, author} in BibTeX entry"')
                logger.info('returning False, conditions met')
                return False;
        return True
