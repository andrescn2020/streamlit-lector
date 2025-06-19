# Lector de Facturas - Aplicación Streamlit

Esta es una aplicación web que procesa archivos PDF y extrae automáticamente solo las páginas que contienen facturas.

## 🚀 Instalación y Configuración

### 1. Instalar Tesseract OCR

**Windows:**

1. Descarga Tesseract desde: https://github.com/UB-Mannheim/tesseract/wiki
2. Instala en `C:\Program Files\Tesseract-OCR\`
3. Asegúrate de que el archivo `tesseract.exe` esté en esa ruta

**macOS:**

```bash
brew install tesseract
```

**Linux (Ubuntu/Debian):**

```bash
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-spa  # Para español
```

### 2. Instalar Dependencias de Python

```bash
pip install -r requirements_streamlit.txt
```

### 3. Ejecutar la Aplicación

```bash
streamlit run app.py
```

La aplicación se abrirá automáticamente en tu navegador en `http://localhost:8501`

## 📋 Cómo Usar

1. **Subir Archivos**: Arrastra y suelta o selecciona los archivos PDF que quieres procesar
2. **Procesar**: Haz clic en "Procesar Archivos"
3. **Descargar**: Descarga los resultados como archivo ZIP o archivos individuales

## ✨ Características

- ✅ **Detección Inteligente**: Identifica páginas de facturas usando OCR
- ✅ **Filtrado Automático**: Excluye emails, remitos, órdenes de compra y otros documentos
- ✅ **Interfaz Web**: Fácil de usar desde cualquier navegador
- ✅ **Múltiples Archivos**: Procesa varios PDFs a la vez
- ✅ **Descarga Flexible**: Opción de descargar como ZIP o archivos individuales
- ✅ **Preservación**: Si no encuentra facturas, mantiene el PDF original

## 🔧 Configuración

En el archivo `app.py`, puedes modificar la ruta de Tesseract si es necesario:

```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

## 📁 Estructura de Archivos

```
├── app.py                    # Aplicación principal de Streamlit
├── lector.py                 # Versión de consola original
├── requirements_streamlit.txt # Dependencias para Streamlit
└── README_streamlit.md       # Este archivo
```

## 🐛 Solución de Problemas

**Error: "tesseract is not recognized"**

- Verifica que Tesseract esté instalado correctamente
- Asegúrate de que la ruta en `app.py` sea correcta

**Error al procesar PDFs**

- Verifica que los archivos PDF no estén corruptos
- Asegúrate de que tengan texto legible (no solo imágenes escaneadas)

**La aplicación no se abre**

- Verifica que todas las dependencias estén instaladas
- Ejecuta `streamlit --version` para verificar la instalación

## 📞 Soporte

Si tienes problemas o preguntas, revisa:

1. Que Tesseract esté instalado correctamente
2. Que todas las dependencias estén instaladas
3. Que los archivos PDF sean válidos
