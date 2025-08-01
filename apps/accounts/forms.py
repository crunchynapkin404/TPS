from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from apps.teams.models import Team, TeamRole
from apps.accounts.models import Skill

User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    """Registration form for new TPS users"""
    
    # Required fields
    first_name = forms.CharField(
        max_length=150,
        label='Name',
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
            'placeholder': 'Enter your first name'
        })
    )
    
    last_name = forms.CharField(
        max_length=150,
        label='Surname',
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
            'placeholder': 'Enter your surname'
        })
    )
    
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
            'placeholder': 'Enter your email address'
        })
    )
    
    # Team selection
    team = forms.ModelChoiceField(
        queryset=Team.objects.filter(is_active=True),
        label='Team',
        empty_label="Select your team",
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm'
        })
    )
    
    # Skills selection (checkbox for Waakdienst and Incident)
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.filter(name__in=['Waakdienst', 'Incident'], is_active=True),
        label='Skills',
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
        }),
        help_text='Select your skills (required for orchestrator assignment)'
    )
    
    # Team Role selection (restricted to Operationeel and Tactisch)
    team_role = forms.ModelChoiceField(
        queryset=TeamRole.objects.filter(name__in=['operationeel', 'tactisch']),
        label='Team Role',
        empty_label="Select your team role",
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
                'placeholder': 'Choose a username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Style the password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
            'placeholder': 'Enter password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
            'placeholder': 'Confirm password'
        })
        
        # Make fields required
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        self.fields['team'].required = True
        self.fields['skills'].required = True
        self.fields['team_role'].required = True
    
    def save(self, commit=True):
        """Save user with role set to USER (Engineer) by default"""
        user = super().save(commit=False)
        user.role = 'USER'  # Always Engineer as specified
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            
            # Create team membership
            from apps.teams.models import TeamMembership
            TeamMembership.objects.create(
                user=user,
                team=self.cleaned_data['team'],
                role=self.cleaned_data['team_role'],
                is_primary_team=True
            )
            
            # Add selected skills to user
            for skill in self.cleaned_data['skills']:
                from apps.accounts.models import UserSkill
                UserSkill.objects.create(
                    user=user,
                    skill=skill,
                    proficiency_level='basic'  # Default level for new users
                )
            
        return user