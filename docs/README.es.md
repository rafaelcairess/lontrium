<p align="center">
  <img src="images/lontrium-logo.png" alt="Lontrium Control" width="128" height="128">
</p>

<h1 align="center">Lontrium Control</h1>

<p align="center">
  <strong>Tus juegos gratuitos y recompensas diarias en un panel local y privado.</strong><br>
  Instálalo una vez, elige tus tiendas y deja que Lontrium Control se ocupe de la rutina.
</p>

<p align="center">
  <a href="../LICENSE"><img alt="Licencia AGPL-3.0" src="https://img.shields.io/github/license/rafaelcairess/lontrium?style=for-the-badge"></a>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white">
  <img alt="Docker Compose" src="https://img.shields.io/badge/Docker%20Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white">
</p>

<p align="center">
  <a href="../README.md">English</a> ·
  <a href="./README.pt-BR.md">Português do Brasil</a> ·
  <a href="./README.es.md">Español</a>
</p>

<p align="center">
  <a href="https://github.com/rafaelcairess/lontrium/releases/latest/download/Lontrium-Setup.exe"><strong>Descargar Lontrium Control para Windows</strong></a>
</p>

> [!NOTE]
> **Lontrium Control v1.2.1 ya está disponible.** Descarga el instalador de arriba y verifícalo con [`SHA256SUMS.txt`](https://github.com/rafaelcairess/lontrium/releases/latest/download/SHA256SUMS.txt).

<p align="center">
  <img src="images/05-dashboard.png" alt="Panel de Lontrium Control con resultados de juegos, AliExpress y Shopee" width="1100">
</p>

## Qué hace

- Reclama juegos, recursos y recompensas elegibles en las tiendas seleccionadas.
- Recoge monedas diarias de AliExpress y Shopee y muestra el resultado y el saldo.
- Informa el resultado real de cada ejecución, no solo una cantidad genérica.
- Funciona con un horario y puede iniciarse automáticamente con Windows.
- Abre un navegador visual cuando una tienda requiere inicio de sesión o confirmación manual.
- Mantiene el panel, la configuración, la base de datos y las sesiones en tu computadora.
- Conserva durante 90 días un historial saneado que permanece tras reinicios y actualizaciones.

## Servicios compatibles

| Juegos y recursos | Recompensas y descubrimiento |
|---|---|
| Epic Games, Steam, GOG, Prime Gaming, Ubisoft, Fab y Unity Asset Store | Monedas diarias de AliExpress y Shopee, más promociones de GamerPower |

GamerPower también puede enviar promociones compatibles de Fanatical, itch.io e IndieGala. La disponibilidad y los requisitos de acceso dependen de cada tienda.

> [!IMPORTANT]
> **Shopee requiere un primer inicio manual mediante _Continuar con Google_.** En la prueba real, la seguridad de Shopee rechazó el acceso directo dentro del navegador Docker, pero el acceso con Google funcionó. Lontrium no intenta eludir esa protección; después, el perfil persistente local reutiliza la sesión.

## Instálalo en tres pasos

1. Descarga `Lontrium-Setup.exe` desde la [Release más reciente](https://github.com/rafaelcairess/lontrium/releases).
2. Ejecuta el instalador. Si falta Docker Desktop, el launcher explica por qué es necesario y solo lo instala desde la fuente oficial después de tu confirmación.
3. Sigue el asistente local. Recomienda iniciar sesión en el navegador, muestra solo las opciones de las tiendas elegidas y ofrece rutinas sencillas de automatización.

Eso es todo. No necesitas clonar el repositorio, editar archivos de configuración ni escribir comandos de Docker.

> [!TIP]
> **No necesitas entregar tus contraseñas a Lontrium.** En todas las tiendas compatibles que requieren una cuenta, elige el inicio de sesión en el navegador y entra directamente en el sitio oficial. Lontrium guarda la sesión resultante en el volumen Docker local y la reutiliza hasta que la tienda vuelva a solicitar autenticación.

El instalador puede solicitar permisos de administrador o reiniciar Windows mientras instala Docker Desktop. Como el primer instalador no estará firmado, Windows SmartScreen puede mostrar un aviso de editor desconocido. Cada Release incluye `SHA256SUMS.txt` para comprobar la descarga.

## Primera configuración

El asistente presenta seis decisiones prácticas sin exigir conocimientos de variables de entorno:

1. **Idioma** — detectado desde Windows/navegador, con inglés, portugués de Brasil y español.
2. **Tiendas** — solo las seleccionadas aparecen en el panel y participan en las ejecuciones.
3. **Inicio de sesión** — el navegador es la opción recomendada; guardar credenciales localmente es opcional.
4. **Cuentas** — con el navegador no se solicita ninguna contraseña. En el otro modo solo aparecen campos de las tiendas elegidas.
5. **Automatización** — elige ejecutar al iniciar Lontrium y a diario, solo a diario o solo manualmente.
6. **Revisión** — confirma dónde quedan los datos y explica el siguiente paso.

Después de **Finalizar y ejecutar**, el panel abre las tiendas elegidas. Cuando una necesite autenticación, abre **Navegador** e inicia sesión en el sitio oficial. El perfil persistente reutiliza la sesión hasta que la propia tienda la caduque.

Puedes volver a ver toda la introducción desde **Configuración → Introducción**. Se abre en modo de vista previa y no sobrescribe ajustes ni inicia una ejecución.

## Cómo funciona

```text
Acceso directo → Docker Desktop → contenedor local
                                    ├─ panel en 127.0.0.1:8080
                                    ├─ navegador visual en 127.0.0.1:7080
                                    ├─ módulos de tiendas seleccionadas
                                    └─ volumen local persistente
                                       (configuración, sesiones e historial)
```

Cada módulo abre el sitio oficial, comprueba la oferta o recompensa y guarda un resultado estructurado. Los juegos muestran título y resultado; AliExpress y Shopee muestran monedas y los datos de saldo o racha disponibles. CAPTCHA, antifraude y verificaciones de cuenta vuelven al usuario en el navegador visual y nunca se eluden.

## Tus datos permanecen en tu computadora

Lontrium Control no tiene un servidor de cuentas ni incluye telemetría.

| Qué sucede | Dónde sucede |
|---|---|
| Panel y configuración | En `127.0.0.1`, disponible solamente desde esta computadora |
| Credenciales y sesiones | En el volumen Docker local |
| Historial sanitizado de ejecuciones | En la base SQLite local durante 90 días |
| Inicio de sesión en tiendas | Directamente entre el navegador automatizado y el sitio oficial de la tienda |
| Respuesta de la API sobre secretos | Solo `configured: true/false`; la contraseña nunca vuelve al panel |
| Actualizaciones | Se consultan en las Releases oficiales de este proyecto en GitHub |

Las credenciales son opcionales y el acceso manual mediante el navegador siempre está disponible. Los secretos locales no están protegidos por un servidor externo de cifrado; protege tu cuenta de Windows y el disco. Lontrium Control no intenta eludir CAPTCHA, sistemas antifraude ni desafíos de seguridad.

## Diseñado para ser claro

Solo las tiendas habilitadas aparecen en el panel. Cada fila explica qué ocurrió: qué juego fue reclamado, cuál ya estaba en la biblioteca, si no había promoción o cuántas monedas de AliExpress o Shopee fueron recogidas.

### Configuración guiada

<p align="center">
  <img src="images/04-credentials.png" alt="Campo de credenciales con explicación de privacidad" width="1000">
</p>

### Detalles de monedas de AliExpress

<p align="center">
  <img src="images/06-aliexpress.png" alt="Monedas diarias, saldo y racha de AliExpress" width="1000">
</p>

El inicio de sesión en el navegador es la opción recomendada, por lo que el asistente no solicita contraseñas sin una elección explícita. Cada credencial tiene una explicación accesible en el botón `?`. La interfaz funciona con ratón, teclado y toque, y está completamente traducida al inglés, portugués de Brasil y español.

## Uso diario

- Abre **Lontrium Control** desde el menú Inicio o el acceso directo del escritorio.
- Usa **Ejecutar ahora** para todas las tiendas o ejecuta una tienda individualmente.
- Usa **Navegador** cuando una tienda solicite acceso, CAPTCHA o confirmación manual.
- Usa **Configuración** para cambiar tiendas, cuentas, notificaciones y horarios.
- Las actualizaciones se ofrecen en el panel y conservan el volumen local.

Al actualizar una instalación antigua, el launcher puede preguntar si debe reutilizar cuentas y sesiones existentes. Elige **Sí**, salvo que quieras un perfil limpio. Se sustituye el contenedor, pero se conserva el volumen persistente seleccionado.

El acceso directo normal comprueba Docker, inicia el servicio, espera al panel y lo abre automáticamente. Para el inicio con Windows, el instalador ofrece el modo económico (predeterminado), que espera la ejecución y libera la memoria WSL de Docker, o el modo panel, que mantiene disponible el panel local. Al desinstalar Lontrium Control se conservan las cuentas y sesiones por defecto; borrar los datos locales es una opción separada y explícita. Docker Desktop nunca se elimina automáticamente.

## ¿Necesitas ayuda?

| Problema | Qué puedes intentar |
|---|---|
| El panel no se abrió | Abre [http://127.0.0.1:8080](http://127.0.0.1:8080) y confirma que Docker Desktop está en ejecución. |
| Una tienda necesita atención | Abre el navegador visual desde el panel y completa la solicitud oficial de la tienda. |
| Una sesión caducó | Inicia sesión otra vez mediante el navegador visual; la sesión actualizada se conservará localmente. |
| Un reclamo falló | Vuelve a ejecutar únicamente esa tienda y adjunta el fragmento relevante del registro sanitizado al abrir una issue. |

Para informar errores o sugerir funciones, usa las [Issues de GitHub](https://github.com/rafaelcairess/lontrium/issues). Nunca publiques contraseñas, cookies, claves TOTP, capturas completas de red ni imágenes sin sanitizar.

## Para contribuidores

El instalador es el camino recomendado para usuarios. Las compilaciones desde el código fuente, la arquitectura y las variables internas son temas de desarrollo:

- [`.env.example`](../.env.example) — referencia completa para compilaciones desde el código fuente
- [`MODIFICATIONS.md`](../MODIFICATIONS.md) — historial de implementación y diferencias técnicas
- [`CHANGELOG.md`](../CHANGELOG.md) — cambios de cada versión

Las pruebas cubren los módulos de tiendas, la API local, la protección de secretos, las traducciones, la configuración inicial y el launcher de Windows.

## Créditos y licencia

**Interfaz y distribución para Windows de Lontrium Control:** [Rafael Caires](https://github.com/rafaelcairess).

Construido sobre [P-Adamiec/Free-Games-Claimer-Remaster](https://github.com/P-Adamiec/Free-Games-Claimer-Remaster), mantenido por Paweł Adamiec y sus contribuidores. Ese proyecto fue inspirado por [vogler/free-games-claimer](https://github.com/vogler/free-games-claimer). Los avisos de terceros se encuentran en [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).

Distribuido bajo la [GNU Affero General Public License v3.0](../LICENSE).
