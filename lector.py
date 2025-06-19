import pytesseract
import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import os
import re
import pandas as pd
from datetime import datetime
import glob

# Configurar la ruta de Tesseract (ajusta según tu instalación)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


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
            # print(f"Error al procesar PDF: {str(e)}")
            pass
        return textos_paginas

    def extraer_datos_proveedor(self, lineas):
        """Busca el nombre del proveedor en la primera 'Razón Social:' encontrada."""
        for linea in lineas:
            if "razón social:" in linea.lower() or "razon social:" in linea.lower():
                # Extraer el nombre después de "Razón Social:"
                partes = linea.split(":")
                if len(partes) > 1:
                    nombre = partes[1].strip()

                    # Detener en palabras que indican fin del nombre
                    palabras_fin = [
                        "fecha",
                        "cuit",
                        "c.u.i.t",
                        "domicilio",
                        "tel",
                        "telefono",
                        "email",
                        "e-mail",
                    ]
                    for palabra in palabras_fin:
                        if palabra in nombre.lower():
                            # Encontrar la posición de la palabra y cortar ahí
                            pos = nombre.lower().find(palabra)
                            nombre = nombre[:pos].strip()
                            break

                    # Limpiar caracteres extra
                    nombre = re.sub(r"[^\w\s\.\-&]", "", nombre).strip()
                    return nombre
        return ""

    def extraer_datos_factura(self, texto):
        """Extrae datos relevantes de una factura."""
        datos = {
            "fecha": "",
            "numero_factura": "",
            "proveedor": "",
            "cuit": "",
            "subtotal": "",
            "iva": "",
            "total": "",
            "descripcion": [],
        }

        # Convertir a minúsculas para búsqueda
        texto_lower = texto.lower()
        lineas = texto.split("\n")

        # Buscar fecha
        patrones_fecha = [
            r"(\d{2}[/-]\d{2}[/-]\d{4})",
            r"(\d{2}[/-]\d{2}[/-]\d{2})",
            r"fecha[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})",
            r"fecha[:\s]*(\d{2}[/-]\d{2}[/-]\d{2})",
        ]

        for patron in patrones_fecha:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                datos["fecha"] = match.group(1)
                break

        # Buscar número de factura
        patrones_factura = [
            r"factura[:\s]*([a-z]?\s*\d+)",
            r"comprobante[:\s]*([a-z]?\s*\d+)",
            r"n[°º]?[:\s]*([a-z]?\s*\d+)",
        ]

        for patron in patrones_factura:
            match = re.search(patron, texto_lower)
            if match:
                datos["numero_factura"] = match.group(1).strip().upper()
                break

        # Buscar proveedor (en las primeras líneas)
        for i, linea in enumerate(lineas[:15]):
            linea_clean = linea.strip()
            if len(linea_clean) > 5 and any(
                palabra in linea_clean.lower()
                for palabra in ["s.a.", "s.r.l.", "sociedad", "ltda", "inc"]
            ):
                datos["proveedor"] = linea_clean
                break

        # Buscar CUIT
        patron_cuit = r"\d{2}-\d{8}-\d{1}"
        match = re.search(patron_cuit, texto)
        if match:
            datos["cuit"] = match.group(0)

        # Buscar montos
        # Subtotal
        patrones_subtotal = [
            r"subtotal[:\s]*\$?\s*([\d,]+\.?\d*)",
            r"neto[:\s]*\$?\s*([\d,]+\.?\d*)",
            r"base imponible[:\s]*\$?\s*([\d,]+\.?\d*)",
        ]

        for patron in patrones_subtotal:
            match = re.search(patron, texto_lower)
            if match:
                datos["subtotal"] = match.group(1)
                break

        # IVA
        patrones_iva = [
            r"iva[:\s]*\$?\s*([\d,]+\.?\d*)",
            r"impuesto[:\s]*\$?\s*([\d,]+\.?\d*)",
        ]

        for patron in patrones_iva:
            match = re.search(patron, texto_lower)
            if match:
                datos["iva"] = match.group(1)
                break

        # Total
        patrones_total = [
            r"total[:\s]*\$?\s*([\d,]+\.?\d*)",
            r"importe total[:\s]*\$?\s*([\d,]+\.?\d*)",
        ]

        for patron in patrones_total:
            match = re.search(patron, texto_lower)
            if match:
                datos["total"] = match.group(1)
                break

        # Buscar descripción de productos
        seccion_descripcion = False
        for linea in lineas:
            if "descripcion" in linea.lower() or "concepto" in linea.lower():
                seccion_descripcion = True
                continue

            if seccion_descripcion and linea.strip():
                # Detener si encontramos totales
                if any(
                    palabra in linea.lower() for palabra in ["total", "subtotal", "iva"]
                ):
                    break
                datos["descripcion"].append(linea.strip())

        return datos

    def es_factura(self, texto):
        """Valida si el documento es una factura con patrón específico."""
        texto_lower = texto.lower()

        # print(f"  🔍 DEBUG: Analizando texto...")

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
        # Solo excluir si el documento es principalmente de ese tipo, no si contiene referencias
        exclusion_count = sum(1 for palabra in no_factura if palabra in texto_lower)

        # Si hay muchas palabras de exclusión, probablemente es ese tipo de documento
        if exclusion_count >= 2:
            # print(
            #     f"  ❌ DEBUG: Excluido por contener {exclusion_count} palabras de exclusión"
            # )
            return False

        # Verificar documentos específicos que siempre se excluyen
        if "documento no" in texto_lower:
            # print(f"  ❌ DEBUG: Excluido por ser documento no válido como factura")
            return False

        # Verificar si contiene "COMO FACTURA" con posibles errores de OCR
        if (
            "como factura" in texto_lower
            or "cowo factura" in texto_lower
            or "cowo factura" in texto_lower
            or "como factura" in texto_lower
        ) and "no es un documento valido" not in texto_lower:
            # print(
            #     f"  ❌ DEBUG: Excluido por contener 'COMO FACTURA' (con posibles errores de OCR)"
            # )
            return False

        # Verificar si es principalmente un email (tiene estructura de email)
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
            # print(f"  ❌ DEBUG: Excluido por ser email ({patrones_email_encontrados} patrones de email detectados)")
            return False

        # Verificar estructura específica de email con "Fwd:" o "Re:"
        if any(palabra in texto_lower for palabra in ["fwd:", "re:", "correo de"]):
            # print(f"  🔍 DEBUG: Detectadas palabras de email, verificando estructura...")
            # Si contiene estructura de email, verificar si es principalmente un email
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

            # Si hay estructura de email y contiene "factura" solo como referencia, es un email
            if lineas_con_email >= 1 and "factura" in texto_lower:
                # Verificar si "factura" aparece en contexto de email
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
                    # print(
                    #     f"  ❌ DEBUG: Excluido por ser email con referencia a factura ({lineas_con_email} líneas con estructura de email)"
                    # )
                    return False

            if lineas_con_email >= 2:  # Si hay múltiples líneas con estructura de email
                # print(
                #     f"  ❌ DEBUG: Excluido por ser principalmente un email ({lineas_con_email} líneas con estructura de email)"
                # )
                return False

        # Verificar si contiene "factura" o "facturas" directamente
        if "factura" in texto_lower or "facturas" in texto_lower:
            # print(f"  ✅ DEBUG: Encontrada palabra 'factura' o 'facturas'")
            return True

        # Debug: mostrar si contiene "facturas" en cualquier variación
        # if "facturas" in texto:
        #     print(f"  🔍 DEBUG: Encontrada 'FACTURAS' en texto original")
        # if "facturas" in texto_lower:
        #     print(f"  🔍 DEBUG: Encontrada 'facturas' en texto en minúsculas")

        # Patrón específico para factura: "FACTURA N°: 0003-00016403"
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
        for i, patron in enumerate(patrones_factura):
            if re.search(patron, texto_lower):
                # print(f"  ✅ DEBUG: Patrón {i+1} encontrado")
                return True

        # print(f"  ❌ DEBUG: No se encontró ningún patrón de factura")
        return False

    def procesar_pdf_individual(self, pdf_path, numero_orden):
        """Procesa un PDF individual y extrae solo las páginas que son facturas."""
        # print(f"\n{'='*60}")
        # print(f"PROCESANDO PDF {numero_orden}: {os.path.basename(pdf_path)}")
        # print(f"{'='*60}")

        textos_paginas = self.extraer_texto_paginas_pdf(pdf_path)
        if not textos_paginas:
            # print("No se pudo extraer texto del PDF.")
            return None

        # Lista para guardar índices de páginas que son facturas
        paginas_facturas = []

        for idx, texto in enumerate(textos_paginas):
            # print(f"\n--- PÁGINA {idx+1} ---")
            # print("TEXTO EXTRAÍDO POR OCR:")
            # print("-" * 30)
            # print(texto)
            # print("-" * 30)

            if self.es_factura(texto):
                # print(f"✅ PÁGINA {idx+1}: CONTIENE FACTURA")
                paginas_facturas.append(idx)
            else:
                # print(f"❌ PÁGINA {idx+1}: NO es factura")
                pass

        # Si hay páginas de facturas, crear nuevo PDF
        if paginas_facturas:
            nuevo_pdf_path = self.crear_pdf_solo_facturas(
                pdf_path, paginas_facturas, numero_orden
            )
            return nuevo_pdf_path
        else:
            # print(f"⚠️ No se encontraron facturas en {os.path.basename(pdf_path)}")
            # print(f"📄 Manteniendo PDF original intacto...")
            # Crear una copia del PDF original con el prefijo de orden
            nuevo_pdf_path = self.crear_copia_pdf_original(pdf_path, numero_orden)
            return nuevo_pdf_path

    def crear_pdf_solo_facturas(self, pdf_original, paginas_facturas, numero_orden):
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

            # Generar nombre del nuevo archivo
            nombre_base = os.path.basename(pdf_original)
            nuevo_nombre = f"{numero_orden:03d}_{nombre_base}"
            nuevo_path = os.path.join(os.getcwd(), nuevo_nombre)

            # Guardar nuevo PDF
            doc_nuevo.save(nuevo_path)
            doc_nuevo.close()
            doc_original.close()

            # print(f"✅ PDF creado: {nuevo_nombre}")
            return nuevo_path

        except Exception as e:
            # print(f"❌ Error al crear PDF: {str(e)}")
            return None

    def crear_copia_pdf_original(self, pdf_original, numero_orden):
        """Crea una copia del PDF original con prefijo de orden."""
        try:
            # Abrir PDF original
            doc_original = fitz.open(pdf_original)

            # Crear nuevo PDF
            doc_nuevo = fitz.open()

            # Copiar todas las páginas del PDF original
            doc_nuevo.insert_pdf(doc_original)

            # Generar nombre del nuevo archivo
            nombre_base = os.path.basename(pdf_original)
            nuevo_nombre = f"{numero_orden:03d}_{nombre_base}"
            nuevo_path = os.path.join(os.getcwd(), nuevo_nombre)

            # Guardar nuevo PDF
            doc_nuevo.save(nuevo_path)
            doc_nuevo.close()
            doc_original.close()

            # print(f"✅ PDF original copiado: {nuevo_nombre}")
            return nuevo_path

        except Exception as e:
            # print(f"❌ Error al copiar PDF original: {str(e)}")
            return None

    def procesar_carpeta(self, carpeta_path):
        """Procesa una carpeta que contiene PDFs."""
        # print(f"\n{'='*60}")
        # print(f"PROCESANDO CARPETA: {os.path.basename(carpeta_path)}")
        # print(f"{'='*60}")

        try:
            # Obtener todos los PDFs de la carpeta en orden
            pdfs_en_carpeta = glob.glob(os.path.join(carpeta_path, "*.pdf"))
            pdfs_en_carpeta.sort()  # Ordenar alfabéticamente para mantener orden consistente

            if not pdfs_en_carpeta:
                # print("❌ No se encontraron PDFs en la carpeta.")
                return

            # print(f"📁 Encontrados {len(pdfs_en_carpeta)} PDFs en la carpeta")
            # print("📋 Orden de procesamiento:")
            # for i, pdf in enumerate(pdfs_en_carpeta, 1):
            #     print(f"   {i:02d}. {os.path.basename(pdf)}")
            # print()

            # Procesar cada PDF
            for i, pdf_path in enumerate(pdfs_en_carpeta, 1):
                nuevo_pdf = self.procesar_pdf_individual(pdf_path, i)
                if nuevo_pdf:
                    self.pdfs_modificados.append(nuevo_pdf)

            # print(f"\n{'='*60}")
            # print(f"RESUMEN: Se procesaron {len(pdfs_en_carpeta)} PDFs")
            # print(f"Se crearon {len(self.pdfs_modificados)} PDFs con facturas")
            # print(f"{'='*60}")

        except Exception as e:
            # print(f"❌ Error al procesar carpeta: {str(e)}")
            pass

    def seleccionar_carpeta(self):
        """Permite al usuario seleccionar una carpeta."""
        try:
            root = tk.Tk()
            root.withdraw()

            carpeta = filedialog.askdirectory(
                title="Seleccionar carpeta con PDFs", initialdir=os.getcwd()
            )

            if carpeta and os.path.exists(carpeta):
                return carpeta
            else:
                # print("No se seleccionó ninguna carpeta válida.")
                return None

        except Exception as e:
            # print(f"Error al seleccionar carpeta: {str(e)}")
            return None

    def ejecutar(self):
        """Ejecuta el programa principal."""
        # print("=== LECTOR DE FACTURAS CON TESSERACT ===")
        # print(
        #     "Este programa procesa carpetas con PDFs y extrae solo las páginas de facturas"
        # )

        while True:
            # Seleccionar carpeta
            carpeta = self.seleccionar_carpeta()
            if not carpeta:
                continuar = input("\n¿Desea intentar con otra carpeta? (s/n): ").lower()
                if continuar != "s":
                    break
                continue

            # Procesar carpeta
            self.procesar_carpeta(carpeta)

            # Preguntar si continuar
            continuar = input("\n¿Desea procesar otra carpeta? (s/n): ").lower()
            if continuar != "s":
                break

        if self.pdfs_modificados:
            # print(
            #     f"\n✅ Procesamiento completado. Se crearon {len(self.pdfs_modificados)} PDFs con facturas."
            # )
            pass
        else:
            # print("\n❌ No se procesó ningún PDF.")
            pass


if __name__ == "__main__":
    lector = LectorFacturas()
    lector.ejecutar()
