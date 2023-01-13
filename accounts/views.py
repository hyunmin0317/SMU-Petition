from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect

def signup(request):
    return render(request, 'accounts/signup.html')from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from accounts.forms import UserForm


def signup(request):
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_vaild():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('index')
        else:
            form = UserForm()
    return render(request, 'accounts/signup.html')