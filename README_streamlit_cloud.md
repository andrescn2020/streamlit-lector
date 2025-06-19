# Lector de Facturas - Versión Streamlit Cloud

Esta es la versión optimizada para funcionar en Streamlit Cloud sin necesidad de software externo.

## 🚀 Despliegue en Streamlit Cloud

### 1. Preparar los Archivos

Asegúrate de tener estos archivos en tu repositorio:

```
├── app_easyocr.py                    # Aplicación principal (EasyOCR)
├── requirements_streamlit_easyocr.txt # Dependencias para EasyOCR
└── README_streamlit_cloud.md         # Este archivo
```

### 2. Subir a GitHub

1. Crea un repositorio en GitHub
2. Sube los archivos necesarios
3. Asegúrate de que el archivo principal se llame `app_easyocr.py`

### 3. Desplegar en Streamlit Cloud

1. Ve a [share.streamlit.io](https://share.streamlit.io)
2. Conecta tu cuenta de GitHub
3. Selecciona tu repositorio
4. En "Main file path" pon: `app_easyocr.py`
5. Haz clic en "Deploy!"

## ✨ Diferencias con la Versión Local

### ✅ Ventajas de EasyOCR:

- **No requiere software externo** - Funciona completamente en la nube
- **Instalación automática** - Se instala con pip
- **Mejor precisión** - Usa deep learning para OCR
- **Múltiples idiomas** - Español e inglés incluidos

### ⚠️ Consideraciones:

- **Primera carga más lenta** - EasyOCR descarga modelos (~100MB)
- **Uso de memoria** - Requiere más RAM que Tesseract
- **Tiempo de procesamiento** - Puede ser un poco más lento

## 🔧 Configuración

### Para Desarrollo Local:

```bash
# Instalar dependencias
pip install -r requirements_streamlit_easyocr.txt

# Ejecutar aplicación
streamlit run app_easyocr.py
```

### Para Streamlit Cloud:

No necesitas configuración adicional. Streamlit Cloud instalará automáticamente todas las dependencias.

## 📋 Archivos de Configuración

### requirements_streamlit_easyocr.txt

```
streamlit==1.28.1
easyocr==1.7.0
PyMuPDF==1.23.8
Pillow==10.0.1
pandas==2.1.3
python-dateutil==2.8.2
numpy==1.24.3
torch==2.0.1
torchvision==0.15.2
```

## 🐛 Solución de Problemas

### Error: "CUDA not available"

- **Solución**: EasyOCR usará CPU automáticamente
- **Impacto**: Procesamiento más lento pero funcional

### Error: "Out of memory"

- **Solución**: Reduce el número de archivos procesados a la vez
- **Prevención**: Procesa archivos en lotes pequeños

### Error: "Model download failed"

- **Solución**: Verifica conexión a internet
- **Alternativa**: Usa la versión local con Tesseract

## 📊 Comparación de Rendimiento

| Aspecto     | Tesseract (Local)         | EasyOCR (Cloud) |
| ----------- | ------------------------- | --------------- |
| Instalación | Requiere software externo | Solo pip        |
| Precisión   | Buena                     | Excelente       |
| Velocidad   | Rápida                    | Media           |
| Memoria     | Baja                      | Alta            |
| Despliegue  | Complejo                  | Simple          |

## 🎯 Recomendaciones

1. **Para uso personal/local**: Usa `app.py` con Tesseract
2. **Para compartir/publicar**: Usa `app_easyocr.py` en Streamlit Cloud
3. **Para procesamiento masivo**: Usa la versión local por velocidad

## 📞 Soporte

Si tienes problemas con el despliegue:

1. Verifica que todos los archivos estén en el repositorio
2. Revisa los logs de Streamlit Cloud
3. Asegúrate de que el archivo principal sea `app_easyocr.py`
4. Verifica que `requirements_streamlit_easyocr.txt` esté presente
