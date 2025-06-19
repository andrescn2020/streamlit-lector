import streamlit as st
import pytesseract
import fitz  # PyMuPDF
from PIL import Image
import os
import re
import pandas as pd
from datetime import datetime
import glob
import tempfile
import shutil

# Configurar la ruta de Tesseract (ajusta según tu instalación)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Configurar página de Streamlit
st.set_page_config(page_title="Lector de Facturas", page_icon="📄", layout="wide")


class LectorFacturas:
    def __init__(self):
        self.facturas_procesadas = []
        self.pdfs_modificados = []

    def extraer_texto_paginas_pdf(self, pdf_path):
        """Extrae el texto de cada página del PDF como una lista."""
        textos_paginas = []
        try:
            doc = fitz.open(pdf_path)
            for pagina_num in range(len(doc)):
                pagina = doc.load_page(pagina_num)
                mat = fitz.Matrix(2.0, 2.0)
                pix = pagina.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # Solo procesar el 25% superior de la imagen
                altura = img.height
                altura_procesar = int(altura * 0.25)
                img_recortada = img.crop((0, 0, img.width, altura_procesar))

                texto_pagina = pytesseract.image_to_string(
                    img_recortada, lang="spa+eng", config="--psm 6 --oem 3"
                )
                textos_paginas.append(texto_pagina)
            doc.close()
        except Exception as e:
            st.error(f"Error al procesar PDF: {str(e)}")
        return textos_paginas

    def es_factura(self, texto):
        """Valida si el documento es una factura con patrón específico."""
        texto_lower = texto.lower()

        # Palabras que indican que NO es una factura
        no_factura = [
            "remito",
            "orden de compra",
            "pedido",
            "presupuesto",
            "cotización",
            "proforma",
            "documento no valido como factura",
            "no valido como factura",
            "no válido como factura",
        ]

        # Verificar que NO sea un documento que no queremos
        exclusion_count = sum(1 for palabra in no_factura if palabra in texto_lower)

        if exclusion_count >= 2:
            return False

        # Verificar documentos específicos que siempre se excluyen
        if "documento no" in texto_lower:
            return False

        # Verificar si contiene "COMO FACTURA" con posibles errores de OCR
        if (
            "como factura" in texto_lower
            or "cowo factura" in texto_lower
            or "cowo factura" in texto_lower
            or "como factura" in texto_lower
        ) and "no es un documento valido" not in texto_lower:
            return False

        # Mejorar detección de emails con patrones más específicos
        patrones_email = [
            r"^\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}",  # Fecha y hora al inicio
            r"correo de\s+\w+",  # "Correo de [nombre]"
            r"fwd:\s*",  # "Fwd:"
            r"re:\s*",  # "Re:"
            r"para:\s*",  # "Para:"
            r"de:\s*",  # "De:"
            r"asunto:\s*",  # "Asunto:"
            r"adjuntos?\s*\d*",  # "adjunto" o "adjuntos"
            r"\d+k\s*$",  # Tamaño de archivo al final (ej: "36K")
            r"\d+\s+mensajes?",  # "3 mensajes" o "1 mensaje"
        ]

        # Contar cuántos patrones de email se encuentran
        patrones_email_encontrados = 0
        for patron in patrones_email:
            if re.search(patron, texto_lower):
                patrones_email_encontrados += 1

        # Si hay múltiples patrones de email, es muy probable que sea un email
        if patrones_email_encontrados >= 2:
            return False

        # Verificar estructura específica de email con "Fwd:" o "Re:"
        if any(palabra in texto_lower for palabra in ["fwd:", "re:", "correo de"]):
            lineas = texto_lower.split("\n")
            lineas_con_email = sum(
                1
                for linea in lineas
                if any(
                    palabra in linea
                    for palabra in [
                        "correo de",
                        "re:",
                        "fwd:",
                        "para:",
                        "de:",
                        "asunto:",
                        "mensaje",
                        "escribio:",
                        "escribió:",
                        "adjuntos",
                        "adjunto",
                    ]
                )
            )

            if lineas_con_email >= 1 and "factura" in texto_lower:
                if any(
                    palabra in texto_lower
                    for palabra in [
                        "realizar la factura",
                        "factura correspondiente",
                        "enviar factura",
                        "fwd: factura",
                        "re: factura",
                    ]
                ):
                    return False

            if lineas_con_email >= 2:
                return False

        # Verificar si contiene "factura" o "facturas" directamente
        if "factura" in texto_lower or "facturas" in texto_lower:
            return True

        # Patrón específico para factura
        patrones_factura = [
            r"factura\s+n[°º]?\s*:\s*\d+-\d+",  # FACTURA N°: 0003-00016403
            r"factura\s+n[°º]?\s*\d+-\d+",  # FACTURA N° 0003-00016403
            r"factura\s+n[°º]?\s*:\s*\d+/\d+",  # FACTURA N°: 0003/00016403
            r"factura\s+n[°º]?\s*\d+/\d+",  # FACTURA N° 0003/00016403
            r"punto de venta\s*:\s*\d+\s+comp\.?nro\s*:\s*\d+",  # Punto de Venta: 00004 Comp.Nro: 00006772
            r"punto de venta\s*:\s*\d+\s+comp\s*nro\s*:\s*\d+",  # Punto de Venta: 00004 Comp Nro: 00006772
            r"cod\.\s*\d+",  # COD. 01
            r"codigo\s*\d+",  # CODIGO 01
            r"cod\.\s*n[°º]?\s*\d+",  # Cod.N° 01
            r"cod\s*n[°º]?\s*\d+",  # Cod N° 01 (sin punto)
            r"cod\.\s*n\s*\d+",  # Cod.N 01 (sin símbolo)
            r"cod\s*n\s*\d+",  # Cod N 01 (sin punto ni símbolo)
            r"cod\.\s*n[°º]?\s*\d+\s*\w*",  # Cod.N° 01 jo (con caracteres extra)
            r"cod\s*n[°º]?\s*\d+\s*\w*",  # Cod N° 01 jo (sin punto, con caracteres extra)
            r"céd\.\s*\d+",  # Céd. 01
            r"céd\s*\d+",  # Céd 01 (sin punto)
            r"empresa distribuidora y comercializadora norte s\.a\.",  # Empresa Distribuidora y Comercializadora Norte S.A.
            r"amx argentina s\.a",  # AMX ARGENTINA S.A
        ]

        # Buscar el patrón específico
        for patron in patrones_factura:
            if re.search(patron, texto_lower):
                return True

        return False

    def procesar_pdf_individual(
        self, pdf_path, numero_orden, output_dir, nombre_original=None
    ):
        """Procesa un PDF individual y extrae solo las páginas que son facturas."""
        with st.spinner(
            f"Procesando PDF {numero_orden}: {nombre_original or os.path.basename(pdf_path)}"
        ):
            textos_paginas = self.extraer_texto_paginas_pdf(pdf_path)
            if not textos_paginas:
                st.error("No se pudo extraer texto del PDF.")
                return None

            # Lista para guardar índices de páginas que son facturas
            paginas_facturas = []

            for idx, texto in enumerate(textos_paginas):
                if self.es_factura(texto):
                    paginas_facturas.append(idx)

            # Si hay páginas de facturas, crear nuevo PDF
            if paginas_facturas:
                nuevo_pdf_path = self.crear_pdf_solo_facturas(
                    pdf_path,
                    paginas_facturas,
                    numero_orden,
                    output_dir,
                    nombre_original,
                )
                return nuevo_pdf_path
            else:
                # Crear una copia del PDF original con el prefijo de orden
                nuevo_pdf_path = self.crear_copia_pdf_original(
                    pdf_path, numero_orden, output_dir, nombre_original
                )
                return nuevo_pdf_path

    def crear_pdf_solo_facturas(
        self,
        pdf_original,
        paginas_facturas,
        numero_orden,
        output_dir,
        nombre_original=None,
    ):
        """Crea un nuevo PDF con solo las páginas que son facturas."""
        try:
            # Abrir PDF original
            doc_original = fitz.open(pdf_original)

            # Crear nuevo PDF
            doc_nuevo = fitz.open()

            # Copiar solo las páginas que son facturas
            for pagina_idx in paginas_facturas:
                doc_nuevo.insert_pdf(
                    doc_original, from_page=pagina_idx, to_page=pagina_idx
                )

            # Generar nombre del nuevo archivo usando el nombre original
            if nombre_original:
                nombre_base = nombre_original
            else:
                nombre_base = os.path.basename(pdf_original)

            nuevo_nombre = f"{numero_orden:03d}_{nombre_base}"
            nuevo_path = os.path.join(output_dir, nuevo_nombre)

            # Guardar nuevo PDF
            doc_nuevo.save(nuevo_path)
            doc_nuevo.close()
            doc_original.close()

            return nuevo_path

        except Exception as e:
            st.error(f"Error al crear PDF: {str(e)}")
            return None

    def crear_copia_pdf_original(
        self, pdf_original, numero_orden, output_dir, nombre_original=None
    ):
        """Crea una copia del PDF original con prefijo de orden."""
        try:
            # Abrir PDF original
            doc_original = fitz.open(pdf_original)

            # Crear nuevo PDF
            doc_nuevo = fitz.open()

            # Copiar todas las páginas del PDF original
            doc_nuevo.insert_pdf(doc_original)

            # Generar nombre del nuevo archivo usando el nombre original
            if nombre_original:
                nombre_base = nombre_original
            else:
                nombre_base = os.path.basename(pdf_original)

            nuevo_nombre = f"{numero_orden:03d}_{nombre_base}"
            nuevo_path = os.path.join(output_dir, nuevo_nombre)

            # Guardar nuevo PDF
            doc_nuevo.save(nuevo_path)
            doc_nuevo.close()
            doc_original.close()

            return nuevo_path

        except Exception as e:
            st.error(f"Error al copiar PDF original: {str(e)}")
            return None

    def procesar_archivos(self, uploaded_files, output_dir):
        """Procesa los archivos subidos."""
        try:
            if not uploaded_files:
                st.warning("No se subieron archivos.")
                return

            st.info(f"Procesando {len(uploaded_files)} archivos...")

            # Crear directorio de salida si no existe
            os.makedirs(output_dir, exist_ok=True)

            # Procesar cada archivo
            for i, uploaded_file in enumerate(uploaded_files, 1):
                # Guardar archivo temporalmente
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".pdf"
                ) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name

                # Procesar el archivo usando el nombre original
                nuevo_pdf = self.procesar_pdf_individual(
                    tmp_path, i, output_dir, uploaded_file.name
                )
                if nuevo_pdf:
                    self.pdfs_modificados.append(nuevo_pdf)

                # Limpiar archivo temporal
                os.unlink(tmp_path)

            st.success(
                f"Procesamiento completado. Se crearon {len(self.pdfs_modificados)} archivos."
            )

        except Exception as e:
            st.error(f"Error al procesar archivos: {str(e)}")


def main():
    st.title("📄 Lector de Facturas")
    st.markdown("---")

    st.markdown(
        """
    ### ¿Qué hace esta aplicación?
    Esta aplicación procesa archivos PDF y extrae automáticamente solo las páginas que contienen facturas.
    
    **Características:**
    - ✅ Detecta páginas de facturas usando OCR
    - ✅ Filtra emails, remitos, órdenes de compra y otros documentos
    - ✅ Mantiene el orden original de los archivos
    - ✅ Si no encuentra facturas, mantiene el PDF original intacto
    """
    )

    # Inicializar el lector
    lector = LectorFacturas()

    # Sidebar para configuración
    st.sidebar.header("⚙️ Configuración")

    # Opción para descargar todos los archivos como ZIP
    crear_zip = st.sidebar.checkbox("Crear archivo ZIP con resultados", value=True)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📋 Instrucciones")
    st.sidebar.markdown(
        """
    1. Sube los archivos PDF que quieres procesar
    2. Haz clic en 'Procesar Archivos'
    3. Descarga los resultados
    """
    )

    # Área principal
    st.header("📁 Subir Archivos")

    uploaded_files = st.file_uploader(
        "Selecciona los archivos PDF",
        type=["pdf"],
        accept_multiple_files=True,
        help="Puedes seleccionar múltiples archivos PDF",
    )

    if uploaded_files:
        st.success(f"✅ Se subieron {len(uploaded_files)} archivos")

        # Mostrar lista de archivos
        st.subheader("📋 Archivos subidos:")
        for i, file in enumerate(uploaded_files, 1):
            st.write(f"{i}. {file.name}")

        # Botón para procesar
        if st.button("🚀 Procesar Archivos", type="primary"):
            # Crear directorio temporal para los resultados
            with tempfile.TemporaryDirectory() as temp_dir:
                # Procesar archivos
                lector.procesar_archivos(uploaded_files, temp_dir)

                if lector.pdfs_modificados:
                    st.subheader("📥 Descargar Resultados")

                    if crear_zip:
                        # Crear archivo ZIP
                        import zipfile

                        zip_path = os.path.join(temp_dir, "facturas_procesadas.zip")

                        with zipfile.ZipFile(zip_path, "w") as zipf:
                            for pdf_path in lector.pdfs_modificados:
                                zipf.write(pdf_path, os.path.basename(pdf_path))

                        # Botón para descargar ZIP
                        with open(zip_path, "rb") as f:
                            st.download_button(
                                label="📦 Descargar todos los archivos (ZIP)",
                                data=f.read(),
                                file_name="facturas_procesadas.zip",
                                mime="application/zip",
                            )
                    else:
                        # Botones individuales para cada archivo
                        st.write("Descargar archivos individuales:")
                        for pdf_path in lector.pdfs_modificados:
                            with open(pdf_path, "rb") as f:
                                st.download_button(
                                    label=f"📄 {os.path.basename(pdf_path)}",
                                    data=f.read(),
                                    file_name=os.path.basename(pdf_path),
                                    mime="application/pdf",
                                )
                else:
                    st.warning("No se procesó ningún archivo.")

    # Footer
    st.markdown("---")
    st.markdown(
        """
    <div style='text-align: center; color: #666;'>
        <p>Desarrollado con ❤️ usando Streamlit y Tesseract OCR</p>
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
