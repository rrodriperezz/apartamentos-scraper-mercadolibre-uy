# apartamentos-scraper-mercadolibre-uy

Busca alquileres de apartamentos en MercadoLibre Uruguay por barrio, precio y dormitorios, y no repite los que ya viste. Imprime un JSON por línea.

## Correrlo

```bash
pip install -r requirements.txt
python main.py --barrio pocitos --verbose
```

Sin `--barrio` busca en todos los de `config.json`.

## Opciones

| Opción | Efecto |
|---|---|
| `--verbose` | Logs detallados |
| `--barrio X` | Un solo barrio |
| `--config ARCHIVO` | Otro archivo de configuración |
| `--sin-gastos-comunes` | Más rápido: no visita cada aviso |
| `--sin-filtro-duplicados` | Muestra también los ya vistos |
| `--limpiar-historial` | Borra `apartamentos_visitados.txt` |

## Configuración

`config.json` define barrios, precio máximo y mínimo, dormitorios, solo últimas 24 h, palabras a excluir y páginas máximas.

## Salida

```json
{"titulo": "Apartamento 2 dormitorios Pocitos", "query_barrio": "pocitos", "precio_total_formatted": "31.500", "gastos_comunes": 3500, "url": "https://apartamento.mercadolibre.com.uy/..."}
```
