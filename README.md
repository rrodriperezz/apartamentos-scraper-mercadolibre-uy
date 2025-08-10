# 🏠 Buscador de Apartamentos 🏠 - MercadoLibre Uruguay

Un buscador automatizado de apartamentos en MercadoLibre Uruguay que te permite encontrar propiedades según tus criterios específicos y evitar ver los mismos anuncios una y otra vez.

## Características

- **Búsqueda por múltiples barrios** de Montevideo simultáneamente
- **Filtrado por precio** configurable
- **Filtrado por número de dormitorios**
- **Extracción de gastos comunes** desde cada apartamento (configurable)
- **Opción de búsqueda solo en las últimas 24 horas**
- **Sistema anti-duplicados** - no verás el mismo apartamento dos veces
- **Búsqueda en barrios específicos** o en todos a la vez
- **Completamente configurable** mediante archivo JSON

## Instalación

1. **Clona el repositorio:**

   ```bash
   git clone https://github.com/rrodriperezz/apartamentos-scraper-mercadolibre-uy.git buscador-apartamento
   cd buscador-apartamento
   ```

2. **Instala las dependencias:**

   ```bash
   pip install -r requirements.txt
   ```

3. **¡Listo para usar!**

## Configuración

El script utiliza el archivo `config.json` para toda la configuración. Aquí puedes personalizar:

### Barrios de búsqueda

```json
"barrios": {
  "cordon": "cordon",
  "tres-cruces": "tres-cruces",
  "aguada": "aguada",
  "pocitos": "pocitos"
}
```

### Criterios de búsqueda

```json
"url_config": {
  "numero_dormitorios": "2",           // Número de dormitorios
  "departamento": "montevideo",        // Departamento
  "precio_minimo": "0",               // Precio mínimo en UYU
  "precio_maximo": "30000",           // Precio máximo en UYU
  "ultimas24hrs": true                // Solo publicaciones de hoy
}
```

### Gastos comunes

```json
"gastos_comunes": {
  "obtener_gastos_comunes": true       // true = obtener gastos, false = más rápido
}
```

** Importante sobre gastos comunes:**

- **`true`**: El script visitará cada apartamento individualmente para extraer los gastos comunes. Esto proporciona información más completa pero **es significativamente más lento** ya que debe hacer una request HTTP adicional por cada apartamento encontrado.

- **`false`**: El script solo obtendrá la información visible en los listados (título, precio, ubicación). Es **mucho más rápido** pero no incluirá gastos comunes en los resultados.

**Recomendación**: Usa `false` para búsquedas rápidas y exploratorias, y `true` cuando necesites información completa de gastos.

### Palabras a excluir

```json
"palabras_excluir": [
  "temporario",
  "temporal",
  "compartido",
  "solo mujeres",
  "solo hombres"
]
```

### Control de duplicados

```json
"duplicados": {
  "archivo_visitados": "apartamentos_visitados.txt",
  "filtrar_duplicados": true
}
```

### Configuración de paginación

```json
"max_paginas": 10                     // Máximo número de páginas a procesar por query
```

## Uso

### Búsqueda básica en todos los barrios

```bash
python main.py
```

### Búsqueda con logs detallados

```bash
python main.py --verbose
```

### Búsqueda en un barrio específico

```bash
python main.py --barrio pocitos --verbose
```

### Usar archivo de configuración personalizado

```bash
python main.py --config mi_config.json --verbose
```

### Búsqueda rápida sin gastos comunes

```bash
python main.py --sin-gastos-comunes --verbose
```

### Limpiar historial de apartamentos visitados

```bash
python main.py --limpiar-historial
```

## Personalización de configuración

### Cambiar rango de precios

Edita en `config.json`:

```json
"precio_minimo": "15000",
"precio_maximo": "35000"
```

### Buscar apartamentos de 1 dormitorio

```json
"numero_dormitorios": "1"
```

### Incluir apartamentos de cualquier fecha (no solo últimas 24hrs)

```json
"ultimas24hrs": false
```

### Configurar extracción de gastos comunes

```json
"gastos_comunes": {
  "obtener_gastos_comunes": false    // Para búsquedas más rápidas
}
```

### Agregar más barrios

```json
"barrios": {
  "cordon": "cordon",
  "pocitos": "pocitos",
  "buceo": "buceo",
  "malvin": "malvin"
}
```

### Personalizar palabras a excluir

```json
"palabras_excluir": [
  "temporario",
  "compartido",
  "estudiantes",
  "solo mujeres"
]
```

## Sistema anti-duplicados

El script mantiene un historial de apartamentos que ya has visto para no molestarte con los mismos anuncios.

**¿Cómo funciona?**

- Cada vez que encuentras apartamentos, sus URLs se guardan en `apartamentos_visitados.txt`
- En ejecuciones posteriores, estos apartamentos se filtran automáticamente
- Solo verás apartamentos **realmente nuevos**

**Gestión del historial:**

```bash
# Ver cuántos apartamentos tienes en el historial
wc -l apartamentos_visitados.txt

# Limpiar completamente el historial
python main.py --limpiar-historial
```

## Formato de salida

El script devuelve cada apartamento como una línea JSON independiente:

**Con gastos comunes activados:**

```json
{
  "titulo": "Apartamento 2 dormitorios Pocitos",
  "precio_alquiler": "28.000",
  "query_barrio": "pocitos",
  "precio_total_formatted": "31.500",
  "ubicacion": "Pocitos, Montevideo",
  "dormitorios": 2,
  "area": "65 m2",
  "gastos_comunes": 3500,
  "url": "https://apartamento.mercadolibre.com.uy/..."
}
```

**Con gastos comunes desactivados:**

```json
{
  "titulo": "Apartamento 2 dormitorios Pocitos",
  "precio_alquiler": "28.000",
  "query_barrio": "pocitos",
  "precio_total_formatted": "28.000",
  "ubicacion": "Pocitos, Montevideo",
  "dormitorios": 2,
  "area": "65 m2",
  "gastos_comunes": null,
  "url": "https://apartamento.mercadolibre.com.uy/..."
}
```

## Opciones de línea de comandos

```bash
python main.py [opciones]

Opciones:
  --verbose                    Mostrar logs detallados del proceso
  --config ARCHIVO            Usar archivo de configuración personalizado
  --limpiar-historial         Eliminar historial de apartamentos visitados
  --sin-filtro-duplicados     Mostrar todos los apartamentos (ignorar historial)
```

## Tips y recomendaciones

### Optimización de búsqueda

- Usa `ultimas24hrs: true` para búsquedas regulares
- Usa `ultimas24hrs: false` para búsquedas exhaustivas ocasionales
- **Para búsquedas rápidas**: desactiva gastos comunes con `"obtener_gastos_comunes": false`
- **Para análisis detallado**: activa gastos comunes pero ten paciencia con el tiempo de ejecución
- Personaliza las palabras a excluir según tus necesidades

### Múltiples configuraciones

Crea diferentes archivos de configuración para distintas necesidades:

- `config_rapido.json` - Sin gastos comunes, para exploración rápida
- `config_detallado.json` - Con gastos comunes, para análisis completo
- `config_estudiante.json` - Apartamentos económicos, incluir "compartido"
- `config_familia.json` - 3+ dormitorios, presupuesto más alto
- `config_inversion.json` - Rangos de precio específicos para inversión

## Solución de problemas

**El script no encuentra apartamentos:**

- Verifica que el rango de precios sea realista
- Revisa si `ultimas24hrs` está en `true` (puede que no haya publicaciones nuevas)
- Ejecuta con `--verbose` para ver los logs detallados

**El script es muy lento:**

- Desactiva gastos comunes: `"obtener_gastos_comunes": false`
- Reduce el número de páginas: `"max_paginas": 3`

**Aparecen apartamentos que no quiero:**

- Agrega palabras clave a `palabras_excluir` en la configuración
- Ajusta el rango de precios
- Verifica el número de dormitorios configurado

**Quiero ver apartamentos que ya había visto:**

- Usa `--sin-filtro-duplicados` para una ejecución
- O limpia el historial con `--limpiar-historial`
- O cambia la configuración en tu archivo de config.json

---

---

https://www.linkedin.com/in/rrodriperezz/
