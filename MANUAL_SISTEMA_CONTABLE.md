# 📚 MANUAL DE USUARIO - SISTEMA CONTABLE PROFESIONAL

**FACTURAS 3.0 - Sistema Contable con Partida Doble**  
**Versión:** 3.0  
**Fecha:** Enero 2026

---

## 📋 Índice

1. [Introducción](#introducción)
2. [Conceptos Básicos de Contabilidad](#conceptos-básicos)
3. [Acceso al Sistema Contable](#acceso-al-sistema)
4. [Plan de Cuentas](#plan-de-cuentas)
5. [Asientos Contables](#asientos-contables)
6. [Estados Financieros](#estados-financieros)
7. [Consultas y Reportes](#consultas-y-reportes)
8. [Integración con Facturas](#integración-con-facturas)
9. [Casos de Uso Prácticos](#casos-de-uso)
10. [Preguntas Frecuentes](#preguntas-frecuentes)

---

## 📖 Introducción

El **Sistema Contable Profesional** de FACTURAS 3.0 es un módulo completo de contabilidad que implementa el método de **partida doble**, cumpliendo con las normas contables de República Dominicana.

### Características Principales

✅ **Partida Doble Automática**: El sistema valida que débito = crédito en cada asiento  
✅ **Plan de Cuentas Estándar**: 59 cuentas predefinidas según normativa RD  
✅ **Asientos Automáticos**: Genera asientos desde facturas emitidas y gastos  
✅ **Estados Financieros**: Balance General, Estado de Resultados, Libro Mayor  
✅ **Exportación PDF**: Reportes profesionales listos para imprimir  
✅ **Integración Total**: Conectado con facturación y análisis financiero  

---

## 📚 Conceptos Básicos de Contabilidad

### ¿Qué es la Partida Doble?

La partida doble es un sistema contable donde cada transacción afecta al menos dos cuentas:

- **DÉBITO**: Incrementa activos o gastos / Disminuye pasivos o ingresos
- **CRÉDITO**: Incrementa pasivos o ingresos / Disminuye activos o gastos

**Regla de Oro**: En cada asiento, la suma de débitos DEBE ser igual a la suma de créditos.

### Tipos de Cuentas

#### 1. ACTIVOS 💰
Bienes y derechos que posee la empresa.
- **Naturaleza**: DÉBITO
- **Ejemplos**: Caja, Banco, Cuentas por Cobrar, Edificios, Equipos

#### 2. PASIVOS 📋
Obligaciones y deudas de la empresa.
- **Naturaleza**: CRÉDITO
- **Ejemplos**: Cuentas por Pagar, ITBIS por Pagar, Préstamos Bancarios

#### 3. PATRIMONIO 💎
Recursos propios de la empresa.
- **Naturaleza**: CRÉDITO
- **Ejemplos**: Capital Social, Utilidades Retenidas

#### 4. INGRESOS 📈
Entradas de dinero por actividades de la empresa.
- **Naturaleza**: CRÉDITO
- **Ejemplos**: Ventas de Servicios, Ingresos por Intereses

#### 5. GASTOS 📉
Costos necesarios para operar el negocio.
- **Naturaleza**: DÉBITO
- **Ejemplos**: Salarios, Alquiler, Servicios Públicos, Papelería

### Ecuación Contable Fundamental

```
ACTIVOS = PASIVOS + PATRIMONIO
```

Si esta ecuación no se cumple, hay un error en los registros contables.

---

## 🚀 Acceso al Sistema Contable

### Paso 1: Abrir el Módulo

1. En la ventana principal de FACTURAS 3.0
2. Buscar el botón **"📚 Contabilidad"** en el menú lateral izquierdo
3. Hacer clic para abrir el menú de opciones contables

### Paso 2: Menú de Contabilidad

Al hacer clic, se despliega un menú con las siguientes opciones:

#### ⚙️ Configuración
- **📊 Plan de Cuentas** - Administrar el catálogo de cuentas
- **🆕 Inicializar Plan de Cuentas** - Crear las 59 cuentas estándar

#### 📝 Movimientos
- **✏️ Crear Asiento Manual** - Registrar transacciones manualmente
- **🧪 Generar Asientos desde Facturas** - Contabilizar facturas automáticamente

#### 📖 Consultas
- **📓 Libro Diario** - Ver todos los asientos cronológicamente
- **📖 Libro Mayor** - Ver movimientos por cuenta específica

#### 📈 Estados Financieros
- **💰 Balance General** - Estado de situación financiera
- **📊 Estado de Resultados** - Utilidades y pérdidas del periodo
- **💵 Flujo de Efectivo** - Entradas y salidas de efectivo
- **💎 Cambios en Patrimonio** - Evolución del capital

---

## 📊 Plan de Cuentas

### Inicializar el Plan de Cuentas Estándar

**Primera vez que usa el sistema:**

1. Click en **"Contabilidad"** → **"Inicializar Plan de Cuentas"**
2. Seleccionar empresa y año fiscal
3. Click en **"Inicializar"**
4. El sistema creará automáticamente **59 cuentas** estándar

### Estructura del Plan de Cuentas

El plan de cuentas tiene **4 niveles** jerárquicos:

```
1. GRUPO           (Nivel 1) - Ej: 1.0.0.000 ACTIVOS
  1.1. SUBGRUPO    (Nivel 2) - Ej: 1.1.0.000 ACTIVOS CORRIENTES
    1.1.1. CUENTA  (Nivel 3) - Ej: 1.1.1.000 Efectivo
      1.1.1.001    (Nivel 4) - Ej: 1.1.1.001 Caja General (DETALLE)
```

**⚠️ IMPORTANTE**: Solo las cuentas de **nivel 4 (detalle)** pueden recibir movimientos.

### Cuentas Estándar Principales

#### ACTIVOS (1.x.x.xxx)

**Activos Corrientes (1.1.x.xxx)**
- `1.1.1.001` - Caja General
- `1.1.1.002` - Banco BHD León
- `1.1.1.003` - Banco Popular
- `1.1.2.001` - Clientes Nacionales
- `1.1.2.002` - Clientes Extranjeros
- `1.1.4.001` - ITBIS por Compensar

**Activos No Corrientes (1.2.x.xxx)**
- `1.2.1.001` - Terrenos
- `1.2.1.002` - Edificios
- `1.2.1.003` - Equipos de Oficina
- `1.2.1.004` - Vehículos
- `1.2.1.005` - (-) Depreciación Acumulada

#### PASIVOS (2.x.x.xxx)

**Pasivos Corrientes (2.1.x.xxx)**
- `2.1.1.001` - Proveedores Locales
- `2.1.1.002` - Proveedores Extranjeros
- `2.1.2.001` - ITBIS por Pagar
- `2.1.2.002` - ISR por Pagar
- `2.1.2.003` - Retenciones por Pagar

**Pasivos No Corrientes (2.2.x.xxx)**
- `2.2.1.001` - Préstamos Bancarios LP
- `2.2.1.002` - Documentos por Pagar LP

#### PATRIMONIO (3.x.x.xxx)
- `3.1.1.001` - Capital Social
- `3.1.2.001` - Utilidades Retenidas
- `3.1.3.001` - Utilidad del Ejercicio

#### INGRESOS (4.x.x.xxx)
- `4.1.1.001` - Ingresos por Servicios
- `4.1.1.002` - Ventas de Productos
- `4.1.2.001` - Ingresos Financieros

#### GASTOS (5.x.x.xxx)
- `5.1.1.001` - Costo de Ventas
- `5.2.1.001` - Gastos de Administración
- `5.2.1.002` - Salarios
- `5.2.1.003` - Alquiler
- `5.2.1.004` - Servicios Públicos
- `5.2.2.001` - Gastos Financieros

### Gestionar el Plan de Cuentas

#### Ver el Plan de Cuentas

1. Click en **"Plan de Cuentas"**
2. Se abre una ventana con vista de árbol jerárquica
3. Expandir/contraer niveles con los triángulos ▶️

#### Buscar una Cuenta

1. En el campo **"🔍 Buscar"**
2. Escribir código o nombre de la cuenta
3. Presionar Enter

#### Filtrar por Tipo

Use los botones de filtro:
- **💰 ACTIVO** - Solo activos
- **📋 PASIVO** - Solo pasivos
- **💎 PATRIMONIO** - Solo patrimonio
- **📈 INGRESO** - Solo ingresos
- **📉 GASTO** - Solo gastos

#### Crear una Cuenta Nueva

1. Click en **"➕ Nueva Cuenta"**
2. Llenar el formulario:
   - **Código**: Ej: `1.1.1.004`
   - **Nombre**: Ej: "Banco Reservas"
   - **Tipo**: ACTIVO
   - **Categoría**: EFECTIVO
   - **Cuenta Padre**: `1.1.1.000`
   - **Nivel**: 4
   - **Naturaleza**: DEBITO
   - **Es Detalle**: ✅ Sí (si recibirá movimientos)
3. Click en **"Guardar"**

**⚠️ VALIDACIONES:**
- El código debe ser único
- No puede eliminar cuentas con movimientos
- La naturaleza debe coincidir con el tipo de cuenta

---

## ✏️ Asientos Contables

### ¿Qué es un Asiento Contable?

Un asiento contable es el registro de una transacción que afecta al menos dos cuentas, siguiendo la partida doble.

### Crear un Asiento Manual

#### Paso 1: Abrir Formulario

1. **"Contabilidad"** → **"Crear Asiento Manual"**
2. Se abre el formulario de nuevo asiento

#### Paso 2: Datos Generales

- **Fecha**: Fecha de la transacción (calendario)
- **Referencia**: Número o código (Ej: "FAC-2025-001", "PAGO-001")
- **Descripción**: Explicación de la transacción

#### Paso 3: Agregar Líneas del Asiento

1. Click en **"➕ Agregar Línea"**
2. Para cada línea:
   - **Cuenta**: Seleccionar del combo (solo cuentas detalle)
   - **Descripción**: Detalle de esta línea
   - **Débito**: Monto si es débito (dejar vacío si es crédito)
   - **Crédito**: Monto si es crédito (dejar vacío si es débito)

**⚠️ IMPORTANTE**: Debe tener mínimo 2 líneas.

#### Paso 4: Verificar Balance

En la parte inferior se muestra:
- **Total Débito**: Suma de todos los débitos
- **Total Crédito**: Suma de todos los créditos
- **Estado**: 
  - ✅ **CUADRADO** - Si débito = crédito
  - ❌ **DESCUADRADO** - Si hay diferencia

#### Paso 5: Guardar

1. Click en **"💾 Guardar Asiento"**
2. Si está cuadrado → Se guarda exitosamente
3. Si está descuadrado → Error, debe corregir

### Ejemplo Práctico: Venta de Servicios

**Situación**: Vendemos servicios por RD$ 100,000 + ITBIS 18% = RD$ 118,000

**Asiento Contable:**

| Cuenta                        | Código      | Débito    | Crédito   |
|-------------------------------|-------------|-----------|-----------|
| Clientes Nacionales           | 1.1.2.001   | 118,000   |           |
| Ingresos por Servicios        | 4.1.1.001   |           | 100,000   |
| ITBIS por Pagar              | 2.1.2.001   |           | 18,000    |
| **TOTAL**                     |             | **118,000** | **118,000** |

**Descripción**: "Venta de servicios a Cliente XYZ según factura FAC-2025-001"

### Ejemplo Práctico: Compra de Suministros

**Situación**: Compramos papelería por RD$ 5,000 + ITBIS 18% = RD$ 5,900

**Asiento Contable:**

| Cuenta                        | Código      | Débito    | Crédito   |
|-------------------------------|-------------|-----------|-----------|
| Gastos de Administración      | 5.2.1.001   | 5,000     |           |
| ITBIS por Compensar          | 1.1.4.001   | 900       |           |
| Proveedores Locales          | 2.1.1.001   |           | 5,900     |
| **TOTAL**                     |             | **5,900** | **5,900** |

**Descripción**: "Compra de papelería a Librería ABC según factura B01-0001234"

### Ejemplo Práctico: Pago de Alquiler

**Situación**: Pagamos alquiler mensual RD$ 15,000 en efectivo

**Asiento Contable:**

| Cuenta                        | Código      | Débito    | Crédito   |
|-------------------------------|-------------|-----------|-----------|
| Alquiler                     | 5.2.1.003   | 15,000    |           |
| Caja General                 | 1.1.1.001   |           | 15,000    |
| **TOTAL**                     |             | **15,000** | **15,000** |

**Descripción**: "Pago de alquiler del mes de marzo 2025"

### Anular un Asiento

**Si se cometió un error:**

1. Ir a **"Libro Diario"**
2. Buscar el asiento a anular
3. Click derecho → **"Anular Asiento"**
4. Ingresar motivo de anulación
5. El sistema crea automáticamente un **asiento inverso**

**⚠️ IMPORTANTE**: No se elimina, se crea un nuevo asiento con débitos y créditos invertidos.

---

## 💼 Asientos Automáticos desde Facturas

### Configurar Contabilización Automática

El sistema puede generar asientos contables automáticamente cuando:
- Emites una factura (ingreso)
- Registras un gasto
- Recibes un pago

### Generar Asientos desde Facturas

#### Opción 1: Generar al Momento

Al crear una factura, marcar la opción:
- ☑️ **"Contabilizar automáticamente"**

#### Opción 2: Generar en Lote

1. **"Contabilidad"** → **"Generar Asientos desde Facturas"**
2. Seleccionar periodo (mes/año)
3. Opciones:
   - ☑️ Incluir facturas emitidas
   - ☑️ Incluir gastos
   - ☑️ Sobrescribir existentes (si necesita regenerar)
4. Click en **"Generar"**

### Asientos Generados Automáticamente

#### Factura Emitida (Ingreso)

```
DÉBITO:  Clientes Nacionales     = Total con ITBIS
CRÉDITO: ITBIS por Pagar        = Monto ITBIS
CRÉDITO: Ingresos por Servicios = Subtotal
```

#### Factura de Gasto

```
DÉBITO:  Gastos Operacionales   = Subtotal
DÉBITO:  ITBIS por Compensar    = Monto ITBIS
CRÉDITO: Proveedores Locales    = Total con ITBIS
```

---

## 📊 Estados Financieros

### Balance General

El **Balance General** muestra la situación financiera en un momento específico.

#### Abrir el Balance General

1. **"Contabilidad"** → **"Balance General"**
2. Seleccionar **Mes** y **Año**
3. Click en **"Generar"**

#### Estructura del Balance

```
╔═══════════════════════════════════════════════════════════════╗
║             BALANCE GENERAL - BARNHOUSE SERVICES SRL          ║
║                      Al 31 de Marzo 2025                      ║
╠═══════════════════════════════════════════════════════════════╣
║ ACTIVOS                                                       ║
╠═══════════════════════════════════════════════════════════════╣
║ Activos Corrientes:                                           ║
║   Caja General                           RD$    850,000       ║
║   Banco BHD León                        RD$    640,000       ║
║   Clientes Nacionales                   RD$  1,140,000       ║
║   ITBIS por Compensar                   RD$     45,000       ║
║   TOTAL ACTIVOS CORRIENTES              RD$  2,675,000       ║
║                                                               ║
║ Activos No Corrientes:                                        ║
║   Equipos de Oficina                    RD$    350,000       ║
║   Vehículos                             RD$  1,200,000       ║
║   (-) Depreciación Acumulada            RD$   (150,000)      ║
║   TOTAL ACTIVOS NO CORRIENTES           RD$  1,400,000       ║
║                                                               ║
║ TOTAL ACTIVOS                           RD$  4,075,000       ║
╠═══════════════════════════════════════════════════════════════╣
║ PASIVOS                                                       ║
╠═══════════════════════════════════════════════════════════════╣
║ Pasivos Corrientes:                                           ║
║   Proveedores Locales                   RD$    450,000       ║
║   ITBIS por Pagar                       RD$    180,000       ║
║   ISR por Pagar                         RD$     25,000       ║
║   TOTAL PASIVOS CORRIENTES              RD$    655,000       ║
║                                                               ║
║ Pasivos No Corrientes:                                        ║
║   Préstamos Bancarios LP                RD$  2,000,000       ║
║   TOTAL PASIVOS NO CORRIENTES           RD$  2,000,000       ║
║                                                               ║
║ TOTAL PASIVOS                           RD$  2,655,000       ║
╠═══════════════════════════════════════════════════════════════╣
║ PATRIMONIO                                                    ║
╠═══════════════════════════════════════════════════════════════╣
║   Capital Social                        RD$  1,000,000       ║
║   Utilidades Retenidas                  RD$    420,000       ║
║   TOTAL PATRIMONIO                      RD$  1,420,000       ║
╠═══════════════════════════════════════════════════════════════╣
║ TOTAL PASIVOS + PATRIMONIO              RD$  4,075,000       ║
╠═══════════════════════════════════════════════════════════════╣
║ ✅ VERIFICACIÓN: BALANCE CUADRADO                             ║
║    (Activos = Pasivos + Patrimonio)                          ║
╚═══════════════════════════════════════════════════════════════╝
```

#### Exportar a PDF

1. En la ventana del Balance General
2. Click en **"📄 Exportar PDF"**
3. Seleccionar ubicación y nombre del archivo
4. El PDF se genera con formato profesional

### Estado de Resultados (P&L)

El **Estado de Resultados** muestra las utilidades o pérdidas de un periodo.

#### Abrir el Estado de Resultados

1. **"Contabilidad"** → **"Estado de Resultados"**
2. Seleccionar **Mes** y **Año**
3. Click en **"Generar"**

#### Estructura del Estado de Resultados

```
╔═══════════════════════════════════════════════════════════════╗
║        ESTADO DE RESULTADOS - BARNHOUSE SERVICES SRL          ║
║                    Mes de Marzo 2025                          ║
╠═══════════════════════════════════════════════════════════════╣
║ Ingresos Operacionales                  RD$  3,200,000       ║
║ (-) Costo de Ventas                     RD$ (1,280,000)      ║
║ ══════════════════════════════════════════════════════        ║
║ = UTILIDAD BRUTA                        RD$  1,920,000       ║
║                                                               ║
║ (-) Gastos Operacionales:                                     ║
║     Gastos de Administración            RD$    680,000       ║
║     Salarios                            RD$    350,000       ║
║     Alquiler                            RD$     45,000       ║
║     Servicios Públicos                  RD$     45,000       ║
║     TOTAL GASTOS OPERACIONALES          RD$ (1,120,000)      ║
║ ══════════════════════════════════════════════════════        ║
║ = UTILIDAD OPERACIONAL                  RD$    800,000       ║
║                                                               ║
║ (-) Gastos Financieros                  RD$    (60,000)      ║
║ (+) Otros Ingresos                      RD$          0       ║
║ (-) Otros Gastos                        RD$          0       ║
║ ══════════════════════════════════════════════════════        ║
║ = UTILIDAD ANTES DE IMPUESTOS           RD$    740,000       ║
║                                                               ║
║ (-) ISR (27%)                           RD$   (199,800)      ║
║ ══════════════════════════════════════════════════════        ║
║ = UTILIDAD NETA                         RD$    540,200       ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## 📖 Consultas y Reportes

### Libro Diario

Lista cronológica de **todos los asientos contables**.

#### Ver el Libro Diario

1. **"Contabilidad"** → **"Libro Diario"**
2. Filtros opcionales:
   - Mes/Año
   - Estado (POSTED, DRAFT, REVERSED)
   - Referencia
3. Click en un asiento para ver detalles

### Libro Mayor

Movimientos de una **cuenta específica**.

#### Ver el Libro Mayor

1. **"Contabilidad"** → **"Libro Mayor"**
2. Seleccionar **Cuenta** (Ej: "Caja General")
3. Seleccionar **Fecha Inicial** y **Fecha Final**
4. Click en **"Consultar"**

#### Estructura del Libro Mayor

```
╔═══════════════════════════════════════════════════════════════╗
║          LIBRO MAYOR - CAJA GENERAL (1.1.1.001)               ║
║              Del 01/03/2025 al 31/03/2025                     ║
╠═══════════════════════════════════════════════════════════════╣
║ Saldo Inicial:                          RD$    500,000       ║
╠═════════════╦══════════════════════╦═══════════╦══════════════╣
║   Fecha     ║    Descripción       ║  Débito   ║   Crédito    ║
╠═════════════╬══════════════════════╬═══════════╬══════════════╣
║ 05/03/2025  ║ Cobro Fact. 001      ║  118,000  ║              ║
║ 10/03/2025  ║ Pago alquiler        ║           ║   15,000     ║
║ 15/03/2025  ║ Cobro Fact. 002      ║   87,000  ║              ║
║ 20/03/2025  ║ Pago servicios       ║           ║   45,000     ║
║ 25/03/2025  ║ Cobro Fact. 003      ║  205,000  ║              ║
╠═════════════╩══════════════════════╬═══════════╬══════════════╣
║ TOTALES                            ║  410,000  ║   60,000     ║
╠════════════════════════════════════╩═══════════╩══════════════╣
║ Saldo Final:                            RD$    850,000       ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## 🔗 Integración con Facturas

### Flujo Completo: Factura → Contabilidad

#### 1. Crear Factura de Venta

**Módulo de Ingresos:**
- Cliente: XYZ Corporation
- Servicios: RD$ 100,000
- ITBIS 18%: RD$ 18,000
- **Total: RD$ 118,000**
- ☑️ Contabilizar automáticamente

#### 2. Asiento Generado Automáticamente

```
Fecha: 15/03/2025
Referencia: FAC-2025-001
Descripción: Venta de servicios a XYZ Corporation

DÉBITO:  1.1.2.001 - Clientes Nacionales    = RD$ 118,000
CRÉDITO: 2.1.2.001 - ITBIS por Pagar        = RD$  18,000
CRÉDITO: 4.1.1.001 - Ingresos por Servicios = RD$ 100,000
```

#### 3. Impacto en Balance General

**Activos:**
- Clientes Nacionales: +RD$ 118,000

**Pasivos:**
- ITBIS por Pagar: +RD$ 18,000

**Resultado:**
- Ingresos: +RD$ 100,000

#### 4. Cobro de la Factura

Cuando el cliente paga:

```
DÉBITO:  1.1.1.001 - Caja General         = RD$ 118,000
CRÉDITO: 1.1.2.001 - Clientes Nacionales  = RD$ 118,000
```

---

## 💡 Casos de Uso Prácticos

### Caso 1: Inicio de Operaciones

**Situación**: Empresa nueva con capital inicial de RD$ 1,000,000

**Asiento:**
```
DÉBITO:  Caja General           = RD$ 1,000,000
CRÉDITO: Capital Social         = RD$ 1,000,000
Descripción: "Aporte inicial de socios"
```

### Caso 2: Compra de Equipo

**Situación**: Compramos computadoras por RD$ 85,000 + ITBIS

**Asiento:**
```
DÉBITO:  Equipos de Oficina     = RD$ 85,000
DÉBITO:  ITBIS por Compensar    = RD$ 15,300
CRÉDITO: Caja General           = RD$ 100,300
Descripción: "Compra de 5 computadoras"
```

### Caso 3: Préstamo Bancario

**Situación**: Recibimos préstamo de RD$ 500,000

**Asiento:**
```
DÉBITO:  Banco BHD León                = RD$ 500,000
CRÉDITO: Préstamos Bancarios LP       = RD$ 500,000
Descripción: "Préstamo bancario a 3 años"
```

### Caso 4: Pago de Salarios

**Situación**: Pagamos nómina mensual RD$ 120,000

**Asiento:**
```
DÉBITO:  Salarios                      = RD$ 120,000
CRÉDITO: Banco BHD León                = RD$ 120,000
Descripción: "Pago de nómina marzo 2025"
```

### Caso 5: Pago a Proveedor

**Situación**: Pagamos factura pendiente de RD$ 45,000

**Asiento:**
```
DÉBITO:  Proveedores Locales           = RD$ 45,000
CRÉDITO: Banco BHD León                = RD$ 45,000
Descripción: "Pago a Proveedor ABC"
```

---

## ❓ Preguntas Frecuentes

### ¿Puedo eliminar un asiento?

**No.** Los asientos no se eliminan, se **anulan** mediante un asiento inverso. Esto mantiene el rastro de auditoría.

### ¿Qué hago si el asiento no cuadra?

Revise que:
1. Todas las líneas tengan monto en débito O crédito (no ambos)
2. La suma de débitos = suma de créditos
3. No haya errores de digitación

### ¿Puedo modificar un asiento ya guardado?

**No.** Los asientos POSTED no se modifican. Debe anularlo y crear uno nuevo correctamente.

### ¿Cómo sé si mis balances están correctos?

En el Balance General debe cumplirse:
```
ACTIVOS = PASIVOS + PATRIMONIO
```

Si no cuadra, hay un error en los asientos.

### ¿El sistema calcula depreciación automáticamente?

Actualmente no. Debe registrar la depreciación manualmente cada mes.

### ¿Puedo agregar cuentas personalizadas?

**Sí.** Use el gestor de Plan de Cuentas para agregar cuentas según sus necesidades.

### ¿Se puede recuperar un asiento anulado?

No se puede "recuperar", pero puede crear un nuevo asiento con los mismos datos del original.

### ¿Los reportes se pueden exportar?

**Sí.** Todos los reportes principales (Balance, Estado de Resultados) pueden exportarse a PDF profesional.

### ¿Hay límite de asientos por mes?

No hay límite. Puede registrar tantos asientos como necesite.

### ¿El sistema maneja múltiples empresas?

**Sí.** Cada empresa tiene su propio plan de cuentas y asientos independientes.

---

## 📞 Soporte y Ayuda

Para soporte técnico o consultas:

- **Email**: soporte@facturas.com
- **Teléfono**: (809) 555-1234
- **Horario**: Lunes a Viernes, 8:00 AM - 6:00 PM

---

## 📝 Notas Finales

- Haga respaldos regulares de su base de datos
- Revise mensualmente que los balances cuadren
- Mantenga documentación física de todas las transacciones
- Consulte con su contador para casos complejos

---

**© 2026 FACTURAS 3.0 - Sistema Contable Profesional**  
**Versión del Manual: 1.0**
