from django import forms 
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CustomUser,Product 




class UserRegistrationForm(UserCreationForm):
    username=forms.CharField(
       
        label="Username",
        # help_text="Must be at least 8 characters long and contain a mix of letters and numbers."
            help_text=""  # Removing help text
    )
    email=forms.EmailField()
     
    password1 = forms.CharField(
        widget=forms.PasswordInput,
        label="Password",
        # help_text="Must be at least 8 characters long and contain a mix of letters and numbers."
            help_text=""  # Removing help text
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirm Password",
 
        help_text="" 
    )

    class Meta:
        model = CustomUser
        fields=('username','email','phone','location','password1','password2')

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'quantity']