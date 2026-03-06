# Mi Siembra Inteligente 2.0 - PWA Offline-First

## Declaración del Problema Original
Crear una PWA instalable para planificación de huertos, seguimiento de cultivos, recordatorios automáticos, diario fotográfico, gestión de plagas/tratamientos y mapa del huerto. La app debe funcionar OFFLINE por defecto.

## Personas de Usuario
- **Horticultores caseros**: Personas que cultivan vegetales en casa para autoconsumo
- **Agricultores urbanos**: Personas con pequeñas parcelas o hidroponía
- **Jardineros principiantes**: Necesitan guía sobre qué sembrar y cuándo

## Requisitos Principales

### Prioridades del Usuario (en orden):
1. Funcionamiento completamente offline (IndexedDB + cache)
2. Recordatorios de riego y fertilización
3. Registro de cultivos en "Mi Huerto"
4. Calendario de siembra según clima
5. Diario/bitácora con fotos

### Características Implementadas:
- ✅ **PWA Offline-First**: Service Worker + IndexedDB
- ✅ **Modo Invitado**: Sin autenticación requerida
- ✅ **Navegación Mobile-First**: 5 tabs + menú hamburguesa
- ✅ **Dashboard**: Estadísticas de cultivos, tareas, cosechas
- ✅ **Widget de Clima**: Condiciones actuales + recomendaciones de riego/tratamiento (Open-Meteo API)
- ✅ **Calendario**: Recomendaciones según clima/hemisferio
- ✅ **Mi Huerto**: CRUD de cultivos con etapas
- ✅ **Fotos de Cultivos**: Cámara/galería, compresión automática (1024px/1MB), miniaturas, backup base64
- ✅ **Galería de Crecimiento por Cultivo**: Timeline de fotos con fecha y notas para documentar el crecimiento de cada planta
- ✅ **Tareas**: Recordatorios recurrentes de riego/fertilización
- ✅ **Notificaciones Push**: Alertas automáticas de tareas pendientes (Web Notifications API)
- ✅ **Alerta de Heladas**: Notificaciones cuando se pronostican temperaturas bajas (umbral configurable 0-5°C)
- ✅ **Integración con Calendario**: Exportar tareas a Google Calendar/Apple Calendar/Outlook (.ics)
- ✅ **Diario**: Entradas con fotos offline (IndexedDB Blobs)
- ✅ **Catálogo**: Biblioteca editable de cultivos
- ✅ **Mapa del Huerto**: Visualización de camas/zonas
- ✅ **Plagas y Tratamientos**: Guías de referencia
- ✅ **Diagnóstico**: Asistente de identificación de problemas
- ✅ **Cosechas**: Registro y reportes
- ✅ **Backup/Restore**: Exportar/importar JSON (incluye fotos en base64)
- ✅ **Almacenamiento**: Info de espacio usado por fotos
- ✅ **Temas**: Claro/Oscuro/Sistema
- ✅ **Datos Demo**: Datos extensos precargados

## Arquitectura Técnica

```
/app/frontend/
├── public/
│   ├── manifest.json      # PWA Manifest
│   └── service-worker.js  # Service Worker
├── src/
│   ├── components/
│   │   ├── layout/        # Header, BottomNav, Layout
│   │   ├── pages/         # 11 páginas principales
│   │   ├── shared/        # FAB, EmptyState, LoadingSpinner
│   │   └── ui/            # Shadcn/UI components
│   ├── context/
│   │   ├── DataContext.jsx    # Estado global + CRUD
│   │   └── ThemeContext.jsx   # Tema claro/oscuro
│   ├── lib/
│   │   ├── db.js          # IndexedDB schema (idb)
│   │   ├── dataService.js # Operaciones de datos
│   │   └── seedData.js    # Datos demo
│   ├── App.js             # Router principal
│   └── index.js           # Entry point + SW registration
└── package.json
```

## Esquema IndexedDB (db.js) - Version 2

| Store | Campos Principales |
|-------|-------------------|
| settings | id, climate, hemisphere, theme, initialized, notifications, frostAlerts, frostThreshold |
| beds | id, name, method (suelo/hidro), notes |
| catalog_crops | id, name, category, harvest_days, sow_months |
| my_crops | id, name, bed_id, sow_date, stage, est_harvest_date, photo_id, thumb_id |
| crop_gallery | id, crop_id, photo_id, thumb_id, date, note |
| tasks | id, title, type, due_datetime, repeat_rule, status |
| diary_entries | id, datetime, type, text, photo_ids, tags |
| harvests | id, crop_id, date, qty, unit, destination |
| pests | id, name, symptoms, affected_plants |
| treatments | id, name, usage, target_pests, organic |
| photos | id, blob, type, size, created_at |

## Estado de Testing

| Feature | Status |
|---------|--------|
| Dashboard | ✅ PASS |
| Tareas | ✅ PASS |
| Mi Huerto | ✅ PASS |
| Calendario | ✅ PASS |
| Diario | ✅ PASS |
| Catálogo | ✅ PASS |
| Mapa | ✅ PASS |
| Opciones | ✅ PASS |
| Fotos Cultivos | ✅ PASS |
| Galería Crecimiento | ✅ PASS |
| Alertas Heladas | ✅ PASS |
| Diagnóstico | ✅ PASS |
| Navegación | ✅ PASS |
| Service Worker | ✅ Registrado |
| IndexedDB | ✅ Funcionando |
| Modo Offline | ✅ Detectado |

**Success Rate: 100%**

## Backlog (P1/P2)

### P1 - Próximas mejoras:
- [ ] Sincronización cloud opcional (backend FastAPI)
- [ ] Mejoras de accesibilidad (aria-describedby en dialogs)
- [ ] Notificaciones programadas en segundo plano (Background Sync API)

### P2 - Futuro:
- [ ] PWA install prompt mejorado
- [ ] Compartir datos entre dispositivos
- [ ] Integración con APIs de clima externas
- [ ] Más idiomas (inglés, portugués)

## Fecha de Última Actualización
6 de Marzo, 2026

## Changelog

### v2.1.1 (6 Marzo 2026)
- ✅ Corregido: Botón "Borrar Todo" ahora vacía la app correctamente (sin cargar datos demo)
- ✅ Nueva opción: "Cargar Datos de Ejemplo" separada de "Borrar Todo"
- ✅ Agregada página /reset.html para reset completo de emergencia
- ✅ Mejorada la zona de peligro con opciones claras

### v2.1.0 (6 Marzo 2026)
- ✅ Galería de fotos por cultivo (timeline de crecimiento con fecha y notas)
- ✅ Alertas de heladas configurables (umbral 0-5°C)
- ✅ Actualizado esquema IndexedDB a versión 2
- ✅ Generados iconos PNG para Play Store y App Store (todos los tamaños)
- ✅ Agregados meta tags iOS para PWA

### v2.0.0 (5 Marzo 2026)
- ✅ Lanzamiento inicial de Mi Siembra Inteligente 2.0 PWA
- ✅ Todas las características core implementadas
- ✅ Widget de clima con Open-Meteo API
- ✅ Notificaciones push para recordatorios
- ✅ Integración con calendario (.ics export)
- ✅ Fotos de cultivos con compresión automática

## URL de Preview
https://siembra-inteligente.preview.emergentagent.com
