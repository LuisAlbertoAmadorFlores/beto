from pdf2image import convert_from_path
import pytesseract
import cv2
import numpy as np
from PIL import Image


# --- TUS RUTAS (NO LAS CAMBIES SI YA FUNCIONAN) ---
poppler_path = r"C:\poppler-25.12.0\Library\bin" # <--- Pon tu ruta real aquí
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def limpiar_imagen(imagen_pil):
    # 1. Convertir de formato PIL a OpenCV (numpy)
    img = np.array(imagen_pil) 
    
    # 2. Convertir a Escala de Grises (elimina colores)
    gris = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    # 3. Aplicar Binarización (Umbral)
    # Esto convierte todo lo que no es letra oscura en blanco absoluto.
    # Ayuda mucho a quitar los dibujos de fondo de las INE/Cedulas.
    _, imagen_binaria = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    
    return imagen_binaria

try:
    print("--- Iniciando escaneo de alta resolución ---")
    
    # PASO CLAVE 1: Aumentar DPI a 300
    paginas = convert_from_path('identificacion.pdf', poppler_path=poppler_path, dpi=300)

    for i, pagina in enumerate(paginas):
        # PASO CLAVE 2: Limpiar la imagen antes de leer
        img_procesada = limpiar_imagen(pagina)

        # Opcional: Guardar la imagen procesada para que veas cómo la "ve" la computadora
        cv2.imwrite(f'debug_pagina_{i}.png', img_procesada)

        # PASO CLAVE 3: Configurar Tesseract
        # --psm 6: Asume un bloque de texto uniforme (funciona bien para listas de datos)
        texto = pytesseract.image_to_string(img_procesada, lang='spa', config='--psm 6')
        
        print(f"--- RESULTADO PÁGINA {i + 1} ---")
        print(texto)

except Exception as e:
    print(f"Error crítico: {e}")
    
def limpiar_imagen(imagen_pil):
    # 1. Convertir a escala de grises
    img = np.array(imagen_pil)
    gris = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    # 2. Aumentar el contraste (Ecualización de histograma)
    # Esto hace que el texto negro sea más negro y el fondo más claro
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gris_contraste = clahe.apply(gris)

    # 3. Aplicar umbral adaptativo (Mejor que Otsu para fondos complejos)
    # Se adapta a la iluminación de cada zona de la credencial
    binaria = cv2.adaptiveThreshold(
        gris_contraste, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )

    # 4. Eliminación de ruido (Morfología)
    # "Erosionamos" la imagen para borrar puntitos aislados y luego "dilatamos" para restaurar las letras
    kernel = np.ones((1, 1), np.uint8) # Kernel muy pequeño para no borrar letras finas
    img_limpia = cv2.morphologyEx(binaria, cv2.MORPH_OPEN, kernel)
    
    return img_limpia

import re

print("--- EXTRACCIÓN INTELIGENTE DE DATOS ---")

# 1. Buscar la CLAVE DE ELECTOR (Suele tener 18 letras/números en mayúscula)
# El patrón busca: 6 letras + 8 números + 1 letra + 1 número... (formato aproximado)
# O simplemente buscamos la palabra clave y tomamos lo que sigue
patron_clave = r"CLAVE DE ELECTOR\s+([A-Z0-9]{18})"
match_clave = re.search(patron_clave, texto)

if match_clave:
    print(f"CLAVE DE ELECTOR ENCONTRADA: {match_clave.group(1)}")
else:
    # Intento alternativo: buscar cualquier cadena de 18 caracteres alfanuméricos largos
    # (A veces el OCR no lee la frase "CLAVE DE ELECTOR" pero sí el código)
    posibles_claves = re.findall(r"[A-Z]{6}[0-9]{8}[A-Z][0-9]{3}", texto)
    if posibles_claves:
        print(f"POSIBLE CLAVE DE ELECTOR: {posibles_claves[0]}")

# 2. Buscar el MRZ (Las líneas de abajo que empiezan con IDMEX)
# IDMEX suele estar en la primera línea del bloque inferior
if "IDMEX" in texto:
    print("¡MRZ DETECTADO!")
    # Buscamos la línea que tiene IDMEX
    lineas = texto.split('\n')
    for linea in lineas:
        if "IDMEX" in linea:
            # Limpiamos caracteres raros que el OCR confunde (ej: '¡' por 'I', '$' por 'S')
            linea_limpia = linea.replace('¡', 'I').replace('!', 'I').replace('|', 'I')
            print(f"Línea MRZ Bruta: {linea_limpia}")
            
            # Aquí podrías extraer el número de identificación que sigue a IDMEX
            # IDMEX123456789...

import re

def limpiar_texto_ocr(texto_sucio):
    print("--- INICIANDO LIMPIEZA DE DATOS ---")
    
    # 1. CORRECCIONES COMUNES DE TESSERACT EN INEs
    # Reemplazamos símbolos que se confunden frecuentemente
    texto_limpio = texto_sucio.replace('¡', 'I').replace('!', 'I').replace('|', 'I').replace('$', 'S')
    
    # Unir palabras rotas (ej: "CLAVE DE ELECTOR" -> "CLAVEDEELECTOR")
    texto_limpio = texto_limpio.replace(" ", "") 
    
    # 2. EXTRAER CLAVE DE ELECTOR
    # Lógica: Busca la palabra "ELECTOR" y toma los siguientes 18 caracteres
    # El patrón [A-Z0-9] significa "letras mayúsculas o números"
    patron_clave = r"ELECTOR.*?([A-Z0-9]{18})"
    match_clave = re.search(patron_clave, texto_limpio, re.IGNORECASE)
    
    data = {}

    if match_clave:
        clave_cruda = match_clave.group(1)
        # A veces lee 'O' en vez de '0' en las fechas, aquí podrías corregirlo si sabes la posición
        data['clave_elector'] = clave_cruda
        print(f"✅ CLAVE DETECTADA: {clave_cruda}")
    else:
        # Intento de respaldo: Buscar cualquier cadena de 18 caracteres que parezca una clave
        # (4 letras + 6 numeros + 8 letras/numeros)
        patron_respaldo = r"([A-Z]{4}[0-9O]{6}[A-Z0-9]{8})"
        match_respaldo = re.search(patron_respaldo, texto_limpio)
        if match_respaldo:
             data['clave_elector'] = match_respaldo.group(1)
             print(f"⚠️ CLAVE (POSIBLE): {match_respaldo.group(1)}")

    # 3. EXTRAER MRZ (Página 2)
    # Buscamos la línea que empieza con "IDMEX" (o sus errores comunes como IOMEX, IONEX)
    # El patrón busca IDMEX seguido de 30 caracteres
    patron_mrz = r"(IDMEX[A-Z0-9<]{10,})"
    match_mrz = re.search(patron_mrz, texto_limpio)
    
    if match_mrz:
        data['mrz_linea1'] = match_mrz.group(1)
        print(f"✅ MRZ DETECTADO: {match_mrz.group(1)}")
    
    # Si no encuentra IDMEX exacto, busca por el patrón de la segunda línea del MRZ
    # que suele tener la fecha de nacimiento (ej: 920521)
    # Buscar patrones de fechas: 6 dígitos seguidos
    fechas = re.findall(r"(\d{6})", texto_limpio)
    if fechas:
        print(f"📅 Posibles fechas encontradas: {fechas}")

    return data

# --- PRUEBA CON TU RESULTADO ACTUAL ---
# Simulación de lo que te salió a ti
texto_pagina_1 = """
. tF'Í¡ v aG — l-;J_'-.
| . . CLAVEDEELECTOR ARFLIFOROS2210MBA ” _.
"""
texto_pagina_2 = """
¡onexzzazº977se<<141|º73377196
$709227¡321231zn:x<o¿<<l.i!f<!
"""

print("\n--- RESULTADOS PÁGINA 1 ---")
limpiar_texto_ocr(texto_pagina_1)

print("\n--- RESULTADOS PÁGINA 2 ---")
limpiar_texto_ocr(texto_pagina_2)

import re

def corregir_confusiones_comunes(texto):
    """Reemplaza caracteres que el OCR confunde siempre."""
    # Mapeo: Caracter erroneo -> Caracter real probable
    reemplazos = {
        '¡': 'I', '!': 'I', '|': 'I', 'l': 'I',  # I latina
        '$': 'S', '§': 'S',                      # S
        '(': 'C', '<': 'C',                      # C
        'º': '0', 'O': '0', 'o': '0', 'Q': '0',  # Cero
        'Z': '2', 'z': '2',                      # Dos
        'b': '6',                                # Seis
        'B': '8',                                # Ocho
        'A': '4',                                # Cuatro
        'g': '9',                                # Nueve
        '—': '-', '_': '-'                       # Guiones
    }
    texto_limpio = texto
    for sucio, limpio in reemplazos.items():
        texto_limpio = texto_limpio.replace(sucio, limpio)
    return texto_limpio

def extraer_datos_ine(texto_completo):
    data = {}
    
    # 1. Limpieza inicial general
    texto_procesado = corregir_confusiones_comunes(texto_completo)
    
    # ---------------------------------------------------------
    # ESTRATEGIA 1: LA CLAVE DE ELECTOR (Por Estructura)
    # ---------------------------------------------------------
    # Formato INE estándar: 4 Letras + 6 Números + 8 Caracteres (Letras/Num)
    # Regex explicada:
    # [A-Z]{4}    -> Busca 4 letras mayúsculas (Apellido/Nombre)
    # [0-9]{6}    -> Busca 6 números (Año/Mes/Día)
    # [A-Z0-9]{8} -> Busca 8 caracteres más (Homoclave, Sexo, Estado)
    
    patron_clave = r"([A-Z]{4}\d{6}[A-Z0-9]{8})"
    match_clave = re.search(patron_clave, texto_procesado.replace(" ", "")) # Quitamos espacios para facilitar búsqueda
    
    if match_clave:
        data['clave_elector'] = match_clave.group(1)
    else:
        # PLAN B: Si el OCR leyó letras en lugar de números en la fecha (muy común)
        # Buscamos: 4 letras + 6 "cosas" + 8 "cosas"
        patron_sucio = r"([A-Z]{4})([A-Z0-9]{6})([A-Z0-9]{8})"
        match_sucio = re.search(patron_sucio, texto_procesado.replace(" ", ""))
        
        if match_sucio:
            parte1 = match_sucio.group(1) # Letras
            parte2 = match_sucio.group(2) # Deberían ser números (Fecha)
            parte3 = match_sucio.group(3) # Resto
            
            # Forzamos conversión de letras a números en la fecha (O->0, I->1, etc)
            # Nota: Esto es una simplificación, requeriría una función mapeadora específica
            data['clave_elector_posible'] = f"{parte1}{parte2}{parte3} (Requiere validación)"

    # ---------------------------------------------------------
    # ESTRATEGIA 2: MRZ (Zona de lectura mecánica)
    # ---------------------------------------------------------
    # El MRZ de la INE empieza con "IDMEX" seguido de la clave, o por "<<<"
    
    # Buscamos "IDMEX" permitiendo errores (ej: 1DMEX, IOMEX)
    # [I1] -> Puede ser I o 1
    # [D0O] -> Puede ser D, 0 u O
    # [M] -> M
    patron_mrz_inicio = r"([I1][D0O]MEX\d+)"
    match_mrz = re.search(patron_mrz_inicio, texto_procesado)
    
    if match_mrz:
        data['mrz_raw'] = match_mrz.group(1)
    
    return data

# --- TUS RESULTADOS (COPIADOS DE TU CHAT) ---
texto_usuario = """
. tF'Í¡ v aG — l-;J_'-.
| . . CLAVEDEELECTOR ARFLIFOROS2210MBA ” _.
¡onexzzazº977se<<141|º73377196
$709227¡321231zn:x<o¿<<l.i!f<!
"""

# EJECUTAR
resultado = extraer_datos_ine(texto_usuario)
print("--- RESULTADO FINAL ---")
print(resultado)

import re

def limpiar_basura_ocr(texto):
    """Limpia caracteres comunes de ruido en identificaciones"""
    # 1. Mapeo de correcciones visuales (letras por números)
    reemplazos = {
        '¡': 'I', '!': 'I', '|': 'I', 'l': 'I', 
        '$': 'S', '§': 'S', 
        '(': 'C', '<': 'C', 
        'º': '0', 'O': '0', 'Q': '0', 
        'Z': '2', 'z': '2', 
        '—': '-', '_': '-', '.': '', ',': ''
    }
    texto_limpio = texto
    for sucio, limpio in reemplazos.items():
        texto_limpio = texto_limpio.replace(sucio, limpio)
    
    return texto_limpio

def extraer_datos_ine(texto_completo):
    print("--- PROCESANDO CON LÓGICA DE ANCLAJE ---")
    data = {}
    
    # Paso 1: Limpieza básica
    texto_limpio = limpiar_basura_ocr(texto_completo)
    
    # Paso 2: ENCONTRAR EL ANCLA "ELECTOR"
    # Buscamos variaciones por si el OCR falló (ELECTOR, ELECT0R, ELE CTOR)
    match_ancla = re.search(r"(ELECTOR|ELECT0R|EIECTOR)", texto_limpio, re.IGNORECASE)
    
    if match_ancla:
        # CORTAMOS EL TEXTO: Nos quedamos solo con lo que sigue después de "ELECTOR"
        # match_ancla.end() nos dice dónde termina la palabra encontrada
        texto_derecha = texto_limpio[match_ancla.end():]
        
        # Quitamos espacios para unir la clave (ej: ARFL IF0R...)
        texto_derecha_unido = texto_derecha.replace(" ", "").strip()
        
        print(f"DEBUG - Texto a la derecha de ELECTOR: {texto_derecha_unido[:25]}...")
        
        # Paso 3: BUSCAR LA CLAVE EN EL TEXTO CORTADO
        # Buscamos el primer bloque de 18 caracteres (o 17 si el OCR se comió uno)
        # [A-Z0-9] significa "cualquier letra o número"
        patron_clave = r"([A-Z0-9]{17,18})"
        match_clave = re.search(patron_clave, texto_derecha_unido)
        
        if match_clave:
            clave_encontrada = match_clave.group(1)
            data['clave_elector'] = clave_encontrada
            print(f"✅ CLAVE EXTRAÍDA: {clave_encontrada}")
        else:
            data['error'] = "Se encontró la etiqueta ELECTOR pero no la clave a la derecha."
            
    else:
        # PLAN B: Si no lee la palabra ELECTOR, buscamos por estructura bruta en todo el texto
        # (4 Letras + 6 Numeros + 8 Caracteres)
        print("⚠️ No se encontró la palabra 'ELECTOR', intentando búsqueda bruta...")
        patron_respaldo = r"([A-Z]{4}\d{6}[A-Z0-9]{8})"
        match_respaldo = re.search(patron_respaldo, texto_limpio.replace(" ", ""))
        if match_respaldo:
            data['clave_elector'] = match_respaldo.group(1)

    return data

# --- PRUEBA CON TU TEXTO REAL ---
texto_usuario = """
. tF'Í¡ v aG — l-;J_'-.
| . . CLAVEDEELECTOR ARFLIFOROS2210MBA ” _.
"""

resultado = extraer_datos_ine(texto_usuario)
print(resultado)