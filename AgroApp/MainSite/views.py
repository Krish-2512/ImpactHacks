from django.shortcuts import render
from .forms import UserRegistrationForm
from django.shortcuts import get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.db import IntegrityError
# Create your views here.
def index(request):
    return render(request,'site.html')


def register(request):

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password1'])
                user.save()
                login(request, user)
                return redirect('profile')
            except IntegrityError:
                form.add_error('email', 'Use with this email Id already exists.')

    else:
        form = UserRegistrationForm()
    
    return render(request, 'register.html', {'form': form})    


@login_required
def profile(request):
    return render(request, 'profile.html')    

@login_required
def dashboard(request):
    return render(request, 'dashboard/dashboard.html')

@login_required
def product(request):
    return render(request, 'dashboard/product.html')

@login_required
def city(request):
    return render(request, 'dashboard/city.html')

@login_required
def sales(request):
    return render(request, 'dashboard/sales.html')

@login_required
def weather(request):
    return render(request, 'dashboard/weather.html')

@login_required
def notification(request):
    return render(request, 'dashboard/notification.html')    