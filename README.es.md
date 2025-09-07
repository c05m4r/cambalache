# Cambalache JSON Modifier

Herramienta de línea de comandos que genera múltiples objetos JSON a partir de una plantilla JSON y una lista de palabras. Permite modificar campos específicos dentro de json_data, ya sea reemplazando sus valores, añadiendo las palabras como prefijos y/o sufijos, o generando valores secuenciales.

## Preparación del entorno

### Instalar uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc
```

### Instalar dependencias

```bash
uv sync
```

## Uso Básico

```bash
uv run cambalache.py [OPCIONES] plantilla.json palabras.txt salida.json
```

  * `plantilla.json`: Tu archivo JSON base (se usa el primer objeto).
  * `palabras.txt`: Archivo con una palabra por línea (se ignora en modo generador).
  * `salida.json`: Nombre del archivo JSON resultante.

-----

## Ejemplos

Para los ejemplos, usaremos estos archivos de entrada:

**`plantilla.json`:**

```json
[
  {
    "testid": "tc101",
    "descripcion": "testcase",
    "json_data": {
      "email": "example@gmail.com",
      "username": "testuser",
      "ciudad": "Lucinico"
    }
  }
]
```

**`palabras.txt`:**

```
user1
admin
test_ palabra
```

-----

### Modo Reemplazo (Default - Sobrescribe valores)

**1. Reemplazar TODOS los campos dentro de `json_data`**
(Default: si no especificas `--include` o `--ignore`)

```bash
uv run cambalache.py plantilla.json palabras.txt salida_reemplazo_todo.json
```

*Resultado: 3 objetos. En el primero, `email`, `username` y `ciudad` valdrán "user1". En el segundo, valdrán "admin", etc.*

**2. Reemplazar SÓLO el campo `email`**

```bash
uv run cambalache.py plantilla.json palabras.txt salida_reemplazo_email.json --include email
```

*Resultado: 3 objetos. `email` será "user1", "admin", "test\_ palabra". `username` y `ciudad` se mantienen originales.*

**3. Reemplazar TODOS EXCEPTO el campo `ciudad`**

```bash
uv run cambalache.py plantilla.json palabras.txt salida_reemplazo_sin_ciudad.json --ignore ciudad
```

*Resultado: 3 objetos. `email` y `username` serán reemplazados por "user1", "admin", etc. `ciudad` se mantiene original ("Lucinico").*

-----

### Modo Generación (Crea NUEVOS objetos con prefijos/sufijos)

**4. Generar añadiendo como PREFIJO a TODOS los campos**

```bash
uv run cambalache.py plantilla.json palabras.txt salida_gen_prefijo.json --prefix
```

*Resultado: 9 objetos (3 palabras x 3 campos). Tendrás objetos donde `email` es "[dirección de correo electrónico eliminada]", otros donde `username` es "user1usuario\_original", otros donde `ciudad` es "user1Lucinico", y así para "admin" y "test\_ palabra".*

**5. Generar añadiendo como SUFIJO a TODOS los campos**

```bash
uv run cambalache.py plantilla.json palabras.txt salida_gen_sufijo.json --suffix
```

*Resultado: 9 objetos. Tendrás `email` como "example@gmail.comuser1", `username` como "usuario\_originaluser1", `ciudad` como "Lucinicouser1", etc.*

**6. Generar objetos con PREFIJO y SUFIJO (separados) para TODOS los campos**

```bash
uv run cambalache.py plantilla.json palabras.txt salida_gen_both.json --both
```

*Resultado: 18 objetos (3 palabras x 3 campos x 2 [prefijo y sufijo]). Por cada palabra/campo, genera un objeto con prefijo y otro con sufijo. Ej: uno con `email`="[dirección de correo electrónico eliminada]" y otro con `email`="example@gmail.comuser1".*

-----

### Combinando Modos y Selección de Campos

**7. Generar con PREFIJO, pero SÓLO para el campo `username`**

```bash
uv run cambalache.py plantilla.json palabras.txt salida_gen_prefijo_nombre.json --prefix --include username
```

*Resultado: 3 objetos. Solo el campo `username` se modifica (ej. "user1usuario\_original"), los demás quedan como en la plantilla.*

**8. Generar con SUFIJO, ignorando `email` y `ciudad` (o sea, SÓLO `username`)**

```bash
uv run cambalache.py plantilla.json palabras.txt salida_gen_sufijo_no_email_ciudad.json --suffix --ignore email ciudad
```

*Resultado: 3 objetos. Solo `username` se modifica con sufijo (ej. "usuario\_originaluser1").*

**9. Generar con PREFIJO y SUFIJO (separados), SÓLO para `email` y `ciudad`**

```bash
uv run cambalache.py plantilla.json palabras.txt salida_gen_both_email_ciudad.json --both --include email ciudad
```

*Resultado: 12 objetos (3 palabras x 2 campos x 2 [prefijo/sufijo]). Objetos modificados solo en `email` o `ciudad`, tanto con prefijo como con sufijo.*

-----

### Modo Generador (Crea valores secuenciales)

**10. Generar valores secuenciales para un campo específico**

```bash
uv run cambalache.py plantilla.json dummy.txt salida.json --gen username
```

*Resultado: 10 objetos (por defecto). El campo `username` tendrá valores secuenciales como "testuser1", "testuser2", "testuser3", etc., basados en el valor original de la plantilla. Los demás campos permanecen sin cambios.*

**Ejemplo con una plantilla de usuario:**

Si tu plantilla tiene:
```json
{
  "json_data": {
    "identificador": "usuario_example",
    "email": "usuario_example@siu.edu.ar",
    "password": "abc123456"
  }
}
```

Ejecutando:
```bash
uv run cambalache.py usuarios.json dummy.txt usuarios_generados.json --gen identificador
```

Generará objetos con:
- `identificador`: "usuario_example1", "usuario_example2", "usuario_example3", ...
- `email` y `password` permanecen como en la plantilla original

**Nota:** En modo generador (`--gen`), el archivo de palabras es requerido pero se ignora. Puedes usar cualquier archivo dummy como segundo argumento.

-----

## Opciones Disponibles

```bash
uv run cambalache.py --help
```

### Argumentos:
- `TEMPLATE_PATH`: Ruta al archivo de plantilla JSON (requerido)
- `WORDLIST_PATH`: Ruta al archivo de lista de palabras (requerido, pero ignorado en modo `--gen`)
- `OUTPUT_PATH`: Ruta al archivo JSON de salida (requerido)

### Opciones:
- `--include -i`: Especificar qué campos en json_data modificar exclusivamente
- `--ignore -x`: Especificar qué campos en json_data ignorar
- `--prefix`: Modo generación - añadir palabras como prefijo a los valores originales
- `--suffix`: Modo generación - añadir palabras como sufijo a los valores originales
- `--both`: Modo generación - crear objetos con prefijo Y sufijo (objetos separados)
- `--gen`: Modo generador - crear valores secuenciales para el campo especificado (ej: usuario1, usuario2, usuario3...)

**Nota:** Los modos `--prefix`, `--suffix`, `--both` y `--gen` son mutuamente excluyentes.