# Etapa 3 — Amazon CloudFront

> **Estado:** ✅ completada
> **Costo de la etapa:** USD 0 (uso dentro del Free Tier permanente de CloudFront)

## 1. Objetivo

Servir el frontend a los usuarios **sin hacer público el bucket S3**:

- entregar el contenido por **HTTPS**;
- mantener el bucket privado, accesible solo para CloudFront;
- reducir la latencia sirviendo copias desde ubicaciones cercanas a los usuarios;
- entender cómo funciona la caché y cómo se invalida.

## 2. Conceptos clave

### 2.1 ¿Qué es un CDN?

**CDN** (*Content Delivery Network*): una red de servidores distribuidos en el mundo (**edge locations**) que guardan copias del contenido cerca de los usuarios.

```text
Primera request (cache MISS):
Usuario ──► Edge cercana ──(no tengo copia)──► Origin (S3 en us-east-1)
Usuario ◄── Edge cercana ◄──(guarda copia)──── Origin

Siguientes requests (cache HIT):
Usuario ──► Edge cercana ──(tengo copia)──► responde directo
```

### 2.2 Vocabulario

| Término | Qué es | En el proyecto |
|---|---|---|
| **Distribution** | Configuración de CloudFront: un dominio + reglas | Una distribución con dominio `*.cloudfront.net` |
| **Origin** | De dónde CloudFront obtiene el contenido original | El bucket S3 del frontend |
| **Edge location** | Punto de presencia donde se guardan copias | Gestionadas por AWS |
| **Cache** | Copia del contenido guardada en una edge | HTML, JS y CSS |
| **TTL** (*Time To Live*) | Tiempo que una copia se considera válida | Política de caché administrada por AWS |
| **Cache hit / miss** | *Hit*: la edge tenía copia. *Miss*: tuvo que ir al origin | Visible en el header `X-Cache` |
| **Invalidation** | Orden de descartar copias antes de que venza el TTL | Se usa después de cada cambio del frontend |
| **Default root object** | Archivo que se devuelve al pedir `/` | `index.html` |
| **Behavior** | Reglas por ruta (caché, métodos, protocolo) | Un único behavior *Default (\*)* |

**Cada edge location tiene su propia caché.** Dos usuarios en distintas regiones del mundo pueden recibir versiones distintas del mismo archivo hasta que se invalide o venza el TTL.

### 2.3 Origin Access Control (OAC)

OAC permite que CloudFront **firme** sus requests a S3. Así S3 puede distinguir a CloudFront de un usuario anónimo.

Firmar no alcanza: el bucket también debe **permitirlo** con una **bucket policy** (resource-based policy).

| Mecanismo | Rol |
|---|---|
| **OAC** | CloudFront **demuestra quién es** (autenticación) |
| **Bucket policy** | S3 **decide si lo deja pasar** (autorización) |
| **Block Public Access** | Impide que cualquier policy haga público el bucket |

> **OAI** (*Origin Access Identity*) es el mecanismo anterior y está considerado legacy. AWS recomienda OAC.

### 2.4 Flujo de una request

```text
Navegador
   │  GET https://<distribucion>.cloudfront.net/   (HTTPS)
   ▼
CloudFront (edge más cercana)
   │  ¿Hay copia válida en caché?
   │   ├── Sí → responde directo (HIT)
   │   └── No ↓ (MISS)
   │  GET /index.html firmado con OAC
   ▼
S3 (bucket privado)
   │  1. ¿Request firmada?                    → Sí, es CloudFront
   │  2. ¿La bucket policy la permite?         → Sí, y la Condition coincide con la distribución
   │  3. ¿Block Public Access la bloquea?      → No, no es acceso público
   ▼
Devuelve index.html → CloudFront guarda copia → responde al navegador
```

### 2.5 Acceso directo a S3

CloudFront **no envuelve** a S3: es otro camino. Una request a la URL directa del bucket **no pasa por CloudFront**.

```text
https://<bucket>.s3.us-east-1.amazonaws.com/index.html
   │
   ▼  request anónima, directo a S3
S3: ¿el principal es CloudFront?  → No → la policy no aplica → deny by default (+ BPA)
   ▼
403 AccessDenied
```

### 2.6 HTTPS

| Opción | Cómo | Costo | Uso |
|---|---|---|---|
| Dominio de CloudFront (`*.cloudfront.net`) | Certificado HTTPS incluido | Sin costo extra | ✅ Elegida |
| Dominio propio | Registro del dominio + certificado en ACM (**obligatoriamente en `us-east-1`**) + DNS | El dominio tiene costo anual | ❌ Posible mejora futura |

La **viewer protocol policy** está configurada como **Redirect HTTP to HTTPS**: ninguna request viaja sin cifrar entre el usuario y CloudFront.

### 2.7 WAF

**AWS WAF** (*Web Application Firewall*) inspecciona el contenido de cada request HTTP (capa 7) y bloquea patrones de ataque conocidos.

| | Firewall tradicional | WAF |
|---|---|---|
| Inspecciona | IPs y puertos (capas 3 y 4) | URL, headers y body de la request HTTP (capa 7) |
| Ejemplo | Bloquear el puerto 22 | Bloquear `' OR 1=1 --` en un parámetro |

## 3. Decisiones técnicas

| # | Decisión | Alternativas evaluadas | Motivo |
|---|---|---|---|
| D13 | **OAC** para acceder a S3 | OAI; bucket público | OAC es el mecanismo recomendado. OAI es legacy y no es compatible con los flat-rate plans. Un bucket público contradice D9 |
| D14 | Precio **pay-as-you-go** con Free Tier permanente | Flat-rate plan *Free* | Las cuentas en Free plan **no son elegibles** para flat-rate plans según la documentación. El Free Tier permanente (1 TB y 10 M requests/mes) supera ampliamente el uso del proyecto |
| D15 | **Sin AWS WAF** | Activar WAF | En pay-as-you-go tiene costo mensual fijo aunque no haya tráfico. Un frontend estático de solo lectura tiene poca superficie de ataque. Se reevaluará delante de la API |
| D16 | Dominio **`*.cloudfront.net`** | Dominio propio con ACM | Evita el costo del dominio. HTTPS incluido |
| D17 | **Standard logging desactivado** | Logs de acceso a S3 | Evita almacenamiento y costos adicionales en esta etapa |

> **Contexto para entrevistas:** el frontend se sirve únicamente a través de CloudFront por HTTPS. El bucket es privado: CloudFront se autentica con Origin Access Control y la bucket policy solo permite `s3:GetObject` al servicio CloudFront, con una condición que restringe el acceso a mi distribución. Evalué WAF y no lo activé para un frontend estático por costo/beneficio; tiene más sentido delante de la API.

## 4. Configuración realizada

### 4.1 Distribución

| Opción | Valor | Por qué |
|---|---|---|
| Nombre | `cloud-sec-checklist-frontend` | Identificación |
| Tipo | Single website or app | No es una plataforma multi-tenant |
| Dominio | `<distribucion>.cloudfront.net` | D16 |
| Origin | Bucket `cloud-sec-checklist-frontend-<sufijo>` (endpoint REST de S3, **no** `s3-website`) | El endpoint `s3-website` requiere bucket público |
| Acceso al origin | OAC (*Allow private S3 bucket access to CloudFront*) | D13 |
| Cache settings | Recomendadas por AWS | Política administrada |
| Security protections (WAF) | *Do not enable security protections* | D15 |
| Default root object | `index.html` | Pedir `/` devuelve la página principal |
| Viewer protocol policy | Redirect HTTP to HTTPS | Cifrado en tránsito obligatorio |
| Standard logging | Off | D17 |
| Tags | `Project = cloud-security-checklist` | D11 |

### 4.2 Bucket policy generada

La consola generó automáticamente esta policy al habilitar el acceso privado:

```json
{
    "Version": "2008-10-17",
    "Id": "PolicyForCloudFrontPrivateContent",
    "Statement": [
        {
            "Sid": "AllowCloudFrontServicePrincipal",
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudfront.amazonaws.com"
            },
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::cloud-sec-checklist-frontend-<sufijo>/*",
            "Condition": {
                "ArnLike": {
                    "AWS:SourceArn": "arn:aws:cloudfront::<cuenta>:distribution/<distribution-id>"
                }
            }
        }
    ]
}
```

| Campo | Valor | Significado |
|---|---|---|
| `Version` | `2008-10-17` | Versión del lenguaje de policies. La actual es `2012-10-17`, y es la que se usará en las policies propias del proyecto |
| `Id` / `Sid` | Nombres descriptivos | Opcionales; identifican la policy y cada *statement* |
| `Effect` | `Allow` | La regla permite |
| `Principal` | `Service: cloudfront.amazonaws.com` | **Quién:** el servicio CloudFront (*service principal*) |
| `Action` | `s3:GetObject` | **Qué:** solo leer objetos → least privilege |
| `Resource` | `arn:aws:s3:::<bucket>/*` | **Sobre qué:** los objetos del bucket |
| `Condition` | `AWS:SourceArn` = ARN de la distribución | **Solo si** la request viene de **esta** distribución |

**Por qué es importante la `Condition`:** sin ella, la policy permitiría el acceso a **cualquier distribución de CloudFront de cualquier cuenta de AWS**. Un atacante podría crear su propia distribución apuntando a este bucket.

**ARN del bucket vs. ARN de los objetos:**

| ARN | Se refiere a | Acciones típicas |
|---|---|---|
| `arn:aws:s3:::<bucket>` | El bucket | `s3:ListBucket`, configuración del bucket |
| `arn:aws:s3:::<bucket>/*` | Los objetos | `s3:GetObject`, `s3:PutObject` |

**Por qué falta `s3:ListBucket` (y es intencional):** si se pide un archivo inexistente (`/secreto.html`), S3 no puede revelar si existe a quien no tiene permiso de listar. CloudFront recibe **403 en lugar de 404**. Así se evita la **enumeración** de archivos.

**El ARN de CloudFront tiene cuenta pero no región**, porque CloudFront es un servicio global.

## 5. Verificación

| # | Prueba | Resultado esperado | Resultado |
|---|---|---|---|
| V1 | Abrir `https://<distribucion>.cloudfront.net` | Se ve el `<h1>` de `index.html` | ✅ |
| V2 | Abrir la misma URL con `http://` | Redirección a `https://` | ✅ |
| V3 | Abrir la URL directa de S3 en incógnito | `403 AccessDenied` | ✅ |
| V4 | Bucket → *Permissions* → *Bucket policy* | Policy con `Principal` CloudFront, `s3:GetObject` y `Condition` con el ARN de la distribución | ✅ |
| V5 | Ejercicio de caché e invalidation (sección 6) | Texto viejo antes de invalidar, texto nuevo después | ✅ |

**Headers útiles para diagnosticar la caché:**

```text
curl -sI https://<distribucion>.cloudfront.net/ | grep -iE "x-cache|age"
```

| Header | Significado |
|---|---|
| `X-Cache: Hit from cloudfront` | Respuesta servida desde la caché de la edge |
| `X-Cache: Miss from cloudfront` | La edge no tenía copia y fue al origin |
| `Age` | Segundos que lleva la copia en la caché de la edge |

## 6. Caché e invalidation: debugging

**Síntoma:** después de subir un `index.html` modificado a S3, la URL de CloudFront seguía mostrando el contenido anterior, incluso en una ventana de incógnito.

| Hipótesis | Evidencia | Resultado |
|---|---|---|
| H1: el archivo no se guardó o no se subió | El archivo en S3 tenía el contenido nuevo | ❌ Descartada |
| H2: no había caché involucrada | El contenido viejo persistía hasta invalidar | ❌ Descartada |
| H3: S3 tenía el contenido nuevo y CloudFront servía la copia vieja | La invalidation resolvió el problema | ✅ Confirmada |

```text
1. Upload del nuevo index.html      → S3: contenido NUEVO
2. Request a CloudFront             → Edge: copia válida (TTL vigente) → contenido VIEJO (HIT)
3. Invalidation de /index.html      → todas las edges descartan su copia
4. Nueva request                    → Edge sin copia → va a S3 → contenido NUEVO (MISS)
```

**Invalidation por CLI:**

```text
aws cloudfront create-invalidation --distribution-id <ID> --paths "/index.html"
aws cloudfront get-invalidation --distribution-id <ID> --id <ID-invalidation>
```

| Aspecto | Detalle |
|---|---|
| Permiso | `cloudfront:CreateInvalidation` / `cloudfront:GetInvalidation` |
| Efecto | Descarta copias en caché; **no borra nada del bucket** |
| Costo | Las primeras 1.000 rutas invalidadas por mes no tienen costo; `/*` cuenta como una ruta |

> **Lección de debugging:** juntar la evidencia **antes** de aplicar la solución. Si se arregla primero, después no se puede demostrar la causa.

## 7. Costos

Según la [página oficial de precios de CloudFront](https://aws.amazon.com/cloudfront/pricing/):

| Modelo | Incluye | Disponible para esta cuenta |
|---|---|---|
| **Pay-as-you-go + Free Tier permanente** | 1 TB de transferencia y 10 M de requests HTTP(S) por mes | ✅ Elegido |
| **Flat-rate plan Free** (USD 0/mes) | 1 M de requests y 100 GB por mes, con WAF y protección DDoS, sin cargos excedentes | ❌ Las cuentas en Free plan no son elegibles |

**Riesgos de costo:**

| Riesgo | Mitigación |
|---|---|
| AWS WAF (cargo mensual fijo + por request) | No activado (D15) |
| Logs de acceso | Desactivados (D17) |
| Dominio propio | No utilizado (D16) |
| Invalidations masivas | Usar pocas rutas o `/*` (cuenta como una) |

## 8. Relación con Cloud Security

| Control | Implementación |
|---|---|
| Bucket nunca público | Block Public Access + OAC + bucket policy con `Condition` |
| Cifrado en tránsito | HTTPS obligatorio (redirect HTTP → HTTPS) |
| Least privilege | CloudFront solo tiene `s3:GetObject`, y solo para esta distribución |
| Prevención de enumeración | Sin `s3:ListBucket` → 403 ante archivos inexistentes |
| Reducción de superficie de ataque | Los usuarios nunca acceden directamente a S3 |
| Protección DDoS básica | AWS Shield Standard, incluido sin costo |

## 9. Cómo revertir esta etapa

| Paso | Acción | Motivo |
|---|---|---|
| 1 | Distribución → **Disable** y esperar a que termine de propagarse | No se puede borrar una distribución habilitada |
| 2 | Distribución → **Delete** | — |
| 3 | CloudFront → *Security* → **Origin access** → borrar el **OAC** | Queda huérfano al borrar la distribución |
| 4 | Bucket → *Permissions* → borrar la **bucket policy** | Queda apuntando a una distribución que ya no existe |
| 5 | Verificar que la distribución, el OAC y la policy no existen | Procedimiento *Destroy → Verify* |

## 10. Cosas que NO se deben hacer

- ❌ Usar el endpoint `s3-website` como origin (requiere bucket público).
- ❌ Quitar la `Condition` de la bucket policy.
- ❌ Agregar `s3:ListBucket` a la policy de CloudFront sin necesidad.
- ❌ Activar WAF o logging sin revisar su costo.
- ❌ Usar OAI en configuraciones nuevas.
- ❌ Publicar capturas con el ID de cuenta o el ID de la distribución visibles.
