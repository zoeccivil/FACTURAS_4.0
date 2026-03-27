# 🔧 Script de Migración: Corrección de ITBIS en Moneda Extranjera

## Problema

Las facturas registradas con moneda extranjera (USD, EUR, etc.) tenían el ITBIS almacenado en la moneda original sin convertir a RD$. Esto causaba:

- ❌ Reportes de ITBIS incorrectos
- ❌ Sumas totales de ITBIS muy bajas
- ❌ Declaraciones fiscales con datos incorrectos

**Ejemplo del problema:**
```
Factura en USD $1,000.00
ITBIS 18%: $180.00
Tasa de cambio: 58.50 RD$/USD

INCORRECTO (antes):
- Campo itbis: 180.00 (se interpretaba como RD$ 180.00)

CORRECTO (ahora):
- Campo itbis: 10,530.00 (RD$)
- Campo itbis_original_currency: 180.00 (USD)
```

## Solución

Este script corrige automáticamente todas las facturas con moneda extranjera en Firestore.

## Uso

### 1. Modo Dry-Run (Simulación - Recomendado primero)

```bash
python fix_itbis_exchange_rate.py
```

Esto **NO modifica** ningún dato. Solo muestra qué facturas serían corregidas.

**Salida ejemplo:**
```
📊 Total de facturas en base de datos: 450

🔧 Factura a corregir: B0100045612
   Tercero: Proveedor Internacional Inc.
   Moneda: USD
   Tasa de cambio: 58.5
   ITBIS actual: 180.00 USD
   ITBIS corregido: RD$ 10,530.00
   Total: 1,000.00 USD
   ℹ️  (No actualizado - modo dry run)

================================================================================
RESUMEN DE OPERACIÓN
================================================================================
Total facturas procesadas: 450
✅ Facturas corregidas: 35
⏭️  Facturas omitidas (no necesitaban corrección): 413
❌ Errores: 2
```

### 2. Modo Aplicación (Modifica datos reales)

Una vez que haya revisado la simulación y esté conforme:

```bash
python fix_itbis_exchange_rate.py --apply
```

El script pedirá confirmación:
```
🔴 MODO ESCRITURA - Los datos SERÁN modificados

¿Está seguro de continuar? (escriba 'SI' para confirmar): SI
```

### 3. Con Credenciales Personalizadas

Si las credenciales no están en `facturas_config/config.json`:

```bash
python fix_itbis_exchange_rate.py --cred /ruta/a/credenciales.json
```

O para aplicar con credenciales personalizadas:

```bash
python fix_itbis_exchange_rate.py --cred /ruta/a/credenciales.json --apply
```

## ¿Qué facturas se corrigen?

El script corrige facturas que cumplan **TODAS** estas condiciones:

1. ✅ Moneda diferente a RD$, DOP, RD, DOP$
2. ✅ Tasa de cambio (exchange_rate) > 1.0
3. ✅ ITBIS > 0
4. ✅ El ITBIS no está ya corregido

**NO modifica:**
- ❌ Facturas en pesos dominicanos (RD$, DOP)
- ❌ Facturas sin ITBIS
- ❌ Facturas ya corregidas anteriormente
- ❌ Facturas donde el ITBIS ya parece estar en RD$

## Campos Actualizados

Para cada factura corregida, el script actualiza:

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| `itbis_original_currency` | ITBIS en moneda original | 180.00 (USD) |
| `itbis_rd` | ITBIS convertido a RD$ | 10,530.00 |
| `itbis` | Campo principal (ahora en RD$) | 10,530.00 |
| `total_amount_original_currency` | Total original (referencia) | 1,000.00 (USD) |

## Seguridad

- 🔒 **Modo dry-run por defecto**: No modifica nada sin su confirmación
- 🔒 **Confirmación requerida**: Debe escribir "SI" para aplicar cambios
- 🔒 **No sobrescribe datos correctos**: Valida antes de actualizar
- 🔒 **Preserva valores originales**: Los datos originales se guardan en `itbis_original_currency`
- 🔒 **Resumen detallado**: Muestra exactamente qué se modificó

## Verificación Post-Migración

Después de ejecutar el script con `--apply`:

### 1. Verificar en Firestore

Abrir Firebase Console → Firestore → `invoices`

Buscar una factura en moneda extranjera y verificar:
```javascript
{
  "currency": "USD",
  "exchange_rate": 58.5,
  "itbis": 10530.00,                    // ✅ Ahora en RD$
  "itbis_original_currency": 180.00,     // ✅ Original preservado
  "itbis_rd": 10530.00,                  // ✅ Convertido
  "total_amount": 1000.00,
  "total_amount_original_currency": 1000.00,
  "total_amount_rd": 58500.00
}
```

### 2. Verificar en la Aplicación

1. Abrir **"Resumen ITBIS"** en el menú
2. Verificar que los montos de ITBIS ahora sean correctos en RD$
3. Los totales deben ser mucho mayores que antes

### 3. Verificar Reportes

Los reportes de ITBIS ahora deberían mostrar:
- Montos correctos en RD$
- Totales que coincidan con declaraciones
- Separación entre ITBIS compensable y por pagar correcta

## Soporte

Si encuentra problemas:

1. **El script no encuentra facturas**: Verifique que las credenciales sean correctas
2. **Error de conexión**: Verifique acceso a internet y credenciales de Firebase
3. **Facturas no se corrigen**: Ejecute en modo dry-run primero para ver detalles

## Requisitos

- Python 3.8+
- `firebase-admin` instalado: `pip install firebase-admin`
- Credenciales de Firebase con permisos de lectura/escritura en Firestore

## Ejemplo Completo

```bash
# 1. Primero simular
$ python fix_itbis_exchange_rate.py

# 2. Revisar la salida, verificar que las facturas listadas necesiten corrección

# 3. Si todo se ve bien, aplicar
$ python fix_itbis_exchange_rate.py --apply
¿Está seguro de continuar? (escriba 'SI' para confirmar): SI

# 4. El script muestra el progreso y resumen final
✅ Facturas corregidas: 35

# 5. Verificar en la aplicación
# Abrir FACTURAS 3.0 → Resumen ITBIS → Verificar montos
```

---

**Creado**: Enero 2026  
**Versión**: 1.0  
**Autor**: Sistema FACTURAS 3.0
