from django.contrib import messages
from django.contrib.auth import login as auth_login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404

from accounts.ecampus import ecampus, information
from accounts.forms import UserForm
from accounts.models import Year, Department, Profile, LoginHistory
from config.settings import DEPT_DIC
from petitions.models import Petition


def agree(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        if User.objects.filter(username=username).exists():     # 학번 중복 검사
            messages.error(request, '⚠️ 이미 가입된 학번입니다.')
            return redirect('accounts:agree')

        context = information(ecampus(username, password))
        if context:
            name = context['department']
            if name in DEPT_DIC.keys():
                name = DEPT_DIC[name]
            if Year.objects.filter(year=username[:4]) and Department.objects.filter(name=name):
                context['id'], context['dept'] = username, name
                request.session['context'] = context
                return redirect('accounts:register')

            messages.error(request, '⚠️ 서비스에서 지원하지 않는 학과와 학번 입니다.')
            return redirect('accounts:agree')
        messages.error(request, '⚠️ 샘물 포털 ID/PW를 다시 확인하세요! (Caps Lock 확인)')
        return redirect('accounts:agree')
    departments = Department.objects.filter(url__isnull=False)
    dept_num = departments.count()
    return render(request, 'accounts/agree.html', {'departments': departments, 'dept_num': dept_num})


def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            auth_login(request, user)
            LoginHistory.objects.create(user=user)
            return redirect('petitions:petition_list')
        if User.objects.filter(username=username):
            messages.error(request, '⚠️ 비밀번호를 확인하세요.')
        else:
            messages.error(request, '⚠️ 가입되지 않은 학번입니다.')
        redirect('accounts:login')
    return render(request, 'accounts/login.html')


def register(request):
    context = request.session.get('context')

    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            year = Year.objects.filter(year=context['id'][:4]).first()
            department = Department.objects.filter(name=context['dept']).first()
            if year and department:  # 지원하는 학과와 학번인지 확인
                form.save()
                username = form.cleaned_data.get('username')
                raw_password = form.cleaned_data.get('password1')
                user = authenticate(username=username, password=raw_password)
                Profile.objects.create(user=user, year=year, department=department, name=context['name'])
                auth_login(request, user)  # 로그인
                LoginHistory.objects.create(user=user)
                return redirect('petitions:petition_list')
            messages.error(request, '⚠️ 서비스에서 지원하지 않는 학과와 학번 입니다.')
            return redirect('accounts:agree')
        messages.error(request, form.errors['password2'][0])
        return redirect('accounts:register')
    form = UserForm()
    context['form'] = form
    return render(request, 'accounts/register.html', context)


@login_required
def change_pw(request):
    if request.method == "POST":
        user = request.user
        if not user.is_authenticated:
            user = get_object_or_404(User, username=request.POST["id"])
        if request.POST["password1"] == request.POST["password2"]:
            user.set_password(request.POST["password1"])
            user.save()
            messages.error(request, '비밀번호가 변경되었습니다.')
        else:
            messages.error("⚠️ 비밀번호가 일치하지 않습니다.")
    return redirect('home')


@login_required
def update(request):
    if request.method == "POST":
        password = request.POST["password"]
        context = information(ecampus(request.user.username, password))
        if context:
            name = context['department']
            if name in DEPT_DIC.keys():
                name = DEPT_DIC[name]
            department = Department.objects.filter(name=name)
            if department:
                Profile.objects.filter(user=request.user).update(name=context['name'], department=department.first())
                messages.error(request, '회원 정보가 업데이트 되었습니다.')
                return redirect('petitions:petition_list')
            messages.error(request, '⚠️ 서비스에서 지원하지 않는 학과와 학번 입니다.')
        messages.error(request, '⚠️ 샘물 포털 ID/PW를 다시 확인하세요! (Caps Lock 확인)')
    return redirect('accounts:mypage')


def find_pw(request):
    if request.method == "POST":
        # ecampus 존재하면
        username = request.POST["id"]
        password = request.POST["password1"]
        if not User.objects.filter(username=username):
            messages.error(request, '⚠️ 가입되지 않은 학번입니다.')
            return redirect('accounts:login')
        context = information(ecampus(username, password))
        if context:
            return render(request, 'accounts/changePW.html', {'username': username})
    messages.error(request, '⚠️ 샘물 포털 ID/PW를 다시 확인하세요! (Caps Lock 확인)')
    return redirect('accounts:login')


@login_required
def change_dept(request, pk):
    profile = get_object_or_404(Profile, user=request.user)
    dept_dic = [7, 8, 9]
    if pk in dept_dic and profile.department.pk in dept_dic:
        department = get_object_or_404(Department, pk=pk)
        profile.department = department
        profile.save()
        messages.error(request, '전공이 변경되었습니다.')
        return redirect('petitions:petition_list')
    messages.error(request, '⚠️ 변경 권한이 없습니다!')
    return redirect('home')


@login_required
def mypage(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    page = request.GET.get('page', '1')
    petition_list = Petition.objects.filter(author=user).annotate(voter_count=Count('voter')).order_by('-create_date')
    paginator = Paginator(petition_list, 4)
    page_obj = paginator.get_page(page)
    return render(request, 'accounts/mypage.html', {'user': user, 'profile': profile, 'petition_list': page_obj})


@login_required
def member_del(request):
    if request.method == "POST":
        pw_del = request.POST["pw_del"]
        user = request.user
        if check_password(pw_del, user.password):
            user.delete()
            messages.error(request, '회원 탈퇴 되었습니다.')
            return redirect('home')
    messages.error(request, '⚠️ 비밀번호가 일치하지 않습니다.')
    return redirect('accounts:mypage')
