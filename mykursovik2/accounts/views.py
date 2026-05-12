from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from mainapp.forms import CustomUserCreationForm, CustomAuthenticationForm



# Регистрация пользователя
def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Например, сделаем пользователя неактивным сразу
            user.save()
            # После регистрации, перенаправляем на страницу ожидания активации
            return render(request, 'accounts/registration_pending.html')  # Страница ожидания активации
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

# Логин пользователя
def login_view(request):
    if request.method == "POST":
        form = CustomAuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('orders_list')  # Исправляем на правильный маршрут
    else:
        form = CustomAuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

# Логаут пользователя
def logout_view(request):
    logout(request)
    return render(request, 'accounts/logout.html')  # Отображаем страницу выхода

# Страница ошибки CSRF
def csrf_failure(request, reason=""):
    return render(request, "accounts/csrf_failure.html", {"reason": reason})
