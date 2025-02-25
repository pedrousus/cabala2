from django.shortcuts import render, redirect
from .models import CustomUser  # Importa tu modelo personalizado
from django.contrib.auth import login
from django.db import IntegrityError
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import Translation
from django.contrib.auth.models import User
from google.cloud import translate_v2 as translate
from django.utils import timezone
from datetime import timedelta
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in

import os
from dotenv import load_dotenv
load_dotenv()

def send_verification_email(user, request):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    verification_url = f"{request.scheme}://{request.get_host()}/verify-email/{uid}/{token}/"
    
    subject = 'Verifica tu correo electrónico'
    message = render_to_string('verification_email.html', {
        'user': user,
        'verification_url': verification_url,
    })
    
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

def singup(request):
    if request.method == 'GET':
        return render(request, 'registro.html', {
            'form': UserCreationForm()
        })
    else:
        if request.POST['password1'] == request.POST['password2']:
            try:
                # Usa CustomUser en lugar de User
                user = CustomUser.objects.create_user(
                    username=request.POST['username'],
                    email=request.POST['email'],
                    password=request.POST['password1'],
                    is_active=False  # El usuario no estará activo hasta que verifique su correo
                )
                user.save()
                
                # Enviar correo de verificación
                send_verification_email(user, request)
                
                # No inicies sesión automáticamente, espera a que el usuario verifique su correo
                return render(request, 'registro.html', {
                    'form': UserCreationForm(),
                    'success': 'Por favor, verifica tu correo electrónico para activar tu cuenta.'
                })
            except IntegrityError:
                return render(request, 'registro.html', {
                    'form': UserCreationForm(),
                    'error': 'El nombre de usuario ya está en uso.'
                })
                
        return render(request, 'registro.html', {
            'form': UserCreationForm(),
            'error': 'Las contraseñas no coinciden.'
        })

def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)  # Usa CustomUser en lugar de User
        
        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            login(request, user)
            return redirect('inicio')
        else:
            return render(request, 'verification_failed.html')
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        return render(request, 'verification_failed.html')

def home(request):
    return render(request, 'home.html') 


def inicio(request):
    if request.method == 'GET' :
        return render(request, 'inicio.html',{
        'form': AuthenticationForm()
        })
    else:
        user = authenticate(request, username=request.POST['username'], password=request.POST['password']) 
        if user is None:
            return render(request, 'inicio.html',{
            'form': AuthenticationForm,
            'error': 'Username and password did not match'
            })
        else:
            login(request, user)
            return redirect('traductor')
        
@login_required
def salir(request):
        logout(request)
        return redirect('home')
    
    
# Diccionario del alfabeto hebreo con valores numerológicos
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "traslate/traslate-451505-3dd398cbea06.json"

def translate_to_hebrew(text):
    """
    Traduce el texto al hebreo usando la API de Google Translate.
    """
    if not text:
        return text
    else:
        try:
            translate_client = translate.Client()
            result = translate_client.translate(text, target_language="he")
            return result["translatedText"]
        except Exception as e:
            print(f"Error al traducir: {e}")
            return text

def calculate_cabala(hebrew_text):
    """
    Calcula el valor numérico de la frase en hebreo según la Cábala.
    Optimizado para textos largos.
    """
    CABA_LISTIC_VALUES = {
        "א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7,
        "ח": 8, "ט": 9, "י": 10, "כ": 20, "ך": 20, "ל": 30, "מ": 40, "ם": 40,
        "נ": 50, "ן": 50, "ס": 60, "ע": 70, "פ": 80, "ף": 80, "צ": 90, "ץ": 90,
        "ק": 100, "ר": 200, "ש": 300, "ת": 400
    }

    # Convertir el diccionario en un set para verificación rápida de caracteres válidos
    valid_chars = set(CABA_LISTIC_VALUES.keys())

    # Filtrar solo los caracteres válidos y sumar sus valores
    return sum(CABA_LISTIC_VALUES[char] for char in hebrew_text if char in valid_chars)

@login_required
def traductor(request):
    hebrew_translation = ""
    cabala_translation = ""
    phrase = ""  # Inicializar la variable para el texto original
    previous_translations = Translation.objects.filter(user=request.user).order_by('-created_at')
    
    # Crear un conjunto para almacenar palabras ya consultadas
    seen_texts = set()
    unique_translations = []

    # Filtrar duplicados en la lista de consultas anteriores
    for translation in previous_translations:
        if translation.original_text not in seen_texts:
            unique_translations.append(translation)
            seen_texts.add(translation.original_text)

    if request.method == "GET":
        return render(request, 'tradu.html', {
            'hebrew_translation': hebrew_translation,
            'cabala_translation': cabala_translation,
            'phrase': phrase,  # Pasar el texto original al template
            'previous_translations': unique_translations,
            'show_as_cards': True
        })
    else:
        if request.method == "POST":
            try:
                phrase = request.POST.get("phrase", "").strip()
                if phrase:
                    # Verificar si la palabra ya existe en la base de datos
                    existing_translation = Translation.objects.filter(
                        user=request.user,
                        original_text=phrase
                    ).first()

                    if existing_translation:
                        # Si ya existe, usar los datos de la consulta anterior
                        hebrew_translation = existing_translation.hebrew_text
                        cabala_translation = existing_translation.cabala_value
                    else:
                        # Si no existe, traducir y guardar en la base de datos
                        hebrew_translation = translate_to_hebrew(phrase)
                        cabala_translation = calculate_cabala(hebrew_translation)
                        
                        Translation.objects.create(
                            user=request.user,
                            original_text=phrase,
                            hebrew_text=hebrew_translation,
                            cabala_value=cabala_translation
                        )
            except Exception as e:
                print(f"Error al traducir: {e}")
                
        return render(request, 'tradu.html', {
            'hebrew_translation': hebrew_translation,
            'cabala_translation': cabala_translation,
            'phrase': phrase,  # Pasar el texto original al template
            'previous_translations': unique_translations,
            'show_as_cards': True
        })
        

def eliminar_traducciones_antiguas(user):
    """
    Elimina las traducciones del usuario que tengan más de 3 días de antigüedad.
    """
    # Calcular la fecha límite (hace 3 días)
    fecha_limite = timezone.now() - timedelta(days=3)
    
    # Filtrar y eliminar traducciones antiguas
    Translation.objects.filter(user=user, created_at__lt=fecha_limite).delete()

@receiver(user_logged_in)
def eliminar_traducciones_al_iniciar_sesion(sender, request, user, **kwargs):
    """
    Elimina las traducciones antiguas del usuario cuando inicia sesión.
    """
    eliminar_traducciones_antiguas(user)