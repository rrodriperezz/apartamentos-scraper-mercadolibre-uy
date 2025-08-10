#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

###############################################################################
# utilidades de logging
###############################################################################

def _printv(*args, _verbose: bool = False, **kwargs):
    """Imprime sólo si `_verbose` es True (helper interno)."""
    if _verbose:
        print(*args, **kwargs)

###############################################################################
# clase principal
###############################################################################


class BuscadorMercadoLibre:
    """Scraper robusto para resultados de Mercado Libre Uruguay."""

    URL_TEMPLATE = (
        "https://listado.mercadolibre.com.uy/"
        "inmuebles/apartamentos/{numero_dormitorios}-dormitorios/{departamento}/"
        "{query_barrio}_PriceRange_{precio_minimo}UYU-{precio_maximo}UYU{filtro_fecha}_NoIndex_True"
    )

    # ---------------------------------------------------------------------
    # life‑cycle
    # ---------------------------------------------------------------------

    def __init__(self, verbose: bool = False, config_file: str = "config.json", obtener_gastos_comunes: bool = True):
        self.verbose = verbose

        # Cargar configuración desde archivo
        config = self._cargar_configuracion(config_file)
        self.BARRIOS = config['barrios']
        self._palabras_excluir = config['palabras_excluir']
        self.url_config = config['url_config']
        self.duplicados_config = config['duplicados']
        self.max_paginas = config['max_paginas']
        self.obtener_gastos_comunes = config['gastos_comunes']['obtener_gastos_comunes']

        # Configurar valores basados en la configuración
        self.max_precio = int(self.url_config['precio_maximo'])
        self.dormitorios = int(self.url_config['numero_dormitorios'])

        # Cargar apartamentos ya visitados
        self.apartamentos_visitados = self._cargar_apartamentos_visitados()

        # headers / user‑agent rotation
        self._user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_6) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:128.0) Gecko/20100101 "
            "Firefox/128.0",
        ]

        self.session = requests.Session()
        self._actualizar_headers()

    def _cargar_configuracion(self, config_file: str) -> Dict[str, Any]:
        """Carga la configuración desde el archivo JSON."""
        try:
            if not os.path.exists(config_file):
                _printv(f"❌ Archivo de configuración {config_file} no encontrado", _verbose=self.verbose)
                sys.exit(1)

            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            barrios = config.get('barrios', {})
            if not barrios:
                _printv(f"❌ No se encontraron barrios en {config_file}", _verbose=self.verbose)
                sys.exit(1)

            palabras_excluir = config.get('palabras_excluir', [])
            if not palabras_excluir:
                _printv(f"❌ No se encontraron palabras a excluir en {config_file}", _verbose=self.verbose)
                sys.exit(1)

            url_config = config.get('url_config', {})
            if not url_config:
                _printv(f"❌ No se encontró configuración de URL en {config_file}", _verbose=self.verbose)
                sys.exit(1)

            duplicados_config = config.get('duplicados', {})
            if not duplicados_config:
                _printv(f"❌ No se encontró configuración de duplicados en {config_file}", _verbose=self.verbose)
                sys.exit(1)

            gastos_comunes_config = config.get('gastos_comunes', {'obtener_gastos_comunes': True})

            max_paginas = config.get('max_paginas', 3)  # valor por defecto 3

            _printv(f"✅ Configuración cargada: {len(barrios)} barrios, {len(palabras_excluir)} palabras a excluir, max {max_paginas} páginas", _verbose=self.verbose)
            return {
                'barrios': barrios,
                'palabras_excluir': palabras_excluir,
                'url_config': url_config,
                'duplicados': duplicados_config,
                'gastos_comunes': gastos_comunes_config,
                'max_paginas': max_paginas
            }

        except json.JSONDecodeError as e:
            _printv(f"❌ Error al parsear JSON en {config_file}: {e}", _verbose=self.verbose)
            sys.exit(1)
        except Exception as e:
            _printv(f"❌ Error cargando configuración: {e}", _verbose=self.verbose)
            sys.exit(1)

    def _cargar_apartamentos_visitados(self) -> set:
        """Carga las URLs de apartamentos ya visitados."""
        if not self.duplicados_config.get('filtrar_duplicados', True):
            return set()

        archivo = self.duplicados_config.get('archivo_visitados', 'apartamentos_visitados.txt')
        try:
            if os.path.exists(archivo):
                with open(archivo, 'r', encoding='utf-8') as f:
                    urls = {line.strip() for line in f if line.strip()}
                _printv(f"✅ Cargadas {len(urls)} URLs de apartamentos visitados", _verbose=self.verbose)
                return urls
            else:
                _printv(f"📝 Archivo {archivo} no existe, se creará al guardar nuevos apartamentos", _verbose=self.verbose)
                return set()
        except Exception as e:
            _printv(f"⚠️  Error cargando apartamentos visitados: {e}", _verbose=self.verbose)
            return set()

    def _guardar_apartamento_visitado(self, url: str) -> None:
        """Guarda una URL de apartamento como visitada."""
        if not self.duplicados_config.get('filtrar_duplicados', True):
            return

        archivo = self.duplicados_config.get('archivo_visitados', 'apartamentos_visitados.txt')
        try:
            with open(archivo, 'a', encoding='utf-8') as f:
                f.write(url + '\n')
            self.apartamentos_visitados.add(url)
        except Exception as e:
            _printv(f"⚠️  Error guardando apartamento visitado: {e}", _verbose=self.verbose)

    def _es_apartamento_nuevo(self, url: str) -> bool:
        """Verifica si el apartamento es nuevo (no visitado anteriormente)."""
        if not self.duplicados_config.get('filtrar_duplicados', True):
            return True
        return url not in self.apartamentos_visitados

    # ------------------------------------------------------------------
    # helpers de bajo nivel
    # ------------------------------------------------------------------

    def _actualizar_headers(self) -> None:
        headers = {
            "User-Agent": random.choice(self._user_agents),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "es-ES,es;q=0.9",
            "Connection": "keep-alive",
        }
        self.session.headers.update(headers)

    # --------------------------------------------------------------
    # regex helpers
    # --------------------------------------------------------------

    _RE_PRECIO_PESOS = re.compile(r"\$\s*([\d.]+)")
    _RE_PRECIO_USD = re.compile(r"US\$\s*(\d+)")
    _RE_AREA = re.compile(r"(\d+)\s*m[²2]", re.I)
    _RE_DORM = re.compile(r"(\d+)\s*dorm", re.I)
    _RE_GASTOS_COMUNES = re.compile(r"gastos comunes.*?\$\s*([\d.]+)", re.I)

    def _extraer_precio(self, texto: str) -> Optional[int]:
        if not texto:
            return None
        if (m := self._RE_PRECIO_PESOS.search(texto)):
            return int(m.group(1).replace(".", ""))
        if (m := self._RE_PRECIO_USD.search(texto)):
            return int(m.group(1)) * 40  # conversión estimada USD→UYU a dia de 10/08/2025
        return None

    def _extraer_gastos_comunes_desde_pagina(self, url: str) -> Optional[int]:
        """Extrae gastos comunes desde la página individual del apartamento."""
        if not url or not self.obtener_gastos_comunes:
            return None

        try:
            _printv(f"    💰 Obteniendo gastos comunes de: {url}", _verbose=self.verbose)

            # Request a la página individual
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                _printv(f"    ⚠️  Error {response.status_code} al obtener página individual", _verbose=self.verbose)
                return None

            soup = BeautifulSoup(response.content, "html.parser")

            # Buscar gastos comunes con selectores específicos
            gastos_elemento = soup.select_one('p.ui-pdp-maintenance-fee-ltr, .ui-pdp-container__row--maintenance-fee-vis p, *[id*="maintenance"]')

            if gastos_elemento:
                gastos_texto = gastos_elemento.get_text(strip=True)
                _printv(f"    💰 Texto gastos encontrado: {gastos_texto}", _verbose=self.verbose)

                # Usar regex mejorado para extraer el número
                if (m := self._RE_GASTOS_COMUNES.search(gastos_texto)):
                    gastos_valor = int(m.group(1).replace(".", ""))
                    _printv(f"    ✅ Gastos comunes: ${gastos_valor}", _verbose=self.verbose)
                    return gastos_valor
                else:
                    _printv(f"    ⚠️  Regex no coincidió con: {gastos_texto}", _verbose=self.verbose)

            # Fallback: buscar en todo el texto de la página
            texto_completo = soup.get_text(" ", strip=True)
            if (m := self._RE_GASTOS_COMUNES.search(texto_completo)):
                gastos_valor = int(m.group(1).replace(".", ""))
                _printv(f"    ✅ Gastos comunes (fallback): ${gastos_valor}", _verbose=self.verbose)
                return gastos_valor
            else:
                _printv(f"    ⚠️  Regex fallback tampoco coincidió", _verbose=self.verbose)

            _printv(f"    ❌ No se encontraron gastos comunes", _verbose=self.verbose)
            return None

        except Exception as exc:
            _printv(f"    ⚠️  Error obteniendo gastos comunes: {exc}", _verbose=self.verbose)
            return None

    def _tiene_palabras_excluidas(self, texto: str) -> bool:
        texto = texto.lower()
        return any(p in texto for p in self._palabras_excluir)

    # --------------------------------------------------------------
    # mini‑helpers para el extractor
    # --------------------------------------------------------------

    @staticmethod
    def _pick_first(node, selectors, *, attr: str | None = None) -> str:
        """Devuelve el primer texto o atributo no vacío encontrado."""
        for sel in selectors:
            tag = node.select_one(sel)
            if not tag:
                continue
            if attr:
                val = tag.get(attr, "").strip()
                if val:
                    return val
            else:
                txt = tag.get_text(" ", strip=True)
                if txt:
                    return txt
        return ""

    @staticmethod
    def _slug_from_url(url: str) -> str:
        slug = url.split("/")[-1].split("_", 1)[0].replace("-", " ")
        return slug

    # --------------------------------------------------------------
    # scraping de N páginas para un barrio específico
    # --------------------------------------------------------------

    def buscar_en_barrio(self, barrio: str) -> List[Dict[str, Any]]:
        """Busca apartamentos en un barrio específico."""
        filtro_fecha = "_PublishedToday_YES" if self.url_config.get('ultimas24hrs', False) else ""

        url_base = self.URL_TEMPLATE.format(
            numero_dormitorios=self.url_config['numero_dormitorios'],
            departamento=self.url_config['departamento'],
            query_barrio=barrio,
            precio_minimo=self.url_config['precio_minimo'],
            precio_maximo=self.url_config['precio_maximo'],
            filtro_fecha=filtro_fecha
        )
        _printv(f"🏘️  Buscando en barrio: {barrio}", _verbose=self.verbose)

        resultados = self.buscar_en_url(url_base, barrio)
        _printv(f"   ✅ {len(resultados)} apartamentos encontrados en {barrio}", _verbose=self.verbose)

        return resultados

    def buscar_en_url(self, url_base: str, barrio: str) -> List[Dict[str, Any]]:
        """Itera paginación ML y devuelve la lista de resultados válidos."""
        resultados: List[Dict[str, Any]] = []

        for pagina in range(1, self.max_paginas + 1):
            _printv(f"📄 Página {pagina} - {barrio}…", _verbose=self.verbose)
            self._actualizar_headers()

            # ML usa offset en la *ruta* (no query‑string)
            url = url_base if pagina == 1 else f"{url_base}_Desde_{(pagina-1)*50}"
            _printv(f"   🌐 URL   : {url}", _verbose=self.verbose)

            # -------- request con reintentos básicos --------
            response: Optional[requests.Response] = None
            for intento in range(3):
                try:
                    response = self.session.get(url, timeout=30)
                    if response.status_code == 200:
                        break
                    if response.status_code == 429:
                        _printv("   ⏳ 429 → pause 15 s", _verbose=self.verbose)
                        time.sleep(15)
                    elif response.status_code in {403, 404}:
                        _printv(f"   🚫 {response.status_code} → rompo", _verbose=self.verbose)
                        return resultados
                    else:
                        _printv(f"   ⚠️  status {response.status_code}", _verbose=self.verbose)
                        time.sleep(5)
                except requests.RequestException as exc:
                    _printv(f"   🔄 intento {intento+1}/3 fail: {exc}", _verbose=self.verbose)
                    time.sleep(5)

            if not response or response.status_code != 200:
                _printv("   ❌ sin respuesta 200", _verbose=self.verbose)
                break

            if len(response.content) < 1000:
                _printv("   ⚠️  respuesta muy pequeña (posible bloqueo)", _verbose=self.verbose)
                break

            # ------------- parseo ------------
            nuevos = self._parsear_pagina_ml(response.content, barrio)
            _printv(f"   ✅ {len(nuevos)} aptos en página", _verbose=self.verbose)
            resultados.extend(nuevos)

            if not nuevos:
                break  # sin más resultados

            time.sleep(random.uniform(5, 8))  # para no abusar

        return resultados

    # --------------------------------------------------------------
    # parseo HTML de una página
    # --------------------------------------------------------------

    def _parsear_pagina_ml(self, html: bytes, barrio: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")

        # selector prioritario → menos ruido
        contenedores = soup.select("li.ui-search-layout__item, .ui-search-result")
        if self.verbose:
            _printv(f"   🎯 {len(contenedores)} contenedores", _verbose=True)

        apartamentos: List[Dict[str, Any]] = []
        for cont in contenedores:
            apt = self._extraer_apartamento_ml(cont, barrio)
            if apt and self._cumple_criterios_ml(apt):
                # Guardar como visitado
                self._guardar_apartamento_visitado(apt.get("url", ""))
                apartamentos.append(apt)
        return apartamentos

    # --------------------------------------------------------------
    # extracción individual (robusta)
    # --------------------------------------------------------------

    def _extraer_apartamento_ml(self, cont, barrio: str) -> Optional[Dict[str, Any]]:
        try:
            # ------------ URL ------------
            url = self._pick_first(cont, ["a.ui-search-link", "a"], attr="href").split("#")[0]

            # ------------ título ------------
            titulo = self._pick_first(
                cont,
                [
                    "h2.ui-search-item__title",
                    "div.ui-search-item__highlight-label",
                    "a.ui-search-link[title]",
                    "h2.ui-search-item__group__element",
                ],
            )
            if not titulo:
                titulo = self._slug_from_url(url)

            # ------------ precio ------------
            frac = cont.select_one("span.andes-money-amount__fraction")
            cents = cont.select_one("span.andes-money-amount__cents")
            if frac:
                precio_alquiler = frac.text + ("," + cents.text if cents else "")
            else:
                precio_alquiler = self._pick_first(
                    cont,
                    [
                        "span.price-tag-fraction",
                        "span.ui-search-price__part--second-line",
                    ],
                )

            # ------------ ubicación ------------
            ubicacion = self._pick_first(
                cont,
                [
                    "span.ui-search-item__location",
                    "span.ui-search-item__location-label",
                ],
            )

            # ------------ dormitorios & área ------------
            texto = cont.get_text(" ", strip=True).lower()
            dormitorios = int(m.group(1)) if (m := self._RE_DORM.search(texto)) else None
            area = f"{m.group(1)} m2" if (m := self._RE_AREA.search(texto)) else ""

            # ------------ gastos comunes (desde página individual) ------------
            gastos_comunes = None
            if self.obtener_gastos_comunes and url:
                gastos_comunes = self._extraer_gastos_comunes_desde_pagina(url)
                # Pausa entre requests a páginas individuales
                time.sleep(random.uniform(2, 4))

            # ------------ calcular precio total ------------
            def parse_miles(valor):
                """Convierte un string con separador de miles o un int a entero."""
                if valor is None:
                    return 0
                return int(str(valor).replace('.', ''))

            def format_miles(numero):
                """Formatea un entero con punto como separador de miles."""
                return f"{numero:,}".replace(',', '.')

            # Mantener precio_total como número para comparaciones
            precio_total_numerico = None
            precio_total_formateado = None

            if precio_alquiler is not None:
                precio_total_numerico = parse_miles(precio_alquiler)
                if gastos_comunes is not None:
                    precio_total_numerico += parse_miles(gastos_comunes)

                # Solo formatear cuando necesites mostrar el valor
                precio_total_formateado = format_miles(precio_total_numerico)

            return {
                "titulo": titulo,
                "precio_alquiler": precio_alquiler,
                "query_barrio": barrio,
                "precio_total_formatted": precio_total_formateado,
                "ubicacion": ubicacion,
                "dormitorios": dormitorios,
                "area": area,
                "gastos_comunes": gastos_comunes,
                "url": url,
            }
        except Exception as exc:
            _printv(f"   ⚠️  error extraer: {exc}", _verbose=self.verbose)
            return None

    # --------------------------------------------------------------
    # filtros
    # --------------------------------------------------------------

    def _cumple_criterios_ml(self, apt: Dict[str, Any]) -> bool:
        if self._tiene_palabras_excluidas(apt["titulo"]):
            return False
        if apt.get("precio_total") and apt["precio_total"] > self.max_precio:
            return False
        if self.dormitorios and apt.get("dormitorios") and apt["dormitorios"] != self.dormitorios:
            return False
        if not self._es_apartamento_nuevo(apt.get("url", "")):
            return False
        return True

    # --------------------------------------------------------------
    # interfaz principal - buscar en todos los barrios
    # --------------------------------------------------------------

    def buscar(self) -> List[Dict[str, Any]]:
        """Busca apartamentos en todos los barrios definidos."""
        todos_resultados: List[Dict[str, Any]] = []

        for barrio_key, barrio_value in self.BARRIOS.items():
            _printv(f"\n🔍 Iniciando búsqueda en {barrio_key}...", _verbose=self.verbose)

            try:
                resultados_barrio = self.buscar_en_barrio(barrio_value)
                todos_resultados.extend(resultados_barrio)

                # Pausa entre barrios para no sobrecargar el servidor
                if barrio_key != list(self.BARRIOS.keys())[-1]:  # No pausar después del último
                    _printv(f"⏳ Pausa entre barrios...", _verbose=self.verbose)
                    time.sleep(random.uniform(10, 15))

            except Exception as exc:
                _printv(f"❌ Error en barrio {barrio_key}: {exc}", _verbose=self.verbose)
                continue

        _printv(f"\n🎉 Total de apartamentos encontrados: {len(todos_resultados)}", _verbose=self.verbose)
        return todos_resultados

    # --------------------------------------------------------------
    # método para buscar en un barrio específico (opcional)
    # --------------------------------------------------------------

    def buscar_barrio_especifico(self, barrio: str) -> List[Dict[str, Any]]:
        """Busca apartamentos en un barrio específico."""
        if barrio not in self.BARRIOS:
            _printv(f"❌ Barrio '{barrio}' no está en la lista de barrios válidos", _verbose=self.verbose)
            _printv(f"Barrios válidos: {list(self.BARRIOS.keys())}", _verbose=self.verbose)
            return []

        return self.buscar_en_barrio(self.BARRIOS[barrio])

###############################################################################
# entry‑point CLI
###############################################################################

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scraper MercadoLibre → JSON Lines (sin base de datos)"
    )
    parser.add_argument("--verbose", action="store_true", help="Logs detallados")
    parser.add_argument("--barrio", type=str, help="Buscar solo en un barrio específico")
    parser.add_argument("--config", type=str, default="config.json",
                       help="Archivo de configuración de barrios (default: config.json)")
    parser.add_argument("--limpiar-historial", action="store_true",
                       help="Limpiar historial de apartamentos visitados")
    parser.add_argument("--sin-filtro-duplicados", action="store_true",
                       help="Deshabilitar filtro de duplicados para esta ejecución")
    parser.add_argument("--sin-gastos-comunes", action="store_true",
                       help="No obtener gastos comunes (hace el scraping más rápido)")
    args = parser.parse_args()

    # Determinar si obtener gastos comunes
    obtener_gastos_comunes = not args.sin_gastos_comunes

    buscador = BuscadorMercadoLibre(
        verbose=args.verbose,
        config_file=args.config,
        obtener_gastos_comunes=obtener_gastos_comunes
    )

    # Limpiar historial si se solicita
    if args.limpiar_historial:
        archivo = buscador.duplicados_config.get('archivo_visitados', 'apartamentos_visitados.txt')
        try:
            if os.path.exists(archivo):
                os.remove(archivo)
                print(f"✅ Historial limpiado: {archivo}")
            else:
                print(f"ℹ️  No hay historial que limpiar: {archivo}")
        except Exception as e:
            print(f"❌ Error limpiando historial: {e}")
        return

    # Deshabilitar filtro de duplicados si se solicita
    if args.sin_filtro_duplicados:
        buscador.duplicados_config['filtrar_duplicados'] = False
        buscador.apartamentos_visitados = set()

    if args.barrio:
        # Buscar en un barrio específico
        apartamentos = buscador.buscar_barrio_especifico(args.barrio)
    else:
        # Buscar en todos los barrios
        apartamentos = buscador.buscar()

    for apt in apartamentos:
        sys.stdout.write(json.dumps(apt, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()