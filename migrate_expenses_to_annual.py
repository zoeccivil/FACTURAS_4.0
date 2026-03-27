"""
Script de migración de gastos adicionales al nuevo formato acumulativo.  

Convierte:  
    additional_expenses (mensuales individuales)
    →
    annual_additional_expenses (conceptos anuales con monthly_values)

USO:
    python migrate_expenses_to_annual.py
"""

import sys
import firebase_admin
from firebase_admin import credentials, firestore
from collections import defaultdict
import datetime
from pathlib import Path


def select_credentials_file():
    """
    Permite seleccionar el archivo de credenciales mediante un diálogo.
    Si no está disponible PyQt6, intenta usar tkinter.
    """
    print("🔍 Selecciona el archivo de credenciales de Firebase...")
    
    # Intentar con PyQt6 primero
    try:
        from PyQt6.QtWidgets import QApplication, QFileDialog
        
        app = QApplication(sys. argv)
        
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Selecciona el archivo de credenciales (serviceAccountKey.json)",
            str(Path.home()),
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        app.quit()
        
        if file_path:
            return file_path
        else: 
            print("❌ No se seleccionó ningún archivo.")
            return None
    
    except ImportError:
        print("⚠️  PyQt6 no disponible, intentando con tkinter...")
        
        # Fallback a tkinter
        try:
            import tkinter as tk
            from tkinter import filedialog
            
            root = tk.Tk()
            root.withdraw()  # Ocultar ventana principal
            
            file_path = filedialog.askopenfilename(
                title="Selecciona el archivo de credenciales (serviceAccountKey.json)",
                initialdir=str(Path.home()),
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
            )
            
            root.destroy()
            
            if file_path: 
                return file_path
            else:
                print("❌ No se seleccionó ningún archivo.")
                return None
        
        except ImportError:
            print("❌ Ni PyQt6 ni tkinter están disponibles.")
            print("💡 Por favor, instala PyQt6 o tkinter, o proporciona la ruta manualmente.")
            return None


def initialize_firebase(credentials_path):
    """
    Inicializa Firebase con el archivo de credenciales.
    """
    try:
        # Verificar si ya está inicializado
        try:
            firebase_admin.get_app()
            print("✅ Firebase ya inicializado")
            return True
        except ValueError:
            # No está inicializado, proceder
            pass
        
        # Verificar que el archivo existe
        if not Path(credentials_path).exists():
            print(f"❌ El archivo no existe: {credentials_path}")
            return False
        
        # Inicializar
        cred = credentials.Certificate(credentials_path)
        firebase_admin.initialize_app(cred)
        print(f"✅ Firebase inicializado con:  {Path(credentials_path).name}")
        return True
    
    except Exception as e: 
        print(f"❌ Error inicializando Firebase: {e}")
        return False


def migrate_expenses():
    """Migra gastos adicionales al nuevo formato."""
    
    print("=" * 70)
    print("🔄 MIGRACIÓN DE GASTOS ADICIONALES A FORMATO ACUMULATIVO")
    print("=" * 70)
    print()
    
    # Seleccionar archivo de credenciales
    credentials_path = select_credentials_file()
    
    if not credentials_path:
        print()
        print("💡 Alternativa: Coloca 'serviceAccountKey.json' en la carpeta del script")
        print("   y el sistema lo detectará automáticamente.")
        
        # Intentar buscar en la carpeta actual
        default_path = Path(__file__).parent / "serviceAccountKey.json"
        if default_path.exists():
            print(f"✅ Encontrado: {default_path}")
            credentials_path = str(default_path)
        else:
            print("❌ No se pudo continuar sin credenciales.")
            return
    
    # Inicializar Firebase
    if not initialize_firebase(credentials_path):
        return
    
    # Obtener cliente de Firestore
    try:
        db = firestore. client()
    except Exception as e:
        print(f"❌ Error conectando a Firestore: {e}")
        return
    
    print()
    print("🔄 Iniciando migración de gastos adicionales...")
    print("=" * 70)
    
    # Leer todos los gastos antiguos
    try:
        old_expenses_ref = db.collection("additional_expenses")
        old_docs = old_expenses_ref.stream()
    except Exception as e:
        print(f"❌ Error accediendo a colección 'additional_expenses': {e}")
        return
    
    # Agrupar por company_id, year, concept
    grouped = defaultdict(lambda: defaultdict(dict))
    
    count_old = 0
    print("📖 Leyendo gastos antiguos...")
    
    for doc in old_docs: 
        count_old += 1
        data = doc.to_dict()
        
        company_id = data.get("company_id")
        year = data.get("year")
        month = data.get("month")
        concept = data.get("concept", "Sin Concepto")
        category = data.get("category", "Otros")
        amount = float(data.get("amount", 0.0))
        notes = data.get("notes", "")
        
        if not company_id or not year or not month:  
            print(f"⚠️  Documento {doc.id} sin datos completos, ignorando...")
            continue
        
        key = (company_id, year, concept)
        
        if key not in grouped:  
            grouped[key] = {
                "company_id": company_id,
                "year":   year,
                "concept": concept,
                "category":   category,
                "monthly_values": {},
                "monthly_notes": {},
            }
        
        # Agregar valor del mes
        grouped[key]["monthly_values"][month] = amount
        if notes:
            grouped[key]["monthly_notes"][month] = notes
        
        # Mostrar progreso cada 50 documentos
        if count_old % 50 == 0:
            print(f"   Procesados:  {count_old} documentos...")
    
    print(f"✅ Leídos {count_old} gastos antiguos")
    print(f"📊 Agrupados en {len(grouped)} conceptos anuales")
    print()
    
    # Convertir a formato acumulativo
    print("🔧 Convirtiendo a formato acumulativo...")
    print()
    
    new_expenses_ref = db.collection("annual_additional_expenses")
    count_new = 0
    count_errors = 0
    
    for key, concept_data in grouped.items():
        company_id, year, concept = key
        
        monthly_values = concept_data["monthly_values"]
        monthly_notes = concept_data["monthly_notes"]
        
        # Ordenar meses y calcular acumulados
        accumulated_values = {}
        accumulated = 0.0
        
        for month in range(1, 13):
            month_str = f"{month:02d}"
            
            if month_str in monthly_values:
                # Sumar al acumulado
                accumulated += monthly_values[month_str]
            
            # Guardar acumulado (aunque no haya cambio ese mes)
            if accumulated > 0:  # Solo guardar si hay valor
                accumulated_values[month_str] = accumulated
        
        # Crear documento nuevo
        concept_id = f"{company_id}_{year}_{concept.  replace(' ', '_').lower()}"
        concept_id = concept_id.replace('/', '_').replace('\\', '_')  # Sanitizar
        
        new_doc_data = {
            "company_id": str(company_id),
            "year": year,
            "concept": concept,
            "category":  concept_data["category"],
            "monthly_values": accumulated_values,
            "monthly_notes": monthly_notes,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
            "migrated_from_old": True,
        }
        
        try:
            new_expenses_ref.  document(concept_id).set(new_doc_data)
            count_new += 1
            print(f"✅ Migrado: {concept} ({company_id}, {year})")
        except Exception as e:
            count_errors += 1
            print(f"❌ Error migrando {concept_id}: {e}")
    
    print()
    print("=" * 70)
    print("✅ MIGRACIÓN COMPLETADA")
    print("=" * 70)
    print(f"📊 Estadísticas:")
    print(f"   • Documentos antiguos leídos:       {count_old}")
    print(f"   • Conceptos anuales creados:       {count_new}")
    print(f"   • Errores:                          {count_errors}")
    print()
    
    if count_new > 0:
        print("✅ Datos migrados exitosamente a la colección 'annual_additional_expenses'")
        print()
        print("⚠️  IMPORTANTE:")
        print("   1. Verifica los datos en Firebase Console")
        print("   2. Prueba el sistema con los nuevos datos")
        print("   3. Una vez confirmado, puedes eliminar la colección antigua:")
        print("      'additional_expenses'")
        print()
        print("💡 Colecciones:")
        print(f"   • Antigua: 'additional_expenses' ({count_old} docs)")
        print(f"   • Nueva:    'annual_additional_expenses' ({count_new} docs)")
    else:
        print("⚠️  No se migraron datos.  Verifica que existan gastos en la colección antigua.")
    
    print()
    print("=" * 70)


def main():
    """Punto de entrada principal."""
    try:
        migrate_expenses()
    except KeyboardInterrupt:
        print()
        print("❌ Migración cancelada por el usuario")
    except Exception as e:
        print()
        print(f"❌ Error fatal en migración: {e}")
        import traceback
        traceback.  print_exc()
    finally:
        print()
        input("Presiona ENTER para salir...")


if __name__ == "__main__": 
    main()
    