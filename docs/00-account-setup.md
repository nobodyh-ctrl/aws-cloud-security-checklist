# Etapa 0 — Preparación segura de la cuenta AWS y control de costos

> **Estado:** ✅ completada
> **Costo de la etapa:** USD 0 (IAM y el monitoreo de AWS Budgets no tienen costo)

## 1. Objetivo

Preparar la cuenta de AWS para comenzar el desarrollo y el aprendizaje **antes de crear cualquier recurso**, de forma que:

- el usuario root quede protegido y no se use en el día a día;
- exista una identidad de trabajo separada, con MFA y sin credenciales permanentes;
- cualquier consumo inesperado de créditos genere una alerta;
- todo el proyecto viva en una única región.

## 2. Conceptos clave

### 2.1 Cómo decide AWS si una acción está permitida

Cada acción en AWS (desde la consola, la CLI, CDK o boto3) es una llamada a una API. Antes de ejecutarla, AWS responde tres preguntas:

| Pregunta | Concepto | Ejemplo |
|---|---|---|
| ¿Quién sos? | **Identidad** | Root, IAM user, IAM role |
| ¿Cómo lo demostrás? | **Credenciales** | Contraseña + MFA, access key, credenciales temporales |
| ¿Qué podés hacer? | **Permisos (policies)** | `AdministratorAccess`, `dynamodb:GetItem` sobre una tabla |

Si una acción no está explícitamente permitida, **se niega por defecto** (*deny by default*).

### 2.2 Identidades en IAM

| Identidad | Qué es | Uso en este proyecto |
|---|---|---|
| **Root user** | Dueño de la cuenta. Puede hacer todo y **no puede ser limitado** por policies de IAM | Solo para tareas que únicamente él puede hacer |
| **IAM user** | Identidad permanente, para una persona o programa | Identidad de trabajo diaria del administrador |
| **IAM group** | Conjunto de usuarios que comparten permisos | `Admins` |
| **IAM role** | Identidad sin contraseña que se *asume* temporalmente | Lo usarán Lambda y GitHub Actions (etapas futuras) |

> **Regla del proyecto:** las personas usan **usuarios**; los servicios usan **roles**.

### 2.3 Tipos de credenciales

| Credencial | ¿Vence? | Riesgo si se filtra |
|---|---|---|
| Contraseña + MFA (consola) | No | Bajo: sin el segundo factor no alcanza |
| **Access key** (IAM user) | **No**, hasta que se borre | Alto: funciona indefinidamente |
| **Credenciales temporales** (STS, al asumir un rol) | **Sí**, en minutos u horas | Limitado a una ventana corta de tiempo |

### 2.4 MFA vs. least privilege

| Medida | Qué reduce |
|---|---|
| **MFA** | La **probabilidad** de que un atacante acceda |
| **Least privilege** | El **impacto** (*blast radius*) si igualmente accede |

Una cuenta segura necesita las dos. Por eso tener MFA en el root no alcanza para usarlo a diario.

### 2.5 Modelo de responsabilidad compartida

| AWS es responsable de… | Yo soy responsable de… |
|---|---|
| Datacenters, hardware, red física, hipervisores | Quién accede a la cuenta y con qué permisos |
| Infraestructura de los servicios administrados | Configuración de los recursos (por ejemplo, que un bucket no sea público) |
| | Mis datos, mi código y mis credenciales |

## 3. Decisiones técnicas

| # | Decisión | Alternativas evaluadas | Motivo |
|---|---|---|---|
| D1 | Trabajar con un **IAM user** y no con el root | Root con MFA | El root no puede ser limitado: si se compromete, el impacto es total |
| D2 | **No** usar IAM Identity Center | Identity Center (credenciales temporales) | Requiere AWS Organizations. En una cuenta con Free plan, crear una Organization **pasa la cuenta automáticamente al Paid plan y hace vencer los créditos** |
| D3 | `AdministratorAccess` para el usuario administrador, **asignado vía grupo** | `PowerUserAccess` (no permite gestionar IAM, que el proyecto necesita); policy a medida (inviable sin conocer aún las acciones necesarias) | El usuario humano necesita permisos amplios para construir. **Least privilege se aplica a los componentes de la aplicación** (roles de Lambda y CI/CD) |
| D4 | **Sin access keys** | Access keys para la CLI | Son credenciales de larga duración. Para la CLI se evaluarán alternativas con credenciales temporales |
| D5 | Región única: **`us-east-1`** | `us-east-2`, `sa-east-1` | Bajo costo y disponibilidad de servicios. CloudFront exige que su certificado esté en `us-east-1`. Usar una sola región facilita verificar y eliminar recursos |

> **Contexto para entrevistas:** en un entorno empresarial usaría IAM Identity Center con credenciales temporales. En una cuenta personal con Free plan, activarlo implicaba perder los créditos, así que opté por un IAM user con MFA, sin access keys, y el root reservado para emergencias.

## 4. Configuración realizada

### 4.1 Usuario root

| Configuración | Estado |
|---|---|
| MFA activado | ✅ |
| Sin access keys | ✅ |
| Uso diario | ❌ Solo para tareas exclusivas del root |

### 4.2 Acceso a la facturación

Se activó **"IAM user and role access to Billing information"** (menú de la cuenta → *Account*).

Es una configuración **de la cuenta**, no del usuario, y **solo el root puede activarla**. Sin ella, ni siquiera un usuario con `AdministratorAccess` puede ver la facturación.

### 4.3 Identidad de trabajo

```text
IAM user (<admin-user>)
   │  pertenece a
   ▼
IAM group: Admins
   │  tiene adjunta
   ▼
AWS managed policy: AdministratorAccess
```

| Configuración | Valor |
|---|---|
| Acceso a la consola | ✅ Contraseña + MFA |
| Access keys | ❌ Ninguna |
| Permisos | Heredados del grupo `Admins` (no asignados directamente al usuario) |


### 4.4 Control de costos

**Contexto de la cuenta:** Free plan con USD 100 en créditos (más hasta USD 100 por actividades). El acceso gratuito termina a los 6 meses o al agotarse los créditos, lo que ocurra primero. En el Free plan no se cobra a la tarjeta, así que **el riesgo real es agotar los créditos y perder el acceso** antes de terminar el proyecto.

**Budget `monthly-credits-guard`:**

| Parámetro | Valor |
|---|---|
| Tipo | Cost budget, mensual, recurrente |
| Monto | USD 5 |
| Filtro | `Charge type` **Excludes** `Credit` |
| Agregación | Unblended costs |
| Alertas (email) | 50 % real · 100 % real · 100 % pronosticado |
| Acciones automáticas | Ninguna |

**Por qué se excluyen los créditos:**

```text
Costo de uso:          USD 3.00   ← lo que ve el budget (excluye Credit)
Créditos aplicados:   -USD 3.00
─────────────────────────────────
Total a pagar:         USD 0.00   ← lo que vería si incluyera Credit (nunca alertaría)
```

Excluir `Credit` **no evita que se consuman créditos**. Solo cambia **lo que el budget mide**, para que alerte sobre el consumo real.

> ⚠️ **Un budget no es un límite de gasto.** Es una alarma: AWS avisa, pero no apaga ni borra recursos. Además, los datos de facturación se actualizan con horas de retraso, así que la alerta no es instantánea.

**Otras medidas:**

- Alertas de Free Tier activadas en *Billing preferences*.
- Revisar el widget **"Estado del plan gratuito"** (créditos y días restantes) al empezar y al terminar cada sesión de trabajo.

### 4.5 Región

Región por defecto de la consola: **US East (N. Virginia) — `us-east-1`** (*Unified Settings → Default Region*).

## 5. Verificación

| # | Qué verificar | Dónde | Resultado esperado |
|---|---|---|---|
| V1 | Root con MFA y sin access keys | IAM → Panel → *Recomendaciones de seguridad* | Ambos checks en verde ✅ |
| V2 | El IAM user tiene MFA | IAM → Users → `<admin-user>` → *Security credentials* | Dispositivo MFA asignado |
| V3 | El IAM user no tiene access keys | IAM → Users → `<admin-user>` → *Security credentials* → *Access keys* | Lista vacía |
| V4 | Los permisos vienen del grupo | IAM → Users → `<admin-user>` → *Permissions* | `AdministratorAccess` heredada de `Admins`, ninguna policy adjunta directamente |
| V5 | El login exige MFA | Cerrar sesión y volver a entrar con la *sign-in URL* del IAM user | Pide el código MFA |
| V6 | El IAM user puede ver la facturación | Billing and Cost Management (con el IAM user) | Se ve el widget de créditos, sin *Access Denied* |
| V7 | El budget existe y está bien configurado | Billing → Budgets → `monthly-credits-guard` | Monto USD 5, filtro `Charge type Excludes Credit`, 3 alertas |
| V8 | Región por defecto | Selector de región al abrir la consola | `us-east-1` |

## 6. Cosas que NO se deben hacer

- ❌ Usar el root para el trabajo diario.
- ❌ Crear access keys para el root.
- ❌ Guardar contraseñas, access keys o el `.csv` de credenciales dentro del repositorio.
- ❌ Hacer clic en **"actualizar el plan"** o crear una AWS Organization sin evaluar que se pierden los créditos.
- ❌ Configurar *budget actions* automáticas sin entender qué permisos modifican.

## 7. Cómo revertir esta etapa

| Recurso | Cómo eliminarlo |
|---|---|
| Budget | Billing → Budgets → seleccionar → *Delete* |
| IAM user | IAM → Users → seleccionar → *Delete* (antes quitar el MFA y sacarlo del grupo) |
| IAM group | IAM → User groups → `Admins` → *Delete* |
| Acceso de IAM a Billing | Menú de la cuenta → *Account* → desactivar (solo el root) |

Ninguno de estos recursos genera costo, así que no es necesario eliminarlos al pausar el proyecto.
