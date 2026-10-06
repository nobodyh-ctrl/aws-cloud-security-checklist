# Etapa 1 — Conceptos fundamentales de Cloud y AWS

> **Estado:** ✅ completada
> **Costo de la etapa:** USD 0 (etapa conceptual, no se crearon recursos)

## 1. Objetivo

Construir el modelo mental necesario para el resto del proyecto **antes de crear cualquier recurso**:

- qué es la nube y cómo se interactúa con AWS;
- cómo está organizada la infraestructura global de AWS;
- qué cambia entre usar servidores y usar servicios serverless;
- cómo se cobra cada modelo y por qué eso define la arquitectura del proyecto.

## 2. Conceptos clave

### 2.1 ¿Qué es la nube?

Usar cómputo, almacenamiento y red de los datacenters de otra empresa, **pedidos por API** y **pagados por uso**.

| Modelo tradicional | Cloud |
|---|---|
| Se compra o alquila un servidor por mes | Los recursos se crean por API o consola en minutos |
| Se paga aunque no se use | Se paga por uso (segundos, requests, GB) |
| Escalar implica comprar más hardware | Se escala pidiendo más capacidad, incluso de forma automática |
| El dueño gestiona discos, red y energía | El proveedor gestiona la infraestructura física |

### 2.2 Todo en AWS es una API

La consola, la CLI, CDK y boto3 son **distintas formas de llamar a las mismas APIs**.

```text
Consola web ─┐
AWS CLI ─────┤
AWS CDK ─────┼──►  API de AWS  ──►  IAM: ¿está permitido?  ──►  Se ejecuta la acción
boto3 ───────┘                            │
                                          └──►  CloudTrail: queda registrado
```

Esto tiene dos consecuencias de seguridad:

| Consecuencia | Servicio | Qué permite |
|---|---|---|
| Cada acción se puede **controlar** | **IAM** | Permitir o negar acciones concretas (por ejemplo `s3:GetObject`) |
| Cada acción se puede **auditar** | **CloudTrail** | Registrar quién llamó a qué API, cuándo y desde dónde |

### 2.3 Infraestructura global de AWS

```text
AWS
 └── Región (ej: us-east-1, N. Virginia)        ← área geográfica
      ├── Availability Zone us-east-1a          ← uno o más datacenters,
      ├── Availability Zone us-east-1b             aislados entre sí
      ├── Availability Zone us-east-1c             (energía, red, refrigeración)
      └── ...

 + Edge locations (cientos en todo el mundo)    ← puntos de presencia de CloudFront
```

| Concepto | Qué es | Por qué importa |
|---|---|---|
| **Región** | Área geográfica con varios datacenters | Los recursos y los datos viven ahí. Precios y servicios disponibles varían por región |
| **Availability Zone (AZ)** | Uno o más datacenters físicamente separados dentro de una región | Si una AZ falla, las demás siguen funcionando |
| **Edge location** | Punto de presencia cercano a los usuarios | CloudFront sirve el contenido desde ahí, con menor latencia |

**Servicios regionales vs. globales:**

| Alcance | Servicios del proyecto |
|---|---|
| **Regional** | S3, API Gateway, Lambda, DynamoDB, CloudWatch |
| **Global** | IAM, CloudFront |

### 2.4 Multi-AZ vs. multi-región

| Escenario | App serverless en `us-east-1` | App en un único EC2 en `us-east-1a` |
|---|---|---|
| Falla la AZ `us-east-1a` | ✅ Sigue funcionando: Lambda, DynamoDB y S3 son multi-AZ por defecto | ❌ Se cae: el servidor vive en una sola AZ |
| Falla toda la región `us-east-1` | ❌ Se cae: la app vive en una sola región | ❌ Se cae |

Lograr tolerancia a fallos con EC2 requiere varias instancias en distintas AZ y un load balancer: más trabajo, más costo, más superficie de error. Los servicios serverless la incluyen sin configuración.

### 2.5 Modelos de servicio: qué gestiona cada parte

```text
                On-premise   EC2 (IaaS)   Contenedores    Lambda (serverless)
                                          (ECS/Fargate)
Código             YO           YO            YO               YO
Dependencias       YO           YO            YO               YO
Runtime            YO           YO            YO (imagen)      AWS
Sist. operativo    YO           YO            AWS              AWS
Servidor           YO           AWS           AWS              AWS
Escalado           YO           YO (config)   YO (config)      AWS (automático)
Hardware / red     YO           AWS           AWS              AWS
```

Un **servicio administrado** (*managed service*) es uno en el que AWS opera la infraestructura y el cliente solo lo usa. Ejemplo: DynamoDB es una base de datos sin instalación, parches ni gestión de discos.

### 2.6 Responsabilidad compartida según el modelo

Cuanto más administrado es el servicio, **menor** es la responsabilidad de seguridad del cliente, **pero nunca llega a cero**.

| Ejemplo: vulnerabilidad crítica en el kernel de Linux | ¿Quién la parcha? |
|---|---|
| Con EC2 | **Yo** |
| Con Lambda | **AWS** |

Aun usando Lambda, siguen siendo responsabilidad propia:

| Responsabilidad | Ejemplo de riesgo |
|---|---|
| Código | Bugs, falta de validación de entrada, inyecciones |
| Dependencias | Librerías con vulnerabilidades conocidas |
| Permisos (IAM) | Un rol con más permisos de los necesarios |
| Configuración | Un bucket público, CORS abierto a cualquier origen |
| Datos | Información sensible guardada sin necesidad |

### 2.7 Modelos de cobro

| Servicio | Se cobra por… | ¿Cuesta si nadie lo usa? |
|---|---|---|
| **EC2** | Tiempo encendido + disco + IP pública | **Sí**, 24/7 |
| **Lambda** | Invocaciones + duración × memoria | **No** |
| **API Gateway** | Requests | **No** |
| **DynamoDB** (on-demand) | Lecturas, escrituras y GB almacenados | Casi nada (solo almacenamiento) |
| **S3** | GB almacenados + requests + transferencia | Casi nada |
| **CloudFront** | Requests + transferencia | **No** |

> **Servidores:** se paga capacidad reservada. **Serverless:** se paga uso real.

**Ejemplo con el uso esperado del proyecto (~50 requests por semana):**

```text
Semana = 168 horas

EC2      → se cobran 168 horas, aunque el trabajo real sean unos segundos
Lambda   → se cobran solo los segundos de ejecución (dentro de la capa gratuita)
```

Para una aplicación de portfolio, que pasa casi todo el tiempo sin uso, **el modelo serverless consume una fracción mínima de los créditos**.

### 2.8 Costos ocultos a vigilar

| Costo | Por qué aparece | Cómo se mitiga en el proyecto |
|---|---|---|
| Transferencia de datos a internet | Los datos que salen de AWS se cobran | El frontend pesa pocos KB y se sirve vía CloudFront |
| Logs de CloudWatch | Se acumulan si no tienen retención | Configurar retención de logs |
| Recursos huérfanos | Quedan después de "borrar" la app | Procedimiento *Destroy → Verify* |
| Servicios que cobran por hora | NAT Gateway, load balancers, IPs públicas | No se usan en este proyecto |

## 3. Cómo aplica al proyecto

| Componente | Modelo | Alcance | Se cobra por |
|---|---|---|---|
| CloudFront | Administrado | Global (edge locations) | Requests y transferencia |
| S3 (frontend) | Administrado | Regional, multi-AZ | GB y requests |
| API Gateway | Serverless | Regional | Requests |
| Lambda | Serverless | Regional, multi-AZ | Invocaciones y duración |
| DynamoDB | Serverless / administrado | Regional, multi-AZ | Lecturas, escrituras y GB |
| CloudWatch | Administrado | Regional | GB de logs ingeridos y almacenados |
| IAM | Administrado | Global | Sin costo |

**Ningún componente cobra por estar encendido.** Esta es la decisión de arquitectura más importante del proyecto.

## 4. Decisiones técnicas

| # | Decisión | Alternativas evaluadas | Motivo |
|---|---|---|---|
| D6 | Arquitectura **serverless** | EC2, contenedores (ECS/Fargate) | Costo proporcional al uso real, alta disponibilidad multi-AZ sin configuración, sin sistema operativo que parchar |
| D7 | **Una sola región**, aceptando el riesgo de una caída regional | Multi-región | Multi-región agrega complejidad y costo que no se justifican en un proyecto de portfolio |
| D8 | **No** usar EC2, RDS, ECS, EKS, NAT Gateway ni load balancers | — | Cobran por hora aunque no se usen y no resuelven ningún requisito actual del proyecto |



## 5. Relación con Cloud Security

- **IAM** controla cada llamada a la API → base de **least privilege**.
- **CloudTrail** registra cada llamada → base de la **auditoría**. Es uno de los checks de la aplicación.
- Elegir servicios administrados **reduce la superficie de ataque** propia, pero no elimina la responsabilidad sobre la configuración, que es justamente lo que evalúa un checklist de seguridad cloud.
