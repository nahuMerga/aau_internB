from django.shortcuts import render

def some_view(request):
    return render(request, 'telegram_bot/some_template.html')
